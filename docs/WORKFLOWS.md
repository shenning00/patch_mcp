# Error Recovery Workflow Patterns

This document provides a comprehensive guide to the error recovery patterns implemented in the File Patch MCP Server. These patterns help you safely apply patches with automatic rollback and recovery mechanisms.

## Table of Contents

1. [Overview](#overview)
2. [Pattern Comparison](#pattern-comparison)
3. [Pattern 1: Try-Revert](#pattern-1-try-revert-sequential-patches)
4. [Pattern 2: Backup-Restore](#pattern-2-backup-restore-safe-experimentation)
5. [Pattern 3: Validate-All-Then-Apply](#pattern-3-validate-all-then-apply-atomic-batch)
6. [Pattern 4: Progressive Validation](#pattern-4-progressive-validation)
7. [Best Practices](#best-practices)
8. [Example Workflows](#example-workflows)

---

## Overview

The File Patch MCP Server provides four error recovery patterns that combine basic patch operations into safe, robust workflows. These patterns handle common error scenarios and provide automatic recovery mechanisms.

### Why Use Workflow Patterns?

- **Safety**: Automatic backup and rollback on failure
- **Atomicity**: All-or-nothing guarantees for multi-file operations
- **Visibility**: Detailed error reporting and step-by-step tracking
- **Simplicity**: Complex operations wrapped in simple function calls

### Available Patterns

1. **Try-Revert**: Apply patches sequentially with automatic revert on failure
2. **Backup-Restore**: Safe experimentation with automatic backup and restore
3. **Validate-All-Then-Apply**: Atomic batch operations (all-or-nothing)
4. **Progressive Validation**: Step-by-step validation with detailed reporting

---

## Pattern Comparison

Choose the right pattern for your use case:

| Pattern | Use Case | Multi-File | Automatic Backup | Rollback | Detail Level |
|---------|----------|------------|------------------|----------|--------------|
| **Try-Revert** | Sequential patches to one file | No | No | Yes | Medium |
| **Backup-Restore** | Safe single patch application | No | Yes | Yes | Medium |
| **Validate-All-Then-Apply** | Multi-file atomic changes | Yes | Yes | Yes | Medium |
| **Progressive Validation** | Maximum visibility and control | No | Yes | Yes | High |

### Decision Tree

```
Need to apply multiple patches?
├─ Yes: To the same file?
│  ├─ Yes → Use Try-Revert
│  └─ No → Use Validate-All-Then-Apply (Atomic Batch)
└─ No: Need detailed step-by-step info?
   ├─ Yes → Use Progressive Validation
   └─ No → Use Backup-Restore
```

---

## Pattern 1: Try-Revert (Sequential Patches)

Apply multiple patches to a file sequentially. If any patch fails, automatically revert all previously applied patches.

### When to Use

- Applying a series of dependent patches
- Multi-step modifications to a single file
- Transactional patch application

### Function Signature

```python
from patch_mcp.workflows import apply_patches_with_revert

def apply_patches_with_revert(
    file_path: str,
    patches: list[str]
) -> dict[str, Any]:
    """Apply patches sequentially with automatic revert on failure."""
```

### Parameters

- `file_path` (str): Path to the file to patch
- `patches` (list[str]): List of patches to apply in order

### Return Values

**Success:**
```python
{
    "success": True,
    "patches_applied": 3,
    "message": "Successfully applied 3 patches"
}
```

**Failure (with revert):**
```python
{
    "success": False,
    "patches_applied": 2,
    "failed_at": 3,
    "error": "Context mismatch...",
    "reverted": True
}
```

### Example

```python
from patch_mcp.workflows import apply_patches_with_revert

# Multiple patches to apply in sequence
patches = [
    """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
-DEBUG = False
+DEBUG = True
 PORT = 8000
""",
    """--- config.py
+++ config.py
@@ -1,3 +1,4 @@
 DEBUG = True
 PORT = 8000
+TIMEOUT = 30
""",
]

result = apply_patches_with_revert("config.py", patches)

if result["success"]:
    print(f"Applied {result['patches_applied']} patches")
else:
    print(f"Failed at patch {result['failed_at']}")
    print(f"Reverted: {result['reverted']}")
```

### Characteristics

- **Sequential Application**: Patches applied one by one in order
- **Automatic Rollback**: If any patch fails, all previous patches are reverted
- **Transactional**: Either all patches succeed or none (reverted state)
- **Error Propagation**: Detailed error from failed patch is returned

### Edge Cases

- **Empty List**: Returns success with 0 patches applied
- **Single Patch**: Works correctly as a special case
- **First Fails**: Returns with reverted=True (nothing to revert)
- **Revert Failure**: Raises exception (critical error)

---

## Pattern 2: Backup-Restore (Safe Experimentation)

Apply a patch with automatic backup creation. If the patch fails, automatically restore from backup.

### When to Use

- Testing experimental patches
- Modifying critical files
- Safe one-time patch application
- Need to keep backup for later rollback

### Function Signature

```python
from patch_mcp.workflows import apply_patch_with_backup

def apply_patch_with_backup(
    file_path: str,
    patch: str,
    keep_backup: bool = False
) -> dict[str, Any]:
    """Apply patch with automatic backup and restore on failure."""
```

### Parameters

- `file_path` (str): Path to the file to patch
- `patch` (str): Patch to apply
- `keep_backup` (bool): If True, keep backup even on success (default: False)

### Return Values

**Success:**
```python
{
    "success": True,
    "backup_file": "config.py.backup.20251017_143052",  # or None
    "message": "Patch applied successfully"
}
```

**Failure (with restore):**
```python
{
    "success": False,
    "error": "Context mismatch...",
    "restored": True,
    "phase": "apply"
}
```

**Critical failure:**
```python
{
    "success": False,
    "error": "...",
    "restore_failed": True,
    "backup_file": "config.py.backup.20251017_143052",
    "phase": "restore"
}
```

### Example

```python
from patch_mcp.workflows import apply_patch_with_backup

patch = """--- app.py
+++ app.py
@@ -1,2 +1,2 @@
-version = 1
+version = 2
"""

# Apply with automatic cleanup
result = apply_patch_with_backup("app.py", patch)

if result["success"]:
    print("Patch applied, backup cleaned up")
else:
    print(f"Patch failed, file restored: {result['restored']}")

# Apply and keep backup for safety
result = apply_patch_with_backup("critical.py", patch, keep_backup=True)

if result["success"]:
    print(f"Backup saved at: {result['backup_file']}")
    # Can restore later if needed
```

### Characteristics

- **Automatic Backup**: Creates timestamped backup before applying
- **Automatic Restore**: Restores from backup on failure
- **Optional Retention**: Can keep backup even on success
- **Emergency Recovery**: Handles unexpected errors with restore attempt

### Phases

1. **backup**: Create backup
2. **apply**: Apply patch
3. **restore**: Restore from backup (on failure)
4. **unexpected**: Emergency recovery (on exception)

---

## Pattern 3: Validate-All-Then-Apply (Atomic Batch)

Apply patches to multiple files atomically. All patches must succeed or all changes are rolled back.

### When to Use

- Multi-file refactoring
- Coordinated changes across files
- Ensuring consistency across multiple files
- All-or-nothing requirement

### Function Signature

```python
from patch_mcp.workflows import apply_patches_atomic

def apply_patches_atomic(
    file_patch_pairs: list[tuple[str, str]]
) -> dict[str, Any]:
    """Apply multiple patches atomically (all-or-nothing)."""
```

### Parameters

- `file_patch_pairs` (list[tuple[str, str]]): List of (file_path, patch) tuples

### Return Values

**Success:**
```python
{
    "success": True,
    "applied": 5,
    "message": "Atomically applied 5 patches"
}
```

**Validation failure:**
```python
{
    "success": False,
    "phase": "validation",
    "validated": 5,
    "failed": 2,
    "failures": [
        {"file": "file1.py", "reason": "Context mismatch..."},
        {"file": "file2.py", "reason": "Invalid patch..."}
    ]
}
```

**Apply failure:**
```python
{
    "success": False,
    "phase": "apply",
    "applied": 3,
    "failed_at": "file4.py",
    "error": "...",
    "rolled_back": True
}
```

### Example

```python
from patch_mcp.workflows import apply_patches_atomic

patches = [
    ("src/config.py", config_patch),
    ("src/utils.py", utils_patch),
    ("src/main.py", main_patch),
    ("tests/test_main.py", test_patch),
]

result = apply_patches_atomic(patches)

if result["success"]:
    print(f"Atomically applied {result['applied']} patches")
elif result["phase"] == "validation":
    print(f"Validation failed for {result['failed']} files")
    for failure in result["failures"]:
        print(f"  {failure['file']}: {failure['reason']}")
else:
    print(f"Apply failed at {result['failed_at']}, rolled back")
```

### Characteristics

- **Three-Phase Process**:
  1. Validate all patches against all files
  2. Create backups for all files
  3. Apply all patches
- **All-or-Nothing**: Either all patches succeed or all are rolled back
- **Pre-validation**: Catches errors before any files are modified
- **Automatic Rollback**: Restores all files if any apply fails

### Phases

1. **validation**: Validate all patches can be applied
2. **apply**: Apply all patches
3. **unexpected**: Emergency rollback on exception

---

## Pattern 4: Progressive Validation

Apply a patch with step-by-step validation and detailed error reporting at each stage.

### When to Use

- Debugging patch application issues
- Understanding exactly where failures occur
- Maximum visibility into the patch process
- Learning or troubleshooting

### Function Signature

```python
from patch_mcp.workflows import apply_patch_progressive

def apply_patch_progressive(
    file_path: str,
    patch: str
) -> dict[str, Any]:
    """Apply patch with progressive validation and detailed reporting."""
```

### Parameters

- `file_path` (str): Path to the file to patch
- `patch` (str): Patch to apply

### Return Values

**Success:**
```python
{
    "success": True,
    "steps": {
        "safety_check": {"passed": True, "details": None},
        "validation": {"passed": True, "details": {...}},
        "backup": {"passed": True, "details": {...}},
        "apply": {"passed": True, "details": {...}}
    },
    "backup_file": "file.py.backup.20251017_143052",
    "changes": {...}
}
```

**Failure:**
```python
{
    "success": False,
    "steps": {
        "safety_check": {"passed": True, "details": None},
        "validation": {"passed": False, "details": {...}}
    },
    "error": "...",
    "error_type": "context_mismatch",
    "failed_at": "validation"
}
```

### Example

```python
from patch_mcp.workflows import apply_patch_progressive

result = apply_patch_progressive("module.py", patch)

if result["success"]:
    print("All steps completed successfully:")
    for step_name, step_info in result["steps"].items():
        print(f"  ✓ {step_name}")
else:
    print(f"Failed at: {result['failed_at']}")
    print(f"Error: {result['error']}")
    print(f"\nSteps completed:")
    for step_name, step_info in result["steps"].items():
        status = "✓" if step_info["passed"] else "✗"
        print(f"  {status} {step_name}")
```

### Characteristics

- **Five Steps**:
  1. Safety check (file exists, not symlink, not binary, etc.)
  2. Validation (patch format and context)
  3. Backup (create timestamped backup)
  4. Apply (apply the patch)
  5. Restore (restore on failure, if needed)
- **Detailed Tracking**: Each step has `passed` flag and `details`
- **Early Exit**: Stops at first failure
- **Comprehensive Details**: Full information from each step

### Steps

| Step | Description | Details Included |
|------|-------------|------------------|
| safety_check | File safety validation | Error dict or None |
| validation | Patch validation | Validation result with preview |
| backup | Backup creation | Backup file path and size |
| apply | Patch application | Changes made |
| restore | Restore from backup (failure only) | Restore result |

---

## Best Practices

### General Guidelines

1. **Always Validate First**: Use `validate_patch` or dry-run before applying
2. **Use Appropriate Pattern**: Match pattern to your use case
3. **Handle Errors**: Check `success` field and handle failures appropriately
4. **Log Operations**: Enable logging for production environments
5. **Test Workflows**: Test your workflow with known good and bad patches

### Pattern-Specific Tips

#### Try-Revert
- Use for patches that build on each other
- Keep patches small and focused
- Verify each patch independently before batching
- Handle critical revert failures (exceptions)

#### Backup-Restore
- Use `keep_backup=True` for critical files
- Clean up old backups periodically
- Verify restore succeeded before continuing
- Keep backup paths for manual recovery if needed

#### Validate-All-Then-Apply
- Validate patches independently first
- Ensure files don't change during operation
- Handle partial rollback scenarios
- Consider file locking for concurrent access

#### Progressive Validation
- Use for debugging and learning
- Analyze step details for troubleshooting
- Save full results for audit trails
- Use in development, simpler patterns in production

### Error Handling

```python
from patch_mcp.workflows import apply_patch_with_backup
import logging

logger = logging.getLogger(__name__)

def safe_patch_application(file_path, patch):
    """Example of robust error handling."""
    try:
        result = apply_patch_with_backup(file_path, patch, keep_backup=True)

        if result["success"]:
            logger.info(f"Patch applied successfully to {file_path}")
            if result["backup_file"]:
                logger.info(f"Backup saved at: {result['backup_file']}")
            return True
        else:
            logger.error(f"Patch failed at phase: {result.get('phase')}")
            logger.error(f"Error: {result.get('error')}")

            if result.get("restored"):
                logger.info("File successfully restored from backup")
            elif result.get("restore_failed"):
                logger.critical(f"RESTORE FAILED! Manual recovery needed.")
                logger.critical(f"Backup at: {result.get('backup_file')}")

            return False

    except Exception as e:
        logger.exception(f"Unexpected error applying patch: {e}")
        return False
```

---

## Example Workflows

### Workflow 1: Multi-Step Code Refactoring

```python
from patch_mcp.workflows import apply_patches_with_revert

def refactor_module(module_path):
    """Apply a series of refactoring patches."""

    patches = [
        # Step 1: Rename variables
        rename_variables_patch,
        # Step 2: Update function signatures
        update_signatures_patch,
        # Step 3: Add type hints
        add_type_hints_patch,
    ]

    result = apply_patches_with_revert(module_path, patches)

    if result["success"]:
        print(f"✓ Refactoring complete: {result['patches_applied']} patches applied")
        return True
    else:
        print(f"✗ Refactoring failed at step {result['failed_at']}")
        print(f"  All changes reverted: {result['reverted']}")
        print(f"  Error: {result['error']}")
        return False
```

### Workflow 2: Safe Production Update

```python
from patch_mcp.workflows import apply_patch_with_backup

def update_production_config(config_file, patch):
    """Safely update production configuration."""

    # Apply with backup retention
    result = apply_patch_with_backup(config_file, patch, keep_backup=True)

    if result["success"]:
        print(f"✓ Configuration updated")
        print(f"  Backup: {result['backup_file']}")
        print(f"  You can restore with: restore_backup('{result['backup_file']}')")
        return True
    else:
        print(f"✗ Update failed: {result['error']}")
        print(f"  Configuration restored: {result.get('restored', False)}")
        return False
```

### Workflow 3: Multi-File Feature Addition

```python
from patch_mcp.workflows import apply_patches_atomic

def add_feature_across_files(feature_patches):
    """Add a feature that spans multiple files atomically."""

    result = apply_patches_atomic(feature_patches)

    if result["success"]:
        print(f"✓ Feature added to {result['applied']} files")
        return True
    elif result["phase"] == "validation":
        print(f"✗ Validation failed for {result['failed']} files:")
        for failure in result["failures"]:
            print(f"  - {failure['file']}: {failure['reason']}")
        return False
    else:
        print(f"✗ Apply failed at {result['failed_at']}")
        print(f"  All changes rolled back: {result.get('rolled_back', False)}")
        return False
```

### Workflow 4: Debugging Patch Issues

```python
from patch_mcp.workflows import apply_patch_progressive

def debug_patch_application(file_path, patch):
    """Debug why a patch isn't applying."""

    result = apply_patch_progressive(file_path, patch)

    print(f"Patch application result: {'SUCCESS' if result['success'] else 'FAILURE'}")
    print(f"\nStep-by-step breakdown:")

    for step_name, step_info in result["steps"].items():
        status = "✓" if step_info["passed"] else "✗"
        print(f"\n{status} {step_name.upper()}")

        if not step_info["passed"]:
            print(f"  Failed here!")
            if step_info["details"]:
                print(f"  Details: {step_info['details']}")

    if not result["success"]:
        print(f"\nFailed at: {result['failed_at']}")
        print(f"Error: {result['error']}")
        print(f"Error type: {result.get('error_type')}")

    return result["success"]
```

### Workflow 5: Automated Testing Pipeline

```python
from patch_mcp.workflows import apply_patches_atomic
from patch_mcp.tools.validate import validate_patch
import subprocess

def test_patches_pipeline(patches_to_test):
    """Test multiple patches in an automated pipeline."""

    # Phase 1: Static validation
    print("Phase 1: Validating patches...")
    for file_path, patch in patches_to_test:
        result = validate_patch(file_path, patch)
        if not result["can_apply"]:
            print(f"✗ Validation failed for {file_path}")
            return False

    print("✓ All patches validated")

    # Phase 2: Apply atomically
    print("\nPhase 2: Applying patches...")
    result = apply_patches_atomic(patches_to_test)

    if not result["success"]:
        print(f"✗ Apply failed: {result.get('error')}")
        return False

    print(f"✓ Applied {result['applied']} patches")

    # Phase 3: Run tests
    print("\nPhase 3: Running tests...")
    test_result = subprocess.run(["pytest"], capture_output=True)

    if test_result.returncode != 0:
        print("✗ Tests failed, rolling back...")
        # Restore from backups would go here
        return False

    print("✓ All tests passed")
    return True
```

---

## Summary

The four workflow patterns provide comprehensive error recovery mechanisms:

- **Try-Revert**: Sequential patches with automatic revert
- **Backup-Restore**: Safe experimentation with backup
- **Validate-All-Then-Apply**: Atomic multi-file operations
- **Progressive Validation**: Detailed step-by-step reporting

Choose the pattern that best fits your use case, follow best practices, and handle errors appropriately for robust patch operations.

For more information, see:
- `src/patch_mcp/workflows.py` - Implementation
- `tests/integration/test_workflows.py` - Comprehensive tests
- `tests/integration/test_example_workflows.py` - Example usage
- `project_design.md` - Complete design specification
