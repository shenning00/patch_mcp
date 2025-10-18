"""Inspect patch tool - analyze unified diff patches without files.

This module implements the inspect_patch tool which parses and analyzes patch
content to extract information about affected files, hunks, and changes.

CRITICAL: Supports multi-file patches (returns files array, not file object).
"""

import re
from typing import Any, Dict, List

# Regex patterns for parsing unified diff format
HEADER_PATTERN = re.compile(r"^---\s+(.+?)(?:\t|\s|$)", re.MULTILINE)
HUNK_PATTERN = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", re.MULTILINE)


def inspect_patch(patch: str) -> Dict[str, Any]:
    """Analyze patch content without requiring any files.

    Parses a unified diff format patch and extracts information about all
    affected files, hunks, and line changes. Supports multi-file patches.

    This is different from validate_patch:
        - inspect_patch: Analyzes patch structure only, no file needed
        - validate_patch: Checks if patch can be applied to a specific file

    Args:
        patch: Unified diff patch content

    Returns:
        Dict with the following structure on success:
            {
                "success": True,
                "valid": True,
                "files": [  # Array of affected files
                    {
                        "source": str,
                        "target": str,
                        "hunks": int,
                        "lines_added": int,
                        "lines_removed": int
                    },
                    ...
                ],
                "summary": {
                    "total_files": int,
                    "total_hunks": int,
                    "total_lines_added": int,
                    "total_lines_removed": int
                },
                "message": str
            }

        Dict with the following structure on invalid patch:
            {
                "success": False,
                "valid": False,
                "error": str,
                "error_type": "invalid_patch",
                "message": str
            }

    Example:
        >>> result = inspect_patch(patch_content)
        >>> if result["success"]:
        ...     print(f"Affects {result['summary']['total_files']} files")
        ...     for file_info in result["files"]:
        ...         print(f"  {file_info['target']}: +{file_info['lines_added']}")
    """
    if not patch or not patch.strip():
        # Empty patch is technically valid, just has no changes
        return {
            "success": True,
            "valid": True,
            "files": [],
            "summary": {
                "total_files": 0,
                "total_hunks": 0,
                "total_lines_added": 0,
                "total_lines_removed": 0,
            },
            "message": "Empty patch - no changes",
        }

    # Parse the patch into file sections
    file_sections = _split_into_file_sections(patch)

    if not file_sections:
        return {
            "success": False,
            "valid": False,
            "error": "Invalid patch format: missing --- header at line 1",
            "error_type": "invalid_patch",
            "message": "Patch is not valid",
        }

    # Process each file section
    files_info: List[Dict[str, Any]] = []
    total_hunks = 0
    total_lines_added = 0
    total_lines_removed = 0

    for section in file_sections:
        file_info = _parse_file_section(section)
        if file_info is None:
            return {
                "success": False,
                "valid": False,
                "error": "Invalid patch format: malformed hunk or header",
                "error_type": "invalid_patch",
                "message": "Patch is not valid",
            }

        files_info.append(file_info)
        total_hunks += file_info["hunks"]
        total_lines_added += file_info["lines_added"]
        total_lines_removed += file_info["lines_removed"]

    return {
        "success": True,
        "valid": True,
        "files": files_info,
        "summary": {
            "total_files": len(files_info),
            "total_hunks": total_hunks,
            "total_lines_added": total_lines_added,
            "total_lines_removed": total_lines_removed,
        },
        "message": "Patch analysis complete",
    }


def _split_into_file_sections(patch: str) -> List[str]:
    """Split a multi-file patch into individual file sections.

    Args:
        patch: Full patch content

    Returns:
        List of patch sections, one per file
    """
    sections = []
    current_section = []
    lines = patch.split("\n")

    for line in lines:
        # New file section starts with "---"
        if line.startswith("---") and current_section:
            # Save previous section
            sections.append("\n".join(current_section))
            current_section = [line]
        else:
            current_section.append(line)

    # Save last section
    if current_section:
        sections.append("\n".join(current_section))

    return sections


def _parse_file_section(section: str) -> Dict[str, Any] | None:
    """Parse a single file's patch section.

    Args:
        section: Patch content for one file

    Returns:
        Dict with file info, or None if invalid
    """
    lines = section.split("\n")

    # Find source and target file names
    source_file = None
    target_file = None

    for i, line in enumerate(lines):
        if line.startswith("---"):
            # Extract source filename (after "---")
            parts = line[3:].strip().split()
            if parts:
                source_file = parts[0]
        elif line.startswith("+++"):
            # Extract target filename (after "+++")
            parts = line[3:].strip().split()
            if parts:
                target_file = parts[0]
            break

    if not source_file or not target_file:
        return None

    # Count hunks and changes
    hunks = 0
    lines_added = 0
    lines_removed = 0
    in_hunk = False

    for line in lines:
        if line.startswith("@@"):
            hunks += 1
            in_hunk = True
        elif in_hunk:
            if line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_removed += 1
            elif line.startswith("\\"):
                # "\ No newline at end of file" - skip
                pass

    return {
        "source": source_file,
        "target": target_file,
        "hunks": hunks,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
    }
