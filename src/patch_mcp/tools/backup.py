"""Backup and restore tools for File Patch MCP Server.

This module provides tools for creating timestamped backups of files and
restoring from those backups. These tools are essential for safe patch
application workflows.
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils import atomic_file_replace, validate_file_safety


def backup_file(file_path: str) -> Dict[str, Any]:
    """Create a timestamped backup copy of a file.

    Creates a backup with naming format: {original}.backup.YYYYMMDD_HHMMSS
    Example: config.py -> config.py.backup.20250117_143052

    The backup is created in the same directory as the original file and
    preserves file metadata (permissions, timestamps) using shutil.copy2().

    Args:
        file_path: Path to the file to backup (absolute or relative)

    Returns:
        Dict with success status and backup information:
        Success: {
            "success": True,
            "original_file": "/path/to/file.py",
            "backup_file": "/path/to/file.py.backup.20250117_143052",
            "backup_size": 1024,
            "message": "Backup created successfully"
        }
        Failure: {
            "success": False,
            "original_file": "/path/to/file.py",
            "error": "Error description",
            "error_type": "error_type_enum"
        }

    Example:
        >>> result = backup_file("config.py")
        >>> if result["success"]:
        ...     print(f"Backup: {result['backup_file']}")
        >>> else:
        ...     print(f"Error: {result['error']}")
    """
    # Convert to Path object
    path = Path(file_path)
    original_file_str = str(path.resolve())

    # Security checks on source file
    safety_error = validate_file_safety(path, check_write=False, check_space=False)
    if safety_error:
        return {"success": False, "original_file": original_file_str, **safety_error}

    # Generate timestamp in format YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create backup filename: original.backup.YYYYMMDD_HHMMSS
    backup_path = Path(f"{path}.backup.{timestamp}")

    try:
        # Check if we can write to the directory
        parent_dir = path.parent
        if not parent_dir.exists():
            return {
                "success": False,
                "original_file": original_file_str,
                "error": f"Parent directory does not exist: {parent_dir}",
                "error_type": "io_error",
            }

        if not os.access(parent_dir, os.W_OK):
            return {
                "success": False,
                "original_file": original_file_str,
                "error": f"No write permission in directory: {parent_dir}",
                "error_type": "permission_denied",
            }

        # Check disk space before creating backup
        import shutil as shutil_module

        try:
            disk_usage = shutil_module.disk_usage(parent_dir)
            free_space = disk_usage.free
            file_size = path.stat().st_size
            MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB

            if free_space < MIN_FREE_SPACE:
                return {
                    "success": False,
                    "original_file": original_file_str,
                    "error": f"Insufficient disk space: {free_space} bytes free (minimum: {MIN_FREE_SPACE})",
                    "error_type": "disk_space_error",
                }

            # Need at least 110% of file size available
            safety_margin = int(file_size * 1.1)
            if free_space < safety_margin:
                return {
                    "success": False,
                    "original_file": original_file_str,
                    "error": f"Insufficient disk space for backup: {free_space} bytes free, {safety_margin} needed",
                    "error_type": "disk_space_error",
                }
        except Exception as e:
            return {
                "success": False,
                "original_file": original_file_str,
                "error": f"Cannot check disk space: {str(e)}",
                "error_type": "io_error",
            }

        # Create backup using copy2 to preserve metadata
        shutil.copy2(path, backup_path)

        # Get backup file size
        backup_size = backup_path.stat().st_size

        return {
            "success": True,
            "original_file": original_file_str,
            "backup_file": str(backup_path.resolve()),
            "backup_size": backup_size,
            "message": "Backup created successfully",
        }

    except PermissionError as e:
        return {
            "success": False,
            "original_file": original_file_str,
            "error": f"Permission denied: {str(e)}",
            "error_type": "permission_denied",
        }
    except OSError as e:
        # Handle insufficient disk space or other OS errors
        error_msg = str(e).lower()
        if "no space" in error_msg or "disk full" in error_msg:
            return {
                "success": False,
                "original_file": original_file_str,
                "error": f"Insufficient disk space: {str(e)}",
                "error_type": "disk_space_error",
            }
        return {
            "success": False,
            "original_file": original_file_str,
            "error": f"I/O error during backup: {str(e)}",
            "error_type": "io_error",
        }
    except Exception as e:
        return {
            "success": False,
            "original_file": original_file_str,
            "error": f"Unexpected error during backup: {str(e)}",
            "error_type": "io_error",
        }


def parse_backup_filename(backup_file: str) -> Optional[str]:
    """Parse backup filename to extract original file path.

    Backup files follow the format: {original}.backup.YYYYMMDD_HHMMSS
    This function extracts the original filename from the backup filename.

    Args:
        backup_file: Path to the backup file

    Returns:
        Original file path if valid backup filename, None otherwise

    Example:
        >>> parse_backup_filename("file.py.backup.20250117_143052")
        'file.py'
        >>> parse_backup_filename("/path/to/file.py.backup.20250117_143052")
        '/path/to/file.py'
        >>> parse_backup_filename("invalid.txt")
        None
    """
    # Convert to Path to extract filename
    backup_path = Path(backup_file)

    # Check if filename matches pattern: *.backup.YYYYMMDD_HHMMSS
    pattern = r"^(.+)\.backup\.\d{8}_\d{6}$"
    match = re.match(pattern, backup_path.name)

    if match:
        # Extract original filename
        original_name = match.group(1)
        # Reconstruct full path if input had a directory
        if backup_path.parent != Path("."):
            return str(backup_path.parent / original_name)
        return original_name

    return None


def restore_backup(
    backup_file: str, target_file: Optional[str] = None, force: bool = False
) -> Dict[str, Any]:
    """Restore a file from a timestamped backup.

    Restores a backup file to its original location or to a specified target.
    By default, the target location is auto-detected from the backup filename.

    Features:
    - Auto-detects target from backup filename if not specified
    - Checks if target has been modified since backup (unless force=True)
    - Uses atomic file replacement for safe restoration
    - Preserves file metadata from backup

    Args:
        backup_file: Path to the backup file to restore from
        target_file: Where to restore (optional, auto-detected if None)
        force: Overwrite target even if modified since backup (default: False)

    Returns:
        Dict with success status and restore information:
        Success: {
            "success": True,
            "backup_file": "/path/to/file.py.backup.20250117_143052",
            "restored_to": "/path/to/file.py",
            "restored_size": 1024,
            "message": "Successfully restored from backup"
        }
        Failure: {
            "success": False,
            "backup_file": "/path/to/file.py.backup.20250117_143052",
            "error": "Error description",
            "error_type": "error_type_enum"
        }

    Example:
        >>> # Auto-detect target from backup filename
        >>> result = restore_backup("config.py.backup.20250117_143052")
        >>> # Explicit target location
        >>> result = restore_backup("config.py.backup.20250117_143052",
        ...                         target_file="config_restored.py")
        >>> # Force overwrite even if modified
        >>> result = restore_backup("config.py.backup.20250117_143052", force=True)
    """
    import os

    # Convert to Path object
    backup_path = Path(backup_file)
    backup_file_str = str(backup_path.resolve()) if backup_path.exists() else backup_file

    # Check if backup file exists
    if not backup_path.exists():
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Backup file not found: {backup_file}",
            "error_type": "file_not_found",
        }

    # Check backup file is regular file
    if not backup_path.is_file():
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Backup is not a regular file: {backup_file}",
            "error_type": "io_error",
        }

    # Check backup file is readable
    if not os.access(backup_path, os.R_OK):
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Backup file is not readable: {backup_file}",
            "error_type": "permission_denied",
        }

    # Auto-detect target if not provided
    if target_file is None:
        target_file = parse_backup_filename(backup_file)
        if target_file is None:
            return {
                "success": False,
                "backup_file": backup_file_str,
                "error": f"Cannot parse backup filename (expected format: file.backup.YYYYMMDD_HHMMSS): {backup_file}",
                "error_type": "io_error",
            }

    target_path = Path(target_file)
    target_file_str = str(target_path.resolve())

    # Check if target is a symlink (security policy)
    if target_path.exists() and target_path.is_symlink():
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Target is a symlink (security policy): {target_file}",
            "error_type": "symlink_error",
        }

    # Create parent directory if needed
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Cannot create parent directory: {str(e)}",
            "error_type": "io_error",
        }

    # Check if we can write to target location
    if target_path.exists():
        if not os.access(target_path, os.W_OK):
            return {
                "success": False,
                "backup_file": backup_file_str,
                "error": f"Target file is not writable: {target_file}",
                "error_type": "permission_denied",
            }
    else:
        # Check if we can write to parent directory
        if not os.access(target_path.parent, os.W_OK):
            return {
                "success": False,
                "backup_file": backup_file_str,
                "error": f"Cannot write to target directory: {target_path.parent}",
                "error_type": "permission_denied",
            }

    # Check disk space before restoration
    try:
        disk_usage = shutil.disk_usage(target_path.parent)
        free_space = disk_usage.free
        backup_size = backup_path.stat().st_size
        MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB

        if free_space < MIN_FREE_SPACE:
            return {
                "success": False,
                "backup_file": backup_file_str,
                "error": f"Insufficient disk space: {free_space} bytes free (minimum: {MIN_FREE_SPACE})",
                "error_type": "disk_space_error",
            }

        # Need at least 110% of backup size available
        safety_margin = int(backup_size * 1.1)
        if free_space < safety_margin:
            return {
                "success": False,
                "backup_file": backup_file_str,
                "error": f"Insufficient disk space for restore: {free_space} bytes free, {safety_margin} needed",
                "error_type": "disk_space_error",
            }
    except Exception as e:
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Cannot check disk space: {str(e)}",
            "error_type": "io_error",
        }

    # Check if target has been modified since backup (unless force=True)
    modification_warning = ""
    if target_path.exists() and not force:
        try:
            target_mtime = target_path.stat().st_mtime
            backup_mtime = backup_path.stat().st_mtime

            if target_mtime > backup_mtime:
                modification_warning = " (warning: target was modified since backup)"
        except Exception:
            # If we can't check, proceed anyway
            pass

    try:
        # Use atomic file replacement for safe restoration
        # First copy to a temporary file in the same directory
        temp_path = target_path.parent / f".{target_path.name}.tmp.{os.getpid()}"

        try:
            # Copy backup to temporary file
            shutil.copy2(backup_path, temp_path)

            # Atomically replace target with temp file
            atomic_file_replace(temp_path, target_path)

            # Get restored file size
            restored_size = target_path.stat().st_size

            return {
                "success": True,
                "backup_file": backup_file_str,
                "restored_to": target_file_str,
                "restored_size": restored_size,
                "message": f"Successfully restored from backup{modification_warning}",
            }

        finally:
            # Clean up temp file if it still exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass  # Best effort cleanup

    except PermissionError as e:
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Permission denied during restore: {str(e)}",
            "error_type": "permission_denied",
        }
    except OSError as e:
        # Handle insufficient disk space or other OS errors
        error_msg = str(e).lower()
        if "no space" in error_msg or "disk full" in error_msg:
            return {
                "success": False,
                "backup_file": backup_file_str,
                "error": f"Insufficient disk space: {str(e)}",
                "error_type": "disk_space_error",
            }
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"I/O error during restore: {str(e)}",
            "error_type": "io_error",
        }
    except Exception as e:
        return {
            "success": False,
            "backup_file": backup_file_str,
            "error": f"Unexpected error during restore: {str(e)}",
            "error_type": "io_error",
        }
