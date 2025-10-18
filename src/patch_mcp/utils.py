"""Security and utility functions for File Patch MCP Server.

This module provides critical security validation functions to ensure safe
file operations. All file operations MUST go through these security checks
before being performed.
"""

import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

# Security configuration constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_FREE_SPACE = 100 * 1024 * 1024  # 100MB
BINARY_CHECK_BYTES = 8192
NON_TEXT_THRESHOLD = 0.3  # 30% non-text chars = binary


def validate_file_safety(
    file_path: Path, check_write: bool = False, check_space: bool = False
) -> Optional[Dict[str, Any]]:
    """Comprehensive file safety validation.

    Performs security checks on a file to ensure it is safe to operate on.
    This function MUST be called before any file operations.

    Security Checks:
        1. File exists and is a regular file
        2. Not a symlink (security policy - rejected)
        3. Not a binary file (not supported)
        4. Within file size limits (10MB max)
        5. Write permissions (if check_write=True)
        6. Sufficient disk space (if check_space=True)

    Args:
        file_path: Path to the file to validate
        check_write: If True, verify file is writable
        check_space: If True, verify sufficient disk space (100MB + 110% of file size)

    Returns:
        None if all checks pass, otherwise a dict with 'error' and 'error_type' fields

    Example:
        >>> path = Path("config.py")
        >>> error = validate_file_safety(path, check_write=True, check_space=True)
        >>> if error:
        ...     return {"success": False, **error}
    """
    # Check file exists
    if not file_path.exists():
        return {"error": f"File not found: {file_path}", "error_type": "file_not_found"}

    # Check is regular file
    if not file_path.is_file():
        return {"error": f"Not a regular file: {file_path}", "error_type": "io_error"}

    # Security: Check for symlinks (security policy - always rejected)
    if file_path.is_symlink():
        return {
            "error": f"Symlinks are not allowed (security policy): {file_path}",
            "error_type": "symlink_error",
        }

    # Check if binary file
    if is_binary_file(file_path):
        return {
            "error": f"Binary files are not supported: {file_path}",
            "error_type": "binary_file",
        }

    # Check file size limits
    try:
        file_size = file_path.stat().st_size
    except OSError as e:
        return {"error": f"Cannot stat file: {str(e)}", "error_type": "io_error"}

    if file_size > MAX_FILE_SIZE:
        return {
            "error": f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})",
            "error_type": "resource_limit",
        }

    # Check write permission if needed
    if check_write:
        if not os.access(file_path, os.W_OK):
            return {
                "error": f"File is not writable: {file_path}",
                "error_type": "permission_denied",
            }

    # Check disk space if needed
    if check_space:
        try:
            disk_usage = shutil.disk_usage(file_path.parent)
            free_space = disk_usage.free

            if free_space < MIN_FREE_SPACE:
                return {
                    "error": f"Insufficient disk space: {free_space} bytes free (minimum: {MIN_FREE_SPACE})",
                    "error_type": "disk_space_error",
                }

            # Also check if we have at least 110% of file size available
            safety_margin = int(file_size * 1.1)
            if free_space < safety_margin:
                return {
                    "error": f"Insufficient disk space for operation: {free_space} bytes free, {safety_margin} needed",
                    "error_type": "disk_space_error",
                }
        except Exception as e:
            return {"error": f"Cannot check disk space: {str(e)}", "error_type": "io_error"}

    return None  # All checks passed


def is_binary_file(file_path: Path, check_bytes: int = BINARY_CHECK_BYTES) -> bool:
    """Check if a file is binary.

    Uses multiple heuristics to detect binary files:
        1. Presence of null bytes (strong indicator)
        2. Attempt UTF-8 decoding (valid UTF-8 = likely text)
        3. Ratio of non-text characters (>30% = likely binary)

    Args:
        file_path: Path to the file to check
        check_bytes: Number of bytes to check (default: 8192)

    Returns:
        True if file appears to be binary, False otherwise

    Example:
        >>> if is_binary_file(Path("image.png")):
        ...     print("Binary file detected")
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(check_bytes)

            # Empty file is considered text
            if not chunk:
                return False

            # Check for null bytes (strong indicator of binary)
            if b"\x00" in chunk:
                return True

            # Try to decode as UTF-8 - if successful, it's likely text
            try:
                chunk.decode("utf-8")
                return False  # Valid UTF-8 text
            except UnicodeDecodeError:
                pass  # Not valid UTF-8, continue checking

            # Check for high ratio of non-text bytes
            # Text characters: printable ASCII + common whitespace
            text_chars = bytes(range(32, 127)) + b"\n\r\t\b"
            non_text = sum(1 for byte in chunk if byte not in text_chars)

            # If more than 30% non-text characters, likely binary
            if (non_text / len(chunk)) > NON_TEXT_THRESHOLD:
                return True

            return False
    except Exception:
        # If we can't read it, assume binary for safety
        return True


def check_path_traversal(file_path: str, base_dir: str) -> Optional[Dict[str, Any]]:
    """Check if a path attempts to escape a base directory.

    Validates that a file path stays within a specified base directory,
    preventing directory traversal attacks (e.g., "../../../etc/passwd").

    Args:
        file_path: Path to validate (can be relative or absolute)
        base_dir: Base directory that file_path must stay within

    Returns:
        None if path is safe, otherwise a dict with 'error' and 'error_type' fields

    Example:
        >>> error = check_path_traversal("../../etc/passwd", "/home/user/project")
        >>> if error:
        ...     return {"success": False, **error}
    """
    try:
        # Resolve to absolute paths to handle .. and symlinks
        abs_file = Path(file_path).resolve()
        abs_base = Path(base_dir).resolve()

        # Check if file path is under base directory
        try:
            abs_file.relative_to(abs_base)
            return None  # Path is safe
        except ValueError:
            return {
                "error": f"Path attempts to escape base directory: {file_path}",
                "error_type": "permission_denied",
            }
    except Exception as e:
        return {"error": f"Invalid path: {str(e)}", "error_type": "io_error"}


def atomic_file_replace(source: Path, target: Path) -> None:
    """Atomically replace a file using rename.

    Performs an atomic file replacement operation. On Unix systems, this is
    truly atomic. On Windows, the target must be removed first (not atomic).

    Args:
        source: Path to the source file (must exist)
        target: Path to the target file (will be replaced)

    Raises:
        OSError: If the atomic replace operation fails

    Example:
        >>> temp_file = Path("config.py.tmp")
        >>> target_file = Path("config.py")
        >>> # Write to temp_file first
        >>> atomic_file_replace(temp_file, target_file)
    """
    if platform.system() == "Windows":
        # Windows: need to remove target first (not atomic, but best we can do)
        if target.exists():
            target.unlink()
        source.rename(target)
    else:
        # Unix: atomic rename
        source.rename(target)
