"""Integration tests for the 5 example workflows from the design document.

These tests verify the example workflows described in project_design.md
lines 2023-2149:
1. Safe Single Patch Application
2. Dry Run Test Before Apply
3. Batch Atomic Application
4. Inspect and Apply Multi-file Patch
5. Generate and Distribute Patch
"""

from patch_mcp.tools.apply import apply_patch
from patch_mcp.tools.backup import backup_file, restore_backup
from patch_mcp.tools.generate import generate_patch
from patch_mcp.tools.inspect import inspect_patch
from patch_mcp.tools.validate import validate_patch
from patch_mcp.workflows import apply_patches_atomic


class TestWorkflow1SafeSinglePatchApplication:
    """Test Workflow 1: Safe Single Patch Application (design doc lines 2025-2047)."""

    def test_workflow_1_success_path(self, tmp_path):
        """Test the complete safe patch workflow with success."""
        # Setup
        config_file = tmp_path / "config.py"
        config_file.write_text("DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n")

        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        # Step 1: Validate patch
        validation = validate_patch(str(config_file), patch)
        assert validation["success"] is True
        assert validation["can_apply"] is True

        # Step 2: Create backup
        backup = backup_file(str(config_file))
        assert backup["success"] is True
        backup["backup_file"]

        # Step 3: Apply patch
        result = apply_patch(str(config_file), patch)
        assert result["success"] is True

        # Verify changes
        content = config_file.read_text()
        assert "LOG_LEVEL = 'DEBUG'" in content

    def test_workflow_1_failure_path(self, tmp_path):
        """Test the safe patch workflow with failure and restore."""
        # Setup
        config_file = tmp_path / "config.py"
        config_file.write_text("DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n")

        # Bad patch (wrong context)
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'WRONG'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        # Step 1: Validate patch
        validation = validate_patch(str(config_file), patch)
        assert validation["success"] is False
        assert validation["can_apply"] is False

        # Workflow stops here - no backup or apply attempted
        # File remains unchanged
        content = config_file.read_text()
        assert "LOG_LEVEL = 'INFO'" in content

    def test_workflow_1_with_restore(self, tmp_path):
        """Test workflow with failed apply and restore."""
        # Setup
        config_file = tmp_path / "config.py"
        original_content = "DEBUG = False\nLOG_LEVEL = 'INFO'\nPORT = 8000\n"
        config_file.write_text(original_content)

        # Patch that validates but we'll simulate failure
        patch = """--- config.py
+++ config.py
@@ -1,3 +1,3 @@
 DEBUG = False
-LOG_LEVEL = 'INFO'
+LOG_LEVEL = 'DEBUG'
 PORT = 8000
"""

        # Create backup first
        backup = backup_file(str(config_file))
        backup_path = backup["backup_file"]

        # Apply succeeds in this case, but let's test restore mechanism
        result = apply_patch(str(config_file), patch)
        assert result["success"] is True

        # Simulate needing to restore (e.g., tests failed)
        restore_result = restore_backup(backup_path)
        assert restore_result["success"] is True

        # Verify restored to original
        assert config_file.read_text() == original_content


class TestWorkflow2DryRunTestBeforeApply:
    """Test Workflow 2: Dry Run Test Before Apply (design doc lines 2049-2068)."""

    def test_workflow_2_dry_run_then_apply(self, tmp_path):
        """Test dry run followed by real apply."""
        # Setup
        app_file = tmp_path / "app.py"
        app_file.write_text("def main():\n    print('Hello')\n")

        patch = """--- app.py
+++ app.py
@@ -1,2 +1,2 @@
 def main():
-    print('Hello')
+    print('Hello, World!')
"""

        # Step 1: Dry run test
        dry_result = apply_patch(str(app_file), patch, dry_run=True)
        assert dry_result["success"] is True
        assert dry_result["changes"]["lines_added"] == 1
        assert dry_result["changes"]["lines_removed"] == 1

        # Verify file NOT modified
        content = app_file.read_text()
        assert "print('Hello')" in content
        assert "World" not in content

        # Step 2: Create backup
        backup = backup_file(str(app_file))
        assert backup["success"] is True

        # Step 3: Apply for real
        real_result = apply_patch(str(app_file), patch)
        assert real_result["success"] is True

        # Verify file IS modified
        content = app_file.read_text()
        assert "print('Hello, World!')" in content

    def test_workflow_2_dry_run_failure(self, tmp_path):
        """Test dry run fails, no apply attempted."""
        # Setup
        app_file = tmp_path / "app.py"
        app_file.write_text("def main():\n    print('Hello')\n")

        # Bad patch - context doesn't match
        patch = """--- app.py
+++ app.py
@@ -1,2 +1,2 @@
-def wrong():
+def main():
     print('Hello')
"""

        # Step 1: Dry run test
        dry_result = apply_patch(str(app_file), patch, dry_run=True)
        assert dry_result["success"] is False

        # No backup or real apply attempted
        # File unchanged
        assert app_file.read_text() == "def main():\n    print('Hello')\n"


class TestWorkflow3BatchAtomicApplication:
    """Test Workflow 3: Batch Atomic Application (design doc lines 2070-2089)."""

    def test_workflow_3_atomic_success(self, tmp_path):
        """Test atomic batch application with all patches succeeding."""
        # Setup files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file3 = tmp_path / "file3.py"

        file1.write_text("# File 1\ndata = 1\n")
        file2.write_text("# File 2\ndata = 2\n")
        file3.write_text("# File 3\ndata = 3\n")

        # Create patches
        patch1 = """--- file1.py
+++ file1.py
@@ -1,2 +1,2 @@
 # File 1
-data = 1
+data = 10
"""

        patch2 = """--- file2.py
+++ file2.py
@@ -1,2 +1,2 @@
 # File 2
-data = 2
+data = 20
"""

        patch3 = """--- file3.py
+++ file3.py
@@ -1,2 +1,2 @@
 # File 3
-data = 3
+data = 30
"""

        # Use atomic pattern
        pairs = [
            (str(file1), patch1),
            (str(file2), patch2),
            (str(file3), patch3),
        ]

        result = apply_patches_atomic(pairs)

        # Verify success
        assert result["success"] is True
        assert result["applied"] == 3

        # Verify all files modified
        assert "data = 10" in file1.read_text()
        assert "data = 20" in file2.read_text()
        assert "data = 30" in file3.read_text()

    def test_workflow_3_atomic_failure_validation(self, tmp_path):
        """Test atomic batch with validation failure."""
        # Setup files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        file1.write_text("data = 1\n")
        file2.write_text("data = 2\n")

        # Good patch
        patch1 = """--- file1.py
+++ file1.py
@@ -1,1 +1,1 @@
-data = 1
+data = 10
"""

        # Bad patch (wrong context)
        patch2 = """--- file2.py
+++ file2.py
@@ -1,1 +1,1 @@
-data = 999
+data = 20
"""

        pairs = [(str(file1), patch1), (str(file2), patch2)]
        result = apply_patches_atomic(pairs)

        # Verify failure at validation phase
        assert result["success"] is False
        assert result["phase"] == "validation"

        # Verify NO files modified
        assert file1.read_text() == "data = 1\n"
        assert file2.read_text() == "data = 2\n"


class TestWorkflow4InspectAndApplyMultifilePatch:
    """Test Workflow 4: Inspect and Apply Multi-file Patch (design doc lines 2091-2119)."""

    def test_workflow_4_multifile_inspect_and_apply(self, tmp_path):
        """Test inspecting and applying a multi-file patch."""
        # Setup files
        config_file = tmp_path / "config.py"
        utils_file = tmp_path / "utils.py"

        config_file.write_text("DEBUG = False\n")
        utils_file.write_text("def helper():\n    pass\n")

        # Multi-file patch - note: this is not how multi-file patches work
        # In reality, you'd need to split the patch or use separate patches
        # For this test, we'll use separate patches for each file

        config_patch = """--- config.py
+++ config.py
@@ -1,1 +1,1 @@
-DEBUG = False
+DEBUG = True
"""

        utils_patch = """--- utils.py
+++ utils.py
@@ -1,2 +1,2 @@
 def helper():
-    pass
+    return True
"""

        # Combine for inspection
        combined_patch = config_patch + utils_patch

        # Step 1: Inspect the patch
        info = inspect_patch(combined_patch)

        assert info["success"] is True
        assert info["summary"]["total_files"] == 2
        assert len(info["files"]) == 2

        # Verify file information
        file_names = [f["source"] for f in info["files"]]
        assert "config.py" in file_names
        assert "utils.py" in file_names

        # Step 2: Validate and apply each file with its specific patch
        # For config.py
        validation = validate_patch(str(config_file), config_patch)
        assert validation["can_apply"] is True

        backup_file(str(config_file))
        result = apply_patch(str(config_file), config_patch)
        assert result["success"] is True

        # For utils.py
        validation = validate_patch(str(utils_file), utils_patch)
        assert validation["can_apply"] is True

        backup_file(str(utils_file))
        result = apply_patch(str(utils_file), utils_patch)
        assert result["success"] is True

        # Verify all files modified
        assert "DEBUG = True" in config_file.read_text()
        assert "return True" in utils_file.read_text()

    def test_workflow_4_inspect_shows_changes(self, tmp_path):
        """Test that inspect provides useful statistics."""
        # Create a patch with various changes
        patch = """--- file1.py
+++ file1.py
@@ -1,3 +1,4 @@
 line1
-line2
+line2_modified
 line3
+line4
--- file2.py
+++ file2.py
@@ -1,2 +1,1 @@
 start
-removed
"""

        info = inspect_patch(patch)

        assert info["success"] is True
        assert info["summary"]["total_files"] == 2
        assert info["summary"]["total_lines_added"] == 2
        assert info["summary"]["total_lines_removed"] == 2


class TestWorkflow5GenerateAndDistributePatch:
    """Test Workflow 5: Generate and Distribute Patch (design doc lines 2121-2149)."""

    def test_workflow_5_generate_and_apply(self, tmp_path):
        """Test generating a patch and applying it elsewhere."""
        # Step 1: Create old and new versions
        old_config = tmp_path / "config.py.old"
        new_config = tmp_path / "config.py.new"

        old_config.write_text("DEBUG = False\nLOG_LEVEL = 'INFO'\n")
        new_config.write_text("DEBUG = True\nLOG_LEVEL = 'DEBUG'\n")

        # Step 2: Generate patch from development changes
        dev_patch = generate_patch(str(old_config), str(new_config))
        assert dev_patch["success"] is True
        patch_content = dev_patch["patch"]

        # Verify patch has changes
        assert dev_patch["changes"]["lines_added"] == 2
        assert dev_patch["changes"]["lines_removed"] == 2

        # Step 3: Save patch (simulated - we just keep it in memory)
        # In real workflow: write_file("config_update.patch", patch_content)

        # Step 4: Apply to production
        production_config = tmp_path / "production_config.py"
        production_config.write_text("DEBUG = False\nLOG_LEVEL = 'INFO'\n")

        # Validate first
        validation = validate_patch(str(production_config), patch_content)
        assert validation["success"] is True
        assert validation["can_apply"] is True

        # Apply with backup
        backup_file(str(production_config))
        result = apply_patch(str(production_config), patch_content)
        assert result["success"] is True

        # Verify production updated
        prod_content = production_config.read_text()
        assert "DEBUG = True" in prod_content
        assert "LOG_LEVEL = 'DEBUG'" in prod_content

    def test_workflow_5_generate_no_changes(self, tmp_path):
        """Test generating patch when files are identical."""
        # Create identical files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        content = "same content\n"
        file1.write_text(content)
        file2.write_text(content)

        # Generate patch
        result = generate_patch(str(file1), str(file2))

        assert result["success"] is True
        assert result["changes"]["lines_added"] == 0
        assert result["changes"]["lines_removed"] == 0
        assert result["changes"]["hunks"] == 0

    def test_workflow_5_patch_distribution_failure(self, tmp_path):
        """Test patch distribution when production differs."""
        # Generate patch from dev
        old_dev = tmp_path / "dev_old.py"
        new_dev = tmp_path / "dev_new.py"

        old_dev.write_text("version = 1\n")
        new_dev.write_text("version = 2\n")

        dev_patch = generate_patch(str(old_dev), str(new_dev))
        patch_content = dev_patch["patch"]

        # Production has different content
        production = tmp_path / "production.py"
        production.write_text("version = 99\n")  # Different!

        # Validation should fail
        validation = validate_patch(str(production), patch_content)
        assert validation["success"] is False
        assert validation["can_apply"] is False

        # Patch is NOT applied
        assert production.read_text() == "version = 99\n"


class TestWorkflowCombinations:
    """Test combinations of workflows."""

    def test_combined_workflow_comprehensive(self, tmp_path):
        """Test a comprehensive workflow using multiple patterns."""
        # Setup
        app_file = tmp_path / "app.py"
        app_file.write_text("def main():\n    return 1\n")

        patch = """--- app.py
+++ app.py
@@ -1,2 +1,2 @@
 def main():
-    return 1
+    return 2
"""

        # Step 1: Inspect (if needed)
        info = inspect_patch(patch)
        assert info["success"] is True

        # Step 2: Dry run first
        dry_result = apply_patch(str(app_file), patch, dry_run=True)
        assert dry_result["success"] is True

        # Step 3: Validate
        validation = validate_patch(str(app_file), patch)
        assert validation["success"] is True

        # Step 4: Create backup
        backup = backup_file(str(app_file))
        assert backup["success"] is True

        # Step 5: Apply
        result = apply_patch(str(app_file), patch)
        assert result["success"] is True

        # Verify
        assert "return 2" in app_file.read_text()

    def test_workflow_error_recovery_pattern(self, tmp_path):
        """Test using workflow patterns for error recovery."""
        from patch_mcp.workflows import apply_patch_with_backup

        # Setup
        critical_file = tmp_path / "critical.py"
        critical_file.write_text("important = True\n")

        # Good patch
        patch = """--- critical.py
+++ critical.py
@@ -1,1 +1,2 @@
 important = True
+verified = True
"""

        # Use backup-restore pattern
        result = apply_patch_with_backup(str(critical_file), patch, keep_backup=True)

        assert result["success"] is True
        assert result["backup_file"] is not None

        # Verify we can restore if needed
        backup_path = result["backup_file"]
        restore_result = restore_backup(backup_path)
        assert restore_result["success"] is True

        # Verify restored
        assert critical_file.read_text() == "important = True\n"
