"""Data models for File Patch MCP Server.

This module defines Pydantic models used throughout the patch MCP server for
data validation, serialization, and type safety.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ErrorType(str, Enum):
    """Standard error types for patch operations.

    Standard Errors (6):
        FILE_NOT_FOUND: File doesn't exist
        PERMISSION_DENIED: Cannot read/write file
        INVALID_PATCH: Patch format is malformed
        CONTEXT_MISMATCH: Patch context doesn't match file content
        ENCODING_ERROR: File encoding issue
        IO_ERROR: General I/O error

    Security Errors (4):
        SYMLINK_ERROR: Target is a symlink (security policy)
        BINARY_FILE: Target is a binary file (not supported)
        DISK_SPACE_ERROR: Insufficient disk space
        RESOURCE_LIMIT: File too large or operation timed out
    """

    # Standard errors
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_PATCH = "invalid_patch"
    CONTEXT_MISMATCH = "context_mismatch"
    ENCODING_ERROR = "encoding_error"
    IO_ERROR = "io_error"

    # Security errors
    SYMLINK_ERROR = "symlink_error"
    BINARY_FILE = "binary_file"
    DISK_SPACE_ERROR = "disk_space_error"
    RESOURCE_LIMIT = "resource_limit"


class PatchChanges(BaseModel):
    """Statistics about patch changes.

    Tracks the number of lines added, removed, and hunks applied during
    a patch operation.

    Attributes:
        lines_added: Number of lines added (must be >= 0)
        lines_removed: Number of lines removed (must be >= 0)
        hunks_applied: Number of hunks applied (must be >= 0)
    """

    lines_added: int = Field(..., ge=0, description="Number of lines added")
    lines_removed: int = Field(..., ge=0, description="Number of lines removed")
    hunks_applied: int = Field(..., ge=0, description="Number of hunks applied")


class AffectedLineRange(BaseModel):
    """Line range affected by a patch.

    Represents the starting and ending line numbers affected by a patch
    operation.

    Attributes:
        start: Starting line number (must be >= 1)
        end: Ending line number (must be >= 1)
    """

    start: int = Field(..., ge=1, description="Starting line number")
    end: int = Field(..., ge=1, description="Ending line number")
