"""Tests for apply_patch tool.

Tests the patch application functionality including:
- Successful application
- Context mismatch
- Dry run mode (CRITICAL)
- Empty patches
- Edge cases
- Security checks
"""

from patch_mcp.tools.apply import apply_patch


class TestApplyPatch:
    """Test suite for apply_patch tool."""

    def test_apply_success(self, tmp_path):
        """Apply patch successfully."""
        # Create file
        file = tmp_path / "config.py"
        file.write_text("DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n")

        # Create patch
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        result = apply_patch(str(file), patch)

        # Verify success
        assert result["success"] is True
        assert result["file_path"] == str(file)
        assert result["applied"] is True
        assert "Successfully applied" in result["message"]

        # Verify changes
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 1
        assert result["changes"]["hunks_applied"] == 1

        # Verify file was actually modified
        content = file.read_text()
        assert "LOG_LEVEL = 'DEBUG'" in content
        assert "LOG_LEVEL = 'INFO'" not in content

    def test_apply_context_mismatch(self, tmp_path):
        """Context mismatch should fail gracefully."""
        # Create file with different content
        file = tmp_path / "config.py"
        file.write_text("DEBUG = False\nLOG_LEVEL = 'WARNING'\nPORT = 8000\n")

        # Patch expects different content
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        result = apply_patch(str(file), patch)

        # Should fail
        assert result["success"] is False
        assert result["applied"] is False
        assert result["error_type"] == "context_mismatch"

        # File should remain unchanged
        content = file.read_text()
        assert "LOG_LEVEL = 'WARNING'" in content

    def test_dry_run_success(self, tmp_path):
        """Dry run should validate without modifying."""
        # Create file
        file = tmp_path / "config.py"
        original_content = "DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n"
        file.write_text(original_content)

        # Create patch
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        result = apply_patch(str(file), patch, dry_run=True)

        # Should succeed
        assert result["success"] is True
        assert result["applied"] is True
        assert "dry run" in result["message"]

        # Verify changes info
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 1

        # CRITICAL: File should NOT be modified
        content = file.read_text()
        assert content == original_content
        assert "LOG_LEVEL = 'INFO'" in content
        assert "LOG_LEVEL = 'DEBUG'" not in content

    def test_dry_run_does_not_modify(self, tmp_path):
        """CRITICAL: Dry run must not modify file under any circumstance."""
        # Create file
        file = tmp_path / "file.py"
        original = "line1\nline2\nline3\n"
        file.write_text(original)

        # Apply with dry run
        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
 line1
-line2
+modified
 line3
"""

        result = apply_patch(str(file), patch, dry_run=True)

        # Even though it succeeds, file should be unchanged
        assert result["success"] is True
        assert file.read_text() == original

    def test_empty_patch(self, tmp_path):
        """Empty patch should succeed with zero counts."""
        file = tmp_path / "file.txt"
        original = "content\n"
        file.write_text(original)

        result = apply_patch(str(file), "")

        # Should succeed with no changes
        assert result["success"] is True
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 0
        assert result["changes"]["hunks_applied"] == 0

        # File should be unchanged
        assert file.read_text() == original

    def test_whitespace_only_changes(self, tmp_path):
        """Whitespace-only changes should be counted normally."""
        file = tmp_path / "file.py"
        file.write_text("line1\nline2\nline3\n")

        # Add whitespace
        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
 line1
-line2
+line2
 line3
"""

        result = apply_patch(str(file), patch)

        # Should succeed
        assert result["success"] is True
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 1

    def test_reject_symlink(self, tmp_path):
        """Symlinks should be rejected."""
        real_file = tmp_path / "real.txt"
        real_file.write_text("content\n")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(real_file)

        patch = """--- link.txt
+++ link.txt
@@ -1,1 +1,1 @@
-content
+modified
"""

        result = apply_patch(str(symlink), patch)

        assert result["success"] is False
        assert result["error_type"] == "symlink_error"
        assert result["applied"] is False

    def test_reject_binary(self, tmp_path):
        """Binary files should be rejected."""
        binary = tmp_path / "binary.dat"
        binary.write_bytes(b"\x00\x01\x02" * 100)

        patch = """--- binary.dat
+++ binary.dat
@@ -1,1 +1,1 @@
-old
+new
"""

        result = apply_patch(str(binary), patch)

        assert result["success"] is False
        assert result["error_type"] == "binary_file"
        assert result["applied"] is False

    def test_apply_multiple_hunks(self, tmp_path):
        """Apply patch with multiple hunks."""
        file = tmp_path / "file.py"
        file.write_text(
            "line1\nline2\nline3\nline4\nline5\n" "line6\nline7\nline8\nline9\nline10\n"
        )

        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
-line1
+line1 modified
 line2
 line3
@@ -8,3 +8,3 @@
 line8
-line9
+line9 modified
 line10
"""

        result = apply_patch(str(file), patch)

        # Should succeed
        assert result["success"] is True
        assert result["changes"]["hunks_applied"] == 2
        assert result["changes"]["lines_added"] == 2
        assert result["changes"]["lines_removed"] == 2

        # Verify modifications
        content = file.read_text()
        assert "line1 modified" in content
        assert "line9 modified" in content

    def test_apply_addition_only(self, tmp_path):
        """Apply patch with only additions."""
        file = tmp_path / "file.py"
        file.write_text("line1\nline2\n")

        patch = """--- file.py
+++ file.py
@@ -1,2 +1,3 @@
 line1
+added
 line2
"""

        result = apply_patch(str(file), patch)

        assert result["success"] is True
        assert result["changes"]["lines_added"] == 1
        assert result["changes"]["lines_removed"] == 0

        # Verify addition
        content = file.read_text()
        assert "added" in content

    def test_apply_removal_only(self, tmp_path):
        """Apply patch with only removals."""
        file = tmp_path / "file.py"
        file.write_text("line1\nremove_me\nline2\n")

        patch = """--- file.py
+++ file.py
@@ -1,3 +1,2 @@
 line1
-remove_me
 line2
"""

        result = apply_patch(str(file), patch)

        assert result["success"] is True
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 1

        # Verify removal
        content = file.read_text()
        assert "remove_me" not in content

    def test_apply_file_not_found(self, tmp_path):
        """Missing file should return error."""
        missing = tmp_path / "missing.txt"
        patch = """--- missing.txt
+++ missing.txt
@@ -1,1 +1,1 @@
-old
+new
"""

        result = apply_patch(str(missing), patch)

        assert result["success"] is False
        assert result["error_type"] == "file_not_found"
        assert result["applied"] is False

    def test_dry_run_no_write_permission_needed(self, tmp_path):
        """Dry run should not require write permission."""
        # Create read-only file
        file = tmp_path / "readonly.txt"
        file.write_text("content\n")
        file.chmod(0o444)

        patch = """--- readonly.txt
+++ readonly.txt
@@ -1,1 +1,1 @@
-content
+modified
"""

        # Dry run should succeed (no write check)
        result = apply_patch(str(file), patch, dry_run=True)
        assert result["success"] is True

        # Restore write permission for cleanup
        file.chmod(0o644)

    def test_apply_preserves_line_endings(self, tmp_path):
        """Apply should preserve line endings."""
        file = tmp_path / "file.txt"
        file.write_text("line1\nline2\nline3\n")

        patch = """--- file.txt
+++ file.txt
@@ -1,3 +1,3 @@
 line1
-line2
+modified
 line3
"""

        result = apply_patch(str(file), patch)

        assert result["success"] is True

        # Verify line endings preserved (all \n)
        content = file.read_text()
        assert "modified\n" in content

    def test_apply_creates_backup_atomically(self, tmp_path):
        """Apply should use atomic file replacement."""
        file = tmp_path / "file.txt"
        original = "line1\nline2\nline3\n"
        file.write_text(original)

        patch = """--- file.txt
+++ file.txt
@@ -1,3 +1,3 @@
 line1
-line2
+modified
 line3
"""

        result = apply_patch(str(file), patch)

        # Should succeed
        assert result["success"] is True

        # File should exist and be modified
        assert file.exists()
        assert "modified" in file.read_text()

        # No temp files should remain
        temp_files = list(tmp_path.glob(".patch_tmp_*"))
        assert len(temp_files) == 0

    def test_dry_run_with_context_mismatch(self, tmp_path):
        """Dry run should fail on context mismatch too."""
        file = tmp_path / "file.py"
        file.write_text("wrong\ncontent\n")

        patch = """--- file.py
+++ file.py
@@ -1,2 +1,2 @@
-expected
+modified
 content
"""

        result = apply_patch(str(file), patch, dry_run=True)

        # Should fail even in dry run
        assert result["success"] is False
        assert result["applied"] is False

    def test_apply_complex_changes(self, tmp_path):
        """Apply complex patch with additions, removals, and modifications."""
        file = tmp_path / "complex.py"
        file.write_text("def foo():\n    old_line1\n    old_line2\n    old_line3\n")

        patch = """--- complex.py
+++ complex.py
@@ -1,4 +1,5 @@
 def foo():
-    old_line1
-    old_line2
+    new_line1
+    new_line2
+    added_line
     old_line3
"""

        result = apply_patch(str(file), patch)

        assert result["success"] is True
        assert result["changes"]["lines_added"] == 3
        assert result["changes"]["lines_removed"] == 2

        # Verify result
        content = file.read_text()
        assert "new_line1" in content
        assert "new_line2" in content
        assert "added_line" in content
        assert "old_line1" not in content
        assert "old_line2" not in content
        assert "old_line3" in content

    def test_apply_patch_with_triple_quotes(self, tmp_path):
        """Apply patch that adds/removes lines containing triple quotes."""
        # Create file with docstring
        file = tmp_path / "module.py"
        file.write_text('def foo():\n    """Old docstring"""\n    return 42\n')

        # Create patch that changes a docstring (contains triple quotes)
        # Use single quotes for the outer string to avoid escaping
        patch = '''--- module.py
@@ -1,3 +1,3 @@
 def foo():
-    """Old docstring"""
+    """New docstring with more detail"""
     return 42
'''

        result = apply_patch(str(file), patch)

        # Verify success
        assert result["success"] is True
        assert result["applied"] is True

        # Verify the triple quotes were handled correctly
        content = file.read_text()
        assert '"""New docstring with more detail"""' in content
        assert '"""Old docstring"""' not in content

    def test_apply_patch_adding_triple_quoted_string(self, tmp_path):
        """Apply patch that adds a new triple-quoted string."""
        file = tmp_path / "test.py"
        file.write_text("x = 1\ny = 2\n")

        # Patch adds a docstring
        patch = '''--- test.py
@@ -1,2 +1,3 @@
+"""Module docstring"""
 x = 1
 y = 2
'''

        result = apply_patch(str(file), patch)
        assert result["success"] is True
        assert '"""Module docstring"""' in file.read_text()
