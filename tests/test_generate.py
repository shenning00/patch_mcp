"""Tests for generate_patch tool.

Tests the patch generation functionality including:
- Simple patch generation
- Identical files (empty patch)
- Binary file rejection
- Symlink rejection
- Custom context lines
- Multiple hunks
- File not found errors
"""

from patch_mcp.tools.generate import generate_patch


class TestGeneratePatch:
    """Test suite for generate_patch tool."""

    def test_generate_simple_patch(self, tmp_path):
        """Generate a simple patch with one change."""
        # Create original file
        original = tmp_path / "original.txt"
        original.write_text("line1\nline2\nline3\n")

        # Create modified file
        modified = tmp_path / "modified.txt"
        modified.write_text("line1\nline2 modified\nline3\n")

        # Generate patch
        result = generate_patch(str(original), str(modified))

        # Verify success
        assert result["success"] is True
        assert result["original_file"] == str(original)
        assert result["modified_file"] == str(modified)
        assert "patch" in result
        assert result["message"] == "Generated patch from file comparison"

        # Verify changes
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 1
        assert result["changes"]["hunks"] == 1

        # Verify patch format
        patch = result["patch"]
        assert "--- original.txt" in patch
        assert "+++ modified.txt" in patch
        assert "-line2" in patch
        assert "+line2 modified" in patch

    def test_generate_identical_files(self, tmp_path):
        """Generate patch from identical files should produce empty patch."""
        # Create two identical files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        content = "same content\nline2\nline3\n"
        file1.write_text(content)
        file2.write_text(content)

        # Generate patch
        result = generate_patch(str(file1), str(file2))

        # Verify success with empty patch
        assert result["success"] is True
        assert result["patch"] == ""
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 0
        assert result["changes"]["hunks"] == 0
        assert result["message"] == "Files are identical - no patch generated"

    def test_generate_reject_binary(self, tmp_path):
        """Binary files should be rejected."""
        # Create binary file (contains null bytes)
        binary_file = tmp_path / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02" * 100)

        # Create text file
        text_file = tmp_path / "text.txt"
        text_file.write_text("some text\n")

        # Test binary as original
        result = generate_patch(str(binary_file), str(text_file))
        assert result["success"] is False
        assert result["error_type"] == "binary_file"
        assert "Original file" in result["error"]

        # Test binary as modified
        result = generate_patch(str(text_file), str(binary_file))
        assert result["success"] is False
        assert result["error_type"] == "binary_file"
        assert "Modified file" in result["error"]

    def test_custom_context_lines(self, tmp_path):
        """Test custom number of context lines."""
        # Create files with more lines
        original = tmp_path / "original.txt"
        original.write_text("line1\nline2\nline3\nline4\nline5\nline6\nline7\n")

        modified = tmp_path / "modified.txt"
        modified.write_text("line1\nline2\nchanged\nline4\nline5\nline6\nline7\n")

        # Generate with 1 context line
        result = generate_patch(str(original), str(modified), context_lines=1)
        assert result["success"] is True
        assert result["changes"]["hunks"] == 1

        # Generate with 5 context lines
        result = generate_patch(str(original), str(modified), context_lines=5)
        assert result["success"] is True
        assert result["changes"]["hunks"] == 1

    def test_generate_reject_symlink(self, tmp_path):
        """Symlinks should be rejected (security policy)."""
        # Create a real file
        real_file = tmp_path / "real.txt"
        real_file.write_text("content\n")

        # Create a symlink
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(real_file)

        # Test symlink as original
        result = generate_patch(str(symlink), str(real_file))
        assert result["success"] is False
        assert result["error_type"] == "symlink_error"
        assert "Original file" in result["error"]

        # Test symlink as modified
        result = generate_patch(str(real_file), str(symlink))
        assert result["success"] is False
        assert result["error_type"] == "symlink_error"
        assert "Modified file" in result["error"]

    def test_generate_file_not_found(self, tmp_path):
        """Missing files should return file_not_found error."""
        # Create one file
        existing = tmp_path / "exists.txt"
        existing.write_text("content\n")

        # Missing file
        missing = tmp_path / "missing.txt"

        # Test missing original
        result = generate_patch(str(missing), str(existing))
        assert result["success"] is False
        assert result["error_type"] == "file_not_found"
        assert "Original file" in result["error"]

        # Test missing modified
        result = generate_patch(str(existing), str(missing))
        assert result["success"] is False
        assert result["error_type"] == "file_not_found"
        assert "Modified file" in result["error"]

    def test_generate_multiple_hunks(self, tmp_path):
        """Generate patch with multiple hunks."""
        # Create original file
        original = tmp_path / "original.txt"
        original.write_text(
            "line1\nline2\nline3\nline4\nline5\n"
            "line6\nline7\nline8\nline9\nline10\n"
            "line11\nline12\nline13\nline14\nline15\n"
        )

        # Create modified file with changes in multiple locations
        modified = tmp_path / "modified.txt"
        modified.write_text(
            "line1 changed\nline2\nline3\nline4\nline5\n"
            "line6\nline7\nline8\nline9\nline10\n"
            "line11\nline12\nline13 changed\nline14\nline15\n"
        )

        # Generate patch
        result = generate_patch(str(original), str(modified))

        # Verify success
        assert result["success"] is True
        assert result["changes"]["lines_added"] == 2
        assert result["changes"]["lines_removed"] == 2
        assert result["changes"]["hunks"] == 2

    def test_generate_addition_only(self, tmp_path):
        """Generate patch with only additions."""
        # Create original file
        original = tmp_path / "original.txt"
        original.write_text("line1\nline2\n")

        # Create modified file with additions
        modified = tmp_path / "modified.txt"
        modified.write_text("line1\nline2\nline3\nline4\n")

        # Generate patch
        result = generate_patch(str(original), str(modified))

        # Verify success
        assert result["success"] is True
        assert result["changes"]["lines_added"] == 2
        assert result["changes"]["lines_removed"] == 0
        assert result["changes"]["hunks"] == 1

    def test_generate_removal_only(self, tmp_path):
        """Generate patch with only removals."""
        # Create original file
        original = tmp_path / "original.txt"
        original.write_text("line1\nline2\nline3\nline4\n")

        # Create modified file with removals
        modified = tmp_path / "modified.txt"
        modified.write_text("line1\nline2\n")

        # Generate patch
        result = generate_patch(str(original), str(modified))

        # Verify success
        assert result["success"] is True
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 2
        assert result["changes"]["hunks"] == 1

    def test_generate_encoding_error(self, tmp_path):
        """Non-UTF-8 files should be rejected (binary or encoding error)."""
        # Create file with invalid UTF-8 (high bytes trigger binary detection)
        bad_file = tmp_path / "bad.txt"
        bad_file.write_bytes(b"\x80\x81\x82\x83")  # Invalid UTF-8

        # Create good file
        good_file = tmp_path / "good.txt"
        good_file.write_text("content\n")

        # Test bad original - binary detection happens first
        result = generate_patch(str(bad_file), str(good_file))
        assert result["success"] is False
        assert result["error_type"] in ["encoding_error", "binary_file"]

        # Test bad modified
        result = generate_patch(str(good_file), str(bad_file))
        assert result["success"] is False
        assert result["error_type"] in ["encoding_error", "binary_file"]

    def test_generate_empty_files(self, tmp_path):
        """Generate patch from empty files."""
        # Create two empty files
        file1 = tmp_path / "empty1.txt"
        file2 = tmp_path / "empty2.txt"
        file1.write_text("")
        file2.write_text("")

        # Generate patch
        result = generate_patch(str(file1), str(file2))

        # Should succeed with no changes
        assert result["success"] is True
        assert result["changes"]["hunks"] == 0
        assert result["patch"] == ""
