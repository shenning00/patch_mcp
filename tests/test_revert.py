"""Tests for revert_patch tool.

Tests the patch reversion functionality including:
- Successful reversion
- Reversion after file modification
- Reversion with multiple hunks
- Edge cases
"""

import pytest
from pathlib import Path

from patch_mcp.tools.apply import apply_patch
from patch_mcp.tools.revert import revert_patch


class TestRevertPatch:
    """Test suite for revert_patch tool."""

    def test_revert_success(self, tmp_path):
        """Apply then revert should restore original content."""
        # Create file
        file = tmp_path / "config.py"
        original_content = "DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n"
        file.write_text(original_content)

        # Create and apply patch
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        # Apply patch
        apply_result = apply_patch(str(file), patch)
        assert apply_result["success"] is True

        # Verify file was modified
        assert file.read_text() != original_content
        assert "LOG_LEVEL = 'DEBUG'" in file.read_text()

        # Revert patch
        revert_result = revert_patch(str(file), patch)

        # Verify success
        assert revert_result["success"] is True
        assert revert_result["file_path"] == str(file)
        assert revert_result["reverted"] is True
        assert "Successfully reverted" in revert_result["message"]

        # Verify changes (opposite of apply)
        assert revert_result["changes"]["lines_added"] == 1
        assert revert_result["changes"]["lines_removed"] == 1
        assert revert_result["changes"]["hunks_reverted"] == 1

        # CRITICAL: File should be back to original
        assert file.read_text() == original_content

    def test_revert_after_modification(self, tmp_path):
        """Revert should fail if file was modified after patch."""
        # Create file and apply patch
        file = tmp_path / "config.py"
        file.write_text("DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n")

        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        apply_result = apply_patch(str(file), patch)
        assert apply_result["success"] is True

        # Modify file in the same area
        file.write_text("DEBUG = False\nLOG_LEVEL = 'WARNING'\nPORT = 8000\n")

        # Try to revert - should fail
        revert_result = revert_patch(str(file), patch)

        # Should fail with context mismatch
        assert revert_result["success"] is False
        assert revert_result["reverted"] is False
        assert revert_result["error_type"] == "context_mismatch"
        assert "modified" in revert_result["error"].lower()

    def test_revert_file_not_found(self, tmp_path):
        """Revert on missing file should fail."""
        missing = tmp_path / "missing.txt"
        patch = """--- missing.txt
+++ missing.txt
@@ -1,1 +1,1 @@
-old
+new
"""

        result = revert_patch(str(missing), patch)

        assert result["success"] is False
        assert result["reverted"] is False
        assert result["error_type"] == "file_not_found"

    def test_revert_unchanged_if_already_reverted(self, tmp_path):
        """Reverting twice should fail (file already in original state)."""
        # Create file
        file = tmp_path / "file.py"
        original = "line1\nline2\nline3\n"
        file.write_text(original)

        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
 line1
-line2
+modified
 line3
"""

        # Apply and revert
        apply_patch(str(file), patch)
        revert_patch(str(file), patch)

        # File is back to original
        assert file.read_text() == original

        # Try to revert again - should fail
        result = revert_patch(str(file), patch)

        # Should fail because patch expects "modified" but finds "line2"
        assert result["success"] is False
        assert result["reverted"] is False

    def test_revert_multiple_hunks(self, tmp_path):
        """Revert patch with multiple hunks."""
        file = tmp_path / "file.py"
        original = (
            "line1\nline2\nline3\nline4\nline5\n"
            "line6\nline7\nline8\nline9\nline10\n"
        )
        file.write_text(original)

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

        # Apply patch
        apply_result = apply_patch(str(file), patch)
        assert apply_result["success"] is True

        # Revert patch
        revert_result = revert_patch(str(file), patch)

        assert revert_result["success"] is True
        assert revert_result["changes"]["hunks_reverted"] == 2

        # File should be back to original
        assert file.read_text() == original

    def test_revert_addition_only(self, tmp_path):
        """Revert patch that only added lines."""
        file = tmp_path / "file.py"
        original = "line1\nline2\n"
        file.write_text(original)

        # Patch adds a line
        patch = """--- file.py
+++ file.py
@@ -1,2 +1,3 @@
 line1
+added
 line2
"""

        # Apply (adds line)
        apply_patch(str(file), patch)
        assert "added" in file.read_text()

        # Revert (removes line)
        revert_result = revert_patch(str(file), patch)

        assert revert_result["success"] is True
        # When reverting an addition, we remove it
        assert revert_result["changes"]["lines_removed"] == 1
        assert revert_result["changes"]["lines_added"] == 0

        # File back to original
        assert file.read_text() == original

    def test_revert_removal_only(self, tmp_path):
        """Revert patch that only removed lines."""
        file = tmp_path / "file.py"
        original = "line1\nremove_me\nline2\n"
        file.write_text(original)

        # Patch removes a line
        patch = """--- file.py
+++ file.py
@@ -1,3 +1,2 @@
 line1
-remove_me
 line2
"""

        # Apply (removes line)
        apply_patch(str(file), patch)
        assert "remove_me" not in file.read_text()

        # Revert (adds it back)
        revert_result = revert_patch(str(file), patch)

        assert revert_result["success"] is True
        # When reverting a removal, we add it back
        assert revert_result["changes"]["lines_added"] == 1
        assert revert_result["changes"]["lines_removed"] == 0

        # File back to original
        assert file.read_text() == original

    def test_revert_empty_patch(self, tmp_path):
        """Reverting an empty patch should succeed."""
        file = tmp_path / "file.txt"
        content = "content\n"
        file.write_text(content)

        result = revert_patch(str(file), "")

        # Should succeed (no-op)
        assert result["success"] is True
        assert result["changes"]["hunks_reverted"] == 0

        # File unchanged
        assert file.read_text() == content

    def test_revert_complex_patch(self, tmp_path):
        """Revert complex patch with mixed operations."""
        file = tmp_path / "complex.py"
        original = "def foo():\n    old1\n    old2\n    keep\n"
        file.write_text(original)

        patch = """--- complex.py
+++ complex.py
@@ -1,4 +1,4 @@
 def foo():
-    old1
-    old2
+    new1
+    new2
     keep
"""

        # Apply
        apply_patch(str(file), patch)
        modified = file.read_text()
        assert "new1" in modified
        assert "new2" in modified
        assert "old1" not in modified

        # Revert
        result = revert_patch(str(file), patch)

        assert result["success"] is True

        # Back to original
        assert file.read_text() == original

    def test_revert_preserves_error_type(self, tmp_path):
        """Error types from apply should be preserved."""
        # Create symlink
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

        result = revert_patch(str(symlink), patch)

        # Should preserve symlink_error from apply
        assert result["success"] is False
        assert result["error_type"] == "symlink_error"

    def test_revert_with_whitespace_changes(self, tmp_path):
        """Revert whitespace-only changes."""
        file = tmp_path / "file.py"
        original = "line1\nline2\nline3\n"
        file.write_text(original)

        # Add trailing space
        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
 line1
-line2
+line2
 line3
"""

        # Apply
        apply_patch(str(file), patch)

        # Revert
        result = revert_patch(str(file), patch)

        assert result["success"] is True

        # Should restore exact original (including whitespace)
        assert file.read_text() == original

    def test_revert_sequential_patches(self, tmp_path):
        """Test reverting patches in reverse order."""
        file = tmp_path / "file.py"
        v0 = "version0\n"
        file.write_text(v0)

        patch1 = """--- file.py
+++ file.py
@@ -1,1 +1,1 @@
-version0
+version1
"""

        patch2 = """--- file.py
+++ file.py
@@ -1,1 +1,1 @@
-version1
+version2
"""

        # Apply both patches
        apply_patch(str(file), patch1)
        assert "version1" in file.read_text()

        apply_patch(str(file), patch2)
        assert "version2" in file.read_text()

        # Revert in reverse order (last applied first)
        revert_patch(str(file), patch2)
        assert "version1" in file.read_text()

        revert_patch(str(file), patch1)
        assert file.read_text() == v0
