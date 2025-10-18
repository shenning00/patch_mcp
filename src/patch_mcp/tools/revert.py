"""Revert patch tool - reverse previously applied patches.

This module implements the revert_patch tool which reverts a previously
applied patch by reversing it (swapping additions and removals) and applying
the reversed patch.

CRITICAL: Use the EXACT same patch that was originally applied.
"""

from pathlib import Path
from typing import Any, Dict

from .apply import apply_patch


def revert_patch(file_path: str, patch: str) -> Dict[str, Any]:
    """Revert a previously applied patch (apply in reverse).

    Takes a patch and applies it in reverse to undo the changes it made.
    This works by swapping the + and - lines in the patch and then applying
    the reversed patch.

    IMPORTANT:
        - Use the EXACT same patch that was originally applied
        - The file must not have been modified in the affected areas
        - If the file has changed, revert will fail with context mismatch

    Args:
        file_path: Path to the file to revert
        patch: The same patch that was previously applied

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "file_path": str,
                "reverted": True,
                "changes": {
                    "lines_added": int,     # Opposite of original
                    "lines_removed": int,   # Opposite of original
                    "hunks_reverted": int
                },
                "message": str
            }

        Dict with the following structure on failure:
            {
                "success": False,
                "file_path": str,
                "reverted": False,
                "error": str,
                "error_type": str
            }

    Example:
        >>> # Apply patch
        >>> apply_result = apply_patch("config.py", patch)
        >>> # Later, revert it
        >>> revert_result = revert_patch("config.py", patch)
        >>> # File is now back to original state
    """
    path = Path(file_path)

    # Reverse the patch (swap + and -)
    reversed_patch = _reverse_patch(patch)

    # Apply the reversed patch
    result = apply_patch(str(path), reversed_patch)

    # Transform the result to use "reverted" terminology
    if result["success"]:
        return {
            "success": True,
            "file_path": str(path),
            "reverted": True,
            "changes": {
                # Report what the revert operation actually did
                "lines_added": result["changes"]["lines_added"],  # What revert added
                "lines_removed": result["changes"]["lines_removed"],  # What revert removed
                "hunks_reverted": result["changes"]["hunks_applied"],
            },
            "message": f"Successfully reverted patch from {path.name}",
        }
    else:
        # Transform error message
        error_msg = result.get("error", "Cannot revert patch")
        if "context" in error_msg.lower() or "mismatch" in error_msg.lower():
            error_msg = (
                f"Cannot revert: file has been modified since patch was applied. {error_msg}"
            )

        return {
            "success": False,
            "file_path": str(path),
            "reverted": False,
            "error": error_msg,
            "error_type": result.get("error_type", "context_mismatch"),
        }


def _reverse_patch(patch: str) -> str:
    """Reverse a patch by swapping additions and removals.

    This swaps:
        - Lines starting with "+" to start with "-"
        - Lines starting with "-" to start with "+"
        - Source and target line numbers in hunk headers
        - File headers (--- and +++) stay the same to target the same file

    Args:
        patch: Original patch

    Returns:
        Reversed patch
    """
    if not patch or not patch.strip():
        return patch

    lines = patch.split("\n")
    reversed_lines = []

    for line in lines:
        if line.startswith("--- ") or line.startswith("+++ "):
            # Keep file headers as-is (same file)
            reversed_lines.append(line)
        elif line.startswith("@@ "):
            # Reverse the hunk header (swap source and target ranges)
            reversed_lines.append(_reverse_hunk_header(line))
        elif line.startswith("+") and not line.startswith("+++"):
            # Change + to -
            reversed_lines.append("-" + line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            # Change - to +
            reversed_lines.append("+" + line[1:])
        else:
            # Context lines and other lines remain the same
            reversed_lines.append(line)

    return "\n".join(reversed_lines)


def _reverse_hunk_header(header: str) -> str:
    """Reverse a hunk header by swapping source and target ranges.

    Args:
        header: Original hunk header (e.g., "@@ -1,3 +1,4 @@")

    Returns:
        Reversed hunk header (e.g., "@@ -1,4 +1,3 @@")
    """
    # Extract the parts between @@
    try:
        parts = header.split("@@")
        if len(parts) < 3:
            return header

        ranges = parts[1].strip().split()
        if len(ranges) < 2:
            return header

        # Swap source (-) and target (+) ranges
        source_range = ranges[0]  # e.g., "-1,3"
        target_range = ranges[1]  # e.g., "+1,4"

        # Swap the prefixes
        new_source = "+" + source_range[1:]  # "-1,3" -> "+1,3"
        new_target = "-" + target_range[1:]  # "+1,4" -> "-1,4"

        # Reconstruct header
        return f"@@ {new_target} {new_source} @@"
    except Exception:
        # If parsing fails, return original
        return header
