"""Error Recovery Workflow Patterns for File Patch MCP Server.

This module implements optional helper functions that demonstrate best practices
for error recovery workflows. These patterns combine multiple tools into common
workflows for safe and reliable patch operations.

The four patterns implemented:
1. Try-Revert: Apply patches sequentially, reverting all on first failure
2. Backup-Restore: Apply patch with automatic backup and restore on failure
3. Validate-All-Then-Apply: Atomic batch operations (all-or-nothing)
4. Progressive Validation: Step-by-step validation with detailed error reporting
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .tools.apply import apply_patch
from .tools.backup import backup_file, restore_backup
from .tools.revert import revert_patch
from .tools.validate import validate_patch
from .utils import validate_file_safety

# Configure logging
logger = logging.getLogger(__name__)


def apply_patches_with_revert(file_path: str, patches: List[str]) -> Dict[str, Any]:
    """Apply multiple patches sequentially, reverting all on first failure.

    This pattern applies patches one by one in order. If any patch fails,
    all previously applied patches are reverted in reverse order to restore
    the original state.

    This is useful for:
    - Applying a series of dependent patches
    - Transactional patch application
    - Safe multi-step modifications

    Args:
        file_path: Path to the file to patch
        patches: List of patches to apply in order

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "patches_applied": int,
                "message": str
            }

        Dict with the following structure on failure:
            {
                "success": False,
                "patches_applied": int,
                "failed_at": int,
                "error": str,
                "reverted": bool
            }

    Raises:
        Exception: If revert fails (critical error requiring manual intervention)

    Example:
        >>> patches = [patch1, patch2, patch3]
        >>> result = apply_patches_with_revert("config.py", patches)
        >>> if result["success"]:
        ...     print(f"Applied {result['patches_applied']} patches")
        ... else:
        ...     print(f"Failed at patch {result['failed_at']}")
    """
    if not patches:
        return {
            "success": True,
            "patches_applied": 0,
            "message": "No patches to apply",
        }

    applied_patches: List[str] = []

    try:
        for i, patch in enumerate(patches):
            logger.info(f"Applying patch {i + 1}/{len(patches)} to {file_path}")
            result = apply_patch(file_path, patch)

            if not result["success"]:
                logger.error(f"Patch {i + 1} failed: {result['error']}")

                # Revert all previously applied patches in reverse order
                if applied_patches:
                    logger.info(f"Reverting {len(applied_patches)} previously applied patches")
                    for j, applied_patch in enumerate(reversed(applied_patches)):
                        logger.info(
                            f"Reverting patch {len(applied_patches) - j}/{len(applied_patches)}"
                        )
                        revert_result = revert_patch(file_path, applied_patch)

                        if not revert_result["success"]:
                            logger.error(f"CRITICAL: Revert failed: {revert_result['error']}")
                            raise Exception(
                                f"Cannot revert patches - manual intervention required. "
                                f"Revert failed at patch {len(applied_patches) - j} with error: "
                                f"{revert_result['error']}"
                            )

                return {
                    "success": False,
                    "patches_applied": len(applied_patches),
                    "failed_at": i + 1,
                    "error": result["error"],
                    "reverted": True,
                }

            applied_patches.append(patch)
            logger.info(f"Successfully applied patch {i + 1}/{len(patches)}")

        return {
            "success": True,
            "patches_applied": len(applied_patches),
            "message": f"Successfully applied {len(applied_patches)} patches",
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "patches_applied": len(applied_patches),
            "error": str(e),
            "reverted": False,
        }


def apply_patch_with_backup(
    file_path: str, patch: str, keep_backup: bool = False
) -> Dict[str, Any]:
    """Apply patch with automatic backup and restore on failure.

    This pattern creates a backup before applying a patch. If the patch fails,
    the backup is automatically restored. On success, the backup can be optionally
    kept or deleted.

    This is useful for:
    - Safe experimentation with patches
    - Critical file modifications
    - Testing patches before committing changes

    Args:
        file_path: Path to the file to patch
        patch: Patch to apply
        keep_backup: If True, keep backup even on success (default: False)

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "backup_file": str or None,
                "message": str
            }

        Dict with the following structure on failure (restored):
            {
                "success": False,
                "error": str,
                "restored": True,
                "phase": str
            }

        Dict with the following structure on critical failure:
            {
                "success": False,
                "error": str,
                "restore_failed": True,
                "backup_file": str,
                "phase": str
            }

    Example:
        >>> # Apply patch with automatic cleanup
        >>> result = apply_patch_with_backup("app.py", patch)
        >>>
        >>> # Apply patch and keep backup for safety
        >>> result = apply_patch_with_backup("critical.py", patch, keep_backup=True)
        >>> if result["success"]:
        ...     print(f"Backup saved at: {result['backup_file']}")
    """
    # Create backup
    backup_result = backup_file(file_path)
    if not backup_result["success"]:
        return {
            "success": False,
            "error": f"Cannot create backup: {backup_result['error']}",
            "phase": "backup",
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
                    "phase": "restore",
                }

            # Clean up backup after successful restore
            try:
                Path(backup_path).unlink()
            except Exception as e:
                logger.warning(f"Could not delete backup after restore: {e}")

            return {
                "success": False,
                "error": result["error"],
                "restored": True,
                "phase": "apply",
            }

        # Success - optionally clean up backup
        if not keep_backup:
            try:
                Path(backup_path).unlink()
                logger.info("Removed backup after successful apply")
            except Exception as e:
                logger.warning(f"Could not delete backup: {e}")

        return {
            "success": True,
            "backup_file": backup_path if keep_backup else None,
            "message": "Patch applied successfully",
        }

    except Exception as e:
        # Emergency restore
        logger.error(f"Unexpected error: {str(e)}, attempting restore")
        try:
            restore_backup(backup_path)
            logger.info("Emergency restore successful")
        except Exception as restore_error:
            logger.error(f"CRITICAL: Emergency restore failed: {restore_error}")

        return {
            "success": False,
            "error": str(e),
            "phase": "unexpected",
            "backup_file": backup_path,
        }


def apply_patches_atomic(file_patch_pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Apply multiple patches to multiple files atomically (all-or-nothing).

    This pattern validates all patches first, creates backups for all files,
    then applies all patches. If any step fails, all changes are rolled back
    by restoring all backups.

    This is useful for:
    - Multi-file refactoring
    - Coordinated changes across files
    - Ensuring consistency across multiple files

    Args:
        file_patch_pairs: List of (file_path, patch) tuples

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "applied": int,
                "message": str
            }

        Dict with the following structure on validation failure:
            {
                "success": False,
                "phase": "validation",
                "validated": int,
                "failed": int,
                "failures": List[Dict[str, str]]
            }

        Dict with the following structure on apply failure:
            {
                "success": False,
                "phase": "apply",
                "applied": int,
                "failed_at": str,
                "error": str,
                "rolled_back": bool
            }

    Example:
        >>> pairs = [
        ...     ("config.py", config_patch),
        ...     ("utils.py", utils_patch),
        ...     ("main.py", main_patch),
        ... ]
        >>> result = apply_patches_atomic(pairs)
        >>> if result["success"]:
        ...     print(f"Applied {result['applied']} patches atomically")
    """
    if not file_patch_pairs:
        return {
            "success": True,
            "applied": 0,
            "message": "No patches to apply",
        }

    # Phase 1: Validate all patches
    logger.info(f"Validating {len(file_patch_pairs)} patches")
    validations: List[Tuple[str, Dict[str, Any]]] = []

    for file_path, patch in file_patch_pairs:
        result = validate_patch(file_path, patch)
        validations.append((file_path, result))

        if not result.get("can_apply", False):
            logger.error(f"Validation failed for {file_path}: {result.get('reason')}")

    # Check if all valid
    failures = [(fp, v) for fp, v in validations if not v.get("can_apply", False)]
    if failures:
        return {
            "success": False,
            "phase": "validation",
            "validated": len(validations),
            "failed": len(failures),
            "failures": [
                {"file": fp, "reason": v.get("reason", v.get("error", "Unknown error"))}
                for fp, v in failures
            ],
        }

    logger.info("All patches validated successfully")

    # Phase 2: Create backups for all files
    logger.info("Creating backups")
    backups: Dict[str, str] = {}

    try:
        for file_path, _ in file_patch_pairs:
            backup_result = backup_file(file_path)
            if not backup_result["success"]:
                raise Exception(f"Backup failed for {file_path}: {backup_result['error']}")
            backups[file_path] = backup_result["backup_file"]

        logger.info(f"Created {len(backups)} backups")

        # Phase 3: Apply all patches
        logger.info("Applying patches")
        applied: List[str] = []

        for file_path, patch in file_patch_pairs:
            result = apply_patch(file_path, patch)

            if not result["success"]:
                # Rollback: restore all backups
                logger.error(f"Apply failed for {file_path}, rolling back all changes")

                for backed_up_file, backup_path in backups.items():
                    restore_result = restore_backup(backup_path)
                    if not restore_result["success"]:
                        logger.error(
                            f"CRITICAL: Cannot restore {backed_up_file}: "
                            f"{restore_result['error']}"
                        )

                return {
                    "success": False,
                    "phase": "apply",
                    "applied": len(applied),
                    "failed_at": file_path,
                    "error": result["error"],
                    "rolled_back": True,
                }

            applied.append(file_path)

        # Success - clean up backups
        for backup_path in backups.values():
            try:
                Path(backup_path).unlink()
            except Exception as e:
                logger.warning(f"Could not delete backup {backup_path}: {e}")

        logger.info(f"Successfully applied {len(applied)} patches")

        return {
            "success": True,
            "applied": len(applied),
            "message": f"Atomically applied {len(applied)} patches",
        }

    except Exception as e:
        # Emergency rollback
        logger.error(f"Critical error: {str(e)}")

        for file_path, backup_path in backups.items():
            try:
                restore_backup(backup_path)
            except Exception as restore_error:
                logger.error(
                    f"CRITICAL: Cannot restore {file_path} from {backup_path}: " f"{restore_error}"
                )

        return {
            "success": False,
            "phase": "unexpected",
            "error": str(e),
            "attempted_rollback": True,
        }


def apply_patch_progressive(file_path: str, patch: str) -> Dict[str, Any]:
    """Apply patch with progressive validation and detailed error reporting.

    This pattern validates at each step (safety, validation, backup, apply)
    and provides maximum information about what succeeded and what failed.
    This is the most thorough approach with detailed step-by-step tracking.

    This is useful for:
    - Debugging patch failures
    - Understanding exactly where problems occur
    - Maximum visibility into the patch process

    Args:
        file_path: Path to the file to patch
        patch: Patch to apply

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "steps": {
                    "safety_check": {"passed": True, "details": None},
                    "validation": {"passed": True, "details": {...}},
                    "backup": {"passed": True, "details": {...}},
                    "apply": {"passed": True, "details": {...}}
                },
                "backup_file": str,
                "changes": {...}
            }

        Dict with the following structure on failure:
            {
                "success": False,
                "steps": {
                    ... (steps completed so far)
                },
                "error": str,
                "error_type": str,
                "failed_at": str
            }

    Example:
        >>> result = apply_patch_progressive("module.py", patch)
        >>> if not result["success"]:
        ...     print(f"Failed at: {result['failed_at']}")
        ...     print(f"Steps completed: {list(result['steps'].keys())}")
    """
    results: Dict[str, Any] = {"success": False, "steps": {}}

    # Step 1: Check file safety
    path = Path(file_path)
    safety_check = validate_file_safety(path, check_write=True, check_space=True)
    results["steps"]["safety_check"] = {
        "passed": safety_check is None,
        "details": safety_check,
    }

    if safety_check:
        results["error"] = safety_check["error"]
        results["error_type"] = safety_check["error_type"]
        results["failed_at"] = "safety_check"
        return results

    # Step 2: Validate patch format
    validation = validate_patch(file_path, patch)
    results["steps"]["validation"] = {
        "passed": validation.get("can_apply", False) if validation["success"] else False,
        "details": validation,
    }

    if not validation.get("can_apply", False):
        results["error"] = validation.get("reason") or validation.get("error", "Validation failed")
        results["error_type"] = validation.get("error_type", "context_mismatch")
        results["failed_at"] = "validation"
        return results

    # Step 3: Create backup
    backup = backup_file(file_path)
    results["steps"]["backup"] = {"passed": backup["success"], "details": backup}

    if not backup["success"]:
        results["error"] = backup["error"]
        results["error_type"] = backup["error_type"]
        results["failed_at"] = "backup"
        return results

    # Step 4: Apply patch
    apply_result = apply_patch(file_path, patch)
    results["steps"]["apply"] = {
        "passed": apply_result["success"],
        "details": apply_result,
    }

    if not apply_result["success"]:
        # Step 5: Restore from backup
        restore_result = restore_backup(backup["backup_file"])
        results["steps"]["restore"] = {
            "passed": restore_result["success"],
            "details": restore_result,
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
