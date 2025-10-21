# Security Code Review - patch-mcp v3.0.0

**Review Date**: 2025-10-19
**Reviewer**: Security Analysis
**Scope**: All Python source code in src/patch_mcp/
**Methodology**: OWASP Top 10 + CWE Analysis (14-step comprehensive review)

---

## Executive Summary

**Overall Security Rating: B+ (Good)**

The patch-mcp project demonstrates a strong security-conscious design with multiple defense-in-depth layers. The codebase is safe for personal and development use. However, production enterprise deployment would benefit from implementing the recommended hardening measures.

### Key Strengths
- ✅ Comprehensive input validation (symlinks, binary files, size limits)
- ✅ Atomic file operations preventing partial writes
- ✅ Strict type safety with mypy
- ✅ No SQL/command injection vectors (no shell commands or SQL)
- ✅ Secure temporary file handling with mkstemp()
- ✅ Information disclosure protection via error sanitization

### Critical Findings
- ⚠️ **MEDIUM**: Path traversal vulnerability (CWE-22) - No directory whitelist
- ⚠️ **MEDIUM**: TOCTOU race condition (CWE-367) in update_content
- ℹ️ **LOW**: Missing audit logging for security events
- ℹ️ **LOW**: Broad exception handling patterns
- ℹ️ **LOW**: Dependencies not pinned to exact versions

---

## Detailed Findings

### 1. Path Traversal Vulnerability (MEDIUM)

**CWE-22: Improper Limitation of a Pathname to a Restricted Directory**

**Location**: `src/patch_mcp/utils.py` - `validate_file_safety()`

**Vulnerability**:
The current implementation validates individual file safety (symlinks, binary files, size) but does NOT validate that the file path is within an allowed directory tree. An attacker could potentially access files outside the intended working directory.

**Attack Scenario**:
```python
# Malicious MCP client could request:
apply_patch("../../../../etc/passwd", malicious_patch)
backup_file("../../../home/user/.ssh/id_rsa")
```

**Current Code** (utils.py:21-115):
```python
def validate_file_safety(
    file_path: Path, check_write: bool = False, check_space: bool = False
) -> Optional[Dict[str, Any]]:
    # Checks file exists, is regular file, not symlink, not binary, size limits
    # BUT: No check for path traversal (../../etc/passwd)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}", "error_type": "file_not_found"}
    # ... other checks ...
```

**Remediation**:

Add path validation to ensure files are within an allowed base directory:

```python
def validate_path_within_base(file_path: Path, base_dir: Path) -> Optional[Dict[str, Any]]:
    """Validate that file_path is within base_dir (prevents path traversal).

    Args:
        file_path: Path to validate
        base_dir: Base directory that file must be within

    Returns:
        None if valid, error dict if path traversal detected
    """
    try:
        # Resolve to absolute paths (handles symlinks, .., .)
        abs_file = file_path.resolve()
        abs_base = base_dir.resolve()

        # Check if file is within base directory
        try:
            abs_file.relative_to(abs_base)
        except ValueError:
            return {
                "error": f"Path traversal detected: {file_path} is outside allowed directory",
                "error_type": "path_traversal",
            }

        return None
    except Exception as e:
        return {
            "error": f"Path validation failed: {str(e)}",
            "error_type": "path_error",
        }

# Update validate_file_safety to include path check:
def validate_file_safety(
    file_path: Path,
    check_write: bool = False,
    check_space: bool = False,
    base_dir: Optional[Path] = None  # NEW: Add base directory validation
) -> Optional[Dict[str, Any]]:
    """Comprehensive file safety validation."""

    # NEW: Path traversal check (if base_dir provided)
    if base_dir is not None:
        path_error = validate_path_within_base(file_path, base_dir)
        if path_error:
            return path_error

    # ... rest of existing checks ...
```

**Deployment Recommendation**:
- For personal use: Current behavior acceptable (user controls all inputs)
- For enterprise/multi-tenant: Implement whitelist with environment variable `PATCH_MCP_BASE_DIR`

---

### 2. TOCTOU Race Condition (MEDIUM)

**CWE-367: Time-of-Check Time-of-Use (TOCTOU) Race Condition**

**Location**: `src/patch_mcp/tools/update.py:120-198`

**Vulnerability**:
The `update_content()` function has a race condition window between verifying the original content matches (line 120) and writing the new content (line 194). A concurrent process could modify the file during this window.

**Attack Scenario**:
```
Time T0: LLM reads file (content = "version=1.0")
Time T1: update_content() verifies current content matches original
Time T2: Concurrent process writes file (content = "version=2.0")  ← RACE WINDOW
Time T3: update_content() writes new content (overwrites v2.0 with v1.1)
Result: Lost update - version 2.0 changes silently discarded
```

**Current Code** (update.py:119-198):
```python
# Step 3: Verify original_content matches current file
if current_content != original_content:
    return {"success": False, "error": "Content mismatch"}

# ... time passes - file could be modified here ...

# Step 5b: Apply changes atomically
try:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    atomic_file_replace(temp_path, path)
```

**Remediation**:

Implement file locking to prevent concurrent modifications:

```python
import fcntl  # Add to imports

def update_content(
    file_path: str, original_content: str, new_content: str, dry_run: bool = False
) -> Dict[str, Any]:
    """Update file content with safety verification and diff generation."""
    path = Path(file_path)

    # Step 1: Security validation
    safety_error = validate_file_safety(path, check_write=True, check_space=True)
    if safety_error:
        return {"success": False, **safety_error}

    # Step 2-5: Read, verify, generate diff, apply with FILE LOCKING
    try:
        with open(path, "r+", encoding="utf-8") as f:
            # ACQUIRE EXCLUSIVE LOCK (blocks other writers)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            try:
                # Step 2: Read current content (under lock)
                current_content = f.read()

                # Step 3: Verify match (under lock)
                if current_content != original_content:
                    # Generate diff showing mismatch
                    expected_lines = original_content.splitlines(keepends=True)
                    actual_lines = current_content.splitlines(keepends=True)
                    diff_lines = list(
                        difflib.unified_diff(
                            expected_lines, actual_lines,
                            fromfile="expected", tofile="actual", n=3
                        )
                    )
                    actual_diff = "".join(diff_lines) if diff_lines else "(content differs)"

                    return {
                        "success": False,
                        "error": "File content does not match expected original content",
                        "error_type": "content_mismatch",
                        "diff_from_expected": actual_diff,
                        "message": "File has been modified since you read it. Re-read and try again.",
                    }

                # Step 4: Generate unified diff
                original_lines = original_content.splitlines(keepends=True)
                new_lines = new_content.splitlines(keepends=True)
                diff_lines = list(
                    difflib.unified_diff(
                        original_lines, new_lines,
                        fromfile=path.name, tofile=path.name, n=3
                    )
                )

                if not diff_lines:
                    return {
                        "success": True,
                        "applied": False,
                        "file_path": str(path),
                        "diff": "",
                        "changes": {"lines_added": 0, "lines_removed": 0, "hunks": 0},
                        "message": "No changes needed - content is identical",
                    }

                patch = "".join(diff_lines)
                lines_added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
                lines_removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
                hunks = sum(1 for line in diff_lines if line.startswith("@@"))

                # Step 5a: Dry run
                if dry_run:
                    return {
                        "success": True,
                        "applied": False,
                        "file_path": str(path),
                        "diff": patch,
                        "changes": {
                            "lines_added": lines_added,
                            "lines_removed": lines_removed,
                            "hunks": hunks,
                        },
                        "message": f"Dry run: would modify {hunks} section(s) (+{lines_added}/-{lines_removed} lines)",
                    }

                # Step 5b: Apply changes (still under lock)
                temp_path = path.with_suffix(path.suffix + ".tmp")
                with open(temp_path, "w", encoding="utf-8") as temp_f:
                    temp_f.write(new_content)

                # Atomic replace (lock prevents concurrent access)
                atomic_file_replace(temp_path, path)

                return {
                    "success": True,
                    "applied": True,
                    "file_path": str(path),
                    "diff": patch,
                    "changes": {
                        "lines_added": lines_added,
                        "lines_removed": lines_removed,
                        "hunks": hunks,
                    },
                    "message": f"Successfully updated {path.name} (+{lines_added}/-{lines_removed} lines)",
                }

            finally:
                # RELEASE LOCK (automatic on file close, but explicit is better)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Cannot decode file as UTF-8: {str(e)}",
            "error_type": "encoding_error",
            "message": "File encoding is not UTF-8",
        }
    except OSError as e:
        # Clean up temp file if it exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass
        return {
            "success": False,
            "error": f"Failed to write file: {str(e)}",
            "error_type": "io_error",
            "message": f"Could not update {path.name}",
        }
```

**Note**: File locking behavior varies by OS:
- **Linux/Unix**: Advisory locks (processes must cooperate)
- **Windows**: May need different locking mechanism (msvcrt.locking)
- Consider cross-platform locking library like `portalocker` for production use

---

### 3. Missing Audit Logging (LOW)

**Location**: All tool implementations

**Issue**:
Security-relevant events (file modifications, validation failures, permission errors) are not logged. This makes incident investigation and security monitoring difficult.

**Recommendation**:

Add structured audit logging:

```python
import logging
from typing import Any, Dict

# Configure security audit logger
security_logger = logging.getLogger("patch_mcp.security")
security_logger.setLevel(logging.INFO)

def audit_log(event_type: str, details: Dict[str, Any], success: bool = True) -> None:
    """Log security-relevant events for audit trail.

    Args:
        event_type: Type of event (e.g., "file_modified", "validation_failed")
        details: Event details (file paths, error types, etc.)
        success: Whether operation succeeded
    """
    log_level = logging.INFO if success else logging.WARNING
    security_logger.log(
        log_level,
        f"AUDIT: {event_type}",
        extra={
            "event_type": event_type,
            "success": success,
            "timestamp": time.time(),
            **details,
        },
    )

# Usage in tools:
def apply_patch(file_path: str, patch: str, dry_run: bool = False) -> Dict[str, Any]:
    """Apply a unified diff patch to a file."""
    path = Path(file_path)

    # ... validation and application ...

    if result["success"]:
        audit_log("patch_applied", {
            "file_path": str(path),
            "dry_run": dry_run,
            "changes": result["changes"],
        })
    else:
        audit_log("patch_failed", {
            "file_path": str(path),
            "error_type": result.get("error_type"),
            "error": result.get("error"),
        }, success=False)

    return result
```

**Events to Log**:
- File modifications (apply_patch, update_content, restore_backup)
- Validation failures (invalid patches, content mismatches)
- Security policy violations (symlinks, binary files, path traversal)
- Permission errors
- Backup operations

---

### 4. Broad Exception Handling (LOW)

**Location**: Multiple files (apply.py:167, update.py:228, backup.py)

**Issue**:
Several functions use broad `except Exception` clauses that could mask unexpected errors:

```python
except Exception as e:
    return {
        "success": False,
        "error": f"Unexpected error: {str(e)}",
        "error_type": "io_error",  # Generic type - loses specificity
    }
```

**Recommendation**:

Use specific exception types and re-raise unexpected exceptions:

```python
# BEFORE (broad)
except Exception as e:
    return {"success": False, "error": str(e), "error_type": "io_error"}

# AFTER (specific)
except (OSError, IOError) as e:
    return {"success": False, "error": str(e), "error_type": "io_error"}
except (UnicodeDecodeError, UnicodeEncodeError) as e:
    return {"success": False, "error": str(e), "error_type": "encoding_error"}
except Exception as e:
    # Log unexpected exceptions for debugging
    logging.exception(f"Unexpected error in apply_patch: {e}")
    # Re-raise or return generic error
    return {
        "success": False,
        "error": "An unexpected error occurred",
        "error_type": "internal_error",
    }
```

**Benefits**:
- Better error classification
- Prevents masking bugs
- Easier debugging
- More informative error messages

---

### 5. Dependency Pinning (LOW)

**Location**: `pyproject.toml:23-26`

**Issue**:
Dependencies use minimum version constraints instead of exact pinning:

```toml
dependencies = [
    "pydantic>=2.0.0",  # Could resolve to 2.0.0, 2.5.0, 3.0.0, etc.
    "mcp>=0.1.0",       # Could resolve to 0.1.0, 0.9.0, 1.0.0, etc.
]
```

**Risk**:
- Supply chain attacks (compromised package update)
- Breaking changes in minor/patch versions
- Inconsistent behavior across environments

**Recommendation**:

Use exact version pinning with hash verification:

```toml
# pyproject.toml - Use lock file
dependencies = [
    "pydantic==2.5.3",  # Exact version
    "mcp==0.9.1",       # Exact version
]

[tool.uv]
# Enable hash verification
locked = true
```

Create a `requirements.txt` with hashes:
```bash
# Generate locked requirements with hashes
uv pip compile pyproject.toml --generate-hashes > requirements.lock

# requirements.lock will contain:
pydantic==2.5.3 \
    --hash=sha256:abc123...
mcp==0.9.1 \
    --hash=sha256:def456...
```

**Deployment**:
```bash
# Install with hash verification
uv pip install -r requirements.lock --require-hashes
```

---

## Security Checklist Results

### ✅ PASSED

1. **Input Validation**: ✅ Comprehensive (symlinks, binary files, size limits, encoding)
2. **Output Encoding**: ✅ UTF-8 encoding enforced, error sanitization implemented
3. **Authentication**: ✅ N/A (local stdio server - by design)
4. **Authorization**: ✅ N/A (single-user local execution)
5. **Cryptography**: ✅ N/A (no crypto operations)
6. **Error Handling**: ✅ Errors sanitized, no stack traces to clients
7. **Data Protection**: ✅ Atomic operations, temp file cleanup
8. **Injection Attacks**: ✅ No SQL/command injection vectors
9. **File Operations**: ✅ Atomic writes, secure temp files
10. **Dependencies**: ✅ Minimal attack surface (2 dependencies)

### ⚠️ NEEDS IMPROVEMENT

11. **Logging**: ⚠️ No audit logging for security events
12. **Configuration**: ⚠️ No path whitelist configuration
13. **Business Logic**: ⚠️ TOCTOU race condition in update_content
14. **Testing**: ⚠️ No security-focused test cases (fuzzing, path traversal tests)

---

## Risk Assessment

### Current Risk Level: LOW-MEDIUM

**Personal/Development Use**: ✅ **LOW RISK** - Safe to use as-is
**Production/Enterprise Use**: ⚠️ **MEDIUM RISK** - Requires hardening

### Risk Factors

| Factor | Current State | Production Requirement |
|--------|---------------|----------------------|
| Path Traversal Protection | None | REQUIRED |
| Concurrent Access Control | Basic (atomic writes) | File locking REQUIRED |
| Audit Logging | None | REQUIRED |
| Dependency Pinning | Loose ranges | Exact versions + hashes REQUIRED |
| Error Handling | Generic exceptions | Specific exceptions RECOMMENDED |

---

## Recommendations by Priority

### Priority 1 (REQUIRED for production)
1. ✅ Implement path traversal protection with directory whitelist
2. ✅ Add file locking to update_content to prevent TOCTOU
3. ✅ Implement comprehensive audit logging

### Priority 2 (RECOMMENDED for production)
4. ✅ Pin dependencies to exact versions with hash verification
5. ✅ Improve exception handling specificity
6. ✅ Add security-focused test cases (fuzzing, path traversal, TOCTOU)

### Priority 3 (NICE TO HAVE)
7. Add rate limiting for tool calls (DoS prevention)
8. Implement file size quotas per session
9. Add backup retention policies

---

## Testing Recommendations

### Security Test Cases to Add

```python
# tests/test_security.py

def test_path_traversal_rejected():
    """Verify path traversal attacks are blocked."""
    malicious_paths = [
        "../../etc/passwd",
        "../../../home/user/.ssh/id_rsa",
        "subdir/../../../../../../etc/shadow",
    ]
    for path in malicious_paths:
        result = apply_patch(path, "dummy patch")
        assert not result["success"]
        assert result["error_type"] == "path_traversal"

def test_toctou_race_condition():
    """Verify concurrent modifications are detected."""
    # Test requires threading to simulate race
    import threading

    def modify_file():
        time.sleep(0.01)  # Simulate race window
        with open(test_file, "w") as f:
            f.write("concurrent modification")

    thread = threading.Thread(target=modify_file)
    thread.start()

    result = update_content(test_file, original, new_content)
    # Should either succeed (lock held) or fail with content_mismatch
    assert result["success"] or result["error_type"] == "content_mismatch"

def test_symlink_rejected():
    """Verify symlinks are rejected (existing test - keep it)."""
    # Already implemented in test_utils.py
    pass

def test_oversized_file_rejected():
    """Verify files exceeding MAX_FILE_SIZE are rejected."""
    # Already implemented - good coverage
    pass
```

---

## Conclusion

The patch-mcp project demonstrates **strong security fundamentals** with defense-in-depth protections against common vulnerabilities. The identified issues are addressable with the provided remediation code.

**Security Posture Summary**:
- ✅ No critical vulnerabilities
- ⚠️ 2 medium-severity issues (path traversal, TOCTOU)
- ℹ️ 3 low-severity improvements (logging, exceptions, dependencies)

**Recommendation**: Safe for personal and development use. Implement Priority 1 fixes before production deployment.

---

**Review Completed**: 2025-10-19
**Next Review Recommended**: After implementing remediation fixes
