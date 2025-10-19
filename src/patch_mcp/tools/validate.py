"""Validate patch tool - check if a patch can be applied to a file.

This module implements the validate_patch tool which validates whether a patch
can be successfully applied to a target file without actually modifying it.

CRITICAL: Return value semantics
    - success=True when patch CAN be applied
    - success=False when patch CANNOT be applied (even if patch format is valid)
    - Always includes error_type when success=False
"""

import difflib
from pathlib import Path
from typing import Any, Dict

from ..utils import sanitize_error_message, validate_file_safety


def validate_patch(file_path: str, patch: str) -> Dict[str, Any]:
    """Validate a patch can be applied to a file (read-only operation).

    Checks whether a patch can be cleanly applied to a file by validating:
        1. File safety (exists, not symlink, not binary)
        2. Patch format validity
        3. Context lines match file content exactly

    This is a READ-ONLY operation - the file is never modified.

    Return Value Semantics (CRITICAL):
        - success=True: Patch CAN be applied cleanly
        - success=False + can_apply=False: Patch CANNOT be applied (context mismatch)
        - success=False + valid=False: Patch format is invalid

    Args:
        file_path: Path to the file to validate against
        patch: Unified diff patch content to validate

    Returns:
        Dict when patch CAN be applied:
            {
                "success": True,
                "file_path": str,
                "valid": True,
                "can_apply": True,
                "preview": {
                    "lines_to_add": int,
                    "lines_to_remove": int,
                    "hunks": int,
                    "affected_line_range": {
                        "start": int,
                        "end": int
                    }
                },
                "message": "Patch is valid and can be applied cleanly"
            }

        Dict when patch CANNOT be applied (context mismatch):
            {
                "success": False,  # NOT True!
                "file_path": str,
                "valid": True,
                "can_apply": False,
                "preview": {...},
                "reason": str,  # Why it can't be applied
                "error_type": "context_mismatch",
                "message": "Patch is valid but cannot be applied to this file"
            }

        Dict when patch format is invalid:
            {
                "success": False,
                "file_path": str,
                "valid": False,
                "error": str,
                "error_type": "invalid_patch"
            }

    Example:
        >>> result = validate_patch("config.py", patch)
        >>> if result["success"]:
        ...     print(f"Can apply! Will change {result['preview']['lines_to_add']} lines")
        ... elif not result.get("can_apply", False):
        ...     print(f"Cannot apply: {result['reason']}")
    """
    path = Path(file_path)

    # Security checks (read-only, no write or space checks needed)
    safety_error = validate_file_safety(path, check_write=False, check_space=False)
    if safety_error:
        return {
            "success": False,
            "file_path": str(path),
            **safety_error,
        }

    # Read file content
    try:
        with open(path, "r", encoding="utf-8") as f:
            file_lines = f.readlines()
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "file_path": str(path),
            "error": f"Cannot decode file as UTF-8: {str(e)}",
            "error_type": "encoding_error",
        }
    except OSError as e:
        return {
            "success": False,
            "file_path": str(path),
            "error": f"Cannot read file: {str(e)}",
            "error_type": "io_error",
        }

    # Parse and validate patch format
    parse_result = _parse_patch(patch)
    if not parse_result["valid"]:
        return {
            "success": False,
            "file_path": str(path),
            "valid": False,
            "error": parse_result["error"],
            "error_type": "invalid_patch",
        }

    hunks = parse_result["hunks"]
    lines_to_add = parse_result["lines_to_add"]
    lines_to_remove = parse_result["lines_to_remove"]

    # Check if patch can be applied (validate context)
    validation = _can_apply_patch(file_lines, hunks)

    # Build preview
    if hunks:
        min_line = min(h["target_start"] for h in hunks)
        max_line = max(h["target_start"] + h["target_count"] - 1 for h in hunks)
        affected_range = {"start": min_line, "end": max(max_line, min_line)}
    else:
        affected_range = {"start": 1, "end": 1}

    preview = {
        "lines_to_add": lines_to_add,
        "lines_to_remove": lines_to_remove,
        "hunks": len(hunks),
        "affected_line_range": affected_range,
    }

    if validation["can_apply"]:
        # SUCCESS: Patch can be applied
        return {
            "success": True,
            "file_path": str(path),
            "valid": True,
            "can_apply": True,
            "preview": preview,
            "message": "Patch is valid and can be applied cleanly",
        }
    else:
        # FAILURE: Patch cannot be applied (context mismatch)
        # CRITICAL: success=False when can_apply=False!
        return {
            "success": False,
            "file_path": str(path),
            "valid": True,
            "can_apply": False,
            "preview": preview,
            "reason": validation["reason"],
            "error_type": "context_mismatch",
            "message": "Patch is valid but cannot be applied to this file",
        }


def _parse_patch(patch: str) -> Dict[str, Any]:
    """Parse patch format and extract hunks.

    Args:
        patch: Patch content to parse

    Returns:
        Dict with:
            - valid: bool
            - hunks: List of hunk info (if valid)
            - lines_to_add: int
            - lines_to_remove: int
            - error: str (if invalid)
    """
    if not patch or not patch.strip():
        return {
            "valid": True,
            "hunks": [],
            "lines_to_add": 0,
            "lines_to_remove": 0,
        }

    lines = patch.split("\n")
    hunks: list[Dict[str, Any]] = []
    current_hunk: Dict[str, Any] | None = None
    lines_to_add = 0
    lines_to_remove = 0
    found_header = False

    for i, line in enumerate(lines):
        # Check for file headers
        if line.startswith("---"):
            found_header = True
        elif line.startswith("+++"):
            if not found_header:
                return {
                    "valid": False,
                    "error": f"Invalid patch format: +++ before --- at line {i+1}",
                }
        elif line.startswith("@@"):
            # Parse hunk header
            # Format: @@ -source_start,source_count +target_start,target_count @@
            try:
                parts = line.split("@@")[1].strip().split()
                if len(parts) < 2:
                    return {
                        "valid": False,
                        "error": f"Invalid hunk header at line {i+1}",
                    }

                # Parse source range (-start,count)
                source_part = parts[0]
                if not source_part.startswith("-"):
                    return {
                        "valid": False,
                        "error": f"Invalid source range at line {i+1}",
                    }
                source_parts = source_part[1:].split(",")
                source_start = int(source_parts[0])
                source_count = int(source_parts[1]) if len(source_parts) > 1 else 1

                # Parse target range (+start,count)
                target_part = parts[1]
                if not target_part.startswith("+"):
                    return {
                        "valid": False,
                        "error": f"Invalid target range at line {i+1}",
                    }
                target_parts = target_part[1:].split(",")
                target_start = int(target_parts[0])
                target_count = int(target_parts[1]) if len(target_parts) > 1 else 1

                current_hunk = {
                    "source_start": source_start,
                    "source_count": source_count,
                    "target_start": target_start,
                    "target_count": target_count,
                    "context_lines": [],
                    "added_lines": [],
                    "removed_lines": [],
                }
                hunks.append(current_hunk)
            except (ValueError, IndexError) as e:
                return {
                    "valid": False,
                    "error": f"Cannot parse hunk header at line {i+1}: {str(e)}",
                }
        elif current_hunk is not None:
            # Inside a hunk - collect lines
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk["added_lines"].append(line[1:])
                lines_to_add += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk["removed_lines"].append(line[1:])
                lines_to_remove += 1
            elif line.startswith(" "):
                current_hunk["context_lines"].append(line[1:])
            elif line.startswith("\\"):
                # "\ No newline at end of file" - skip
                pass

    if not found_header and hunks:
        return {
            "valid": False,
            "error": "Invalid patch format: missing --- header",
        }

    return {
        "valid": True,
        "hunks": hunks,
        "lines_to_add": lines_to_add,
        "lines_to_remove": lines_to_remove,
    }


def _can_apply_patch(file_lines: list[str], hunks: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Check if patch hunks can be applied to file.

    Args:
        file_lines: Lines from the target file
        hunks: Parsed hunk information

    Returns:
        Dict with:
            - can_apply: bool
            - reason: str (if cannot apply)
    """
    if not hunks:
        # Empty patch - can always be applied
        return {"can_apply": True}

    for hunk in hunks:
        # Get the section of the file this hunk affects
        start_line = hunk["source_start"] - 1  # Convert to 0-indexed
        end_line = start_line + hunk["source_count"]

        if start_line < 0 or end_line > len(file_lines):
            reason = (
                f"Hunk refers to lines {hunk['source_start']}-{end_line} "
                f"but file only has {len(file_lines)} lines"
            )
            return {
                "can_apply": False,
                "reason": reason,
            }

        # Extract the actual lines from the file
        actual_lines = file_lines[start_line:end_line]
        actual_content_clean = [line.rstrip("\n") for line in actual_lines]

        # Check if removed lines exist in the actual content
        for removed_line in hunk["removed_lines"]:
            clean_removed = removed_line.rstrip("\n")
            if clean_removed not in actual_content_clean:
                # Find closest match for better error message
                closest = difflib.get_close_matches(
                    clean_removed, actual_content_clean, n=1, cutoff=0.6
                )
                if closest:
                    reason = (
                        f"Context mismatch at line {hunk['source_start']}: "
                        f"expected '{clean_removed}' but found '{closest[0]}'"
                    )
                    # Sanitize to prevent content leakage
                    reason = sanitize_error_message(reason)
                    return {
                        "can_apply": False,
                        "reason": reason,
                    }
                else:
                    reason = (
                        f"Context mismatch: line '{clean_removed}' "
                        "not found in file at expected position"
                    )
                    # Sanitize to prevent content leakage
                    reason = sanitize_error_message(reason)
                    return {
                        "can_apply": False,
                        "reason": reason,
                    }

    return {"can_apply": True}
