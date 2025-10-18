# AI Implementation Guide - File Patch MCP Server

## Overview

This guide helps AI assistants implement the File Patch MCP Server based on the complete `project_design.md` specification.

**Status**: The design document is **COMPLETE** and production-ready.

---

## Quick Facts

- **Design File**: `project_design.md` (2409 lines, complete)
- **Total Tools**: 7 (4 core + 3 optional)
- **Error Types**: 10 (6 standard + 4 security)
- **Estimated Implementation**: 8 days
- **Test Coverage Target**: 90%+

---

## Reading Order

```
PHASE 1: UNDERSTAND THE DESIGN (60-90 minutes)
└── project_design.md
    ├── Overview (lines 1-67)
    ├── Toolset Summary (lines 69-99)
    ├── All 7 Tool Specifications (lines 102-1089)
    ├── Security Implementation (lines 1092-1284)
    ├── Testing Strategy (lines 1594-1673)
    ├── Error Recovery Patterns (lines 1677-2019)
    └── Example Workflows (lines 2023-2149)

PHASE 2: IMPLEMENT
└── Follow implementation order below
```

---

## Complete Tool Reference

All tools are fully specified in `project_design.md`:

| Tool | Lines | Status | Notes |
|------|-------|--------|-------|
| `apply_patch` | 104-243 | ✅ Complete | Includes dry_run parameter |
| `validate_patch` | 247-394 | ✅ Complete | Correct success=false semantics |
| `revert_patch` | 398-511 | ✅ Complete | Reverse patch application |
| `generate_patch` | 515-624 | ✅ Complete | Create patches from files |
| `inspect_patch` | 628-829 | ✅ Complete | Multi-file support included |
| `backup_file` | 833-937 | ✅ Complete | Timestamped backups |
| `restore_backup` | 941-1088 | ✅ Complete | Restore with safety checks |

---

## Recommended Implementation Order

### Phase 1: Foundation (Days 1-2)

#### Step 1.1: Project Setup

**Read**: project_design.md:1287-1369

**Tasks**:
```bash
# Create structure
mkdir -p src/patch_mcp/tools tests/integration
touch src/patch_mcp/{__init__.py,server.py,models.py,utils.py}
touch src/patch_mcp/tools/__init__.py

# Create pyproject.toml (copy from lines 1325-1367)
# Install dependencies
pip install -e ".[dev]"
```

**Verification**: `pytest --collect-only` should run without errors

---

#### Step 1.2: Data Models

**Read**: project_design.md:1370-1422

**Implement**: `src/patch_mcp/models.py`

Key models to implement:
- `ErrorType` enum (10 types)
- `PatchChanges` (lines_added, lines_removed, hunks_applied)
- `AffectedLineRange` (start, end)
- `FileInfo` (for inspect_patch)
- `PatchSummary` (for multi-file patches)
- `ToolResult` (standard response format)

**Test**: `tests/test_models.py`
```python
def test_error_types():
    """Verify all 10 error types exist."""
    assert len(ErrorType) == 10
    assert ErrorType.SYMLINK_ERROR == "symlink_error"

def test_patch_changes_validation():
    """Test Pydantic validation."""
    changes = PatchChanges(lines_added=5, lines_removed=3, hunks_applied=2)
    assert changes.lines_added == 5

    # Negative values should fail
    with pytest.raises(ValidationError):
        PatchChanges(lines_added=-1, lines_removed=0, hunks_applied=0)
```

---

#### Step 1.3: Security Utilities

**Read**: project_design.md:1092-1263

**Implement**: `src/patch_mcp/utils.py`

Four critical functions to implement:
1. `validate_file_safety()` - Lines 1108-1189
   - Check file exists, is regular file
   - Reject symlinks (security)
   - Reject binary files
   - Check file size limit (10MB)
   - Check write permissions (if needed)
   - Check disk space (if needed, 100MB minimum)

2. `is_binary_file()` - Lines 1192-1217
   - Check for null bytes
   - Check ratio of non-text characters (>30% = binary)

3. `check_path_traversal()` - Lines 1220-1244
   - Prevent directory escaping attacks
   - Validate paths stay within base directory

4. `atomic_file_replace()` - Lines 1247-1262
   - Atomic rename on Unix
   - Handle Windows requirements

**Test**: `tests/test_security.py`
```python
def test_reject_symlink(tmp_path):
    """Symlinks must be rejected."""
    target = tmp_path / "target.txt"
    target.write_text("content")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    error = validate_file_safety(link)
    assert error is not None
    assert error["error_type"] == "symlink_error"

def test_reject_binary_file(tmp_path):
    """Binary files must be rejected."""
    binary = tmp_path / "binary.dat"
    binary.write_bytes(b'\x00\x01\x02' * 100)

    error = validate_file_safety(binary)
    assert error is not None
    assert error["error_type"] == "binary_file"

def test_file_size_limit(tmp_path):
    """Files over 10MB must be rejected."""
    large = tmp_path / "large.txt"
    large.write_bytes(b'x' * (11 * 1024 * 1024))  # 11MB

    error = validate_file_safety(large)
    assert error is not None
    assert error["error_type"] == "resource_limit"
```

---

### Phase 2: Core Tools (Days 3-5)

Implement in dependency order:

#### Step 2.1: generate_patch

**Read**: project_design.md:515-624

**Why first**: No dependencies on other tools

**Implement**: `src/patch_mcp/tools/generate.py`
```python
import patch_ng
from pathlib import Path
from typing import Dict, Any
from ..utils import validate_file_safety

def generate_patch(
    original_file: str,
    modified_file: str,
    context_lines: int = 3
) -> Dict[str, Any]:
    """Generate unified diff patch from two files.

    Args:
        original_file: Path to original/old version
        modified_file: Path to modified/new version
        context_lines: Number of context lines (default: 3)

    Returns:
        Dict with success status and patch content
    """
    # Security checks for both files
    # Read both files
    # Use patch_ng to generate diff
    # Count changes
    # Return formatted result
```

**Key points from spec**:
- Default 3 context lines (line 533)
- Reject symlinks and binary files (lines 601-602)
- Empty patch if files are identical (line 599)
- Return format includes `changes` dict (lines 547-552)

**Test**: `tests/test_generate.py`
```python
def test_generate_simple_patch():
def test_generate_identical_files():
def test_generate_reject_binary():
def test_custom_context_lines():
```

---

#### Step 2.2: inspect_patch

**Read**: project_design.md:628-829

**Why second**: No dependencies, needed by workflows

**Implement**: `src/patch_mcp/tools/inspect.py`
```python
from typing import Dict, Any, List
import patch_ng

def inspect_patch(patch: str) -> Dict[str, Any]:
    """Analyze patch content (supports multi-file patches).

    Args:
        patch: Unified diff patch content

    Returns:
        Dict with files array and summary
    """
    # Parse patch format
    # Extract file information
    # Calculate statistics per file
    # Build summary
```

**CRITICAL**: Multi-file support (lines 715-716)
- Return format: `{"files": [...], "summary": {...}}`
- NOT: `{"file": {...}}` (old single-file format)

**Return format**:
```python
{
    "success": True,
    "valid": True,
    "files": [  # Array, always!
        {
            "source": "config.py",
            "target": "config.py",
            "hunks": 2,
            "lines_added": 5,
            "lines_removed": 3
        }
    ],
    "summary": {
        "total_files": 1,
        "total_hunks": 2,
        "total_lines_added": 5,
        "total_lines_removed": 3
    }
}
```

**Test**: `tests/test_inspect.py`
```python
def test_inspect_single_file():
    """Single file returns array with 1 element."""
    result = inspect_patch(single_file_patch)
    assert len(result["files"]) == 1
    assert result["summary"]["total_files"] == 1

def test_inspect_multiple_files():
    """Multiple files all returned."""
    result = inspect_patch(multi_file_patch)
    assert len(result["files"]) == 2
    assert result["summary"]["total_files"] == 2

def test_inspect_invalid_patch():
    """Invalid patch returns error."""
    result = inspect_patch("not a patch")
    assert result["success"] is False
    assert result["error_type"] == "invalid_patch"
```

---

#### Step 2.3: validate_patch

**Read**: project_design.md:247-394

**Why third**: Needed by apply_patch

**Implement**: `src/patch_mcp/tools/validate.py`
```python
from pathlib import Path
from typing import Dict, Any
from ..utils import validate_file_safety
import patch_ng

def validate_patch(file_path: str, patch: str) -> Dict[str, Any]:
    """Validate patch can be applied to file (read-only).

    Args:
        file_path: Target file path
        patch: Unified diff patch

    Returns:
        Dict with validation result
    """
    # Security checks
    # Parse patch
    # Check context matches
    # Return result
```

**CRITICAL**: Return value semantics (lines 43-45, 288-307)

When patch **cannot be applied**:
```python
return {
    "success": False,  # NOT True!
    "valid": True,     # Patch format is valid
    "can_apply": False,
    "preview": {...},  # Still provide preview
    "reason": "Context mismatch at line 23: expected 'foo' but found 'bar'",
    "error_type": "context_mismatch",  # Required
    "message": "Patch is valid but cannot be applied to this file"
}
```

When patch **can be applied**:
```python
return {
    "success": True,
    "valid": True,
    "can_apply": True,
    "preview": {
        "lines_to_add": 5,
        "lines_to_remove": 3,
        "hunks": 2,
        "affected_line_range": {  # Object, not string!
            "start": 15,
            "end": 42
        }
    },
    "message": "Patch is valid and can be applied cleanly"
}
```

**Test**: `tests/test_validate.py`
```python
def test_validate_can_apply():
    """When context matches, success=True."""
    result = validate_patch(file, good_patch)
    assert result["success"] is True
    assert result["can_apply"] is True
    assert "preview" in result

def test_validate_cannot_apply():
    """When context mismatches, success=False."""
    result = validate_patch(file, bad_patch)
    assert result["success"] is False  # Key point!
    assert result["valid"] is True
    assert result["can_apply"] is False
    assert result["error_type"] == "context_mismatch"
    assert "reason" in result
```

---

#### Step 2.4: apply_patch

**Read**: project_design.md:104-243

**Why fourth**: Uses validate_patch internally

**Implement**: `src/patch_mcp/tools/apply.py`
```python
from pathlib import Path
from typing import Dict, Any
from ..utils import validate_file_safety, atomic_file_replace
import patch_ng

def apply_patch(
    file_path: str,
    patch: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Apply patch to file with security checks and optional dry-run.

    Args:
        file_path: Target file path
        patch: Unified diff patch
        dry_run: If True, validate only (don't modify)

    Returns:
        Dict with application result
    """
    # Security checks (check_write=not dry_run)
    # Parse patch
    # Apply or validate only
    # Return result
```

**Key features**:
1. **dry_run support** (lines 120-125, 228-242)
   - When True: validate but don't modify
   - Returns same format as normal apply
   - Message says "dry run"

2. **Edge cases** (lines 190-194):
   - Empty patches: success with all counts 0
   - Whitespace-only: counted as normal
   - Binary files: rejected
   - Symlinks: rejected

3. **Security**: Call `validate_file_safety()` first

**Test**: `tests/test_apply.py`
```python
def test_apply_success():
def test_apply_context_mismatch():
def test_dry_run_success():
def test_dry_run_does_not_modify():
def test_empty_patch():
def test_whitespace_only_changes():
def test_reject_symlink():
def test_reject_binary():
```

---

#### Step 2.5: revert_patch

**Read**: project_design.md:398-511

**Why last**: Simple wrapper around apply_patch

**Implement**: `src/patch_mcp/tools/revert.py`
```python
def revert_patch(file_path: str, patch: str) -> Dict[str, Any]:
    """Revert previously applied patch (apply in reverse).

    Args:
        file_path: Target file path
        patch: The SAME patch that was applied

    Returns:
        Dict with revert result
    """
    # Reverse the patch (+ becomes -, - becomes +)
    # Apply reversed patch
    # Return result with "reverted" field
```

**Key points** (lines 449-453):
- Use EXACT same patch as originally applied
- File must not be modified in affected areas
- Returns `reverted: True/False` field
- Changes are opposite of original

**Test**: `tests/test_revert.py`
```python
def test_revert_success():
    """Apply then revert should restore original."""
    original = read_file(file)
    apply_patch(file, patch)
    revert_patch(file, patch)
    assert read_file(file) == original

def test_revert_after_modification():
    """Revert fails if file was modified."""
    apply_patch(file, patch1)
    apply_patch(file, patch2)  # Modifies same area
    result = revert_patch(file, patch1)
    assert result["success"] is False
    assert result["error_type"] == "context_mismatch"
```

---

### Phase 3: Backup Tools (Day 6)

#### Step 3.1: backup_file

**Read**: project_design.md:833-937

**Implement**: `src/patch_mcp/tools/backup.py`
```python
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import shutil

def backup_file(file_path: str) -> Dict[str, Any]:
    """Create timestamped backup copy.

    Args:
        file_path: File to backup

    Returns:
        Dict with backup file path and size
    """
    # Security checks
    # Generate timestamp: YYYYMMDD_HHMMSS
    # Create backup: original.backup.YYYYMMDD_HHMMSS
    # Return backup path
```

**Format** (lines 874-877):
- Original: `/path/to/file.py`
- Backup: `/path/to/file.py.backup.20250117_143052`

**Test**: `tests/test_backup.py`
```python
def test_backup_creates_file():
def test_backup_naming_format():
def test_backup_preserves_content():
```

---

#### Step 3.2: restore_backup

**Read**: project_design.md:941-1088

**Implement**: Add to `src/patch_mcp/tools/backup.py`
```python
from typing import Optional

def restore_backup(
    backup_file: str,
    target_file: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """Restore file from timestamped backup.

    Args:
        backup_file: Path to backup file
        target_file: Where to restore (auto-detected if None)
        force: Overwrite even if target modified (default: False)

    Returns:
        Dict with restore result
    """
    # Parse backup filename to get original
    # Check backup exists
    # Check target writable
    # Check if target modified (unless force)
    # Atomic restore
```

**Key features** (lines 993-1008):
1. **Auto-detect target**: `file.py.backup.20250117_143052` → `file.py`
2. **Safety checks**: Warn if target modified since backup
3. **Force mode**: Override modification check
4. **Atomic**: Use atomic_file_replace()

**Test**: `tests/test_backup.py`
```python
def test_restore_success():
def test_restore_auto_detect_target():
def test_restore_to_different_location():
def test_restore_force_overwrite():
def test_restore_backup_not_found():
```

---

### Phase 4: MCP Server Integration (Day 7)

#### Step 4.1: MCP Server

**Read**: project_design.md:1424-1580

**Implement**: `src/patch_mcp/server.py`
```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import json
from .tools import apply, validate, revert, generate, inspect, backup

server = Server("patch-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all 7 tools."""
    return [
        Tool(
            name="apply_patch",
            description="Apply a unified diff patch to a file (supports dry_run)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "patch": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False}
                },
                "required": ["file_path", "patch"]
            }
        ),
        # ... 6 more tools
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to implementations."""
    result = None

    if name == "apply_patch":
        result = apply.apply_patch(
            arguments["file_path"],
            arguments["patch"],
            arguments.get("dry_run", False)
        )
    elif name == "validate_patch":
        result = validate.validate_patch(
            arguments["file_path"],
            arguments["patch"]
        )
    # ... handle all 7 tools

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

**Test**: Manual MCP testing with Claude Desktop

---

### Phase 5: Error Recovery Patterns (Day 8)

**Read**: project_design.md:1677-2019

These are **optional helper functions** that demonstrate best practices. Consider implementing as `src/patch_mcp/workflows.py`:

1. **Pattern 1: Try-Revert** (lines 1679-1733)
   - Apply patches sequentially
   - Revert all on first failure

2. **Pattern 2: Backup-Restore** (lines 1737-1823)
   - Create backup before apply
   - Auto-restore on failure

3. **Pattern 3: Validate-All-Then-Apply** (lines 1827-1935)
   - Atomic batch operations
   - All-or-nothing guarantee

4. **Pattern 4: Progressive Validation** (lines 1939-2019)
   - Step-by-step validation
   - Detailed error reporting

**Test**: `tests/integration/test_workflows.py`

---

## Testing Strategy

### Test Organization

**Read**: project_design.md:1594-1673

```
tests/
├── test_models.py           # Pydantic models and enums
├── test_security.py         # Security utilities (100% coverage)
├── test_apply.py            # apply_patch + edge cases
├── test_validate.py         # validate_patch + semantics
├── test_revert.py           # revert_patch
├── test_generate.py         # generate_patch
├── test_inspect.py          # inspect_patch + multi-file
├── test_backup.py           # backup_file + restore_backup
└── integration/
    ├── test_workflows.py    # Error recovery patterns
    └── test_mcp_server.py   # MCP integration
```

### Coverage Targets

- **Overall**: 90%+ coverage
- **Security utilities**: 100% coverage (critical)
- **Each tool**: 95%+ coverage
- **Edge cases**: All documented cases tested

### Example Test Structure

```python
# tests/test_apply.py

import pytest
from pathlib import Path
from patch_mcp.tools.apply import apply_patch

class TestApplyPatch:
    """Test apply_patch tool."""

    def test_apply_success(self, tmp_path):
        """Apply simple patch successfully."""

    def test_apply_dry_run(self, tmp_path):
        """Dry run doesn't modify file."""

    def test_apply_empty_patch(self, tmp_path):
        """Empty patch returns success with zero counts."""

    def test_apply_reject_symlink(self, tmp_path):
        """Symlinks are rejected."""

    def test_apply_reject_binary(self, tmp_path):
        """Binary files are rejected."""

    def test_apply_context_mismatch(self, tmp_path):
        """Context mismatch returns proper error."""
```

---

## Verification Checklist

Before considering implementation complete:

### Tool Completeness
- [ ] All 7 tools implemented
- [ ] All tools registered in MCP server
- [ ] All tools have comprehensive docstrings
- [ ] All tools have test coverage >95%

### API Correctness
- [ ] `validate_patch` returns `success=false` when `can_apply=false`
- [ ] `validate_patch` returns `affected_line_range` as object `{start, end}`
- [ ] `inspect_patch` returns `files` array (not `file` object)
- [ ] `inspect_patch` includes `summary` field
- [ ] `apply_patch` has `dry_run` parameter
- [ ] `restore_backup` exists and works
- [ ] All tools return proper `error_type` for failures

### Security
- [ ] Symlinks rejected (test passes)
- [ ] Binary files rejected (test passes)
- [ ] File size limit enforced (test passes)
- [ ] Disk space checked (test passes)
- [ ] Path traversal protection works (test passes)

### Edge Cases
- [ ] Empty patches handled
- [ ] Whitespace-only changes work
- [ ] CRLF line endings preserved
- [ ] Multi-file patches work
- [ ] All edge cases from spec tested

### Error Handling
- [ ] All 10 error types can be returned
- [ ] Error messages are descriptive
- [ ] `error_type` always included with errors
- [ ] `reason` field present when `can_apply=false`

### Documentation
- [ ] README.md with quick start
- [ ] All tools documented
- [ ] Example workflows work
- [ ] Installation instructions clear

---

## Common Implementation Pitfalls

### 1. Wrong validate_patch Return Value

```python
# WRONG
if can_apply:
    return {"success": True, "can_apply": True, ...}
else:
    return {"success": True, "can_apply": False, ...}  # ❌ Still True!

# CORRECT
if can_apply:
    return {"success": True, "can_apply": True, ...}
else:
    return {
        "success": False,  # ✅ False when can't apply!
        "can_apply": False,
        "error_type": "context_mismatch",  # ✅ Required
        ...
    }
```

### 2. Wrong inspect_patch Format

```python
# WRONG - Old single-file format
return {
    "file": {"source": "config.py", ...}  # ❌ Not "file"!
}

# CORRECT - Multi-file format
return {
    "files": [  # ✅ Array, always!
        {"source": "config.py", ...}
    ],
    "summary": {  # ✅ Summary required
        "total_files": 1,
        ...
    }
}
```

### 3. Missing dry_run Support

```python
# WRONG
def apply_patch(file_path: str, patch: str):  # ❌ No dry_run!
    pass

# CORRECT
def apply_patch(file_path: str, patch: str, dry_run: bool = False):  # ✅
    if dry_run:
        # Validate only, don't modify
        pass
    else:
        # Apply for real
        pass
```

### 4. Forgetting Security Checks

```python
# WRONG
def apply_patch(file_path: str, patch: str, dry_run: bool = False):
    # Directly modify file without checks  # ❌

# CORRECT
def apply_patch(file_path: str, patch: str, dry_run: bool = False):
    # Security checks first  # ✅
    path = Path(file_path)
    safety_error = validate_file_safety(
        path,
        check_write=not dry_run,
        check_space=not dry_run
    )
    if safety_error:
        return {"success": False, **safety_error}

    # Now safe to proceed
```

### 5. Wrong affected_line_range Type

```python
# WRONG
"affected_line_range": "15-42"  # ❌ String!

# CORRECT
"affected_line_range": {  # ✅ Object!
    "start": 15,
    "end": 42
}
```

---

## Example Workflows

**Read**: project_design.md:2023-2149

Five complete workflow examples are provided:

1. **Workflow 1**: Safe Single Patch Application (lines 2025-2047)
2. **Workflow 2**: Dry Run Test Before Apply (lines 2049-2068)
3. **Workflow 3**: Batch Atomic Application (lines 2070-2089)
4. **Workflow 4**: Inspect and Apply Multi-file Patch (lines 2091-2119)
5. **Workflow 5**: Generate and Distribute Patch (lines 2121-2149)

These should be tested in integration tests.

---

## Quick Reference

### Essential Workflow

```python
# The fundamental safe patching workflow:
1. inspect_patch(patch)           # What does it do?
2. validate_patch(file, patch)    # Can I apply it?
3. backup_file(file)              # Save current state
4. apply_patch(file, patch)       # Do it
5. restore_backup(backup)         # Undo if needed
```

### Tool Selection Guide

| Task | Tool |
|------|------|
| Apply a patch | `apply_patch` |
| Test without modifying | `apply_patch(dry_run=True)` |
| Check if patch will work | `validate_patch` |
| Undo a patch | `revert_patch` |
| Create patch from files | `generate_patch` |
| Understand unknown patch | `inspect_patch` |
| Multi-file patch analysis | `inspect_patch` |
| Save file before changes | `backup_file` |
| Restore after failure | `restore_backup` |

### Error Type Reference

| Error Type | Meaning | Common Cause |
|------------|---------|--------------|
| `file_not_found` | File doesn't exist | Wrong path |
| `permission_denied` | Can't read/write | File permissions |
| `invalid_patch` | Bad patch format | Malformed patch |
| `context_mismatch` | Context doesn't match | File was modified |
| `encoding_error` | Encoding issue | Non-UTF-8 file |
| `io_error` | General I/O error | Filesystem issue |
| `symlink_error` | Target is symlink | Security policy |
| `binary_file` | Target is binary | Not supported |
| `disk_space_error` | Not enough space | Disk full |
| `resource_limit` | File too large/timeout | Resource constraints |

---

## Summary

### Implementation Timeline

- **Phase 1** (Foundation): 2 days
- **Phase 2** (Core Tools): 3 days
- **Phase 3** (Backup Tools): 1 day
- **Phase 4** (MCP Server): 1 day
- **Phase 5** (Error Recovery): 1 day
- **Total**: 8 days

### Success Criteria

✅ All 7 tools working correctly
✅ All tests passing (90%+ coverage)
✅ All security checks enforced
✅ All edge cases handled
✅ Correct API semantics (validate_patch, inspect_patch)
✅ MCP server registration complete

### Key Points

1. **Single source of truth**: `project_design.md` (complete, 2409 lines)
2. **No missing files**: Everything is in the design doc
3. **No contradictions**: All specs are consistent and finalized
4. **Production-ready**: Security, error handling, testing all specified
5. **LLM-friendly**: Clear examples, consistent patterns, comprehensive docs

---

*End of AI Implementation Guide*
