"""Error Recovery Helper Functions for File Patch MCP Server.

This module provides helper functions that demonstrate error recovery patterns
for safe patch operations. These functions combine core tools with backup/restore
functionality to handle failures gracefully.

The four recovery patterns:
1. safe_apply_with_backup: Apply with automatic rollback on failure
2. validate_before_apply: Validate before attempting application
3. batch_apply_patches: All-or-nothing batch operations
4. safe_revert_with_validation: Revert with modification detection
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .tools.apply import apply_patch
from .tools.backup import backup_file, restore_backup
from .tools.inspect import inspect_patch
from .tools.revert import revert_patch
from .tools.validate import validate_patch


def safe_apply_with_backup(file_path: str, patch: str) -> Dict[str, Any]:
    """Apply patch with automatic backup and rollback on failure.

    This function creates a backup before applying a patch. If the patch
    application fails, it automatically restores from the backup. The backup
    is always created and its path is always returned.

    Pattern:
    1. Create backup
    2. Validate patch can be applied
    3. Apply patch
    4. If failure, restore from backup
    5. Return result with backup info

    Args:
        file_path: Path to the file to patch
        patch: Unified diff patch content

    Returns:
        Dict with the following structure:
            {
                "success": bool,
                "file_path": str,
                "applied": bool,
                "backup_file": str,  # Always created
                "restored": bool,    # True if rollback occurred
                "changes": {...},    # Present if applied successfully
                "message": str,
                "error": Optional[str],
                "error_type": Optional[str]
            }

    Example:
        >>> result = safe_apply_with_backup("config.py", patch)
        >>> if result["success"]:
        ...     print(f"Applied successfully, backup at: {result['backup_file']}")
        >>> else:
        ...     print(f"Failed: {result['error']}, restored: {result['restored']}")
    """
    # Step 1: Create backup
    backup_result = backup_file(file_path)
    if not backup_result["success"]:
        return {
            "success": False,
            "file_path": file_path,
            "applied": False,
            "backup_file": "",
            "restored": False,
            "message": f"Cannot create backup: {backup_result['error']}",
            "error": backup_result["error"],
            "error_type": backup_result.get("error_type"),
        }

    backup_path = backup_result["backup_file"]

    # Step 2: Validate patch can be applied
    validation = validate_patch(file_path, patch)
    if not validation.get("can_apply", False):
        # Validation failed - clean up backup and return
        try:
            Path(backup_path).unlink()
        except Exception:
            pass  # Best effort cleanup

        return {
            "success": False,
            "file_path": file_path,
            "applied": False,
            "backup_file": backup_path,
            "restored": False,
            "message": f"Validation failed: {validation.get('reason', validation.get('error'))}",
            "error": validation.get("reason") or validation.get("error"),
            "error_type": validation.get("error_type"),
        }

    # Step 3: Apply patch
    apply_result = apply_patch(file_path, patch)

    if not apply_result["success"]:
        # Step 4: Restore from backup on failure
        restore_result = restore_backup(backup_path)
        restored = restore_result["success"]
        status = "restored" if restored else "FAILED TO RESTORE"

        return {
            "success": False,
            "file_path": file_path,
            "applied": False,
            "backup_file": backup_path,
            "restored": restored,
            "message": f"Apply failed and {status} from backup",
            "error": apply_result["error"],
            "error_type": apply_result.get("error_type"),
        }

    # Success!
    return {
        "success": True,
        "file_path": file_path,
        "applied": True,
        "backup_file": backup_path,
        "restored": False,
        "changes": apply_result.get("changes", {}),
        "message": f"Successfully applied patch to {file_path}",
    }


def validate_before_apply(file_path: str, patch: str, dry_run: bool = False) -> Dict[str, Any]:
    """Validate patch before attempting to apply.

    This function performs comprehensive validation before applying a patch.
    It first inspects the patch format, then validates it can be applied to
    the file. Optionally, it can perform a dry run or actually apply the patch.

    Pattern:
    1. Validate patch format (inspect_patch)
    2. Validate can apply to file (validate_patch)
    3. If validation passes and not dry_run, apply
    4. Return detailed validation info

    Args:
        file_path: Path to the file to patch
        patch: Unified diff patch content
        dry_run: If True, validate only (don't apply)

    Returns:
        Dict with the following structure:
            {
                "success": bool,
                "file_path": str,
                "validation": {...},  # From validate_patch
                "inspection": {...},  # From inspect_patch
                "applied": bool,
                "changes": Optional[...],
                "message": str,
                "error": Optional[str],
                "error_type": Optional[str]
            }

    Example:
        >>> # Dry run to check if patch would work
        >>> result = validate_before_apply("app.py", patch, dry_run=True)
        >>> if result["success"] and result["validation"]["can_apply"]:
        ...     # Now apply for real
        ...     result = validate_before_apply("app.py", patch, dry_run=False)
    """
    # Step 1: Inspect patch format
    inspection = inspect_patch(patch)
    if not inspection.get("valid", False):
        return {
            "success": False,
            "file_path": file_path,
            "validation": {},
            "inspection": inspection,
            "applied": False,
            "message": f"Invalid patch format: {inspection.get('error')}",
            "error": inspection.get("error"),
            "error_type": inspection.get("error_type"),
        }

    # Step 2: Validate can apply to file
    validation = validate_patch(file_path, patch)
    if not validation.get("can_apply", False):
        error_msg = validation.get("reason", validation.get("error"))
        return {
            "success": False,
            "file_path": file_path,
            "validation": validation,
            "inspection": inspection,
            "applied": False,
            "message": f"Patch cannot be applied: {error_msg}",
            "error": validation.get("reason") or validation.get("error"),
            "error_type": validation.get("error_type"),
        }

    # Step 3: If validation passes and not dry_run, apply
    if dry_run:
        return {
            "success": True,
            "file_path": file_path,
            "validation": validation,
            "inspection": inspection,
            "applied": False,
            "message": f"Patch is valid and can be applied to {file_path} (dry run)",
        }

    # Apply for real
    apply_result = apply_patch(file_path, patch)
    if not apply_result["success"]:
        return {
            "success": False,
            "file_path": file_path,
            "validation": validation,
            "inspection": inspection,
            "applied": False,
            "message": f"Apply failed: {apply_result['error']}",
            "error": apply_result["error"],
            "error_type": apply_result.get("error_type"),
        }

    return {
        "success": True,
        "file_path": file_path,
        "validation": validation,
        "inspection": inspection,
        "applied": True,
        "changes": apply_result.get("changes", {}),
        "message": f"Successfully validated and applied patch to {file_path}",
    }


def batch_apply_patches(patches: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Apply multiple patches with rollback on any failure.

    This function implements all-or-nothing semantics for applying multiple
    patches. It backs up all files first, then applies patches sequentially.
    If any patch fails, ALL files are rolled back to their original state.

    Pattern:
    1. Backup all files first
    2. Apply patches sequentially
    3. If any fails, rollback ALL to original state
    4. Return summary of successes/failures

    Args:
        patches: List of (file_path, patch) tuples

    Returns:
        Dict with the following structure:
            {
                "success": bool,
                "total_patches": int,
                "applied_count": int,
                "failed_count": int,
                "backups": List[str],
                "results": List[...],  # Individual results
                "rollback_performed": bool,
                "message": str,
                "error": Optional[str]
            }

    Example:
        >>> patches = [
        ...     ("file1.py", patch1),
        ...     ("file2.py", patch2),
        ...     ("file3.py", patch3),
        ... ]
        >>> result = batch_apply_patches(patches)
        >>> if result["success"]:
        ...     print(f"Applied {result['applied_count']} patches")
        >>> else:
        ...     print(f"Failed, rolled back: {result['rollback_performed']}")
    """
    if not patches:
        return {
            "success": True,
            "total_patches": 0,
            "applied_count": 0,
            "failed_count": 0,
            "backups": [],
            "results": [],
            "rollback_performed": False,
            "message": "No patches to apply",
        }

    total_patches = len(patches)
    backups: Dict[str, str] = {}
    results: List[Dict[str, Any]] = []

    # Step 1: Backup all files first
    for file_path, _ in patches:
        backup_result = backup_file(file_path)
        if not backup_result["success"]:
            # Cleanup any backups already created
            for backup_path in backups.values():
                try:
                    Path(backup_path).unlink()
                except Exception:
                    pass

            return {
                "success": False,
                "total_patches": total_patches,
                "applied_count": 0,
                "failed_count": total_patches,
                "backups": [],
                "results": [],
                "rollback_performed": False,
                "message": f"Cannot create backup for {file_path}: {backup_result['error']}",
                "error": backup_result["error"],
            }

        backups[file_path] = backup_result["backup_file"]

    # Step 2: Apply patches sequentially
    applied_count = 0
    failed = False
    failure_error = None

    for file_path, patch in patches:
        apply_result = apply_patch(file_path, patch)
        results.append(
            {
                "file_path": file_path,
                "success": apply_result["success"],
                "error": apply_result.get("error"),
            }
        )

        if not apply_result["success"]:
            failed = True
            failure_error = apply_result.get("error")
            break

        applied_count += 1

    # Step 3: If any failed, rollback ALL
    rollback_performed = False
    if failed:
        for file_path, backup_path in backups.items():
            restore_result = restore_backup(backup_path)
            if restore_result["success"]:
                rollback_performed = True

        # Clean up backups after rollback
        for backup_path in backups.values():
            try:
                Path(backup_path).unlink()
            except Exception:
                pass

        msg = f"Failed at patch {applied_count + 1}/{total_patches}, " "rolled back all changes"
        return {
            "success": False,
            "total_patches": total_patches,
            "applied_count": applied_count,
            "failed_count": total_patches - applied_count,
            "backups": list(backups.values()),
            "results": results,
            "rollback_performed": rollback_performed,
            "message": msg,
            "error": failure_error,
        }

    # Success - clean up backups
    for backup_path in backups.values():
        try:
            Path(backup_path).unlink()
        except Exception:
            pass

    return {
        "success": True,
        "total_patches": total_patches,
        "applied_count": applied_count,
        "failed_count": 0,
        "backups": list(backups.values()),
        "results": results,
        "rollback_performed": False,
        "message": f"Successfully applied all {total_patches} patches",
    }


def safe_revert_with_validation(file_path: str, patch: str) -> Dict[str, Any]:
    """Revert patch with validation that file hasn't been modified.

    This function safely reverts a previously applied patch. It creates a
    backup of the current state (for safety), validates the patch can be
    reverted, then performs the revert operation.

    Pattern:
    1. Backup current state (for safety)
    2. Validate patch can be reverted
    3. Revert patch
    4. Verify revert was successful

    Args:
        file_path: Path to the file to revert
        patch: The same patch that was previously applied

    Returns:
        Dict with the following structure:
            {
                "success": bool,
                "file_path": str,
                "reverted": bool,
                "backup_file": str,
                "changes": {...},
                "message": str,
                "error": Optional[str],
                "error_type": Optional[str]
            }

    Example:
        >>> # Apply a patch
        >>> apply_result = apply_patch("module.py", patch)
        >>>
        >>> # Later, revert it safely
        >>> result = safe_revert_with_validation("module.py", patch)
        >>> if result["success"]:
        ...     print(f"Reverted, backup at: {result['backup_file']}")
    """
    # Step 1: Backup current state (for safety)
    backup_result = backup_file(file_path)
    if not backup_result["success"]:
        return {
            "success": False,
            "file_path": file_path,
            "reverted": False,
            "backup_file": "",
            "message": f"Cannot create backup: {backup_result['error']}",
            "error": backup_result["error"],
            "error_type": backup_result.get("error_type"),
        }

    backup_path = backup_result["backup_file"]

    # Step 2: Attempt to revert patch
    revert_result = revert_patch(file_path, patch)

    if not revert_result["success"]:
        # Revert failed - clean up backup
        try:
            Path(backup_path).unlink()
        except Exception:
            pass

        return {
            "success": False,
            "file_path": file_path,
            "reverted": False,
            "backup_file": backup_path,
            "message": f"Revert failed: {revert_result['error']}",
            "error": revert_result["error"],
            "error_type": revert_result.get("error_type"),
        }

    # Success!
    return {
        "success": True,
        "file_path": file_path,
        "reverted": True,
        "backup_file": backup_path,
        "changes": revert_result.get("changes", {}),
        "message": f"Successfully reverted patch from {file_path}",
    }
