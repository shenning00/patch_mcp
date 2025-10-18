# Patch MCP Server - API Documentation

Complete API reference for all tools and workflows provided by the Patch MCP Server.

## Table of Contents

- [Core Patch Tools](#core-patch-tools)
- [Analysis Tools](#analysis-tools)
- [Backup Tools](#backup-tools)
- [Error Recovery Workflows](#error-recovery-workflows)
- [Security Features](#security-features)
- [Error Types](#error-types)
- [Return Value Semantics](#return-value-semantics)

---

## Core Patch Tools

### apply_patch

Apply a unified diff patch to a file with optional dry-run mode.

**Parameters:**
- `file_path` (string, required): Path to the file to patch
- `patch` (string, required): Unified diff patch content (supports multi-hunk patches)
- `dry_run` (boolean, optional): If true, validate only without modifying file (default: false)

**Returns:**
```python
# Success
{
    "success": True,
    "file_path": str,
    "applied": True,
    "changes": {
        "lines_added": int,
        "lines_removed": int,
        "hunks_applied": int
    },
    "message": str
}

# Failure
{
    "success": False,
    "file_path": str,
    "applied": False,
    "error": str,
    "error_type": str  # See Error Types section
}
```

**Example:**
```python
from patch_mcp.tools.apply import apply_patch

patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 def get_timeout():
-    return 30
+    return 60
"""

# Test with dry run
result = apply_patch("config.py", patch, dry_run=True)
if result["success"]:
    # Apply for real
    result = apply_patch("config.py", patch)
```

**Multi-hunk Example:**
```python
# Apply multiple changes atomically in one patch
multi_hunk_patch = """--- config.py
+++ config.py
@@ -10,3 +10,3 @@
-timeout = 30
+timeout = 60
@@ -25,3 +25,3 @@
-retries = 3
+retries = 5
"""

result = apply_patch("config.py", multi_hunk_patch)
# Both changes applied atomically or neither
```

---

### validate_patch

Check if a patch can be applied to a file (read-only operation).

**Parameters:**
- `file_path` (string, required): Path to the file to validate against
- `patch` (string, required): Unified diff patch content to validate

**Returns:**
```python
# Can apply (success)
{
    "success": True,
    "file_path": str,
    "valid": True,
    "can_apply": True,
    "preview": {
        "lines_to_add": int,
        "lines_to_remove": int,
        "hunks": int,
        "affected_line_range": {
            "start": int,
            "end": int
        }
    },
    "message": "Patch is valid and can be applied cleanly"
}

# Cannot apply (failure)
{
    "success": False,  # Note: False when can't apply
    "file_path": str,
    "valid": True,
    "can_apply": False,
    "preview": {...},
    "reason": str,  # Why it can't be applied
    "error_type": "context_mismatch",
    "message": "Patch is valid but cannot be applied to this file"
}
```

**Example:**
```python
from patch_mcp.tools.validate import validate_patch

result = validate_patch("config.py", patch)
if result["can_apply"]:
    print(f"Will add {result['preview']['lines_to_add']} lines")
else:
    print(f"Cannot apply: {result['reason']}")
```

---

### revert_patch

Reverse a previously applied patch.

**Parameters:**
- `file_path` (string, required): Path to the file to revert
- `patch` (string, required): The same patch that was previously applied

**Returns:**
```python
# Success
{
    "success": True,
    "file_path": str,
    "reverted": True,
    "changes": {
        "lines_added": int,
        "lines_removed": int,
        "hunks_reverted": int
    },
    "message": str
}

# Failure
{
    "success": False,
    "file_path": str,
    "reverted": False,
    "error": str,
    "error_type": str
}
```

**Example:**
```python
from patch_mcp.tools.apply import apply_patch
from patch_mcp.tools.revert import revert_patch

# Apply patch
apply_patch("config.py", patch)

# Later, revert it
result = revert_patch("config.py", patch)
# File is back to original state
```

**Important:**
- Must use the EXACT same patch that was applied
- File must not have been modified in affected areas since patch was applied
- For multi-hunk patches, all hunks are reverted atomically

---

### generate_patch

Generate a unified diff patch by comparing two files.

**Parameters:**
- `original_file` (string, required): Path to the original/old version
- `modified_file` (string, required): Path to the modified/new version
- `context_lines` (integer, optional): Number of context lines (default: 3)

**Returns:**
```python
# Success
{
    "success": True,
    "original_file": str,
    "modified_file": str,
    "patch": str,  # Unified diff format
    "changes": {
        "lines_added": int,
        "lines_removed": int,
        "hunks": int
    },
    "message": str
}

# Failure
{
    "success": False,
    "error": str,
    "error_type": str
}
```

**Example:**
```python
from patch_mcp.tools.generate import generate_patch

result = generate_patch("config_v1.py", "config_v2.py")
if result["success"]:
    patch_content = result["patch"]
    print(f"Generated {result['changes']['hunks']} hunks")
```

---

## Analysis Tools

### inspect_patch

Analyze patch content without requiring any files.

**Parameters:**
- `patch` (string, required): Unified diff patch content

**Returns:**
```python
# Success
{
    "success": True,
    "valid": True,
    "files": [  # Array of affected files (supports multi-file patches)
        {
            "source": str,
            "target": str,
            "hunks": int,
            "lines_added": int,
            "lines_removed": int
        }
    ],
    "summary": {
        "total_files": int,
        "total_hunks": int,
        "total_lines_added": int,
        "total_lines_removed": int
    },
    "message": str
}

# Invalid patch
{
    "success": False,
    "valid": False,
    "error": str,
    "error_type": "invalid_patch"
}
```

**Example:**
```python
from patch_mcp.tools.inspect import inspect_patch

result = inspect_patch(patch_content)
if result["success"]:
    print(f"Affects {result['summary']['total_files']} files")
    for file_info in result["files"]:
        print(f"  {file_info['target']}: +{file_info['lines_added']} -{file_info['lines_removed']}")
```

---

## Backup Tools

### backup_file

Create a timestamped backup of a file.

**Parameters:**
- `file_path` (string, required): Path to the file to backup

**Returns:**
```python
# Success
{
    "success": True,
    "original_file": str,
    "backup_file": str,  # Format: {original}.backup.YYYYMMDD_HHMMSS
    "backup_size": int,
    "message": str
}

# Failure
{
    "success": False,
    "original_file": str,
    "error": str,
    "error_type": str
}
```

**Example:**
```python
from patch_mcp.tools.backup import backup_file

result = backup_file("config.py")
if result["success"]:
    print(f"Backup created: {result['backup_file']}")
```

---

### restore_backup

Restore a file from a timestamped backup.

**Parameters:**
- `backup_file` (string, required): Path to the backup file
- `target_file` (string, optional): Where to restore (auto-detected if None)
- `force` (boolean, optional): Overwrite even if modified (default: false)

**Returns:**
```python
# Success
{
    "success": True,
    "backup_file": str,
    "restored_to": str,
    "restored_size": int,
    "message": str
}

# Failure
{
    "success": False,
    "backup_file": str,
    "error": str,
    "error_type": str
}
```

**Example:**
```python
from patch_mcp.tools.backup import restore_backup

# Auto-detect target from backup filename
result = restore_backup("config.py.backup.20250118_143052")

# Explicit target
result = restore_backup("config.py.backup.20250118_143052",
                       target_file="config_restored.py")
```

---

## Error Recovery Workflows

The workflows module provides high-level patterns combining multiple tools.

### apply_patches_with_revert

Apply multiple patches sequentially with automatic revert on failure.

**Parameters:**
- `file_path` (string, required): Path to the file
- `patches` (list[string], required): List of patches to apply
- `stop_on_failure` (boolean, optional): Stop at first failure (default: true)

**Returns:**
```python
{
    "success": bool,
    "file_path": str,
    "patches_applied": int,
    "patches_total": int,
    "failed_at": int | None,  # Index of failed patch if any
    "message": str
}
```

**Use cases:** Multi-step refactoring, dependent patches

---

### apply_patch_with_backup

Apply patch with automatic backup and restore on failure.

**Parameters:**
- `file_path` (string, required): Path to the file
- `patch` (string, required): Patch to apply
- `keep_backup` (boolean, optional): Keep backup even on success (default: false)

**Returns:**
```python
{
    "success": bool,
    "file_path": str,
    "backup_file": str | None,
    "applied": bool,
    "restored": bool,
    "message": str
}
```

**Use cases:** Critical files, experimental changes, production updates

---

### apply_patches_atomic

Apply multiple patches to multiple files atomically - all succeed or all rollback.

**Parameters:**
- `patches` (list[tuple], required): List of (file_path, patch) pairs

**Returns:**
```python
{
    "success": bool,
    "patches_applied": int,
    "patches_total": int,
    "failed_at": int | None,
    "rollback_successful": bool | None,
    "message": str
}
```

**Use cases:** Multi-file refactoring, coordinated changes, consistency requirements

---

### apply_patch_progressive

Step-by-step validation with detailed error reporting.

**Parameters:**
- `file_path` (string, required): Path to the file
- `patch` (string, required): Patch to apply

**Returns:**
```python
{
    "success": bool,
    "file_path": str,
    "steps": {
        "safety_check": {"passed": bool, "details": dict},
        "validation": {"passed": bool, "details": dict},
        "backup": {"passed": bool, "details": dict},
        "apply": {"passed": bool, "details": dict},
        "restore": {"passed": bool, "details": dict} | None
    },
    "message": str
}
```

**Use cases:** Debugging, troubleshooting, learning

---

## Security Features

All file operations include comprehensive security checks:

### Security Validations

1. **Symlink Detection**: Symlinks are automatically rejected (security policy)
2. **Binary File Detection**: Binary files detected and rejected
3. **File Size Limits**: Maximum 10MB file size
4. **Disk Space Validation**: Minimum 100MB free space + 110% of file size
5. **Path Traversal Protection**: Prevents directory escaping attacks
6. **Permission Checks**: Read/write permissions validated
7. **Atomic Operations**: File replacements use atomic rename

### Configuration Constants

```python
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB
BINARY_CHECK_BYTES = 8192           # First 8KB checked
NON_TEXT_THRESHOLD = 0.3            # 30% non-text = binary
```

### Binary File Detection

Files are considered binary if:
- Contains null bytes (`\x00`)
- Cannot be decoded as UTF-8
- More than 30% non-text characters

---

## Error Types

The server provides 10 distinct error types for precise error handling:

### Standard Errors

| Error Type | Description |
|------------|-------------|
| `file_not_found` | File doesn't exist |
| `permission_denied` | Cannot read/write file |
| `invalid_patch` | Patch format is malformed |
| `context_mismatch` | Patch context doesn't match file content |
| `encoding_error` | File encoding issue |
| `io_error` | General I/O error |

### Security Errors

| Error Type | Description |
|------------|-------------|
| `symlink_error` | Target is a symlink (security policy) |
| `binary_file` | Target is a binary file (not supported) |
| `disk_space_error` | Insufficient disk space |
| `resource_limit` | File too large or operation timed out |

---

## Return Value Semantics

### Critical Semantics

1. **validate_patch success field**:
   - `success=True` when patch CAN be applied
   - `success=False` when patch CANNOT be applied (even if format is valid)
   - Always check both `success` and `can_apply` fields

2. **inspect_patch files field**:
   - Always returns `files` array (never `file` object)
   - Supports multi-file patches
   - Empty array for empty patches

3. **apply_patch with dry_run**:
   - `dry_run=True` never modifies the file
   - Returns same structure as normal apply
   - Useful for validation and preview

4. **revert_patch terminology**:
   - Uses `reverted` field (not `applied`)
   - Must use exact same patch that was applied
   - Fails if file was modified since patch application

### Consistent Return Structure

All tools follow this pattern:

**Success:**
```python
{
    "success": True,
    "file_path": str,  # Most tools
    # ... tool-specific fields ...
    "message": str
}
```

**Failure:**
```python
{
    "success": False,
    "file_path": str,  # Most tools
    "error": str,
    "error_type": str,  # One of 10 error types
    "message": str  # Optional
}
```

---

## Example Workflows

### Safe Single Patch Application

```python
from patch_mcp.tools.validate import validate_patch
from patch_mcp.tools.backup import backup_file, restore_backup
from patch_mcp.tools.apply import apply_patch

# Step 1: Validate
validation = validate_patch("config.py", patch)
if not validation["can_apply"]:
    print(f"Cannot apply: {validation['reason']}")
    exit(1)

# Step 2: Backup
backup = backup_file("config.py")

# Step 3: Apply
result = apply_patch("config.py", patch)

if not result["success"]:
    # Restore on failure
    restore_backup(backup["backup_file"])
```

### Multi-file Atomic Application

```python
from patch_mcp.workflows import apply_patches_atomic

patches = [
    ("src/config.py", config_patch),
    ("src/utils.py", utils_patch),
    ("src/main.py", main_patch),
]

result = apply_patches_atomic(patches)

if result["success"]:
    print(f"Applied {result['patches_applied']} patches atomically")
else:
    print(f"Failed at patch {result['failed_at']}, all rolled back")
```

### Progressive Debugging

```python
from patch_mcp.workflows import apply_patch_progressive

result = apply_patch_progressive("module.py", patch)

# Check each step
for step_name, step_result in result["steps"].items():
    if not step_result["passed"]:
        print(f"Failed at {step_name}: {step_result['details']}")
        break
```

---

## Testing

### Coverage Statistics

- **Total Tests**: 244 (all passing)
- **Overall Coverage**: 83%
- **Unit Tests**: 209 tests
- **Integration Tests**: 35 tests

### Coverage Breakdown

| Module | Coverage |
|--------|----------|
| models.py | 100% |
| inspect.py | 99% |
| validate.py | 92% |
| revert.py | 91% |
| utils.py | 88% |
| apply.py | 87% |
| server.py | 86% |
| generate.py | 81% |
| backup.py | 70% |
| workflows.py | 70% |

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/patch_mcp --cov-report=term --cov-report=html

# Run specific test suites
pytest tests/test_apply.py -v
pytest tests/integration/test_workflows.py -v

# View coverage report
open htmlcov/index.html
```

---

## Code Quality

The project maintains strict code quality standards:

```bash
# Format code
black src/patch_mcp tests/

# Lint code
ruff check src/patch_mcp tests/

# Type check
mypy src/patch_mcp --strict
```

All code passes:
- Black formatting (line length: 100)
- Ruff linting (E, F, I, N, W rules)
- Mypy strict type checking

---

For workflow pattern details, see [WORKFLOWS.md](../WORKFLOWS.md).
For security policy, see [SECURITY.md](../SECURITY.md).
For contributing guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).
