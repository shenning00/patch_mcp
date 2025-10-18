"""Generate patch tool - create unified diff patches from file comparisons.

This module implements the generate_patch tool which creates unified diff patches
by comparing two versions of a file.
"""

import difflib
from pathlib import Path
from typing import Any, Dict

from ..utils import validate_file_safety


def generate_patch(
    original_file: str, modified_file: str, context_lines: int = 3
) -> Dict[str, Any]:
    """Generate a unified diff patch by comparing two files.

    Creates a unified diff format patch from the differences between an original
    and modified version of a file. The patch can then be applied to other files
    using apply_patch.

    Security:
        - Both files are validated for safety (no symlinks, no binaries)
        - Files must be under 10MB
        - UTF-8 encoding is assumed

    Args:
        original_file: Path to the original/old version of the file
        modified_file: Path to the modified/new version of the file
        context_lines: Number of context lines to include (default: 3)

    Returns:
        Dict with the following structure on success:
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

        Dict with the following structure on failure:
            {
                "success": False,
                "error": str,
                "error_type": str
            }

    Example:
        >>> result = generate_patch("config_v1.py", "config_v2.py")
        >>> if result["success"]:
        ...     print(f"Generated patch with {result['changes']['hunks']} hunks")
        ...     patch_content = result["patch"]
    """
    original_path = Path(original_file)
    modified_path = Path(modified_file)

    # Security checks for both files
    for file_path, file_label in [
        (original_path, "Original"),
        (modified_path, "Modified"),
    ]:
        safety_error = validate_file_safety(file_path)
        if safety_error:
            return {
                "success": False,
                "error": f"{file_label} file: {safety_error['error']}",
                "error_type": safety_error["error_type"],
            }

    # Read both files
    try:
        with open(original_path, "r", encoding="utf-8") as f:
            original_lines = f.readlines()
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Cannot decode original file as UTF-8: {str(e)}",
            "error_type": "encoding_error",
        }
    except OSError as e:
        return {
            "success": False,
            "error": f"Cannot read original file: {str(e)}",
            "error_type": "io_error",
        }

    try:
        with open(modified_path, "r", encoding="utf-8") as f:
            modified_lines = f.readlines()
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Cannot decode modified file as UTF-8: {str(e)}",
            "error_type": "encoding_error",
        }
    except OSError as e:
        return {
            "success": False,
            "error": f"Cannot read modified file: {str(e)}",
            "error_type": "io_error",
        }

    # Generate unified diff
    diff_lines = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=original_path.name,
            tofile=modified_path.name,
            n=context_lines,
            lineterm="",
        )
    )

    # Join with newlines and add final newline if content exists
    if diff_lines:
        patch = "\n".join(diff_lines) + "\n"
    else:
        patch = ""

    # Count changes
    lines_added = 0
    lines_removed = 0
    hunks = 0

    for line in diff_lines:
        if line.startswith("@@"):
            hunks += 1
        elif line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            lines_removed += 1

    # Return result
    if hunks == 0:
        message = "Files are identical - no patch generated"
    else:
        message = "Generated patch from file comparison"

    return {
        "success": True,
        "original_file": str(original_path),
        "modified_file": str(modified_path),
        "patch": patch,
        "changes": {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "hunks": hunks,
        },
        "message": message,
    }
