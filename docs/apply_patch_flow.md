# apply_patch Function Flow Trace

Complete execution trace from LLM invocation to patch application.

**Last Updated**: 2025-01-18
**Coverage**: MCP Server → apply_patch → Security → Patch Application → Response

---

## Overview

This document traces the complete function call flow when an LLM invokes the `apply_patch` tool through the MCP server. The flow includes security validation, patch parsing, and atomic file operations.

**Key Characteristics**:
- **Security-First**: Multiple validation checkpoints
- **Atomic Operations**: Temp files + atomic rename
- **Structured Errors**: 10 distinct error types
- **Dry-Run Support**: Test without modification
- **Multi-Hunk Atomic**: All changes succeed or fail together

---

## 1. Entry Point: MCP Server

**Module**: `src/patch_mcp/server.py`

```
LLM sends MCP request
    ↓
main() (async)                                    [server.py:229]
    ↓
stdio_server() context manager                    [server.py:237]
    ↓
server.run(read_stream, write_stream)            [server.py:238]
    ↓
call_tool(name="apply_patch", arguments={...})   [server.py:176]
```

### `call_tool()` Function

**Location**: `server.py:176`

**Input**:
```python
{
  "name": "apply_patch",
  "arguments": {
    "file_path": "/path/to/file.py",
    "patch": "--- file.py\n+++ file.py\n@@ ... @@",
    "dry_run": false  # optional
  }
}
```

**Routing Logic**: Lines 191-196
```python
if name == "apply_patch":
    result = apply.apply_patch(
        arguments["file_path"],
        arguments["patch"],
        arguments.get("dry_run", False),
    )
```

**Output**: `TextContent` with JSON-formatted result (Line 226)

---

## 2. Tool Implementation: apply_patch

**Module**: `src/patch_mcp/tools/apply.py`

### Function Entry

**Signature**: `apply_patch(file_path: str, patch: str, dry_run: bool = False)`
**Location**: `apply.py:18`

### Execution Flow

```
apply_patch(file_path, patch, dry_run=False)     [apply.py:18]
    ↓
┌─────────────────────────────────────────────┐
│ PHASE 1: SECURITY VALIDATION                │
└─────────────────────────────────────────────┘
    ↓
validate_file_safety(path, check_write, check_space)  [apply.py:75]
    │                                          [utils.py:21]
    ├─ Check file exists                      [utils.py:52]
    ├─ Check is regular file                  [utils.py:56]
    ├─ Check NOT symlink (SECURITY)           [utils.py:60]
    ├─ Check NOT binary                       [utils.py:67]
    │   └─> is_binary_file(path)              [utils.py:118]
    │       ├─ Check for null bytes (0x00)
    │       ├─ Try UTF-8 decode
    │       └─ Check non-text ratio (>30% = binary)
    ├─ Check file size < 10MB                 [utils.py:79]
    ├─ Check writable (if check_write)        [utils.py:86]
    └─ Check disk space (if check_space)      [utils.py:94]
        ├─ Minimum 100MB free
        └─ Plus 110% of file size

    ↓ (If any check fails, return error immediately)

┌─────────────────────────────────────────────┐
│ PHASE 2: PATCH VALIDATION                   │
└─────────────────────────────────────────────┘
    ↓
validate_patch(file_path, patch)              [apply.py:85]
    │                                    [validate.py:19]
    ├─ validate_file_safety() (read-only)     [validate.py:88]
    ├─ Read file content                      [validate.py:98]
    ├─ Parse patch hunks                      [validate.py:115]
    ├─ Validate each hunk:
    │   ├─ Check hunk format
    │   ├─ Verify context lines match exactly
    │   └─ Calculate affected line ranges
    └─ Return validation result:
        {
          "success": True/False,
          "can_apply": True/False,
          "preview": {
            "lines_to_add": int,
            "lines_to_remove": int,
            "hunks": int,
            "affected_line_range": {"start": int, "end": int}
          },
          "reason": str  # If can_apply=False
        }

    ↓
Check validation result                        [apply.py:87]
    ├─ If failed: Return error immediately
    └─ Extract change statistics              [apply.py:98]

    ↓
┌─────────────────────────────────────────────┐
│ PHASE 3: DRY RUN CHECK                      │
└─────────────────────────────────────────────┘
    ↓
if dry_run:                                    [apply.py:106]
    Return success with preview (no modification) [apply.py:107]
    ↓
    STOP HERE (dry run complete)

    ↓
┌─────────────────────────────────────────────┐
│ PHASE 4: ACTUAL PATCH APPLICATION           │
└─────────────────────────────────────────────┘
    ↓
Read original file                             [apply.py:118]
    with open(path, "r", encoding="utf-8") as f:
        original_lines = f.readlines()

    ↓
_apply_patch_to_lines(original_lines, patch)   [apply.py:122]
    │                                          [apply.py:177]
    ├─ _parse_patch_hunks(patch)              [apply.py:209]
    │   ├─ Parse "@@" headers                 [apply.py:223]
    │   ├─ Extract source_start, source_count [apply.py:229-230]
    │   └─ Collect lines for each hunk:       [apply.py:238-248]
    │       - Add lines (starts with +)
    │       - Remove lines (starts with -)
    │       - Context lines (starts with space)
    │
    ├─ Sort hunks by line number (reverse)    [apply.py:201]
    │   # Apply from bottom to top to maintain line numbers
    │   sorted_hunks = sorted(hunks, key=lambda h: h["source_start"], reverse=True)
    │
    └─ For each hunk (bottom to top):         [apply.py:203]
        _apply_single_hunk(lines, hunk)       [apply.py:253]
        ├─ Convert to 0-based index           [apply.py:267]
        ├─ Build new section:                 [apply.py:274-284]
        │   ├─ Keep context lines
        │   ├─ Skip remove lines
        │   └─ Insert add lines
        └─ Replace section in file            [apply.py:290]
            result = lines[:start_idx] + new_section + lines[start_idx + lines_to_replace:]

    ↓ Returns: modified_lines

┌─────────────────────────────────────────────┐
│ PHASE 5: ATOMIC FILE WRITE                  │
└─────────────────────────────────────────────┘
    ↓
Create secure temp file                        [apply.py:125]
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".patch_tmp_",
        suffix=".tmp",
        text=True
    )

    ↓
Write modified content to temp file            [apply.py:131]
    with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
        f.writelines(modified_lines)

    ↓
atomic_file_replace(temp_file, target_file)    [apply.py:135]
    │                                    [utils.py:207]
    ├─ Unix/Linux/macOS:                      [utils.py:233]
    │   source.rename(target)
    │   # Atomic operation via OS rename syscall
    │
    └─ Windows:                               [utils.py:227-230]
        if target.exists():
            target.unlink()
        source.rename(target)
        # Not atomic, but best available on Windows

    ↓
Clean up temp file on error                    [apply.py:137-141]
    try:
        ...
    except Exception:
        if temp_file.exists():
            temp_file.unlink()
        raise

    ↓
Return success with changes                    [apply.py:143-149]
    {
      "success": True,
      "file_path": str(path),
      "applied": True,
      "changes": {
        "lines_added": 5,
        "lines_removed": 3,
        "hunks_applied": 2
      },
      "message": "Successfully applied patch to file.py"
    }
```

---

## 3. Response Flow

```
apply_patch() returns Dict                     [apply.py:143-149]
    {
      "success": true,
      "file_path": "...",
      "applied": true,
      "changes": {
        "lines_added": int,
        "lines_removed": int,
        "hunks_applied": int
      },
      "message": "Successfully applied patch to ..."
    }
    ↓
call_tool() wraps in TextContent               [server.py:226]
    TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )
    ↓
MCP server sends response via stdio
    ↓
LLM receives JSON response
```

---

## 4. Error Handling Paths

Throughout the flow, errors are caught and returned as structured responses with specific error types.

### Error Return Format

```python
{
  "success": false,
  "file_path": "/path/to/file.py",
  "applied": false,
  "error": "Human-readable error message",
  "error_type": "specific_error_type"
}
```

### Error Types (10 Total)

| Error Type | Trigger | Phase |
|------------|---------|-------|
| `file_not_found` | File doesn't exist | Security (Phase 1) |
| `permission_denied` | No write permission | Security (Phase 1) |
| `symlink_error` | File is a symlink | Security (Phase 1) |
| `binary_file` | File is binary | Security (Phase 1) |
| `resource_limit` | File > 10MB | Security (Phase 1) |
| `disk_space_error` | Insufficient disk space | Security (Phase 1) |
| `invalid_patch` | Malformed patch format | Validation (Phase 2) |
| `context_mismatch` | Patch context doesn't match file | Validation (Phase 2) |
| `encoding_error` | Cannot decode as UTF-8 | Application (Phase 4) |
| `io_error` | Generic I/O failure | Any phase |

### Exception Handling

**Locations**:
- `apply.py:151-174` - Catches UnicodeDecodeError, OSError, and general exceptions
- `utils.py:112-113` - Disk space check exceptions
- `utils.py:166-168` - Binary file check exceptions

**Strategy**: All exceptions are caught and converted to structured error responses. Never allows exceptions to propagate to LLM.

---

## 5. Security Validation Details

### validate_file_safety() Checklist

**Module**: `utils.py:21`

```python
def validate_file_safety(
    file_path: Path,
    check_write: bool = False,
    check_space: bool = False
) -> Optional[Dict[str, Any]]
```

**Checks (in order)**:

1. **File Exists** [Line 52]
   ```python
   if not file_path.exists():
       return {"error": "File not found", "error_type": "file_not_found"}
   ```

2. **Is Regular File** [Line 56]
   ```python
   if not file_path.is_file():
       return {"error": "Not a regular file", "error_type": "io_error"}
   ```

3. **Not a Symlink (SECURITY POLICY)** [Line 60]
   ```python
   if file_path.is_symlink():
       return {"error": "Symlinks not allowed", "error_type": "symlink_error"}
   ```
   **Rationale**: Prevents following symlinks to protected files

4. **Not Binary** [Line 67]
   ```python
   if is_binary_file(file_path):
       return {"error": "Binary files not supported", "error_type": "binary_file"}
   ```

5. **Size Limit (10MB)** [Line 79]
   ```python
   if file_size > MAX_FILE_SIZE:  # 10 * 1024 * 1024
       return {"error": "File too large", "error_type": "resource_limit"}
   ```
   **Rationale**: Prevents resource exhaustion

6. **Write Permission (if check_write)** [Line 86]
   ```python
   if not os.access(file_path, os.W_OK):
       return {"error": "File not writable", "error_type": "permission_denied"}
   ```

7. **Disk Space (if check_space)** [Line 94]
   ```python
   free_space = shutil.disk_usage(file_path.parent).free
   if free_space < MIN_FREE_SPACE:  # 100 MB
       return {"error": "Insufficient disk space", "error_type": "disk_space_error"}
   if free_space < file_size * 1.1:  # 110% safety margin
       return {"error": "Insufficient space for operation", "error_type": "disk_space_error"}
   ```

**Return**: `None` if all checks pass, otherwise error dict

---

## 6. Patch Parsing Algorithm

### Hunk Format

Unified diff format:
```diff
@@ -10,7 +10,8 @@
 context line
-removed line
+added line
 context line
```

### Parsing Logic

**Function**: `_parse_patch_hunks()` [apply.py:209]

**Steps**:

1. **Split patch into lines** [Line 220]
2. **Find hunk headers** (lines starting with `@@`) [Line 223]
   ```python
   if line.startswith("@@"):
       parts = line.split("@@")[1].strip().split()
       source_part = parts[0][1:].split(",")  # "-10,7"
       source_start = int(source_part[0])
       source_count = int(source_part[1]) if len(source_part) > 1 else 1
   ```

3. **Collect hunk lines** [Line 238-248]
   - Lines starting with `+` (but not `+++`) → Add lines
   - Lines starting with `-` (but not `---`) → Remove lines
   - Lines starting with ` ` (space) → Context lines
   - Lines starting with `\` → Ignore (no newline marker)

4. **Return hunk structures**:
   ```python
   {
       "source_start": 10,
       "source_count": 7,
       "lines": [
           ("context", "context line"),
           ("remove", "old line"),
           ("add", "new line"),
           ...
       ]
   }
   ```

### Application Logic

**Function**: `_apply_single_hunk()` [apply.py:253]

**Algorithm**:

1. **Convert to 0-based index** [Line 267]
   ```python
   start_idx = hunk["source_start"] - 1
   ```

2. **Build new section** [Line 274-284]
   ```python
   for action, content in hunk_lines:
       if action == "context":
           new_section.append(content + "\n")
           original_idx += 1
       elif action == "remove":
           original_idx += 1  # Skip (don't add to new_section)
       elif action == "add":
           new_section.append(content + "\n")
   ```

3. **Replace section** [Line 290]
   ```python
   result = (
       lines[:start_idx] +           # Before hunk
       new_section +                 # Modified section
       lines[start_idx + lines_to_replace:]  # After hunk
   )
   ```

**Why Bottom-Up?** [Line 201]
```python
sorted_hunks = sorted(hunks, key=lambda h: h["source_start"], reverse=True)
```
Applying hunks from bottom to top preserves line numbers for earlier hunks.

---

## 7. Atomic File Operations

### Why Atomic Operations Matter

**Problem**: If a write operation is interrupted (crash, power loss), the file could be corrupted.

**Solution**: Write to temp file, then atomically replace original.

### Implementation

**Function**: `atomic_file_replace()` [utils.py:207]

#### Unix/Linux/macOS (Truly Atomic)

```python
source.rename(target)  # [utils.py:233]
```

- Uses OS `rename()` syscall
- POSIX guarantees atomicity
- Target is replaced in a single operation
- No intermediate state visible to other processes

#### Windows (Best Effort)

```python
if target.exists():
    target.unlink()
source.rename(target)  # [utils.py:227-230]
```

- Windows doesn't allow atomic rename over existing file
- Must delete first, then rename
- Small window of vulnerability
- Best available option on Windows

### Temp File Creation

**Location**: `apply.py:125`

```python
temp_fd, temp_path = tempfile.mkstemp(
    dir=path.parent,      # Same directory (required for atomic rename)
    prefix=".patch_tmp_", # Hidden file
    suffix=".tmp",
    text=True
)
```

**Why same directory?** Atomic rename only works within the same filesystem.

---

## 8. Key Design Patterns

### 1. Security-First Architecture

Every operation goes through `validate_file_safety()` before any action. No file is touched without passing all security checks.

### 2. Fail-Fast Validation

The flow has multiple exit points:
- Security check failure → immediate return
- Validation failure → immediate return
- Dry-run → return without modification
- Success → apply and return

### 3. Structured Error Responses

All errors return consistent JSON with:
- `success: false`
- `error: "Human-readable message"`
- `error_type: "machine-readable-type"`

This enables AI assistants to make decisions based on error type.

### 4. Dry-Run Support

Critical for AI safety:
```python
if dry_run:
    return success_preview  # No modification
```

Allows AI to:
1. Test if patch can be applied
2. See what would change
3. Decide whether to proceed

### 5. Multi-Hunk Atomicity

All hunks in a patch are applied together or not at all. Partial application is impossible because:
- Validation checks all hunks before any application
- Application happens in-memory first
- File is only modified after all hunks succeed

### 6. Bottom-Up Hunk Application

```python
sorted_hunks = sorted(hunks, key=lambda h: h["source_start"], reverse=True)
```

Hunks are applied from bottom to top of the file. This ensures:
- Line numbers remain valid for earlier hunks
- No need to track offset adjustments
- Simpler, more reliable algorithm

---

## 9. Function Call Statistics

### Total Functions Invoked (Typical Success Path)

1. `main()` - Entry point
2. `call_tool()` - Tool routing
3. `apply_patch()` - Main logic
4. `validate_file_safety()` - Security (called twice)
5. `is_binary_file()` - Binary detection
6. `validate_patch()` - Patch validation
7. `_parse_patch_hunks()` - Parse patch
8. `_apply_patch_to_lines()` - Apply to lines
9. `_apply_single_hunk()` - Apply each hunk (×N hunks)
10. `atomic_file_replace()` - Write file

**Total**: ~15-20 function calls depending on number of hunks

### Modules Involved

1. `server.py` - MCP protocol handling
2. `tools/apply.py` - Main apply logic
3. `tools/validate.py` - Validation logic
4. `utils.py` - Security and file operations

### Exit Points (4 Total)

1. **Security failure** → Return error (Phase 1)
2. **Validation failure** → Return error (Phase 2)
3. **Dry-run success** → Return preview (Phase 3)
4. **Application success** → Return result (Phase 5)

---

## 10. Performance Characteristics

### File Operations

- **Reads**: 2 (safety check + actual read)
- **Writes**: 1 (temp file) + 1 (atomic rename)
- **Disk Space Check**: 1 (if check_space=True)

### Memory Usage

- Entire file is loaded into memory as list of lines
- Practical limit: 10MB file size (configurable via `MAX_FILE_SIZE`)
- Reasonable for text files, protects against memory exhaustion

### Algorithmic Complexity

- **Hunk parsing**: O(n) where n = patch lines
- **Hunk application**: O(m × h) where m = file lines, h = hunks
- **Overall**: O(m) for typical small patches

---

## 11. Security Summary

### Security Checkpoints (3 Total)

1. **Pre-validation** (Phase 1) - File safety before any operation
2. **Patch validation** (Phase 2) - Ensure patch can apply cleanly
3. **Atomic write** (Phase 5) - Prevent partial writes

### Attack Surface Mitigations

| Attack Vector | Mitigation | Location |
|---------------|------------|----------|
| Symlink following | Reject all symlinks | utils.py:60 |
| Path traversal | Path validation | utils.py:171 |
| Binary file corruption | Detect and reject | utils.py:67 |
| Resource exhaustion | 10MB size limit | utils.py:79 |
| Disk filling | 100MB + 110% check | utils.py:94 |
| Partial writes | Atomic operations | utils.py:207 |
| Malicious patches | Format validation | validate.py |

### No Code Execution

The server never executes code from patches:
- Patches are parsed as data, not code
- No `eval()`, `exec()`, or subprocess calls
- Pure data transformation

---

## 12. Related Documentation

- **API Reference**: [`docs/API.md`](API.md)
- **Tool Usage Guide**: [`docs/apply_patch_tool_use.md`](apply_patch_tool_use.md)
- **Project Design**: [`docs/project_design.md`](project_design.md)
- **Security Policy**: [`../SECURITY.md`](../SECURITY.md)

---

## Appendix: Example Execution Trace

### Input

```json
{
  "name": "apply_patch",
  "arguments": {
    "file_path": "/project/config.py",
    "patch": "--- config.py\n+++ config.py\n@@ -10,3 +10,3 @@\n DEBUG = False\n-PORT = 8000\n+PORT = 9000\n API_KEY = '...'",
    "dry_run": false
  }
}
```

### Execution Steps

1. ✅ Security: File exists, regular file, not symlink, not binary, size OK, writable, space OK
2. ✅ Validation: Patch format valid, context matches, can apply
3. ⏭️ Dry-run: Skip (dry_run=false)
4. ✅ Application: Parse 1 hunk, apply changes
5. ✅ Write: Create temp file, write, atomic rename
6. ✅ Return: Success with statistics

### Output

```json
{
  "success": true,
  "file_path": "/project/config.py",
  "applied": true,
  "changes": {
    "lines_added": 1,
    "lines_removed": 1,
    "hunks_applied": 1
  },
  "message": "Successfully applied patch to config.py"
}
```

---

**Document Version**: 1.0
**Generated**: 2025-01-18
**Tracing Tool**: Manual code analysis + documentation
