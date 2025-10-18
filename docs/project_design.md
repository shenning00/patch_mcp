# File Patch MCP Server - Complete Project Design

**Version**: 2.0
**Last Updated**: 2025-01-17
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Toolset Summary](#toolset-summary)
3. [Tool Specifications](#tool-specifications)
4. [Security Implementation](#security-implementation)
5. [Implementation Guidelines](#implementation-guidelines)
6. [Testing Strategy](#testing-strategy)
7. [Error Recovery Patterns](#error-recovery-patterns)
8. [Example Workflows](#example-workflows)
9. [Migration Guide](#migration-guide)
10. [Quick Reference](#quick-reference)

---

## Overview

This document specifies a Model Context Protocol (MCP) server for applying unified diff patches to files. The design provides both a minimal viable toolset (4 tools) and an optimal extended toolset (7 tools).

### Purpose

Enable LLMs to safely and effectively apply, validate, and generate patches for files with comprehensive security and error handling.

### Core Philosophy

Simple, focused tools that are easy for LLMs to understand and compose into workflows.

### Supported Format

This server **only handles unified diff format** patches. Other formats (git-format-patch, SVN, Mercurial, etc.) are not supported.

### Key Design Decisions

1. **Success Field Semantics**:
   - `success=false` indicates operation failure (tool couldn't complete)
   - `success=false` with `can_apply=false` means validation determined patch cannot be applied
   - All failures include `error_type` for programmatic handling

2. **Security First**:
   - Symlinks rejected (security policy)
   - Binary files not supported
   - Disk space validated before operations
   - File size limits enforced (10MB default)

3. **Dry Run Support**:
   - Destructive operations support validation modes
   - Test without modification using `dry_run=true`

4. **Consistent Error Reporting**:
   - All errors include both `error` message and `error_type`
   - 10 distinct error types for precise handling

### Encoding and Line Endings

- **Default Encoding**: UTF-8
- **Line Endings**: Preserved from original file (CRLF/LF)
- **Context Lines**: 3 lines (unified diff standard)

---

## Toolset Summary

### Minimal Viable Toolset (4 Core Tools)

1. **`apply_patch`** - Apply a patch to a file (supports dry_run)
2. **`validate_patch`** - Check if a patch can be applied safely
3. **`revert_patch`** - Reverse a previously applied patch
4. **`generate_patch`** - Create a patch from two files

### Optimal Extended Toolset (+ 3 Additional Tools)

5. **`inspect_patch`** - Analyze patch content without files (supports multi-file patches)
6. **`backup_file`** - Create a timestamped backup
7. **`restore_backup`** - Restore a file from a backup

### Error Types (10 Total)

**Standard Errors (6)**:
- `file_not_found` - File doesn't exist
- `permission_denied` - Cannot read/write file
- `invalid_patch` - Patch format is malformed
- `context_mismatch` - Patch context doesn't match file content
- `encoding_error` - File encoding issue
- `io_error` - General I/O error

**Security Errors (4)**:
- `symlink_error` - Target is a symlink (security policy)
- `binary_file` - Target is a binary file (not supported)
- `disk_space_error` - Insufficient disk space
- `resource_limit` - File too large or operation timed out

---

## Tool Specifications

### Tool 1: apply_patch

#### Parameters

```json
{
  "file_path": {
    "type": "string",
    "description": "Path to the file to patch (absolute or relative)",
    "required": true
  },
  "patch": {
    "type": "string",
    "description": "Unified diff patch content",
    "required": true
  },
  "dry_run": {
    "type": "boolean",
    "description": "If true, validate the patch can be applied but don't modify the file",
    "required": false,
    "default": false
  }
}
```

#### Return Value - Success

```json
{
  "success": true,
  "file_path": "/path/to/file.py",
  "applied": true,
  "changes": {
    "lines_added": 5,
    "lines_removed": 3,
    "hunks_applied": 2
  },
  "message": "Successfully applied patch to file.py"
}
```

#### Return Value - Failure

```json
{
  "success": false,
  "file_path": "/path/to/file.py",
  "applied": false,
  "error": "Context mismatch at line 42: expected 'def foo():' but found 'def bar():'",
  "error_type": "context_mismatch"
}
```

#### Documentation

Apply a unified diff patch to a file.

⚠️ **WARNING**: This WILL modify the file in place (unless `dry_run=true`).

**DRY RUN MODE**:
- Set `dry_run=true` to validate without modifying the file
- Useful for safe automation and pre-flight checks
- Returns the same information as if the patch was applied
- Equivalent to calling `validate_patch` but with full apply_patch response format

**IMPORTANT**:
- Call `validate_patch` first OR use `dry_run=true` to ensure the patch will apply cleanly
- Consider calling `backup_file` before applying patches to important files
- If applying multiple patches, validate all first before applying any

**PATCH FORMAT**:
```
--- original_file
+++ modified_file
@@ -start,count +start,count @@
 context line
-removed line
+added line
 context line
```

**ENCODING**:
- Files are read/written as UTF-8 by default
- Encoding errors reported with `error_type: "encoding_error"`
- Line endings (CRLF/LF) are preserved from the original file

**EDGE CASES**:
- Empty patches (no changes): Returns success with all counts as 0
- Whitespace-only changes: Counted as normal additions/removals
- Binary files: Rejected with `error_type: "binary_file"`
- Symlinks: Rejected with `error_type: "symlink_error"` (security policy)

**ERROR HANDLING**:
If the operation fails, the file may be left in a partially modified state. Use `revert_patch` to undo changes, or `restore_backup` to restore from a backup.

#### Example

```python
# Example 1: Normal application
{
  "file_path": "config.py",
  "patch": """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""
}

# Response
{
  "success": true,
  "file_path": "config.py",
  "applied": true,
  "changes": {
    "lines_added": 1,
    "lines_removed": 1,
    "hunks_applied": 1
  },
  "message": "Successfully applied patch to config.py"
}

# Example 2: Dry run
{
  "file_path": "config.py",
  "patch": "...",
  "dry_run": true
}

# Response (file not modified)
{
  "success": true,
  "file_path": "config.py",
  "applied": true,  # Would have been applied
  "changes": {...},
  "message": "Patch can be applied to config.py (dry run)"
}
```

---

### Tool 2: validate_patch

#### Parameters

```json
{
  "file_path": {
    "type": "string",
    "description": "Path to the file to validate against",
    "required": true
  },
  "patch": {
    "type": "string",
    "description": "Unified diff patch content to validate",
    "required": true
  }
}
```

#### Return Value - Can Apply

```json
{
  "success": true,
  "file_path": "/path/to/file.py",
  "valid": true,
  "can_apply": true,
  "preview": {
    "lines_to_add": 5,
    "lines_to_remove": 3,
    "hunks": 2,
    "affected_line_range": {
      "start": 15,
      "end": 42
    }
  },
  "message": "Patch is valid and can be applied cleanly"
}
```

#### Return Value - Cannot Apply

```json
{
  "success": false,
  "file_path": "/path/to/file.py",
  "valid": true,
  "can_apply": false,
  "preview": {
    "lines_to_add": 5,
    "lines_to_remove": 3,
    "hunks": 2,
    "affected_line_range": {
      "start": 15,
      "end": 42
    }
  },
  "reason": "Context mismatch at line 23: expected 'old_value = 1' but found 'old_value = 2'",
  "error_type": "context_mismatch",
  "message": "Patch is valid but cannot be applied to this file"
}
```

#### Return Value - Invalid Patch

```json
{
  "success": false,
  "file_path": "/path/to/file.py",
  "valid": false,
  "error": "Invalid patch format: missing +++ header",
  "error_type": "invalid_patch"
}
```

#### Documentation

Validate a patch without modifying any files (read-only operation).

**RECOMMENDED WORKFLOW**:
1. Call `validate_patch` first to check if patch will work
2. Review the preview information (lines to add/remove)
3. If `valid` and `can_apply` is true, call `apply_patch`
4. If `can_apply` is false, review the `reason` and fix the patch or file

**VALIDATION CHECKS**:
- File exists and is readable
- File is not a symlink (security)
- File is not binary
- Patch format is valid (has correct headers and structure)
- Patch context matches file content exactly
- All hunks can be applied cleanly

**RETURN VALUE DETAILS**:
- `preview` is always present when the patch format is valid (`valid=true`)
- `reason` is only present when `can_apply=false`, explaining why
- `affected_line_range` is an object with `start` and `end` fields
- Use `reason` to debug context mismatches and fix patches

**IMPORTANT**: Always use this before `apply_patch` in production workflows.

#### Example

```python
# Success case
{
  "file_path": "server.py",
  "patch": """--- server.py
+++ server.py
@@ -10,7 +10,7 @@
 def start_server():
     config = load_config()
-    port = config['port']
+    port = config.get('port', 8080)
     app.run(port=port)
"""
}

# Response
{
  "success": true,
  "file_path": "server.py",
  "valid": true,
  "can_apply": true,
  "preview": {
    "lines_to_add": 1,
    "lines_to_remove": 1,
    "hunks": 1,
    "affected_line_range": {
      "start": 10,
      "end": 15
    }
  },
  "message": "Patch is valid and can be applied cleanly"
}

# Cannot apply case
{
  "success": false,
  "file_path": "server.py",
  "valid": true,
  "can_apply": false,
  "preview": {...},
  "reason": "Context mismatch at line 12: expected 'port = config['port']' but found 'port = config.get('port')'",
  "error_type": "context_mismatch",
  "message": "Patch is valid but cannot be applied to this file"
}
```

---

### Tool 3: revert_patch

#### Parameters

```json
{
  "file_path": {
    "type": "string",
    "description": "Path to the file to revert",
    "required": true
  },
  "patch": {
    "type": "string",
    "description": "The same patch that was previously applied",
    "required": true
  }
}
```

#### Return Value - Success

```json
{
  "success": true,
  "file_path": "/path/to/file.py",
  "reverted": true,
  "changes": {
    "lines_added": 3,
    "lines_removed": 5,
    "hunks_reverted": 2
  },
  "message": "Successfully reverted patch from file.py"
}
```

#### Return Value - Failure

```json
{
  "success": false,
  "file_path": "/path/to/file.py",
  "reverted": false,
  "error": "Cannot revert: file has been modified since patch was applied",
  "error_type": "context_mismatch"
}
```

#### Documentation

Revert a previously applied patch (apply in reverse).

**HOW IT WORKS**:
- Takes the original patch
- Reverses it (+ becomes -, - becomes +)
- Applies the reversed patch

**IMPORTANT**:
- Use the EXACT same patch that was originally applied
- The file must not have been modified in the affected areas since applying
- If the file has changed, revert may fail with a context mismatch

**WHEN TO USE**:
- Undo a problematic patch
- Roll back changes during testing
- Revert to previous state after errors
- Part of a transactional workflow

**IF REVERT FAILS**:
1. Restore from a backup using `restore_backup` (if available)
2. Manually edit the file
3. Apply a new corrective patch

**NOTE**: The `changes` field shows what changed during revert (opposite of original).

#### Example

```python
# Original patch that was applied
original_patch = """--- utils.py
+++ utils.py
@@ -5,7 +5,7 @@
 def process():
-    return old_method()
+    return new_method()
"""

# Revert call
{
  "file_path": "utils.py",
  "patch": original_patch  # Same patch
}

# Success response
{
  "success": true,
  "file_path": "utils.py",
  "reverted": true,
  "changes": {
    "lines_added": 1,
    "lines_removed": 1,
    "hunks_reverted": 1
  },
  "message": "Successfully reverted patch from utils.py"
}

# Failure (file was modified)
{
  "success": false,
  "file_path": "utils.py",
  "reverted": false,
  "error": "Cannot revert: context at line 7 has changed. Expected 'return new_method()' but found 'return newer_method()'",
  "error_type": "context_mismatch"
}
```

---

### Tool 4: generate_patch

#### Parameters

```json
{
  "original_file": {
    "type": "string",
    "description": "Path to the original/old version of the file",
    "required": true
  },
  "modified_file": {
    "type": "string",
    "description": "Path to the modified/new version of the file",
    "required": true
  },
  "context_lines": {
    "type": "integer",
    "description": "Number of context lines (default: 3)",
    "required": false,
    "default": 3
  }
}
```

#### Return Value - Success

```json
{
  "success": true,
  "original_file": "/path/to/old_version.py",
  "modified_file": "/path/to/new_version.py",
  "patch": "--- old_version.py\n+++ new_version.py\n@@ -1,3 +1,3 @@\n line1\n-line2\n+line2 modified\n line3\n",
  "changes": {
    "lines_added": 1,
    "lines_removed": 1,
    "hunks": 1
  },
  "message": "Generated patch from file comparison"
}
```

#### Return Value - Failure

```json
{
  "success": false,
  "error": "Original file not found: /path/to/old_version.py",
  "error_type": "file_not_found"
}
```

#### Documentation

Generate a unified diff patch by comparing two files.

**USE CASES**:
- Capture changes made to a file
- Create patches for distribution
- Document differences between versions
- Generate patches programmatically
- Compare before/after states

**WORKFLOW EXAMPLES**:

*Example 1 - Capture manual edits*:
1. Make a backup: `backup_file("config.py")` → creates `config.py.backup.123`
2. User manually edits `config.py`
3. Generate patch: `generate_patch("config.py.backup.123", "config.py")`
4. Save the patch for later reuse

*Example 2 - Compare versions*:
1. Have `old_version.py` and `new_version.py`
2. Generate patch: `generate_patch("old_version.py", "new_version.py")`
3. Apply patch to other files: `apply_patch("production.py", patch)`

**THE GENERATED PATCH**:
- Is in unified diff format
- Can be applied with `apply_patch`
- Can be saved to a file for version control
- Can be shared with other developers
- Shows exactly what changed between the files

**SPECIAL CASES**:
- If files are identical, generates an empty patch (no hunks)
- Binary files are rejected with `error_type: "binary_file"`
- Symlinks are rejected with `error_type: "symlink_error"`

#### Example

```python
{
  "original_file": "config_v1.py",
  "modified_file": "config_v2.py"
}

# Response
{
  "success": true,
  "original_file": "config_v1.py",
  "modified_file": "config_v2.py",
  "patch": "--- config_v1.py\n+++ config_v2.py\n@@ -1,5 +1,6 @@\n DEBUG = False\n-LOG_LEVEL = 'INFO'\n+LOG_LEVEL = 'DEBUG'\n+LOG_FORMAT = 'json'\n PORT = 8000\n TIMEOUT = 30\n",
  "changes": {
    "lines_added": 2,
    "lines_removed": 1,
    "hunks": 1
  },
  "message": "Generated patch from file comparison"
}
```

---

### Tool 5: inspect_patch

#### Parameters

```json
{
  "patch": {
    "type": "string",
    "description": "Unified diff patch content to analyze",
    "required": true
  }
}
```

#### Return Value - Single File

```json
{
  "success": true,
  "valid": true,
  "files": [
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
  },
  "message": "Patch analysis complete"
}
```

#### Return Value - Multiple Files

```json
{
  "success": true,
  "valid": true,
  "files": [
    {
      "source": "config.py",
      "target": "config.py",
      "hunks": 2,
      "lines_added": 5,
      "lines_removed": 3
    },
    {
      "source": "utils.py",
      "target": "utils.py",
      "hunks": 1,
      "lines_added": 10,
      "lines_removed": 2
    }
  ],
  "summary": {
    "total_files": 2,
    "total_hunks": 3,
    "total_lines_added": 15,
    "total_lines_removed": 5
  },
  "message": "Patch analysis complete"
}
```

#### Return Value - Invalid Patch

```json
{
  "success": false,
  "valid": false,
  "error": "Invalid patch format: missing --- header at line 1",
  "error_type": "invalid_patch",
  "message": "Patch is not valid"
}
```

#### Documentation

Analyze and inspect a patch without requiring any files.

**MULTI-FILE SUPPORT**: This tool supports patches containing changes to multiple files. All files are analyzed and returned in the `files` array.

**DIFFERENCES FROM validate_patch**:
- `inspect_patch`: Analyzes patch structure only, no file needed
- `validate_patch`: Checks if patch can be applied to a specific file

**COMPARISON TABLE**:

| Feature | inspect_patch | validate_patch |
|---------|---------------|----------------|
| Requires file? | ❌ No | ✅ Yes |
| Checks patch format? | ✅ Yes | ✅ Yes |
| Checks context match? | ❌ No | ✅ Yes |
| Returns can_apply? | ❌ No | ✅ Yes |
| Shows file info? | ✅ Yes (from patch) | ❌ No (single file) |
| Multi-file support? | ✅ Yes | ❌ No |
| Read-only? | ✅ Yes | ✅ Yes |

**WHEN TO USE**:

*Use inspect_patch when*:
- You received a patch and don't know what it does
- You need to see which files the patch affects
- You don't have the target files yet
- You need statistics before deciding whether to apply
- You want to analyze a multi-file patch

*Use validate_patch when*:
- You know which file to apply the patch to
- You need to verify the patch will work on a specific file
- You want to check if context matches current file state
- You're about to call apply_patch and need confirmation
- You need the "reason" why a patch can't be applied

**TYPICAL WORKFLOW**:
1. `inspect_patch(patch)` → "This affects config.py and utils.py"
2. `validate_patch("config.py", patch)` → "Can apply to config.py? Yes"
3. `validate_patch("utils.py", patch)` → "Can apply to utils.py? Yes"
4. `apply_patch("config.py", patch)` → Apply changes
5. `apply_patch("utils.py", patch)` → Apply changes

**WHAT IT TELLS YOU**:
- Which files are affected (source and target names)
- How many hunks are in each file
- Lines added/removed per file
- Total statistics across all files
- Whether the patch format is valid (unified diff)

#### Example

```python
# Single file patch
{
  "patch": """--- config.py
+++ config.py
@@ -1,3 +1,4 @@
 DEBUG = False
+VERBOSE = True
 PORT = 8000
"""
}

# Response
{
  "success": true,
  "valid": true,
  "files": [
    {
      "source": "config.py",
      "target": "config.py",
      "hunks": 1,
      "lines_added": 1,
      "lines_removed": 0
    }
  ],
  "summary": {
    "total_files": 1,
    "total_hunks": 1,
    "total_lines_added": 1,
    "total_lines_removed": 0
  },
  "message": "Patch analysis complete"
}

# Multi-file patch
{
  "patch": """--- file1.py
+++ file1.py
@@ -1,1 +1,1 @@
-old
+new
--- file2.py
+++ file2.py
@@ -1,1 +1,2 @@
 existing
+added
"""
}

# Response
{
  "success": true,
  "valid": true,
  "files": [
    {"source": "file1.py", "hunks": 1, "lines_added": 1, "lines_removed": 1},
    {"source": "file2.py", "hunks": 1, "lines_added": 1, "lines_removed": 0}
  ],
  "summary": {
    "total_files": 2,
    "total_hunks": 2,
    "total_lines_added": 2,
    "total_lines_removed": 1
  }
}
```

---

### Tool 6: backup_file

#### Parameters

```json
{
  "file_path": {
    "type": "string",
    "description": "Path to the file to backup",
    "required": true
  }
}
```

#### Return Value - Success

```json
{
  "success": true,
  "original_file": "/path/to/config.py",
  "backup_file": "/path/to/config.py.backup.20250117_143052",
  "backup_size": 1024,
  "message": "Backup created successfully"
}
```

#### Return Value - Failure

```json
{
  "success": false,
  "original_file": "/path/to/config.py",
  "error": "File not found: /path/to/config.py",
  "error_type": "file_not_found"
}
```

#### Documentation

Create a timestamped backup copy of a file before modifying it.

**BACKUP NAMING FORMAT**:
- Original: `/path/to/file.py`
- Backup: `/path/to/file.py.backup.YYYYMMDD_HHMMSS`
- Example: `config.py.backup.20250117_143052`

**RECOMMENDED WORKFLOWS**:

*Workflow 1 - Safe single patch*:
1. `backup_file("important.py")`
2. `validate_patch("important.py", patch)`
3. `apply_patch("important.py", patch)`
4. If problems: `restore_backup(backup_file)`

*Workflow 2 - Multiple patches*:
1. `backup_file("file.py")`
2. For each patch: `validate_patch("file.py", patch)`
3. If all valid: For each patch: `apply_patch("file.py", patch)`

*Workflow 3 - Experimental changes*:
1. `backup_file("module.py")`
2. `apply_patch("module.py", experimental_patch)`
3. Test the changes
4. If bad: `restore_backup(backup_file)`
5. If good: keep changes, optionally delete backup

**WHY USE THIS TOOL**:
- Explicit backup creation (LLM knows backup exists)
- Standardized naming (easy to find backups)
- Automatic timestamps (prevents overwrites)
- Returns backup path (for restoration if needed)

**CHARACTERISTICS**:
- Creates backup in same directory (needs write permission)
- Preserves file permissions and timestamps
- Does not automatically restore (use `restore_backup`)
- Does not manage backup cleanup (old backups remain)
- Returns backup size for verification

#### Example

```python
{
  "file_path": "database.py"
}

# Response
{
  "success": true,
  "original_file": "database.py",
  "backup_file": "database.py.backup.20250117_143052",
  "backup_size": 2048,
  "message": "Backup created successfully"
}

# Workflow example
backup_result = backup_file("config.py")
# Returns: {"backup_file": "config.py.backup.20250117_143052", ...}

patch_result = apply_patch("config.py", patch)

if not patch_result["success"]:
    # Restore from backup
    restore_backup(backup_result["backup_file"])
```

---

### Tool 7: restore_backup

#### Parameters

```json
{
  "backup_file": {
    "type": "string",
    "description": "Path to the backup file to restore from",
    "required": true
  },
  "target_file": {
    "type": "string",
    "description": "Path where the backup should be restored (optional, defaults to original location)",
    "required": false
  },
  "force": {
    "type": "boolean",
    "description": "Overwrite target even if it has been modified (default: false)",
    "required": false,
    "default": false
  }
}
```

#### Return Value - Success

```json
{
  "success": true,
  "backup_file": "/path/to/config.py.backup.20250117_143052",
  "restored_to": "/path/to/config.py",
  "restored_size": 1024,
  "message": "Successfully restored from backup"
}
```

#### Return Value - Failure

```json
{
  "success": false,
  "backup_file": "/path/to/config.py.backup.20250117_143052",
  "error": "Backup file not found",
  "error_type": "file_not_found"
}
```

#### Documentation

Restore a file from a timestamped backup.

**RESTORE BEHAVIOR**:
- By default, restores to the original file location (derived from backup filename)
- Can optionally specify a different `target_file` location
- Checks if target has been modified since backup (unless `force=true`)
- Preserves file permissions and timestamps from backup

**TARGET DETECTION**:
- Backup format: `/path/to/file.py.backup.YYYYMMDD_HHMMSS`
- Auto-detected target: `/path/to/file.py`
- Override with `target_file` parameter if needed

**SAFETY CHECKS**:
- Verifies backup file exists and is readable
- Checks target location is writable
- Warns if target has been modified (unless `force=true`)
- Creates parent directories if needed

**RECOMMENDED WORKFLOWS**:

*Workflow 1 - Simple restore after failed patch*:
```python
backup = backup_file("config.py")
result = apply_patch("config.py", patch)
if not result["success"]:
    restore_backup(backup["backup_file"])
```

*Workflow 2 - Restore to different location*:
```python
backup = backup_file("production.conf")
restore_backup(backup["backup_file"], target_file="production.conf.recovered")
```

*Workflow 3 - Force restore even if modified*:
```python
backup = backup_file("data.json")
# File gets modified multiple times
restore_backup(backup["backup_file"], force=True)  # Overwrite changes
```

**COMPARISON WITH MANUAL RESTORATION**:

| Feature | restore_backup | Read + Write |
|---------|----------------|--------------|
| Auto-detect target | ✅ Yes | ❌ No (manual) |
| Modification check | ✅ Yes | ❌ No |
| Permission check | ✅ Yes | ⚠️ Partial |
| Error reporting | ✅ Detailed | ⚠️ Basic |
| Atomic operation | ✅ Yes | ❌ No |
| Preserve metadata | ✅ Yes | ❌ No |

**WHEN TO USE**:
- Automated recovery workflows
- After failed patch applications
- Rollback mechanisms in testing
- Disaster recovery procedures

#### Example

```python
# Example 1: Simple restore
{
  "backup_file": "config.py.backup.20250117_143052"
}

# Response
{
  "success": true,
  "backup_file": "config.py.backup.20250117_143052",
  "restored_to": "config.py",
  "restored_size": 1024,
  "message": "Successfully restored from backup"
}

# Example 2: Restore to different location
{
  "backup_file": "app.py.backup.20250117_143052",
  "target_file": "app_recovered.py"
}

# Example 3: Force overwrite
{
  "backup_file": "data.json.backup.20250117_143052",
  "force": true
}

# Complete workflow
backup_result = backup_file("important.py")
# {"backup_file": "important.py.backup.20250117_143052", ...}

patch_result = apply_patch("important.py", experimental_patch)

if not patch_result["success"]:
    restore_result = restore_backup(backup_result["backup_file"])
    print(f"Restored from backup: {restore_result['message']}")
```

---

## Security Implementation

### Overview

All file operations include comprehensive security checks to prevent unauthorized access, resource exhaustion, and other security issues.

### Security Utilities

#### File Safety Validation

```python
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

def validate_file_safety(
    file_path: Path,
    check_write: bool = False,
    check_space: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Comprehensive file safety validation.

    Returns None if all checks pass, error dict otherwise.
    """
    # Check exists
    if not file_path.exists():
        return {
            "error": f"File not found: {file_path}",
            "error_type": "file_not_found"
        }

    # Check is regular file
    if not file_path.is_file():
        return {
            "error": f"Not a regular file: {file_path}",
            "error_type": "io_error"
        }

    # Security: Check for symlinks
    if file_path.is_symlink():
        return {
            "error": f"Symlinks are not allowed (security policy): {file_path}",
            "error_type": "symlink_error"
        }

    # Check if binary file
    if is_binary_file(file_path):
        return {
            "error": f"Binary files are not supported: {file_path}",
            "error_type": "binary_file"
        }

    # Check file size limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        return {
            "error": f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})",
            "error_type": "resource_limit"
        }

    # Check write permission if needed
    if check_write:
        if not os.access(file_path, os.W_OK):
            return {
                "error": f"File is not writable: {file_path}",
                "error_type": "permission_denied"
            }

    # Check disk space if needed
    if check_space:
        try:
            disk_usage = shutil.disk_usage(file_path.parent)
            free_space = disk_usage.free
            MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB

            if free_space < MIN_FREE_SPACE:
                return {
                    "error": f"Insufficient disk space: {free_space} bytes free (minimum: {MIN_FREE_SPACE})",
                    "error_type": "disk_space_error"
                }

            # Also check if we have at least 10% of file size available
            safety_margin = file_size * 1.1
            if free_space < safety_margin:
                return {
                    "error": f"Insufficient disk space for operation: {free_space} bytes free, {safety_margin} needed",
                    "error_type": "disk_space_error"
                }
        except Exception as e:
            return {
                "error": f"Cannot check disk space: {str(e)}",
                "error_type": "io_error"
            }

    return None  # All checks passed


def is_binary_file(file_path: Path, check_bytes: int = 8192) -> bool:
    """
    Check if a file is binary.

    Returns True if file appears to be binary.
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(check_bytes)

            # Check for null bytes (strong indicator of binary)
            if b'\x00' in chunk:
                return True

            # Check for high ratio of non-text bytes
            text_chars = bytes(range(32, 127)) + b'\n\r\t\b'
            non_text = sum(1 for byte in chunk if byte not in text_chars)

            # If more than 30% non-text characters, likely binary
            if len(chunk) > 0 and (non_text / len(chunk)) > 0.3:
                return True

            return False
    except Exception:
        # If we can't read it, assume binary
        return True


def check_path_traversal(file_path: str, base_dir: str) -> Optional[Dict[str, Any]]:
    """
    Check if a path attempts to escape a base directory.

    Returns None if safe, error dict if path escapes base_dir.
    """
    try:
        # Resolve to absolute paths
        abs_file = Path(file_path).resolve()
        abs_base = Path(base_dir).resolve()

        # Check if file path is under base directory
        try:
            abs_file.relative_to(abs_base)
            return None  # Path is safe
        except ValueError:
            return {
                "error": f"Path attempts to escape base directory: {file_path}",
                "error_type": "permission_denied"
            }
    except Exception as e:
        return {
            "error": f"Invalid path: {str(e)}",
            "error_type": "io_error"
        }


def atomic_file_replace(source: Path, target: Path) -> None:
    """
    Atomically replace a file using rename.

    Raises OSError if atomic replace fails.
    """
    import platform

    if platform.system() == 'Windows':
        # Windows: need to remove target first (not atomic)
        if target.exists():
            target.unlink()
        source.rename(target)
    else:
        # Unix: atomic rename
        source.rename(target)
```

### Security Checklist

✅ **Symlink Detection**: All tools reject symbolic links (security policy)
✅ **Binary File Detection**: Binary files detected and rejected
✅ **File Size Limits**: 10MB default limit enforced
✅ **Disk Space Validation**: 100MB minimum free space required
✅ **Path Traversal Protection**: Paths validated against base directory
✅ **Permission Validation**: Read/write permissions checked before operations
✅ **Atomic Operations**: File replacements use atomic rename where possible

### Configuration

```python
# Security Configuration (adjust as needed)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB
BINARY_CHECK_BYTES = 8192
NON_TEXT_THRESHOLD = 0.3  # 30% non-text chars = binary
```

---

## Implementation Guidelines

### Project Structure

```
patch_mcp/
├── src/
│   ├── patch_mcp/
│   │   ├── __init__.py
│   │   ├── server.py          # MCP server implementation
│   │   ├── models.py           # Data models (Pydantic)
│   │   ├── utils.py            # Security utilities
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── apply.py        # apply_patch implementation
│   │       ├── validate.py     # validate_patch implementation
│   │       ├── revert.py       # revert_patch implementation
│   │       ├── generate.py     # generate_patch implementation
│   │       ├── inspect.py      # inspect_patch implementation
│   │       └── backup.py       # backup_file + restore_backup
├── tests/
│   ├── test_models.py
│   ├── test_security.py
│   ├── test_apply.py
│   ├── test_validate.py
│   ├── test_revert.py
│   ├── test_generate.py
│   ├── test_inspect.py
│   ├── test_backup.py
│   └── integration/
│       ├── test_workflows.py
│       └── test_error_recovery.py
├── pyproject.toml
├── README.md
├── project_design.md           # This file
└── .gitignore
```

### Dependencies (pyproject.toml)

```toml
[project]
name = "patch-mcp"
version = "2.0.0"
description = "MCP server for applying unified diff patches with comprehensive security"
requires-python = ">=3.10"
dependencies = [
    "patch-ng>=1.19.0",
    "pydantic>=2.0.0",
    "mcp>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --cov=src/patch_mcp --cov-report=html --cov-report=term"
```

### Data Models

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class ErrorType(str, Enum):
    """Standard error types."""
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_PATCH = "invalid_patch"
    CONTEXT_MISMATCH = "context_mismatch"
    ENCODING_ERROR = "encoding_error"
    IO_ERROR = "io_error"
    SYMLINK_ERROR = "symlink_error"
    BINARY_FILE = "binary_file"
    DISK_SPACE_ERROR = "disk_space_error"
    RESOURCE_LIMIT = "resource_limit"

class PatchChanges(BaseModel):
    """Statistics about patch changes."""
    lines_added: int = Field(..., ge=0, description="Number of lines added")
    lines_removed: int = Field(..., ge=0, description="Number of lines removed")
    hunks_applied: int = Field(..., ge=0, description="Number of hunks applied")

class AffectedLineRange(BaseModel):
    """Line range affected by patch."""
    start: int = Field(..., ge=1, description="Starting line number")
    end: int = Field(..., ge=1, description="Ending line number")

class FileInfo(BaseModel):
    """Information about a file in a patch."""
    source: str = Field(..., description="Source filename")
    target: str = Field(..., description="Target filename")
    hunks: int = Field(..., ge=0, description="Number of hunks")
    lines_added: int = Field(..., ge=0, description="Lines added")
    lines_removed: int = Field(..., ge=0, description="Lines removed")

class PatchSummary(BaseModel):
    """Summary statistics for multi-file patches."""
    total_files: int = Field(..., ge=0)
    total_hunks: int = Field(..., ge=0)
    total_lines_added: int = Field(..., ge=0)
    total_lines_removed: int = Field(..., ge=0)

class ToolResult(BaseModel):
    """Standard result format for all tools."""
    success: bool
    message: str
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
```

### MCP Server Registration

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

server = Server("patch-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all 7 available tools."""
    return [
        Tool(
            name="apply_patch",
            description="Apply a unified diff patch to a file (supports dry_run)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to patch"
                    },
                    "patch": {
                        "type": "string",
                        "description": "Unified diff patch content"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Validate without modifying (default: false)",
                        "default": False
                    }
                },
                "required": ["file_path", "patch"]
            }
        ),
        Tool(
            name="validate_patch",
            description="Check if a patch can be applied (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "patch": {"type": "string"}
                },
                "required": ["file_path", "patch"]
            }
        ),
        Tool(
            name="revert_patch",
            description="Reverse a previously applied patch",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "patch": {"type": "string"}
                },
                "required": ["file_path", "patch"]
            }
        ),
        Tool(
            name="generate_patch",
            description="Generate a patch from two files",
            inputSchema={
                "type": "object",
                "properties": {
                    "original_file": {"type": "string"},
                    "modified_file": {"type": "string"}
                },
                "required": ["original_file", "modified_file"]
            }
        ),
        Tool(
            name="inspect_patch",
            description="Analyze patch content (supports multi-file patches)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patch": {"type": "string"}
                },
                "required": ["patch"]
            }
        ),
        Tool(
            name="backup_file",
            description="Create a timestamped backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="restore_backup",
            description="Restore a file from backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "backup_file": {"type": "string"},
                    "target_file": {"type": "string"},
                    "force": {"type": "boolean", "default": False}
                },
                "required": ["backup_file"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to appropriate implementations."""
    from .tools import (
        apply, validate, revert, generate,
        inspect, backup
    )

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
    elif name == "revert_patch":
        result = revert.revert_patch(
            arguments["file_path"],
            arguments["patch"]
        )
    elif name == "generate_patch":
        result = generate.generate_patch(
            arguments["original_file"],
            arguments["modified_file"]
        )
    elif name == "inspect_patch":
        result = inspect.inspect_patch(arguments["patch"])
    elif name == "backup_file":
        result = backup.backup_file(arguments["file_path"])
    elif name == "restore_backup":
        result = backup.restore_backup(
            arguments["backup_file"],
            arguments.get("target_file"),
            arguments.get("force", False)
        )
    else:
        raise ValueError(f"Unknown tool: {name}")

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]
```

### Code Style Best Practices

1. **Type Hints Everywhere**: Use Python 3.10+ type hints for all function signatures
2. **Pydantic Models**: Use Pydantic for data validation and serialization
3. **Pathlib**: Use `pathlib.Path` instead of string manipulation
4. **Comprehensive Logging**: Log all operations with appropriate levels
5. **Error Handling**: Always return structured error responses with `error_type`
6. **Security First**: Call `validate_file_safety()` before all file operations

---

## Testing Strategy

### Unit Tests

#### Test Coverage Requirements

- **Minimum Coverage**: 90% for all modules
- **Critical Paths**: 100% coverage for security utilities and core tools

#### Test Organization

```
tests/
├── test_models.py           # Data models and enums
├── test_security.py         # Security utilities
├── test_apply.py            # apply_patch (including dry_run)
├── test_validate.py         # validate_patch
├── test_revert.py           # revert_patch
├── test_generate.py         # generate_patch
├── test_inspect.py          # inspect_patch (single and multi-file)
├── test_backup.py           # backup_file + restore_backup
└── integration/
    ├── test_workflows.py    # Complete workflow tests
    └── test_error_recovery.py  # Error recovery patterns
```

#### Critical Test Cases

**Security Tests** (`test_security.py`):
```python
def test_reject_symlink()
def test_reject_binary_file()
def test_file_size_limit()
def test_insufficient_disk_space()
def test_path_traversal_protection()
```

**Edge Cases** (`test_apply.py`):
```python
def test_empty_patch()
def test_whitespace_only_changes()
def test_crlf_line_endings()
def test_dry_run_success()
def test_dry_run_failure()
```

**Multi-file Support** (`test_inspect.py`):
```python
def test_inspect_single_file()
def test_inspect_multiple_files()
def test_inspect_invalid_patch()
```

**Backup/Restore** (`test_backup.py`):
```python
def test_backup_create()
def test_restore_success()
def test_restore_to_different_location()
def test_restore_with_force()
def test_restore_backup_not_found()
```

### Integration Tests

```python
def test_full_workflow_safe_patch():
    """Test: validate → backup → apply → success."""

def test_full_workflow_with_recovery():
    """Test: backup → apply (fail) → restore."""

def test_batch_atomic_workflow():
    """Test: validate all → backup all → apply all."""

def test_error_recovery_try_revert():
    """Test Pattern 1: Try-Revert."""

def test_error_recovery_backup_restore():
    """Test Pattern 2: Backup-Restore."""
```

---

## Error Recovery Patterns

### Pattern 1: Try-Revert (Sequential Patches)

Apply multiple patches sequentially, reverting all on first failure.

```python
def apply_patches_with_revert(file_path: str, patches: list[str]) -> Dict[str, Any]:
    """
    Apply multiple patches sequentially, reverting all on first failure.

    Returns:
        Dict with success status and details
    """
    applied_patches = []

    try:
        for i, patch in enumerate(patches):
            logger.info(f"Applying patch {i+1}/{len(patches)}")
            result = apply_patch(file_path, patch)

            if not result["success"]:
                logger.error(f"Patch {i+1} failed: {result['error']}")

                # Revert all previously applied patches
                logger.info(f"Reverting {len(applied_patches)} previously applied patches")
                for applied_patch in reversed(applied_patches):
                    revert_result = revert_patch(file_path, applied_patch)
                    if not revert_result["success"]:
                        logger.error(f"CRITICAL: Revert failed: {revert_result['error']}")
                        raise Exception("Cannot revert patches - manual intervention required")

                return {
                    "success": False,
                    "patches_applied": len(applied_patches),
                    "failed_at": i + 1,
                    "error": result["error"],
                    "reverted": True
                }

            applied_patches.append(patch)

        return {
            "success": True,
            "patches_applied": len(applied_patches),
            "message": f"Successfully applied {len(applied_patches)} patches"
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "patches_applied": len(applied_patches),
            "error": str(e),
            "reverted": False
        }
```

### Pattern 2: Backup-Restore (Safe Experimentation)

Apply patch with automatic backup and restore on failure.

```python
def apply_patch_with_backup(
    file_path: str,
    patch: str,
    keep_backup: bool = False
) -> Dict[str, Any]:
    """
    Apply patch with automatic backup and restore on failure.

    Args:
        file_path: Target file
        patch: Patch to apply
        keep_backup: Keep backup even on success

    Returns:
        Dict with success status
    """
    # Create backup
    backup_result = backup_file(file_path)
    if not backup_result["success"]:
        return {
            "success": False,
            "error": f"Cannot create backup: {backup_result['error']}",
            "phase": "backup"
        }

    backup_path = backup_result["backup_file"]
    logger.info(f"Created backup: {backup_path}")

    try:
        # Apply patch
        result = apply_patch(file_path, patch)

        if not result["success"]:
            # Restore from backup
            logger.warning("Patch failed, restoring from backup")
            restore_result = restore_backup(backup_path)

            if not restore_result["success"]:
                logger.error(f"CRITICAL: Cannot restore backup: {restore_result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "restore_failed": True,
                    "backup_file": backup_path,
                    "phase": "restore"
                }

            # Clean up backup after successful restore
            Path(backup_path).unlink()

            return {
                "success": False,
                "error": result["error"],
                "restored": True,
                "phase": "apply"
            }

        # Success - optionally clean up backup
        if not keep_backup:
            Path(backup_path).unlink()
            logger.info("Removed backup after successful apply")

        return {
            "success": True,
            "backup_file": backup_path if keep_backup else None,
            "message": "Patch applied successfully"
        }

    except Exception as e:
        # Emergency restore
        logger.error(f"Unexpected error: {str(e)}, attempting restore")
        try:
            restore_backup(backup_path)
            logger.info("Emergency restore successful")
        except:
            logger.error("CRITICAL: Emergency restore failed")

        return {
            "success": False,
            "error": str(e),
            "phase": "unexpected",
            "backup_file": backup_path
        }
```

### Pattern 3: Validate-All-Then-Apply (Atomic Batch)

Apply multiple patches atomically - all or nothing.

```python
def apply_patches_atomic(file_patch_pairs: list[tuple[str, str]]) -> Dict[str, Any]:
    """
    Apply multiple patches atomically - all or nothing.

    Args:
        file_patch_pairs: List of (file_path, patch) tuples

    Returns:
        Dict with success status
    """
    # Phase 1: Validate all patches
    logger.info(f"Validating {len(file_patch_pairs)} patches")
    validations = []

    for file_path, patch in file_patch_pairs:
        result = validate_patch(file_path, patch)
        validations.append((file_path, result))

        if not result["can_apply"]:
            logger.error(f"Validation failed for {file_path}: {result.get('reason')}")

    # Check if all valid
    failures = [(fp, v) for fp, v in validations if not v["can_apply"]]
    if failures:
        return {
            "success": False,
            "phase": "validation",
            "validated": len(validations),
            "failed": len(failures),
            "failures": [
                {"file": fp, "reason": v.get("reason")}
                for fp, v in failures
            ]
        }

    logger.info("All patches validated successfully")

    # Phase 2: Create backups for all files
    logger.info("Creating backups")
    backups = {}

    try:
        for file_path, _ in file_patch_pairs:
            backup_result = backup_file(file_path)
            if not backup_result["success"]:
                raise Exception(f"Backup failed for {file_path}: {backup_result['error']}")
            backups[file_path] = backup_result["backup_file"]

        logger.info(f"Created {len(backups)} backups")

        # Phase 3: Apply all patches
        logger.info("Applying patches")
        applied = []

        for file_path, patch in file_patch_pairs:
            result = apply_patch(file_path, patch)

            if not result["success"]:
                # Rollback: restore all backups
                logger.error(f"Apply failed for {file_path}, rolling back all changes")

                for backed_up_file, backup_path in backups.items():
                    restore_result = restore_backup(backup_path)
                    if not restore_result["success"]:
                        logger.error(f"CRITICAL: Cannot restore {backed_up_file}")

                return {
                    "success": False,
                    "phase": "apply",
                    "applied": len(applied),
                    "failed_at": file_path,
                    "error": result["error"],
                    "rolled_back": True
                }

            applied.append(file_path)

        # Success - clean up backups
        for backup_path in backups.values():
            Path(backup_path).unlink()

        logger.info(f"Successfully applied {len(applied)} patches")

        return {
            "success": True,
            "applied": len(applied),
            "message": f"Atomically applied {len(applied)} patches"
        }

    except Exception as e:
        # Emergency rollback
        logger.error(f"Critical error: {str(e)}")

        for file_path, backup_path in backups.items():
            try:
                restore_backup(backup_path)
            except:
                logger.error(f"CRITICAL: Cannot restore {file_path} from {backup_path}")

        return {
            "success": False,
            "phase": "unexpected",
            "error": str(e),
            "attempted_rollback": True
        }
```

### Pattern 4: Progressive Validation

Apply patch with step-by-step validation and detailed error reporting.

```python
def apply_patch_progressive(file_path: str, patch: str) -> Dict[str, Any]:
    """
    Apply patch with progressive validation and detailed error reporting.

    This pattern validates at each step and provides maximum information.
    """
    results = {
        "success": False,
        "steps": {}
    }

    # Step 1: Check file safety
    path = Path(file_path)
    safety_check = validate_file_safety(path, check_write=True, check_space=True)
    results["steps"]["safety_check"] = {
        "passed": safety_check is None,
        "details": safety_check
    }

    if safety_check:
        results["error"] = safety_check["error"]
        results["error_type"] = safety_check["error_type"]
        results["failed_at"] = "safety_check"
        return results

    # Step 2: Validate patch format
    validation = validate_patch(file_path, patch)
    results["steps"]["validation"] = {
        "passed": validation["can_apply"] if validation["success"] else False,
        "details": validation
    }

    if not validation.get("can_apply", False):
        results["error"] = validation.get("reason") or validation.get("error", "Validation failed")
        results["error_type"] = validation.get("error_type", "context_mismatch")
        results["failed_at"] = "validation"
        return results

    # Step 3: Create backup
    backup = backup_file(file_path)
    results["steps"]["backup"] = {
        "passed": backup["success"],
        "details": backup
    }

    if not backup["success"]:
        results["error"] = backup["error"]
        results["error_type"] = backup["error_type"]
        results["failed_at"] = "backup"
        return results

    # Step 4: Apply patch
    apply_result = apply_patch(file_path, patch)
    results["steps"]["apply"] = {
        "passed": apply_result["success"],
        "details": apply_result
    }

    if not apply_result["success"]:
        # Step 5: Restore from backup
        restore_result = restore_backup(backup["backup_file"])
        results["steps"]["restore"] = {
            "passed": restore_result["success"],
            "details": restore_result
        }

        results["error"] = apply_result["error"]
        results["error_type"] = apply_result["error_type"]
        results["failed_at"] = "apply"
        return results

    # Success!
    results["success"] = True
    results["backup_file"] = backup["backup_file"]
    results["changes"] = apply_result["changes"]

    return results
```

---

## Example Workflows

### Workflow 1: Safe Single Patch Application

```python
# Step 1: Validate patch
validation = validate_patch("config.py", patch)
if not validation["success"] or not validation["can_apply"]:
    print(f"Cannot apply: {validation.get('reason', validation.get('error'))}")
    exit(1)

# Step 2: Create backup
backup = backup_file("config.py")
print(f"Created backup: {backup['backup_file']}")

# Step 3: Apply patch
result = apply_patch("config.py", patch)

if not result["success"]:
    # Restore from backup
    print("Patch failed, restoring from backup")
    restore_backup(backup["backup_file"])
else:
    print(f"Successfully applied patch: {result['changes']}")
```

### Workflow 2: Dry Run Test Before Apply

```python
# Test without modifying
dry_result = apply_patch("app.py", patch, dry_run=True)

if dry_result["success"]:
    print(f"Dry run successful, would change {dry_result['changes']['lines_added']} lines")

    # Now apply for real
    backup = backup_file("app.py")
    real_result = apply_patch("app.py", patch)

    if real_result["success"]:
        print("Patch applied successfully")
    else:
        restore_backup(backup["backup_file"])
else:
    print(f"Dry run failed: {dry_result['error']}")
```

### Workflow 3: Batch Atomic Application

```python
patches = [
    ("file1.py", patch1),
    ("file2.py", patch2),
    ("file3.py", patch3),
]

# Use atomic pattern
result = apply_patches_atomic(patches)

if result["success"]:
    print(f"Applied {result['applied']} patches atomically")
else:
    print(f"Failed at phase: {result['phase']}")
    if "failures" in result:
        for failure in result["failures"]:
            print(f"  {failure['file']}: {failure['reason']}")
```

### Workflow 4: Inspect and Apply Multi-file Patch

```python
# Step 1: Inspect unknown patch
patch_content = read_file("changes.patch")
info = inspect_patch(patch_content)

print(f"Patch affects {info['summary']['total_files']} files:")
for file_info in info["files"]:
    print(f"  - {file_info['target']}: +{file_info['lines_added']} -{file_info['lines_removed']}")

# Step 2: Validate each file
for file_info in info["files"]:
    validation = validate_patch(file_info["target"], patch_content)
    if not validation["can_apply"]:
        print(f"Cannot apply to {file_info['target']}: {validation['reason']}")
        exit(1)

# Step 3: Apply to all files
for file_info in info["files"]:
    backup = backup_file(file_info["target"])
    result = apply_patch(file_info["target"], patch_content)
    if not result["success"]:
        restore_backup(backup["backup_file"])
        print(f"Failed on {file_info['target']}")
        exit(1)

print("All patches applied successfully")
```

### Workflow 5: Generate and Distribute Patch

```python
# Step 1: Generate patch from development changes
dev_patch = generate_patch("config.py.old", "config.py.new")
patch_content = dev_patch["patch"]

# Step 2: Save patch
write_file("config_update.patch", patch_content)

# Step 3: Later, apply to production
production_patch = read_file("config_update.patch")

# Validate first
validation = validate_patch("production_config.py", production_patch)
if not validation["can_apply"]:
    print(f"Cannot apply to production: {validation['reason']}")
    exit(1)

# Apply with backup
backup = backup_file("production_config.py")
result = apply_patch("production_config.py", production_patch)

if not result["success"]:
    restore_backup(backup["backup_file"])
    print("Production update failed, restored from backup")
else:
    print(f"Production updated: {result['changes']}")
```

---

## Migration Guide

### For Existing Implementations

If you've already implemented based on an earlier version of this design, here are the changes you need to make:

#### 1. validate_patch Return Value Change

**OLD** (incorrect):
```python
{
  "success": true,  # WRONG - was true even when can't apply
  "can_apply": false,
  "reason": "..."
}
```

**NEW** (correct):
```python
{
  "success": false,  # Correct - false when can't apply
  "can_apply": false,
  "reason": "...",
  "error_type": "context_mismatch"  # Added
}
```

**Migration**:
```python
# Update your code:
result = validate_patch(file, patch)

# OLD: if result["success"] and not result["can_apply"]:
# NEW: if not result["success"] and result.get("valid"):
    # Handle context mismatch
```

#### 2. inspect_patch Return Value Change

**OLD** (single file only):
```python
{
  "success": true,
  "file": {  # Single object
    "source": "config.py",
    "hunks": 2,
    ...
  }
}
```

**NEW** (multi-file support):
```python
{
  "success": true,
  "files": [  # Array of files
    {
      "source": "config.py",
      "hunks": 2,
      ...
    }
  ],
  "summary": {  # New field
    "total_files": 1,
    ...
  }
}
```

**Migration**:
```python
# Update your code:
result = inspect_patch(patch)

# OLD: file_info = result["file"]
# NEW: file_info = result["files"][0]  # First file
# NEW: for file_info in result["files"]:  # All files
```

#### 3. New Error Types to Handle

Add these new error types to your error handling:
```python
ERROR_TYPES = [
    # Existing
    "file_not_found",
    "permission_denied",
    "invalid_patch",
    "context_mismatch",
    "encoding_error",
    "io_error",
    # NEW
    "symlink_error",
    "binary_file",
    "disk_space_error",
    "resource_limit",
]
```

#### 4. New Tool to Implement

Implement the new `restore_backup` tool:
```python
def restore_backup(
    backup_file: str,
    target_file: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """Restore from backup."""
    # See tool specification above
    pass
```

#### 5. Add dry_run Parameter

Update `apply_patch` to support dry_run:
```python
def apply_patch(
    file_path: str,
    patch: str,
    dry_run: bool = False  # NEW parameter
) -> Dict[str, Any]:
    if dry_run:
        # Validate only, don't modify
        pass
    else:
        # Apply normally
        pass
```

#### 6. Add Security Checks

Add security validation before all file operations:
```python
def apply_patch(file_path: str, patch: str, dry_run: bool = False):
    path = Path(file_path)

    # NEW: Security checks
    safety_error = validate_file_safety(
        path,
        check_write=not dry_run,
        check_space=not dry_run
    )
    if safety_error:
        return {
            "success": False,
            **safety_error
        }

    # Continue with normal operation
    ...
```

### Breaking Changes Summary

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| validate_patch success field | **Breaking** | Medium - update all callers |
| inspect_patch file → files | **Breaking** | Low - simple field rename |
| New error types | **Additive** | Low - add to error handlers |
| restore_backup tool | **Additive** | Medium - implement new tool |
| dry_run parameter | **Additive** | Low - optional parameter |
| Security checks | **Additive** | Medium - add validation calls |

### Version History

- **v1.0**: Original design (6 tools, old semantics)
- **v2.0**: Current design (7 tools, fixed semantics, enhanced security)

---

## Quick Reference

### Essential Workflow

```python
# The fundamental safe patching workflow:
1. inspect_patch(patch)           # What does it do?
2. validate_patch(file, patch)    # Can I apply it?
3. backup_file(file)              # Save current state
4. apply_patch(file, patch)       # Do it
5. restore_backup(backup)         # Undo if needed (if failed)
```

### Tool Selection Guide

| Task | Use This Tool |
|------|---------------|
| Apply a patch | `apply_patch` |
| Test without modifying | `apply_patch` with `dry_run=true` |
| Check if patch will work | `validate_patch` |
| Undo a patch | `revert_patch` |
| Create patch from files | `generate_patch` |
| Understand unknown patch | `inspect_patch` |
| Multi-file patch analysis | `inspect_patch` |
| Save file before changes | `backup_file` |
| Restore after failure | `restore_backup` |

### Error Type Quick Reference

| Error Type | Meaning | Common Cause |
|------------|---------|--------------|
| `file_not_found` | File doesn't exist | Wrong path |
| `permission_denied` | Can't read/write | File permissions |
| `invalid_patch` | Bad patch format | Malformed patch |
| `context_mismatch` | Context doesn't match | File was modified |
| `encoding_error` | Encoding issue | Non-UTF-8 file |
| `io_error` | General I/O error | Filesystem issue |
| `symlink_error` | Target is symlink | Security policy |
| `binary_file` | Target is binary | Binary files not supported |
| `disk_space_error` | Not enough space | Disk full |
| `resource_limit` | File too large/timeout | Resource constraints |

### Security Checklist

✅ Symlinks rejected
✅ Binary files rejected
✅ File size limits enforced (10MB)
✅ Disk space validated (100MB minimum)
✅ Path traversal protection
✅ Permission checks
✅ Atomic operations

### Performance Tips

1. Use `validate_patch` instead of `apply_patch` + `dry_run` for pure validation
2. Batch operations with atomic pattern for multiple patches
3. Use `inspect_patch` to filter patches before validation
4. Clean up old backups periodically

---

## Summary

This design provides a comprehensive, production-ready MCP server for patch management with:

✅ **7 Tools**: 4 core + 3 optional
✅ **10 Error Types**: Comprehensive error handling
✅ **Security First**: Symlink, binary, disk space, file size checks
✅ **Multi-file Support**: inspect_patch handles complex patches
✅ **Dry Run Mode**: Test before modifying
✅ **Atomic Operations**: All-or-nothing batch processing
✅ **Error Recovery**: 4 documented recovery patterns
✅ **LLM-Friendly**: Clear docs, consistent APIs, comprehensive examples

**Deployment Options**:
- **Minimal** (4 tools): Core patching functionality
- **Optimal** (7 tools): Full-featured production environment with backup/restore

**Implementation Time**: ~8 days for complete implementation

**Test Coverage**: 90%+ with comprehensive edge case and security testing

---

*End of Document*
