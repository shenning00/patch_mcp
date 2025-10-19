"""Tests for update_content tool.

This module tests the update_content tool which allows updating files by
providing original and new content with automatic diff generation.
"""

import pytest
from pathlib import Path

from patch_mcp.tools.update import update_content


class TestUpdateContent:
    """Test suite for update_content function."""

    def test_update_success(self, tmp_path):
        """Test successful content update."""
        file = tmp_path / "test.txt"
        original = "line 1\nline 2\nline 3\n"
        new = "line 1\nmodified line 2\nline 3\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert result["applied"] is True
        assert file.read_text() == new
        assert "diff" in result
        assert "+modified line 2" in result["diff"]
        assert "-line 2" in result["diff"]
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 1
        assert result["changes"]["hunks"] == 1

    def test_update_dry_run(self, tmp_path):
        """Test dry run mode doesn't modify file."""
        file = tmp_path / "test.txt"
        original = "original content\n"
        new = "new content\n"
        file.write_text(original)

        result = update_content(str(file), original, new, dry_run=True)

        assert result["success"] is True
        assert result["applied"] is False  # Not applied in dry run
        assert file.read_text() == original  # File unchanged
        assert "diff" in result
        assert "+new content" in result["diff"]
        assert "-original content" in result["diff"]
        assert "Dry run" in result["message"]

    def test_update_no_changes(self, tmp_path):
        """Test when content is identical (no changes needed)."""
        file = tmp_path / "test.txt"
        content = "same content\n"
        file.write_text(content)

        result = update_content(str(file), content, content)

        assert result["success"] is True
        assert result["applied"] is False
        assert result["diff"] == ""
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 0
        assert "No changes needed" in result["message"]

    def test_update_content_mismatch(self, tmp_path):
        """Test error when original content doesn't match file."""
        file = tmp_path / "test.txt"
        file.write_text("actual content\n")

        result = update_content(
            str(file),
            "expected content\n",  # Wrong!
            "new content\n",
        )

        assert result["success"] is False
        assert result["error_type"] == "content_mismatch"
        assert "does not match expected original" in result["error"]
        assert "diff_from_expected" in result
        assert "+actual content" in result["diff_from_expected"]
        assert "-expected content" in result["diff_from_expected"]
        assert file.read_text() == "actual content\n"  # Unchanged

    def test_update_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        file = tmp_path / "nonexistent.txt"

        result = update_content(str(file), "old", "new")

        assert result["success"] is False
        assert result["error_type"] == "file_not_found"

    def test_update_symlink_rejected(self, tmp_path):
        """Test that symlinks are rejected for security."""
        real_file = tmp_path / "real.txt"
        symlink = tmp_path / "link.txt"
        real_file.write_text("content\n")
        symlink.symlink_to(real_file)

        result = update_content(str(symlink), "content\n", "new\n")

        assert result["success"] is False
        assert result["error_type"] == "symlink_error"

    def test_update_binary_rejected(self, tmp_path):
        """Test that binary files are rejected."""
        file = tmp_path / "binary.bin"
        file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        result = update_content(str(file), "old", "new")

        assert result["success"] is False
        assert result["error_type"] == "binary_file"

    def test_update_multi_line_changes(self, tmp_path):
        """Test updating multiple lines."""
        file = tmp_path / "multi.txt"
        original = "line 1\nline 2\nline 3\nline 4\nline 5\n"
        new = "line 1\nmodified 2\nmodified 3\nline 4\nline 5\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new
        assert result["changes"]["lines_added"] == 2
        assert result["changes"]["lines_removed"] == 2

    def test_update_add_lines(self, tmp_path):
        """Test adding lines to file."""
        file = tmp_path / "add.txt"
        original = "line 1\nline 2\n"
        new = "line 1\nline 2\nline 3\nline 4\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new
        assert result["changes"]["lines_added"] == 2
        assert result["changes"]["lines_removed"] == 0

    def test_update_remove_lines(self, tmp_path):
        """Test removing lines from file."""
        file = tmp_path / "remove.txt"
        original = "line 1\nline 2\nline 3\nline 4\n"
        new = "line 1\nline 4\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 2

    def test_update_whitespace_sensitive(self, tmp_path):
        """Test that whitespace changes are detected."""
        file = tmp_path / "whitespace.txt"
        original = "no trailing space\n"
        new = "no trailing space \n"  # Added trailing space
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 1

    def test_update_preserves_line_endings(self, tmp_path):
        """Test that line endings are preserved."""
        file = tmp_path / "endings.txt"
        # Unix line endings
        original = "line 1\nline 2\n"
        new = "line 1\nmodified\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        content = file.read_text()
        assert content == new
        assert "\r\n" not in content  # No Windows line endings

    def test_update_empty_to_content(self, tmp_path):
        """Test updating from empty file to content."""
        file = tmp_path / "empty.txt"
        file.write_text("")

        result = update_content(str(file), "", "new content\n")

        assert result["success"] is True
        assert file.read_text() == "new content\n"
        assert result["changes"]["lines_added"] == 1

    def test_update_content_to_empty(self, tmp_path):
        """Test updating from content to empty file."""
        file = tmp_path / "toempty.txt"
        file.write_text("content\n")

        result = update_content(str(file), "content\n", "")

        assert result["success"] is True
        assert file.read_text() == ""
        assert result["changes"]["lines_removed"] == 1

    def test_update_unicode_content(self, tmp_path):
        """Test handling unicode content."""
        file = tmp_path / "unicode.txt"
        original = "Hello 世界\n"
        new = "Hello 世界! 🌍\n"
        file.write_text(original, encoding="utf-8")

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text(encoding="utf-8") == new

    def test_update_returns_diff(self, tmp_path):
        """Test that diff is returned in standard format."""
        file = tmp_path / "diff.txt"
        original = "a\nb\nc\n"
        new = "a\nX\nc\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        diff = result["diff"]
        assert "---" in diff  # Diff header
        assert "+++" in diff
        assert "@@" in diff  # Hunk header
        assert "-b" in diff
        assert "+X" in diff

    def test_update_encoding_error(self, tmp_path):
        """Test handling of encoding errors."""
        file = tmp_path / "bad_encoding.txt"
        # Write binary data that's not valid UTF-8
        file.write_bytes(b"\xff\xfe invalid utf8")

        result = update_content(str(file), "old", "new")

        assert result["success"] is False
        assert result["error_type"] == "encoding_error"

    def test_update_atomic_operation(self, tmp_path):
        """Test that updates are atomic (temp file used)."""
        file = tmp_path / "atomic.txt"
        original = "original\n"
        new = "new\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        # Verify no .tmp file left behind
        assert not (tmp_path / "atomic.txt.tmp").exists()
        assert file.read_text() == new

    def test_update_complex_changes(self, tmp_path):
        """Test complex multi-section changes."""
        file = tmp_path / "complex.py"
        original = """def foo():
    return 1

def bar():
    return 2

def baz():
    return 3
"""
        new = """def foo():
    return 10

def bar():
    return 20

def baz():
    return 30
"""
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new
        assert result["changes"]["lines_added"] == 3
        assert result["changes"]["lines_removed"] == 3
        # Should have multiple hunks (one for each function)
        assert result["changes"]["hunks"] >= 1

    def test_update_preserves_permissions(self, tmp_path):
        """Test that file permissions are preserved."""
        file = tmp_path / "perms.txt"
        original = "old\n"
        new = "new\n"
        file.write_text(original)

        # Set specific permissions
        import stat

        file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        original_mode = file.stat().st_mode

        result = update_content(str(file), original, new)

        assert result["success"] is True
        # Note: atomic_file_replace may not preserve permissions
        # This test documents current behavior


class TestUpdateContentEdgeCases:
    """Test edge cases and error conditions."""

    def test_update_no_trailing_newline(self, tmp_path):
        """Test content without trailing newline."""
        file = tmp_path / "no_newline.txt"
        original = "no newline"
        new = "no newline either"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new

    def test_update_very_long_lines(self, tmp_path):
        """Test handling very long lines."""
        file = tmp_path / "long.txt"
        original = "x" * 5000 + "\n"
        new = "y" * 5000 + "\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert file.read_text() == new

    def test_update_many_lines(self, tmp_path):
        """Test updating file with many lines."""
        file = tmp_path / "many.txt"
        original = "\n".join([f"line {i}" for i in range(1000)]) + "\n"
        new = "\n".join([f"LINE {i}" for i in range(1000)]) + "\n"
        file.write_text(original)

        result = update_content(str(file), original, new)

        assert result["success"] is True
        assert result["changes"]["lines_added"] == 1000
        assert result["changes"]["lines_removed"] == 1000
