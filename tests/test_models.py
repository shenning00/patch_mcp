"""Tests for data models.

This module tests all Pydantic models to ensure proper validation,
serialization, and deserialization.
"""

import pytest
from pydantic import ValidationError

from patch_mcp.models import (
    AffectedLineRange,
    ErrorType,
    FileInfo,
    PatchChanges,
    PatchSummary,
    ToolResult,
)


class TestErrorType:
    """Test ErrorType enum."""

    def test_all_error_types_exist(self):
        """Verify all 10 error types exist."""
        assert len(ErrorType) == 10

    def test_standard_error_types(self):
        """Test the 6 standard error types."""
        assert ErrorType.FILE_NOT_FOUND == "file_not_found"
        assert ErrorType.PERMISSION_DENIED == "permission_denied"
        assert ErrorType.INVALID_PATCH == "invalid_patch"
        assert ErrorType.CONTEXT_MISMATCH == "context_mismatch"
        assert ErrorType.ENCODING_ERROR == "encoding_error"
        assert ErrorType.IO_ERROR == "io_error"

    def test_security_error_types(self):
        """Test the 4 security error types."""
        assert ErrorType.SYMLINK_ERROR == "symlink_error"
        assert ErrorType.BINARY_FILE == "binary_file"
        assert ErrorType.DISK_SPACE_ERROR == "disk_space_error"
        assert ErrorType.RESOURCE_LIMIT == "resource_limit"

    def test_error_type_values_are_strings(self):
        """Verify all error type values are valid strings."""
        for error_type in ErrorType:
            assert isinstance(error_type.value, str)
            assert len(error_type.value) > 0


class TestPatchChanges:
    """Test PatchChanges model."""

    def test_valid_patch_changes(self):
        """Test creating valid PatchChanges."""
        changes = PatchChanges(lines_added=5, lines_removed=3, hunks_applied=2)
        assert changes.lines_added == 5
        assert changes.lines_removed == 3
        assert changes.hunks_applied == 2

    def test_zero_values_allowed(self):
        """Test that zero values are valid."""
        changes = PatchChanges(lines_added=0, lines_removed=0, hunks_applied=0)
        assert changes.lines_added == 0
        assert changes.lines_removed == 0
        assert changes.hunks_applied == 0

    def test_negative_lines_added_rejected(self):
        """Test that negative lines_added is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PatchChanges(lines_added=-1, lines_removed=0, hunks_applied=0)
        assert "lines_added" in str(exc_info.value)

    def test_negative_lines_removed_rejected(self):
        """Test that negative lines_removed is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PatchChanges(lines_added=0, lines_removed=-1, hunks_applied=0)
        assert "lines_removed" in str(exc_info.value)

    def test_negative_hunks_applied_rejected(self):
        """Test that negative hunks_applied is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PatchChanges(lines_added=0, lines_removed=0, hunks_applied=-1)
        assert "hunks_applied" in str(exc_info.value)

    def test_serialization(self):
        """Test model serialization to dict."""
        changes = PatchChanges(lines_added=5, lines_removed=3, hunks_applied=2)
        data = changes.model_dump()
        assert data == {"lines_added": 5, "lines_removed": 3, "hunks_applied": 2}

    def test_deserialization(self):
        """Test model deserialization from dict."""
        data = {"lines_added": 10, "lines_removed": 5, "hunks_applied": 3}
        changes = PatchChanges(**data)
        assert changes.lines_added == 10
        assert changes.lines_removed == 5
        assert changes.hunks_applied == 3


class TestAffectedLineRange:
    """Test AffectedLineRange model."""

    def test_valid_line_range(self):
        """Test creating valid AffectedLineRange."""
        line_range = AffectedLineRange(start=10, end=20)
        assert line_range.start == 10
        assert line_range.end == 20

    def test_start_at_line_one(self):
        """Test that line 1 is valid."""
        line_range = AffectedLineRange(start=1, end=1)
        assert line_range.start == 1
        assert line_range.end == 1

    def test_zero_start_rejected(self):
        """Test that start=0 is rejected (lines start at 1)."""
        with pytest.raises(ValidationError) as exc_info:
            AffectedLineRange(start=0, end=10)
        assert "start" in str(exc_info.value)

    def test_negative_start_rejected(self):
        """Test that negative start is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AffectedLineRange(start=-1, end=10)
        assert "start" in str(exc_info.value)

    def test_zero_end_rejected(self):
        """Test that end=0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AffectedLineRange(start=1, end=0)
        assert "end" in str(exc_info.value)

    def test_serialization(self):
        """Test model serialization to dict."""
        line_range = AffectedLineRange(start=15, end=42)
        data = line_range.model_dump()
        assert data == {"start": 15, "end": 42}


class TestFileInfo:
    """Test FileInfo model."""

    def test_valid_file_info(self):
        """Test creating valid FileInfo."""
        file_info = FileInfo(
            source="old.py", target="new.py", hunks=2, lines_added=10, lines_removed=5
        )
        assert file_info.source == "old.py"
        assert file_info.target == "new.py"
        assert file_info.hunks == 2
        assert file_info.lines_added == 10
        assert file_info.lines_removed == 5

    def test_zero_changes_allowed(self):
        """Test that zero changes are valid."""
        file_info = FileInfo(
            source="file.py", target="file.py", hunks=0, lines_added=0, lines_removed=0
        )
        assert file_info.hunks == 0
        assert file_info.lines_added == 0
        assert file_info.lines_removed == 0

    def test_negative_hunks_rejected(self):
        """Test that negative hunks is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(source="file.py", target="file.py", hunks=-1, lines_added=0, lines_removed=0)
        assert "hunks" in str(exc_info.value)

    def test_negative_lines_added_rejected(self):
        """Test that negative lines_added is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(source="file.py", target="file.py", hunks=0, lines_added=-1, lines_removed=0)
        assert "lines_added" in str(exc_info.value)

    def test_negative_lines_removed_rejected(self):
        """Test that negative lines_removed is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(source="file.py", target="file.py", hunks=0, lines_added=0, lines_removed=-1)
        assert "lines_removed" in str(exc_info.value)

    def test_serialization(self):
        """Test model serialization to dict."""
        file_info = FileInfo(
            source="config.py", target="config.py", hunks=1, lines_added=3, lines_removed=2
        )
        data = file_info.model_dump()
        assert data == {
            "source": "config.py",
            "target": "config.py",
            "hunks": 1,
            "lines_added": 3,
            "lines_removed": 2,
        }


class TestPatchSummary:
    """Test PatchSummary model."""

    def test_valid_patch_summary(self):
        """Test creating valid PatchSummary."""
        summary = PatchSummary(
            total_files=3, total_hunks=5, total_lines_added=20, total_lines_removed=10
        )
        assert summary.total_files == 3
        assert summary.total_hunks == 5
        assert summary.total_lines_added == 20
        assert summary.total_lines_removed == 10

    def test_zero_values_allowed(self):
        """Test that zero values are valid."""
        summary = PatchSummary(
            total_files=0, total_hunks=0, total_lines_added=0, total_lines_removed=0
        )
        assert summary.total_files == 0

    def test_negative_total_files_rejected(self):
        """Test that negative total_files is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PatchSummary(total_files=-1, total_hunks=0, total_lines_added=0, total_lines_removed=0)
        assert "total_files" in str(exc_info.value)

    def test_serialization(self):
        """Test model serialization to dict."""
        summary = PatchSummary(
            total_files=2, total_hunks=4, total_lines_added=15, total_lines_removed=8
        )
        data = summary.model_dump()
        assert data == {
            "total_files": 2,
            "total_hunks": 4,
            "total_lines_added": 15,
            "total_lines_removed": 8,
        }


class TestToolResult:
    """Test ToolResult model."""

    def test_success_result(self):
        """Test creating successful ToolResult."""
        result = ToolResult(success=True, message="Operation completed")
        assert result.success is True
        assert result.message == "Operation completed"
        assert result.error is None
        assert result.error_type is None

    def test_failure_result_with_error_type(self):
        """Test creating failed ToolResult with error type."""
        result = ToolResult(
            success=False,
            message="Operation failed",
            error="File not found: test.py",
            error_type=ErrorType.FILE_NOT_FOUND,
        )
        assert result.success is False
        assert result.message == "Operation failed"
        assert result.error == "File not found: test.py"
        assert result.error_type == ErrorType.FILE_NOT_FOUND

    def test_all_error_types_compatible(self):
        """Test that all error types work with ToolResult."""
        for error_type in ErrorType:
            result = ToolResult(
                success=False, message="Test", error="Test error", error_type=error_type
            )
            assert result.error_type == error_type

    def test_serialization_success(self):
        """Test serialization of successful result."""
        result = ToolResult(success=True, message="Done")
        data = result.model_dump()
        assert data == {"success": True, "message": "Done", "error": None, "error_type": None}

    def test_serialization_failure(self):
        """Test serialization of failed result."""
        result = ToolResult(
            success=False,
            message="Failed",
            error="Something went wrong",
            error_type=ErrorType.IO_ERROR,
        )
        data = result.model_dump()
        assert data == {
            "success": False,
            "message": "Failed",
            "error": "Something went wrong",
            "error_type": "io_error",
        }

    def test_deserialization(self):
        """Test deserialization from dict."""
        data = {
            "success": False,
            "message": "Failed",
            "error": "Context mismatch",
            "error_type": "context_mismatch",
        }
        result = ToolResult(**data)
        assert result.success is False
        assert result.error_type == ErrorType.CONTEXT_MISMATCH
