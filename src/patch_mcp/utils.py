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


def sanitize_error_message(message: str, max_content_length: int = 50) -> str:
    """Sanitize error messages to prevent information disclosure.

    Removes or truncates potentially sensitive content from error messages
    to mitigate prompt injection and information disclosure risks.

    Security improvements:
        1. Truncates long quoted strings that might contain file content
        2. Removes filesystem paths while preserving general location info
        3. Limits length of displayed content snippets

    Args:
        message: The error message to sanitize
        max_content_length: Maximum length for content snippets (default: 50)

    Returns:
        Sanitized error message safe for display to LLM

    Example:
        >>> msg = "Context mismatch: expected 'secret_api_key=abc123...' but found 'secret_api_key=xyz789...'"
        >>> sanitize_error_message(msg)
        "Context mismatch: expected '[CONTENT]' but found '[CONTENT]'"
    """
    # Pattern 1: Replace long quoted strings with [CONTENT]
    import re
    from re import Match

    # Find quoted strings longer than max_content_length
    def replace_long_quotes(match: Match[str]) -> str:
        content = match.group(1)
        if len(content) > max_content_length:
            return "'[CONTENT]'"
        return match.group(0)

    sanitized = re.sub(r"'([^']*)'", replace_long_quotes, message)

    # Pattern 2: Remove absolute paths but keep filename
    # Replace /full/path/to/file.txt with file.txt
    sanitized = re.sub(r"/(?:[^/\s]+/)+([^/\s]+)", r"\1", sanitized)
    # Also handle Windows paths
    sanitized = re.sub(r"[A-Za-z]:\\(?:[^\\:\s]+\\)+([^\\:\s]+)", r"\1", sanitized)

    return sanitized


def detect_sensitive_content(content: str) -> Dict[str, Any]:
    """Detect potentially sensitive content in file or patch content.

    Scans content for patterns that may indicate secrets, credentials, or
    other sensitive data that should not be exposed to LLMs.

    Detected patterns:
        1. Private keys (RSA, SSH, PGP, etc.)
        2. API keys and tokens (various formats)
        3. Passwords in configuration
        4. AWS credentials
        5. JWT tokens
        6. Database connection strings
        7. Generic secrets patterns

    Args:
        content: The content to scan for sensitive data

    Returns:
        Dict with:
            - has_sensitive: bool - True if sensitive content detected
            - findings: List[str] - List of detected sensitive patterns
            - recommendation: str - Security guidance

    Example:
        >>> result = detect_sensitive_content(patch_content)
        >>> if result["has_sensitive"]:
        ...     print(f"WARNING: {result['recommendation']}")
    """
    import re

    findings = []

    # Pattern 1: Private keys
    if re.search(r"-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----", content, re.IGNORECASE):
        findings.append("Private cryptographic key detected")

    # Pattern 2: API keys and tokens (common formats)
    api_key_patterns = [
        (r"api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", "API key"),
        (r"token\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", "Token"),
        (r"secret\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", "Secret"),
        (r"password\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?", "Password"),
    ]

    for pattern, name in api_key_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            findings.append(f"{name} pattern detected")

    # Pattern 3: AWS credentials
    if re.search(r"AKIA[0-9A-Z]{16}", content):
        findings.append("AWS access key ID detected")

    # Pattern 4: JWT tokens
    if re.search(r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", content):
        findings.append("JWT token detected")

    # Pattern 5: Database connection strings
    db_patterns = [
        r"(postgres|mysql|mongodb)://[^\s]+:[^\s]+@",
        r"Server=.*;Database=.*;User.*=.*;Password=.*",
    ]

    for pattern in db_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            findings.append("Database connection string detected")
            break

    # Prepare result
    has_sensitive = len(findings) > 0

    if has_sensitive:
        recommendation = (
            "SECURITY WARNING: Sensitive content detected in patch. "
            "Review carefully before sharing. Consider using environment "
            "variables or secret management instead of hardcoded credentials."
        )
    else:
        recommendation = "No obvious sensitive patterns detected"

    return {
        "has_sensitive": has_sensitive,
        "findings": findings,
        "recommendation": recommendation,
    }
