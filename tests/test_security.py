"""Tests for security utilities.

This module provides comprehensive tests for all security functions.
Target: 100% code coverage (security-critical component).
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from patch_mcp.utils import (
    BINARY_CHECK_BYTES,
    MAX_FILE_SIZE,
    MIN_FREE_SPACE,
    NON_TEXT_THRESHOLD,
    atomic_file_replace,
    check_path_traversal,
    is_binary_file,
    validate_file_safety,
)


class TestIsBinaryFile:
    """Test is_binary_file function."""

    def test_text_file_is_not_binary(self, tmp_path):
        """Test that text files are correctly identified."""
        text_file = tmp_path / "text.txt"
        text_file.write_text("This is a text file\nWith multiple lines\n")
        assert is_binary_file(text_file) is False

    def test_empty_file_is_not_binary(self, tmp_path):
        """Test that empty files are treated as text."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        assert is_binary_file(empty_file) is False

    def test_null_byte_indicates_binary(self, tmp_path):
        """Test that files with null bytes are detected as binary."""
        binary_file = tmp_path / "binary.dat"
        binary_file.write_bytes(b"Some text\x00more text")
        assert is_binary_file(binary_file) is True

    def test_high_non_text_ratio_indicates_binary(self, tmp_path):
        """Test that files with >30% non-text chars are binary."""
        binary_file = tmp_path / "binary.dat"
        # Create content with >30% non-text characters
        content = b"\xff\xfe" * 100  # High-byte characters
        binary_file.write_bytes(content)
        assert is_binary_file(binary_file) is True

    def test_python_source_is_not_binary(self, tmp_path):
        """Test that Python source files are not detected as binary."""
        python_file = tmp_path / "test.py"
        python_file.write_text('def hello():\n    print("Hello, world!")\n')
        assert is_binary_file(python_file) is False

    def test_whitespace_heavy_file_is_not_binary(self, tmp_path):
        """Test that files with lots of whitespace are not binary."""
        whitespace_file = tmp_path / "whitespace.txt"
        whitespace_file.write_text("\n\n\n    \t\t\n\nSome text\n\n\n")
        assert is_binary_file(whitespace_file) is False

    def test_unicode_text_is_not_binary(self, tmp_path):
        """Test that UTF-8 encoded text is not detected as binary."""
        unicode_file = tmp_path / "unicode.txt"
        unicode_file.write_text("Hello 世界 🌍\n", encoding="utf-8")
        assert is_binary_file(unicode_file) is False

    def test_custom_check_bytes(self, tmp_path):
        """Test custom check_bytes parameter."""
        text_file = tmp_path / "text.txt"
        text_file.write_text("Short text")
        assert is_binary_file(text_file, check_bytes=5) is False

    def test_unreadable_file_is_binary(self, tmp_path):
        """Test that unreadable files are treated as binary for safety."""
        unreadable_file = tmp_path / "unreadable.txt"
        unreadable_file.write_text("test")
        unreadable_file.chmod(0o000)
        try:
            # Should return True because we can't read it
            result = is_binary_file(unreadable_file)
            assert result is True
        finally:
            # Clean up: restore permissions
            unreadable_file.chmod(0o644)

    def test_image_file_is_binary(self, tmp_path):
        """Test that a simple image-like file is detected as binary."""
        image_file = tmp_path / "image.png"
        # PNG header signature
        png_header = b"\x89PNG\r\n\x1a\n"
        image_file.write_bytes(png_header + b"\x00" * 100)
        assert is_binary_file(image_file) is True


class TestValidateFileSafety:
    """Test validate_file_safety function."""

    def test_valid_text_file(self, tmp_path):
        """Test that valid text file passes all checks."""
        text_file = tmp_path / "valid.txt"
        text_file.write_text("This is a valid text file\n")
        error = validate_file_safety(text_file)
        assert error is None

    def test_file_not_found(self, tmp_path):
        """Test that non-existent file returns file_not_found error."""
        missing_file = tmp_path / "missing.txt"
        error = validate_file_safety(missing_file)
        assert error is not None
        assert error["error_type"] == "file_not_found"
        assert "not found" in error["error"].lower()

    def test_reject_symlink(self, tmp_path):
        """Test that symlinks are rejected with symlink_error."""
        target = tmp_path / "target.txt"
        target.write_text("target content")
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        error = validate_file_safety(link)
        assert error is not None
        assert error["error_type"] == "symlink_error"
        assert "symlink" in error["error"].lower()

    def test_reject_binary_file(self, tmp_path):
        """Test that binary files are rejected with binary_file error."""
        binary_file = tmp_path / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02\x03" * 100)

        error = validate_file_safety(binary_file)
        assert error is not None
        assert error["error_type"] == "binary_file"
        assert "binary" in error["error"].lower()

    def test_file_size_limit(self, tmp_path):
        """Test that files over 10MB are rejected with resource_limit error."""
        large_file = tmp_path / "large.txt"
        # Create file larger than MAX_FILE_SIZE (10MB)
        large_file.write_bytes(b"x" * (MAX_FILE_SIZE + 1))

        error = validate_file_safety(large_file)
        assert error is not None
        assert error["error_type"] == "resource_limit"
        assert "too large" in error["error"].lower()

    def test_file_at_size_limit(self, tmp_path):
        """Test that files exactly at 10MB limit are accepted."""
        limit_file = tmp_path / "limit.txt"
        limit_file.write_bytes(b"x" * MAX_FILE_SIZE)

        error = validate_file_safety(limit_file)
        assert error is None

    def test_write_permission_check_writable(self, tmp_path):
        """Test write permission check on writable file."""
        writable_file = tmp_path / "writable.txt"
        writable_file.write_text("content")

        error = validate_file_safety(writable_file, check_write=True)
        assert error is None

    def test_write_permission_check_readonly(self, tmp_path):
        """Test write permission check on read-only file."""
        readonly_file = tmp_path / "readonly.txt"
        readonly_file.write_text("content")
        readonly_file.chmod(0o444)  # Read-only

        try:
            error = validate_file_safety(readonly_file, check_write=True)
            assert error is not None
            assert error["error_type"] == "permission_denied"
            assert "not writable" in error["error"].lower()
        finally:
            # Clean up: restore permissions
            readonly_file.chmod(0o644)

    def test_disk_space_check_sufficient(self, tmp_path):
        """Test disk space check with sufficient space."""
        small_file = tmp_path / "small.txt"
        small_file.write_text("small content")

        # This should pass on most systems
        error = validate_file_safety(small_file, check_space=True)
        # Note: This might fail if disk is actually full, but that's expected
        if error:
            assert error["error_type"] == "disk_space_error"

    def test_disk_space_minimum_check(self, tmp_path, monkeypatch):
        """Test that minimum disk space requirement is enforced."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Mock disk_usage to return insufficient space
        class MockUsage:
            def __init__(self):
                self.free = MIN_FREE_SPACE - 1  # Just below minimum

        def mock_disk_usage(path):
            return MockUsage()

        monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

        error = validate_file_safety(test_file, check_space=True)
        assert error is not None
        assert error["error_type"] == "disk_space_error"
        assert "insufficient disk space" in error["error"].lower()

    def test_disk_space_safety_margin_check(self, tmp_path, monkeypatch):
        """Test that 110% safety margin is enforced."""
        test_file = tmp_path / "test.txt"
        # Create a file small enough to pass size check but large enough for margin test
        # Use 1MB file (well under 10MB limit)
        test_file.write_bytes(b"x" * 1_000_000)

        # Mock disk_usage to return space above minimum but below safety margin
        file_size = test_file.stat().st_size
        safety_margin = int(file_size * 1.1)

        # We need to ensure the mocked free space is:
        # 1. Above MIN_FREE_SPACE (100MB)
        # 2. Below safety_margin (1.1MB which is way less than MIN_FREE_SPACE)
        # Since MIN_FREE_SPACE >> safety_margin, we set free space to just below MIN_FREE_SPACE

        class MockUsage:
            def __init__(self):
                # Set free space just above minimum but we'll fail on second check
                # Actually, since safety_margin is so small, let's use a different approach
                # Set to MIN_FREE_SPACE + 1MB, which is above MIN but below what we need
                # if the file was larger
                # Better: Set to be between MIN_FREE_SPACE and a larger safety margin
                # We need a scenario where: MIN_FREE_SPACE < free < safety_margin
                # But safety_margin for 1MB file is only 1.1MB, less than MIN_FREE_SPACE
                # Let's instead use a larger file...
                # Actually, let's make the file size calculation work differently
                # Use MAX_FILE_SIZE - 1MB to get close to limit but not exceed
                self.free = MIN_FREE_SPACE + 1  # Above minimum

        def mock_disk_usage(path):
            return MockUsage()

        # Re-create with a much larger file that's still under MAX_FILE_SIZE
        test_file.write_bytes(b"x" * (MAX_FILE_SIZE - 1024 * 1024))  # 9MB (under 10MB limit)

        file_size = test_file.stat().st_size
        safety_margin = int(file_size * 1.1)  # About 9.9MB

        # Now safety_margin is large enough. Set free space between MIN and safety_margin
        # MIN_FREE_SPACE = 100MB, safety_margin = ~9.9MB
        # Wait, that still doesn't work because MIN > safety_margin
        #
        # The issue is that MIN_FREE_SPACE (100MB) will always be checked first
        # and if we have >= 100MB, the safety margin check won't fail because
        # safety margin for files under 10MB is < 100MB
        #
        # We need to make MIN_FREE_SPACE the smaller constraint by making file bigger
        # But we can't exceed MAX_FILE_SIZE...
        #
        # Let's rethink: we want free < safety_margin but free >= MIN_FREE_SPACE
        # This means: MIN_FREE_SPACE <= free < file_size * 1.1
        # So: MIN_FREE_SPACE < file_size * 1.1
        # So: file_size > MIN_FREE_SPACE / 1.1 = 100MB / 1.1 = 90.9MB
        # But MAX_FILE_SIZE is only 10MB!
        #
        # This is impossible with current constants. Let me mock MIN_FREE_SPACE too

        # Better approach: mock the constants themselves for this test
        original_min = MIN_FREE_SPACE

        # Temporarily make MIN_FREE_SPACE smaller
        import patch_mcp.utils

        monkeypatch.setattr(patch_mcp.utils, "MIN_FREE_SPACE", 1024 * 1024)  # 1MB

        # Now with 9MB file, safety margin is 9.9MB
        # Set free space to 5MB (above 1MB min, below 9.9MB safety)
        class MockUsage:
            def __init__(self):
                self.free = 5 * 1024 * 1024  # 5MB

        monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

        error = validate_file_safety(test_file, check_space=True)
        assert error is not None
        assert error["error_type"] == "disk_space_error"
        assert "needed" in error["error"].lower()

    def test_directory_not_regular_file(self, tmp_path):
        """Test that directories are rejected."""
        directory = tmp_path / "subdir"
        directory.mkdir()

        error = validate_file_safety(directory)
        assert error is not None
        assert error["error_type"] == "io_error"
        assert "not a regular file" in error["error"].lower()

    def test_all_checks_combined(self, tmp_path):
        """Test that all checks can be enabled together."""
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("Valid content for testing\n")

        error = validate_file_safety(valid_file, check_write=True, check_space=True)
        # Should pass if file is valid and disk has space
        if error:
            # Only acceptable error is disk space if disk is actually full
            assert error["error_type"] == "disk_space_error"


class TestCheckPathTraversal:
    """Test check_path_traversal function."""

    def test_safe_path_within_base(self, tmp_path):
        """Test that paths within base directory are safe."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        safe_path = base_dir / "file.txt"
        error = check_path_traversal(str(safe_path), str(base_dir))
        assert error is None

    def test_safe_nested_path(self, tmp_path):
        """Test that nested paths within base are safe."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        nested_path = base_dir / "subdir" / "file.txt"
        error = check_path_traversal(str(nested_path), str(base_dir))
        assert error is None

    def test_reject_parent_traversal(self, tmp_path):
        """Test that ../ traversal is rejected."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        traversal_path = base_dir / ".." / "outside.txt"
        error = check_path_traversal(str(traversal_path), str(base_dir))
        assert error is not None
        assert error["error_type"] == "permission_denied"
        assert "escape" in error["error"].lower()

    def test_reject_absolute_outside_path(self, tmp_path):
        """Test that absolute paths outside base are rejected."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        outside_path = tmp_path / "outside.txt"
        error = check_path_traversal(str(outside_path), str(base_dir))
        assert error is not None
        assert error["error_type"] == "permission_denied"

    def test_relative_path_within_base(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        # Relative path that stays within base
        relative_path = "subdir/file.txt"
        # Note: This test requires the path to be relative to base_dir
        full_path = base_dir / relative_path
        error = check_path_traversal(str(full_path), str(base_dir))
        assert error is None

    def test_same_directory(self, tmp_path):
        """Test that base directory itself is safe."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        error = check_path_traversal(str(base_dir), str(base_dir))
        assert error is None

    def test_complex_traversal_attempt(self, tmp_path):
        """Test complex traversal patterns."""
        base_dir = tmp_path / "project"
        base_dir.mkdir()

        # Try to escape using multiple ../
        traversal_path = str(base_dir / "a" / ".." / ".." / ".." / "etc" / "passwd")
        error = check_path_traversal(traversal_path, str(base_dir))
        assert error is not None
        assert error["error_type"] == "permission_denied"


class TestAtomicFileReplace:
    """Test atomic_file_replace function."""

    def test_atomic_replace_success(self, tmp_path):
        """Test successful atomic file replacement."""
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"

        source.write_text("new content")
        target.write_text("old content")

        atomic_file_replace(source, target)

        assert not source.exists()
        assert target.exists()
        assert target.read_text() == "new content"

    def test_atomic_replace_creates_target(self, tmp_path):
        """Test atomic replace when target doesn't exist."""
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"

        source.write_text("content")

        atomic_file_replace(source, target)

        assert not source.exists()
        assert target.exists()
        assert target.read_text() == "content"

    def test_atomic_replace_preserves_content(self, tmp_path):
        """Test that content is preserved during replacement."""
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"

        test_content = "This is important content\nWith multiple lines\n"
        source.write_text(test_content)
        target.write_text("old")

        atomic_file_replace(source, target)

        assert target.read_text() == test_content

    def test_atomic_replace_source_removed(self, tmp_path):
        """Test that source file is removed after replacement."""
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"

        source.write_text("new")
        target.write_text("old")

        atomic_file_replace(source, target)

        assert not source.exists()

    def test_atomic_replace_missing_source_fails(self, tmp_path):
        """Test that missing source file causes failure."""
        source = tmp_path / "missing.txt"
        target = tmp_path / "target.txt"
        target.write_text("old")

        with pytest.raises(OSError):
            atomic_file_replace(source, target)

    def test_atomic_replace_binary_content(self, tmp_path):
        """Test atomic replace with binary content."""
        source = tmp_path / "source.bin"
        target = tmp_path / "target.bin"

        binary_data = b"\x00\x01\x02\xff\xfe\xfd"
        source.write_bytes(binary_data)
        target.write_bytes(b"old")

        atomic_file_replace(source, target)

        assert target.read_bytes() == binary_data


class TestSecurityConstants:
    """Test that security constants are properly defined."""

    def test_max_file_size_defined(self):
        """Test that MAX_FILE_SIZE is set to 10MB."""
        assert MAX_FILE_SIZE == 10 * 1024 * 1024

    def test_min_free_space_defined(self):
        """Test that MIN_FREE_SPACE is set to 100MB."""
        assert MIN_FREE_SPACE == 100 * 1024 * 1024

    def test_binary_check_bytes_defined(self):
        """Test that BINARY_CHECK_BYTES is set to 8192."""
        assert BINARY_CHECK_BYTES == 8192

    def test_non_text_threshold_defined(self):
        """Test that NON_TEXT_THRESHOLD is set to 30%."""
        assert NON_TEXT_THRESHOLD == 0.3
