"""Tests for inspect_patch tool.

Tests the patch inspection functionality including:
- Single file patches
- Multi-file patches (CRITICAL)
- Invalid patches
- Empty patches
- Summary totals
"""

from patch_mcp.tools.inspect import inspect_patch


class TestInspectPatch:
    """Test suite for inspect_patch tool."""

    def test_inspect_single_file(self):
        """Single file patch should return array with 1 element."""
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        result = inspect_patch(patch)

        # Verify success
        assert result["success"] is True
        assert result["valid"] is True
        assert result["message"] == "Patch analysis complete"

        # Verify files is an array with 1 element
        assert "files" in result
        assert isinstance(result["files"], list)
        assert len(result["files"]) == 1

        # Verify file info
        file_info = result["files"][0]
        assert file_info["source"] == "config.py"
        assert file_info["target"] == "config.py"
        assert file_info["hunks"] == 1
        assert file_info["lines_added"] == 1
        assert file_info["lines_removed"] == 1

        # Verify summary
        assert "summary" in result
        assert result["summary"]["total_files"] == 1
        assert result["summary"]["total_hunks"] == 1
        assert result["summary"]["total_lines_added"] == 1
        assert result["summary"]["total_lines_removed"] == 1

    def test_inspect_multiple_files(self):
        """Multi-file patch should return all files in array."""
        patch = """--- file1.py
+++ file1.py
@@ -1,1 +1,1 @@
-old
+new
--- file2.py
+++ file2.py
@@ -1,1 +1,2 @@
 existing
+added
--- file3.py
+++ file3.py
@@ -1,2 +1,1 @@
 keep
-remove
"""

        result = inspect_patch(patch)

        # Verify success
        assert result["success"] is True
        assert result["valid"] is True

        # Verify all files returned
        assert len(result["files"]) == 3

        # Verify first file
        assert result["files"][0]["source"] == "file1.py"
        assert result["files"][0]["hunks"] == 1
        assert result["files"][0]["lines_added"] == 1
        assert result["files"][0]["lines_removed"] == 1

        # Verify second file
        assert result["files"][1]["source"] == "file2.py"
        assert result["files"][1]["hunks"] == 1
        assert result["files"][1]["lines_added"] == 1
        assert result["files"][1]["lines_removed"] == 0

        # Verify third file
        assert result["files"][2]["source"] == "file3.py"
        assert result["files"][2]["hunks"] == 1
        assert result["files"][2]["lines_added"] == 0
        assert result["files"][2]["lines_removed"] == 1

        # Verify summary totals
        assert result["summary"]["total_files"] == 3
        assert result["summary"]["total_hunks"] == 3
        assert result["summary"]["total_lines_added"] == 2
        assert result["summary"]["total_lines_removed"] == 2

    def test_inspect_invalid_patch(self):
        """Invalid patch should return error."""
        # Patch without proper headers
        bad_patch = """This is not a patch
Just some random text
Without proper formatting
"""

        result = inspect_patch(bad_patch)

        # Verify failure
        assert result["success"] is False
        assert result["valid"] is False
        assert result["error_type"] == "invalid_patch"
        assert "Invalid patch format" in result["error"]
        assert result["message"] == "Patch is not valid"

    def test_inspect_empty_patch(self):
        """Empty patch should return success with zero counts."""
        result = inspect_patch("")

        # Verify success with empty results
        assert result["success"] is True
        assert result["valid"] is True
        assert result["files"] == []
        assert result["summary"]["total_files"] == 0
        assert result["summary"]["total_hunks"] == 0
        assert result["summary"]["total_lines_added"] == 0
        assert result["summary"]["total_lines_removed"] == 0
        assert result["message"] == "Empty patch - no changes"

    def test_inspect_whitespace_only(self):
        """Whitespace-only patch should be treated as empty."""
        result = inspect_patch("   \n\n\t\n   ")

        # Verify success with empty results
        assert result["success"] is True
        assert result["valid"] is True
        assert result["files"] == []
        assert result["summary"]["total_files"] == 0

    def test_inspect_summary_totals(self):
        """Summary should correctly total all files."""
        patch = """--- a.py
+++ a.py
@@ -1,5 +1,6 @@
 line1
 line2
+added1
 line3
 line4
 line5
@@ -10,3 +11,4 @@
 line10
 line11
+added2
 line12
--- b.py
+++ b.py
@@ -1,3 +1,2 @@
 keep1
-remove1
 keep2
"""

        result = inspect_patch(patch)

        # Verify success
        assert result["success"] is True

        # Verify individual files
        assert len(result["files"]) == 2
        assert result["files"][0]["hunks"] == 2
        assert result["files"][0]["lines_added"] == 2
        assert result["files"][0]["lines_removed"] == 0
        assert result["files"][1]["hunks"] == 1
        assert result["files"][1]["lines_added"] == 0
        assert result["files"][1]["lines_removed"] == 1

        # Verify summary totals
        assert result["summary"]["total_files"] == 2
        assert result["summary"]["total_hunks"] == 3
        assert result["summary"]["total_lines_added"] == 2
        assert result["summary"]["total_lines_removed"] == 1

    def test_inspect_no_changes(self):
        """Patch with headers but no hunks."""
        patch = """--- file.py
+++ file.py
"""

        result = inspect_patch(patch)

        # Should succeed with zero hunks
        assert result["success"] is True
        assert len(result["files"]) == 1
        assert result["files"][0]["hunks"] == 0
        assert result["files"][0]["lines_added"] == 0
        assert result["files"][0]["lines_removed"] == 0

    def test_inspect_addition_only(self):
        """Patch with only additions."""
        patch = """--- file.py
+++ file.py
@@ -1,2 +1,4 @@
 line1
+added1
+added2
 line2
"""

        result = inspect_patch(patch)

        assert result["success"] is True
        assert result["files"][0]["lines_added"] == 2
        assert result["files"][0]["lines_removed"] == 0

    def test_inspect_removal_only(self):
        """Patch with only removals."""
        patch = """--- file.py
+++ file.py
@@ -1,4 +1,2 @@
 line1
-removed1
-removed2
 line2
"""

        result = inspect_patch(patch)

        assert result["success"] is True
        assert result["files"][0]["lines_added"] == 0
        assert result["files"][0]["lines_removed"] == 2

    def test_inspect_multiple_hunks_single_file(self):
        """Single file with multiple hunks."""
        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
 line1
-old1
+new1
 line3
@@ -10,3 +10,3 @@
 line10
-old2
+new2
 line12
@@ -20,3 +20,3 @@
 line20
-old3
+new3
 line22
"""

        result = inspect_patch(patch)

        assert result["success"] is True
        assert len(result["files"]) == 1
        assert result["files"][0]["hunks"] == 3
        assert result["files"][0]["lines_added"] == 3
        assert result["files"][0]["lines_removed"] == 3

    def test_inspect_no_newline_marker(self):
        """Patch with 'No newline at end of file' marker."""
        patch = """--- file.py
+++ file.py
@@ -1,2 +1,2 @@
 line1
-line2
\\ No newline at end of file
+line2
"""

        result = inspect_patch(patch)

        # Should succeed and not count the marker as a change
        assert result["success"] is True
        assert result["files"][0]["lines_added"] == 1
        assert result["files"][0]["lines_removed"] == 1

    def test_inspect_path_with_spaces(self):
        """File paths with spaces should be parsed correctly."""
        patch = """--- path/to/my file.py
+++ path/to/my file.py
@@ -1,1 +1,1 @@
-old
+new
"""

        result = inspect_patch(patch)

        assert result["success"] is True
        # Should handle the first path component
        assert "path/to/my" in result["files"][0]["source"]

    def test_inspect_dev_null_new_file(self):
        """New file creation patch (from /dev/null)."""
        patch = """--- /dev/null
+++ newfile.py
@@ -0,0 +1,3 @@
+line1
+line2
+line3
"""

        result = inspect_patch(patch)

        assert result["success"] is True
        assert result["files"][0]["source"] == "/dev/null"
        assert result["files"][0]["target"] == "newfile.py"
        assert result["files"][0]["lines_added"] == 3
        assert result["files"][0]["lines_removed"] == 0

    def test_inspect_dev_null_delete_file(self):
        """File deletion patch (to /dev/null)."""
        patch = """--- oldfile.py
+++ /dev/null
@@ -1,3 +0,0 @@
-line1
-line2
-line3
"""

        result = inspect_patch(patch)

        assert result["success"] is True
        assert result["files"][0]["source"] == "oldfile.py"
        assert result["files"][0]["target"] == "/dev/null"
        assert result["files"][0]["lines_added"] == 0
        assert result["files"][0]["lines_removed"] == 3
