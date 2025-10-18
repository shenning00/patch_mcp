"""Apply patch tool - apply unified diff patches to files.

This module implements the apply_patch tool which applies patches to files
with comprehensive security checks and optional dry-run mode.

CRITICAL: Supports dry_run parameter for testing without modification.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

from ..utils import atomic_file_replace, validate_file_safety
from .validate import validate_patch


def apply_patch(file_path: str, patch: str, dry_run: bool = False) -> Dict[str, Any]:
    """Apply a unified diff patch to a file.

    Applies a patch to a file with security checks. Supports dry-run mode
    to validate without modifying the file.

    WARNING: This WILL modify the file in place (unless dry_run=True).

    Dry Run Mode:
        - When dry_run=True, validates patch but doesn't modify file
        - Returns same format as normal apply
        - Useful for safe automation and pre-flight checks

    Security:
        - Validates file safety (no symlinks, no binaries)
        - Checks disk space before modification
        - Verifies write permissions

    Args:
        file_path: Path to the file to patch
        patch: Unified diff patch content
        dry_run: If True, validate only without modifying file (default: False)

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "file_path": str,
                "applied": True,
                "changes": {
                    "lines_added": int,
                    "lines_removed": int,
                    "hunks_applied": int
                },
                "message": str
            }

        Dict with the following structure on failure:
            {
                "success": False,
                "file_path": str,
                "applied": False,
                "error": str,
                "error_type": str
            }

    Example:
        >>> # Test first with dry run
        >>> result = apply_patch("config.py", patch, dry_run=True)
        >>> if result["success"]:
        ...     # Now apply for real
        ...     result = apply_patch("config.py", patch)
    """
    path = Path(file_path)

    # Security checks
    # For dry_run, we don't need write or space checks
    safety_error = validate_file_safety(
        path, check_write=not dry_run, check_space=not dry_run
    )
    if safety_error:
        return {
            "success": False,
            "file_path": str(path),
            "applied": False,
            **safety_error,
        }

    # Validate patch can be applied
    validation = validate_patch(str(path), patch)

    if not validation["success"]:
        # Patch cannot be applied
        return {
            "success": False,
            "file_path": str(path),
            "applied": False,
            "error": validation.get("reason") or validation.get("error", "Patch validation failed"),
            "error_type": validation.get("error_type", "context_mismatch"),
        }

    # Extract change statistics from validation preview
    preview = validation.get("preview", {})
    changes = {
        "lines_added": preview.get("lines_to_add", 0),
        "lines_removed": preview.get("lines_to_remove", 0),
        "hunks_applied": preview.get("hunks", 0),
    }

    # If dry run, return success without modifying
    if dry_run:
        return {
            "success": True,
            "file_path": str(path),
            "applied": True,
            "changes": changes,
            "message": f"Patch can be applied to {path.name} (dry run)",
        }

    # Apply the patch for real
    try:
        # Read original file
        with open(path, "r", encoding="utf-8") as f:
            original_lines = f.readlines()

        # Parse patch and apply changes
        modified_lines = _apply_patch_to_lines(original_lines, patch)

        # Write to temporary file first
        temp_file = Path(tempfile.mktemp(dir=path.parent, prefix=".patch_tmp_"))
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.writelines(modified_lines)

            # Atomically replace original file
            atomic_file_replace(temp_file, path)

        except Exception:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise

        return {
            "success": True,
            "file_path": str(path),
            "applied": True,
            "changes": changes,
            "message": f"Successfully applied patch to {path.name}",
        }

    except UnicodeDecodeError as e:
        return {
            "success": False,
            "file_path": str(path),
            "applied": False,
            "error": f"Cannot decode file as UTF-8: {str(e)}",
            "error_type": "encoding_error",
        }
    except OSError as e:
        return {
            "success": False,
            "file_path": str(path),
            "applied": False,
            "error": f"I/O error: {str(e)}",
            "error_type": "io_error",
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": str(path),
            "applied": False,
            "error": f"Failed to apply patch: {str(e)}",
            "error_type": "io_error",
        }


def _apply_patch_to_lines(original_lines: list[str], patch: str) -> list[str]:
    """Apply patch to lines and return modified lines.

    Args:
        original_lines: Original file lines
        patch: Patch content

    Returns:
        Modified lines after applying patch

    Raises:
        ValueError: If patch cannot be applied
    """
    # Parse patch into hunks
    hunks = _parse_patch_hunks(patch)

    if not hunks:
        # Empty patch - return original lines
        return original_lines

    # Apply hunks in reverse order (to maintain line numbers)
    result_lines = original_lines.copy()

    # Sort hunks by starting line (descending) to apply from bottom to top
    sorted_hunks = sorted(hunks, key=lambda h: h["source_start"], reverse=True)

    for hunk in sorted_hunks:
        result_lines = _apply_single_hunk(result_lines, hunk)

    return result_lines


def _parse_patch_hunks(patch: str) -> list[Dict[str, Any]]:
    """Parse patch into hunk structures.

    Args:
        patch: Patch content

    Returns:
        List of hunk dictionaries
    """
    hunks = []
    current_hunk = None
    lines = patch.split("\n")

    for line in lines:
        if line.startswith("@@"):
            # New hunk
            parts = line.split("@@")[1].strip().split()
            if len(parts) >= 2:
                # Parse source range
                source_part = parts[0][1:].split(",")  # Remove '-'
                source_start = int(source_part[0])
                source_count = int(source_part[1]) if len(source_part) > 1 else 1

                current_hunk = {
                    "source_start": source_start,
                    "source_count": source_count,
                    "lines": [],
                }
                hunks.append(current_hunk)
        elif current_hunk is not None:
            # Add line to current hunk
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk["lines"].append(("add", line[1:]))
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk["lines"].append(("remove", line[1:]))
            elif line.startswith(" "):
                current_hunk["lines"].append(("context", line[1:]))
            elif line.startswith("\\"):
                # "\ No newline at end of file" - skip
                pass

    return hunks


def _apply_single_hunk(lines: list[str], hunk: Dict[str, Any]) -> list[str]:
    """Apply a single hunk to lines.

    Args:
        lines: Current file lines
        hunk: Hunk to apply

    Returns:
        Modified lines

    Raises:
        ValueError: If hunk cannot be applied
    """
    # Convert to 0-based index
    start_idx = hunk["source_start"] - 1

    # Build new content for this section
    new_section = []
    original_idx = start_idx
    hunk_lines = hunk["lines"]

    for action, content in hunk_lines:
        if action == "context":
            # Context line - should match original
            new_section.append(content + "\n")
            original_idx += 1
        elif action == "remove":
            # Remove line - skip it (don't add to new_section)
            original_idx += 1
        elif action == "add":
            # Add line
            new_section.append(content + "\n")

    # Calculate how many lines to replace
    lines_to_replace = hunk["source_count"]

    # Replace the section
    result = lines[:start_idx] + new_section + lines[start_idx + lines_to_replace :]

    return result
