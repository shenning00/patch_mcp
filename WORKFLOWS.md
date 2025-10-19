# Error Recovery Workflow Patterns

This document describes the four error recovery workflow patterns implemented in the Patch MCP Server. These patterns demonstrate best practices for safe and reliable patch operations by combining multiple tools into common workflows.

## Overview

The Patch MCP Server provides 7 individual tools that can be combined into powerful error recovery patterns:

1. **Try-Revert**: Sequential patches with automatic rollback
2. **Backup-Restore**: Safe experimentation with automatic restore
3. **Validate-All-Then-Apply**: Atomic batch operations (all-or-nothing)
4. **Progressive Validation**: Step-by-step validation with detailed reporting

---

## Pattern 1: Try-Revert

**Use Case**: Apply multiple patches sequentially, reverting all on first failure

### When to Use

- Applying a series of dependent patches
- Transactional patch application
- Safe multi-step modifications

### How It Works

1. Apply patches one by one in order
2. Track each successfully applied patch
3. If any patch fails, revert all previously applied patches in reverse order
4. Return success only if all patches apply successfully

### Example Workflow

```python
# Scenario: Apply 3 related patches to config.py
patches = [timeout_patch, retry_patch, debug_patch]

# Apply with automatic revert on failure
result = apply_patches_with_revert("config.py", patches)

if result["success"]:
    print(f"✓ Applied {result['patches_applied']} patches")
else:
    print(f"✗ Failed at patch {result['failed_at']}")
    print(f"  Error: {result['error']}")
    print(f"  Reverted: {result['reverted']}")
```

### Manual Implementation

```python
# Using individual tools
applied = []

for i, patch in enumerate(patches):
    result = apply_patch("config.py", patch)

    if not result["success"]:
        # Revert all previously applied patches
        for applied_patch in reversed(applied):
            revert_patch("config.py", applied_patch)
        break

    applied.append(patch)
```

### Return Values

**Success**:
```json
{
  "success": true,
  "patches_applied": 3,
  "message": "Successfully applied 3 patches"
}
```

**Failure**:
```json
{
  "success": false,
  "patches_applied": 2,
  "failed_at": 3,
  "error": "context_mismatch",
  "reverted": true
}
```

---

## Pattern 2: Backup-Restore

**Use Case**: Apply patch with automatic backup and restore on failure

### When to Use

- Safe experimentation with patches
- Critical file modifications
- Testing patches before committing changes

### How It Works

1. Create a timestamped backup of the target file
2. Attempt to apply the patch
3. If patch fails, automatically restore from backup
4. On success, optionally keep or delete the backup

### Example Workflow

```python
# Apply patch with automatic cleanup
result = apply_patch_with_backup("app.py", patch)

# Or keep backup for safety
result = apply_patch_with_backup("critical.py", patch, keep_backup=True)

if result["success"]:
    print("✓ Patch applied successfully")
    if result["backup_file"]:
        print(f"  Backup saved at: {result['backup_file']}")
else:
    print(f"✗ Patch failed: {result['error']}")
    if result.get("restored"):
        print("  ✓ File restored from backup")
```

### Manual Implementation

```python
# Using individual tools
# 1. Create backup
backup_result = backup_file("app.py")
backup_path = backup_result["backup_file"]

# 2. Apply patch
result = apply_patch("app.py", patch)

if not result["success"]:
    # 3. Restore on failure
    restore_backup(backup_path)
    print("Restored from backup")
else:
    # 4. Optionally clean up backup
    import os
    os.remove(backup_path)
```

### Return Values

**Success**:
```json
{
  "success": true,
  "backup_file": "app.py.backup.20250119_143052",
  "message": "Patch applied successfully"
}
```

**Failure (Restored)**:
```json
{
  "success": false,
  "error": "context_mismatch",
  "restored": true,
  "phase": "apply"
}
```

**Critical Failure**:
```json
{
  "success": false,
  "error": "context_mismatch",
  "restore_failed": true,
  "backup_file": "app.py.backup.20250119_143052",
  "phase": "restore"
}
```

---

## Pattern 3: Validate-All-Then-Apply

**Use Case**: Apply multiple patches to multiple files atomically (all-or-nothing)

### When to Use

- Multi-file refactoring
- Coordinated changes across files
- Ensuring consistency across multiple files

### How It Works

1. Validate all patches against all files first
2. If any validation fails, stop immediately (no files modified)
3. Create backups for all files
4. Apply all patches
5. If any apply fails, restore all files from backups

### Example Workflow

```python
# Scenario: Refactor function across 3 files
pairs = [
    ("config.py", config_patch),
    ("utils.py", utils_patch),
    ("main.py", main_patch),
]

result = apply_patches_atomic(pairs)

if result["success"]:
    print(f"✓ Applied {result['applied']} patches atomically")
else:
    if result["phase"] == "validation":
        print(f"✗ Validation failed for {result['failed']} files:")
        for failure in result["failures"]:
            print(f"  - {failure['file']}: {failure['reason']}")
    else:
        print(f"✗ Apply failed at {result['failed_at']}")
        print(f"  Rolled back: {result['rolled_back']}")
```

### Manual Implementation

```python
# Using individual tools
files_and_patches = [("config.py", patch1), ("utils.py", patch2)]

# 1. Validate all
for file_path, patch in files_and_patches:
    result = validate_patch(file_path, patch)
    if not result["can_apply"]:
        print(f"Validation failed for {file_path}")
        exit(1)

# 2. Backup all
backups = {}
for file_path, _ in files_and_patches:
    backup_result = backup_file(file_path)
    backups[file_path] = backup_result["backup_file"]

# 3. Apply all (with rollback on failure)
try:
    for file_path, patch in files_and_patches:
        result = apply_patch(file_path, patch)
        if not result["success"]:
            # Restore all backups
            for fp, backup in backups.items():
                restore_backup(backup)
            print("Rolled back all changes")
            exit(1)

    print("All patches applied successfully")
except Exception as e:
    # Emergency restore
    for fp, backup in backups.items():
        restore_backup(backup)
```

### Return Values

**Success**:
```json
{
  "success": true,
  "applied": 3,
  "message": "Atomically applied 3 patches"
}
```

**Validation Failure**:
```json
{
  "success": false,
  "phase": "validation",
  "validated": 3,
  "failed": 1,
  "failures": [
    {"file": "utils.py", "reason": "context_mismatch"}
  ]
}
```

**Apply Failure**:
```json
{
  "success": false,
  "phase": "apply",
  "applied": 2,
  "failed_at": "main.py",
  "error": "permission_denied",
  "rolled_back": true
}
```

---

## Pattern 4: Progressive Validation

**Use Case**: Apply patch with step-by-step validation and detailed error reporting

### When to Use

- Debugging patch failures
- Understanding exactly where problems occur
- Maximum visibility into the patch process

### How It Works

1. **Safety Check**: Validate file exists, is writable, has disk space
2. **Validation**: Check patch format and applicability
3. **Backup**: Create backup before modification
4. **Apply**: Apply the patch
5. **Restore** (if apply fails): Automatically restore from backup

Each step is tracked with success/failure status and details.

### Example Workflow

```python
# Apply with maximum visibility
result = apply_patch_progressive("module.py", patch)

if result["success"]:
    print("✓ Patch applied successfully")
    print(f"  Backup: {result['backup_file']}")
    print(f"  Changes: {result['changes']}")
else:
    print(f"✗ Failed at: {result['failed_at']}")
    print(f"  Error: {result['error']}")
    print(f"  Error type: {result['error_type']}")

    # Show which steps passed
    for step, status in result["steps"].items():
        marker = "✓" if status["passed"] else "✗"
        print(f"  {marker} {step}")
```

### Manual Implementation

```python
# Using individual tools with step-by-step checking
results = {"steps": {}}

# Step 1: Safety check
from patch_mcp.utils import validate_file_safety
from pathlib import Path

safety = validate_file_safety(Path("module.py"), check_write=True, check_space=True)
results["steps"]["safety_check"] = {"passed": safety is None}
if safety:
    print(f"Safety check failed: {safety['error']}")
    exit(1)

# Step 2: Validate patch
validation = validate_patch("module.py", patch)
results["steps"]["validation"] = {"passed": validation.get("can_apply", False)}
if not validation.get("can_apply"):
    print(f"Validation failed: {validation.get('reason')}")
    exit(1)

# Step 3: Create backup
backup = backup_file("module.py")
results["steps"]["backup"] = {"passed": backup["success"]}
if not backup["success"]:
    print(f"Backup failed: {backup['error']}")
    exit(1)

# Step 4: Apply patch
apply_result = apply_patch("module.py", patch)
results["steps"]["apply"] = {"passed": apply_result["success"]}
if not apply_result["success"]:
    # Step 5: Restore
    restore_backup(backup["backup_file"])
    print(f"Apply failed: {apply_result['error']}, restored from backup")
    exit(1)

print("Success!")
```

### Return Values

**Success**:
```json
{
  "success": true,
  "steps": {
    "safety_check": {"passed": true, "details": null},
    "validation": {"passed": true, "details": {...}},
    "backup": {"passed": true, "details": {...}},
    "apply": {"passed": true, "details": {...}}
  },
  "backup_file": "module.py.backup.20250119_143052",
  "changes": {
    "lines_added": 5,
    "lines_removed": 2,
    "hunks_applied": 1
  }
}
```

**Failure**:
```json
{
  "success": false,
  "steps": {
    "safety_check": {"passed": true, "details": null},
    "validation": {"passed": false, "details": {...}}
  },
  "error": "context_mismatch at line 42",
  "error_type": "context_mismatch",
  "failed_at": "validation"
}
```

---

## Choosing the Right Pattern

| Pattern | Best For | Complexity | Atomicity | Visibility |
|---------|----------|------------|-----------|------------|
| **Try-Revert** | Sequential dependent patches | Medium | Per-file | Medium |
| **Backup-Restore** | Single file experimentation | Low | Single-file | Low |
| **Validate-All-Then-Apply** | Multi-file refactoring | High | Multi-file | Medium |
| **Progressive Validation** | Debugging, critical files | Medium | Single-file | High |

### Quick Decision Guide

- **Single file, test safely** → Use **Backup-Restore**
- **Multiple dependent patches to one file** → Use **Try-Revert**
- **Multiple files, must succeed together** → Use **Validate-All-Then-Apply**
- **Need detailed error info** → Use **Progressive Validation**

---

## Implementation

These patterns are implemented in `src/patch_mcp/workflows.py` as helper functions:

- `apply_patches_with_revert(file_path, patches)` - Pattern 1
- `apply_patch_with_backup(file_path, patch, keep_backup)` - Pattern 2
- `apply_patches_atomic(file_patch_pairs)` - Pattern 3
- `apply_patch_progressive(file_path, patch)` - Pattern 4

### Using in Python

```python
from patch_mcp.workflows import (
    apply_patches_with_revert,
    apply_patch_with_backup,
    apply_patches_atomic,
    apply_patch_progressive,
)

# Pattern 1: Sequential with revert
result = apply_patches_with_revert("config.py", [patch1, patch2, patch3])

# Pattern 2: Safe experimentation
result = apply_patch_with_backup("app.py", patch, keep_backup=True)

# Pattern 3: Atomic multi-file
pairs = [("file1.py", patch1), ("file2.py", patch2)]
result = apply_patches_atomic(pairs)

# Pattern 4: Maximum visibility
result = apply_patch_progressive("module.py", patch)
```

---

## Testing

All workflow patterns have comprehensive test coverage (21 workflow integration tests + 14 example workflow tests = 35 tests total). See `tests/integration/` for examples.

---

## See Also

- [README.md](README.md) - Main documentation
- [SECURITY.md](SECURITY.md) - Security features and best practices
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
