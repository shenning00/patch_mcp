"""Update content tool - modify files by providing original and new content.

This module implements the update_content tool which allows LLMs to modify files
by providing the expected original content and desired new content. The tool
verifies the original content matches the file, generates a unified diff, and
applies the changes atomically.
"""

import difflib
from pathlib import Path
from typing import Any, Dict

from ..utils import atomic_file_replace, validate_file_safety


def update_content(
    file_path: str, original_content: str, new_content: str, dry_run: bool = False
) -> Dict[str, Any]:
    """Update file content with safety verification and diff generation.

    This tool is designed for LLMs that have read a file and want to modify it.
    It verifies that the original_content matches the current file (preventing
    race conditions), generates a unified diff showing the changes, and applies
    the modification atomically.

    Workflow:
        1. Validate file safety (not symlink, not binary, etc.)
        2. Read current file content
        3. Verify current content matches original_content
        4. Generate unified diff (original → new)
        5. Apply changes atomically (or preview if dry_run)

    Security:
        - Validates file safety before reading/writing
        - Verifies content hasn't changed since read (prevents races)
        - Atomic file replacement (no partial writes)
        - Rejects symlinks, binary files, oversized files

    Args:
        file_path: Path to the file to modify
        original_content: Expected current file content (for verification)
        new_content: Desired new file content
        dry_run: If True, preview changes without applying (default: False)

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "applied": bool,  # False for dry_run, True for actual apply
                "file_path": str,
                "diff": str,  # Unified diff showing changes
                "changes": {
                    "lines_added": int,
                    "lines_removed": int,
                    "hunks": int
                },
                "message": str
            }

        Dict with the following structure on content mismatch:
            {
                "success": False,
                "error": "File content does not match expected original",
                "error_type": "content_mismatch",
                "diff_from_expected": str,  # Shows actual vs expected
                "message": str
            }

        Dict with the following structure on other errors:
            {
                "success": False,
                "error": str,
                "error_type": str,
                "message": str
            }

    Example:
        >>> # Read the file
        >>> with open("config.py") as f:
        ...     original = f.read()
        >>>
        >>> # Construct new content
        >>> new = original.replace("version = '2.0.0'", "version = '3.0.0'")
        >>>
        >>> # Preview changes first
        >>> result = update_content("config.py", original, new, dry_run=True)
        >>> print(result["diff"])  # Review the unified diff
        >>>
        >>> # Apply if satisfied
        >>> result = update_content("config.py", original, new)
        >>> # File is now updated
    """
    path = Path(file_path)

    # Step 1: Security validation
    safety_error = validate_file_safety(path, check_write=True, check_space=True)
    if safety_error:
        return {"success": False, **safety_error}

    # Step 2: Read current file content
    try:
        with open(path, "r", encoding="utf-8") as f:
            current_content = f.read()
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Cannot decode file as UTF-8: {str(e)}",
            "error_type": "encoding_error",
            "message": "File encoding is not UTF-8",
        }
    except OSError as e:
        return {
            "success": False,
            "error": f"Cannot read file: {str(e)}",
            "error_type": "io_error",
            "message": f"Failed to read {path.name}",
        }

    # Step 3: Verify original_content matches current file
    if current_content != original_content:
        # Generate diff showing what's actually different
        expected_lines = original_content.splitlines(keepends=True)
        actual_lines = current_content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                expected_lines, actual_lines, fromfile="expected", tofile="actual", n=3
            )
        )

        actual_diff = (
            "".join(diff_lines)
            if diff_lines
            else "(content differs but no line-based diff available)"
        )

        return {
            "success": False,
            "error": "File content does not match expected original content",
            "error_type": "content_mismatch",
            "diff_from_expected": actual_diff,
            "message": "File has been modified since you read it. Re-read the file and try again.",
        }

    # Step 4: Generate unified diff (original → new)
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(original_lines, new_lines, fromfile=path.name, tofile=path.name, n=3)
    )

    # Check if there are any changes
    if not diff_lines:
        return {
            "success": True,
            "applied": False,
            "file_path": str(path),
            "diff": "",
            "changes": {"lines_added": 0, "lines_removed": 0, "hunks": 0},
            "message": "No changes needed - content is identical",
        }

    patch = "".join(diff_lines)

    # Count changes for statistics
    lines_added = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    lines_removed = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    hunks = sum(1 for line in diff_lines if line.startswith("@@"))

    # Step 5a: Dry run - return preview without applying
    if dry_run:
        return {
            "success": True,
            "applied": False,
            "file_path": str(path),
            "diff": patch,
            "changes": {
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "hunks": hunks,
            },
            "message": f"Dry run: would modify {hunks} section(s) (+{lines_added}/-{lines_removed} lines)",
        }

    # Step 5b: Apply changes atomically
    try:
        # Write to temporary file first
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Atomic replace (safe even if interrupted)
        atomic_file_replace(temp_path, path)

        return {
            "success": True,
            "applied": True,
            "file_path": str(path),
            "diff": patch,
            "changes": {
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "hunks": hunks,
            },
            "message": f"Successfully updated {path.name} (+{lines_added}/-{lines_removed} lines)",
        }

    except OSError as e:
        # Clean up temp file if it exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        return {
            "success": False,
            "applied": False,
            "error": f"Failed to write file: {str(e)}",
            "error_type": "io_error",
            "message": f"Could not update {path.name}",
        }
    except Exception as e:
        return {
            "success": False,
            "applied": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "io_error",
            "message": f"Failed to update {path.name}",
        }
