"""Test critical API semantics for Phase 2 tools.

This test file verifies the CRITICAL API semantics as specified in the design:
1. validate_patch returns success=False when can_apply=False
2. inspect_patch returns files array (not file object)
3. apply_patch supports dry_run parameter
4. All tools use correct return formats
"""

import pytest
from pathlib import Path

from patch_mcp.tools.generate import generate_patch
from patch_mcp.tools.inspect import inspect_patch
from patch_mcp.tools.validate import validate_patch
from patch_mcp.tools.apply import apply_patch
from patch_mcp.tools.revert import revert_patch


class TestCriticalAPISemantics:
    """Test suite for critical API semantics."""

    def test_validate_patch_success_false_when_cannot_apply(self, tmp_path):
        """CRITICAL: validate_patch must return success=False when can_apply=False."""
        # Create file with content that doesn't match patch
        file = tmp_path / "file.py"
        file.write_text("wrong\ncontent\n")

        # Patch expects different content
        patch = """--- file.py
+++ file.py
@@ -1,2 +1,2 @@
-expected
+modified
 content
"""

        result = validate_patch(str(file), patch)

        # CRITICAL: success must be False when cannot apply
        assert result["success"] is False, "success should be False when patch cannot be applied"
        assert result["valid"] is True, "patch format is valid"
        assert result["can_apply"] is False, "patch cannot be applied"
        assert result["error_type"] == "context_mismatch"
        assert "reason" in result, "reason must be present"
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0
        assert "preview" in result, "preview should still be present"

    def test_validate_patch_success_true_when_can_apply(self, tmp_path):
        """validate_patch must return success=True when can_apply=True."""
        file = tmp_path / "file.py"
        file.write_text("expected\ncontent\n")

        patch = """--- file.py
+++ file.py
@@ -1,2 +1,2 @@
-expected
+modified
 content
"""

        result = validate_patch(str(file), patch)

        # Success should be True when can apply
        assert result["success"] is True
        assert result["can_apply"] is True
        assert result["valid"] is True
        assert "preview" in result

    def test_inspect_patch_returns_files_array(self):
        """CRITICAL: inspect_patch must return files array, NOT file object."""
        # Single file patch
        single_patch = """--- config.py
+++ config.py
@@ -1,1 +1,1 @@
-old
+new
"""

        result = inspect_patch(single_patch)

        # CRITICAL: Must return files array, not file object
        assert result["success"] is True
        assert "files" in result, "Must have 'files' field"
        assert "file" not in result, "Must NOT have 'file' field (old format)"
        assert isinstance(result["files"], list), "files must be a list/array"
        assert len(result["files"]) == 1, "Single file patch should have 1 element in array"

        # Verify file structure
        file_info = result["files"][0]
        assert "source" in file_info
        assert "target" in file_info
        assert "hunks" in file_info
        assert "lines_added" in file_info
        assert "lines_removed" in file_info

        # Verify summary exists
        assert "summary" in result
        assert result["summary"]["total_files"] == 1

    def test_inspect_patch_multi_file_support(self):
        """inspect_patch must support multi-file patches."""
        multi_patch = """--- file1.py
+++ file1.py
@@ -1,1 +1,1 @@
-old1
+new1
--- file2.py
+++ file2.py
@@ -1,1 +1,1 @@
-old2
+new2
"""

        result = inspect_patch(multi_patch)

        assert result["success"] is True
        assert len(result["files"]) == 2, "Multi-file patch should return all files"

        # Verify both files are present
        assert result["files"][0]["source"] == "file1.py"
        assert result["files"][1]["source"] == "file2.py"

        # Verify summary totals
        assert result["summary"]["total_files"] == 2
        assert result["summary"]["total_hunks"] == 2

    def test_apply_patch_dry_run_parameter(self, tmp_path):
        """CRITICAL: apply_patch must support dry_run parameter."""
        file = tmp_path / "file.py"
        original = "line1\nline2\n"
        file.write_text(original)

        patch = """--- file.py
+++ file.py
@@ -1,2 +1,2 @@
-line1
+modified
 line2
"""

        # Test dry_run=True
        result = apply_patch(str(file), patch, dry_run=True)

        # Should succeed
        assert result["success"] is True
        assert result["applied"] is True
        assert "dry run" in result["message"].lower()

        # CRITICAL: File must NOT be modified
        assert file.read_text() == original, "dry_run must not modify file"

        # Test dry_run=False (default)
        result = apply_patch(str(file), patch, dry_run=False)

        assert result["success"] is True
        assert file.read_text() != original, "non-dry-run should modify file"

    def test_validate_affected_line_range_is_object(self, tmp_path):
        """affected_line_range must be an object with start/end, not a string."""
        file = tmp_path / "file.py"
        file.write_text("line1\nline2\nline3\n")

        patch = """--- file.py
+++ file.py
@@ -1,3 +1,3 @@
-line1
+modified
 line2
 line3
"""

        result = validate_patch(str(file), patch)

        assert result["success"] is True
        preview = result["preview"]

        # CRITICAL: affected_line_range must be an object, not a string
        assert "affected_line_range" in preview
        assert isinstance(preview["affected_line_range"], dict), "Must be object/dict, not string"
        assert "start" in preview["affected_line_range"]
        assert "end" in preview["affected_line_range"]
        assert isinstance(preview["affected_line_range"]["start"], int)
        assert isinstance(preview["affected_line_range"]["end"], int)

    def test_revert_patch_uses_reverted_field(self, tmp_path):
        """revert_patch must use 'reverted' field, not 'applied'."""
        file = tmp_path / "file.py"
        file.write_text("original\n")

        patch = """--- file.py
+++ file.py
@@ -1,1 +1,1 @@
-original
+modified
"""

        # Apply then revert
        apply_patch(str(file), patch)
        result = revert_patch(str(file), patch)

        # Must use 'reverted' field
        assert "reverted" in result, "Must have 'reverted' field"
        assert "applied" not in result, "Should not have 'applied' field"
        assert result["reverted"] is True

    def test_all_tools_return_success_field(self, tmp_path):
        """All tools must return 'success' field."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1\n")
        file2.write_text("content2\n")

        patch = """--- file1.py
+++ file1.py
@@ -1,1 +1,1 @@
-content1
+modified
"""

        # Test all tools
        results = [
            generate_patch(str(file1), str(file2)),
            inspect_patch(patch),
            validate_patch(str(file1), patch),
            apply_patch(str(file1), patch, dry_run=True),
            revert_patch(str(file1), patch),
        ]

        for result in results:
            assert "success" in result, "All tools must return 'success' field"
            assert isinstance(result["success"], bool)

    def test_all_failures_include_error_type(self, tmp_path):
        """All failures must include error_type field."""
        missing = tmp_path / "missing.txt"
        patch = """--- missing.txt
+++ missing.txt
@@ -1,1 +1,1 @@
-old
+new
"""

        # Test error scenarios
        results = [
            generate_patch(str(missing), str(missing)),
            validate_patch(str(missing), patch),
            apply_patch(str(missing), patch),
            revert_patch(str(missing), patch),
        ]

        for result in results:
            if not result["success"]:
                assert "error_type" in result, "Failed operations must include error_type"
                assert isinstance(result["error_type"], str)

    def test_empty_patch_handling(self, tmp_path):
        """All tools must handle empty patches correctly."""
        file = tmp_path / "file.py"
        file.write_text("content\n")

        # Empty patch
        empty_patch = ""

        # inspect_patch
        result = inspect_patch(empty_patch)
        assert result["success"] is True
        assert result["files"] == []
        assert result["summary"]["total_files"] == 0

        # validate_patch
        result = validate_patch(str(file), empty_patch)
        assert result["success"] is True
        assert result["can_apply"] is True

        # apply_patch
        result = apply_patch(str(file), empty_patch)
        assert result["success"] is True
        assert result["changes"]["hunks_applied"] == 0

        # revert_patch
        result = revert_patch(str(file), empty_patch)
        assert result["success"] is True


class TestAPICompleteness:
    """Test that all required fields are present in responses."""

    def test_generate_patch_complete_response(self, tmp_path):
        """generate_patch returns all required fields."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("old\n")
        file2.write_text("new\n")

        result = generate_patch(str(file1), str(file2))

        # Required fields
        assert "success" in result
        assert "original_file" in result
        assert "modified_file" in result
        assert "patch" in result
        assert "changes" in result
        assert "message" in result

        # Changes structure
        changes = result["changes"]
        assert "lines_added" in changes
        assert "lines_removed" in changes
        assert "hunks" in changes

    def test_inspect_patch_complete_response(self):
        """inspect_patch returns all required fields."""
        patch = """--- file.py
+++ file.py
@@ -1,1 +1,1 @@
-old
+new
"""

        result = inspect_patch(patch)

        # Required fields
        assert "success" in result
        assert "valid" in result
        assert "files" in result
        assert "summary" in result
        assert "message" in result

        # Summary structure
        summary = result["summary"]
        assert "total_files" in summary
        assert "total_hunks" in summary
        assert "total_lines_added" in summary
        assert "total_lines_removed" in summary

    def test_validate_patch_complete_response(self, tmp_path):
        """validate_patch returns all required fields."""
        file = tmp_path / "file.py"
        file.write_text("content\n")

        patch = """--- file.py
+++ file.py
@@ -1,1 +1,1 @@
-content
+modified
"""

        result = validate_patch(str(file), patch)

        # Required fields
        assert "success" in result
        assert "file_path" in result
        assert "valid" in result
        assert "can_apply" in result
        assert "preview" in result
        assert "message" in result

        # Preview structure
        preview = result["preview"]
        assert "lines_to_add" in preview
        assert "lines_to_remove" in preview
        assert "hunks" in preview
        assert "affected_line_range" in preview
