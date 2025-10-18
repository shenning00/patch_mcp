"""Tests for backup and restore tools.

This module tests the backup_file and restore_backup functions, including:
- Basic backup creation and restoration
- Filename parsing and auto-detection
- Edge cases and error handling
- Integration workflows
"""

import os
import re
import time
from pathlib import Path

from patch_mcp.tools.backup import backup_file, parse_backup_filename, restore_backup


class TestBackupFile:
    """Test backup_file function."""

    def test_backup_creates_file(self, tmp_path):
        """Backup creates a file with correct naming format."""
        # Create original file
        original = tmp_path / "test.py"
        original.write_text("def hello():\n    print('world')\n")

        # Create backup
        result = backup_file(str(original))

        # Verify success
        assert result["success"] is True
        assert "backup_file" in result
        assert "backup_size" in result
        assert result["message"] == "Backup created successfully"

        # Verify backup file exists
        backup_path = Path(result["backup_file"])
        assert backup_path.exists()
        assert backup_path.is_file()

        # Verify content is preserved
        assert backup_path.read_text() == original.read_text()

    def test_backup_naming_format(self, tmp_path):
        """Backup filename follows exact format: file.backup.YYYYMMDD_HHMMSS."""
        original = tmp_path / "config.py"
        original.write_text("DEBUG = True\n")

        result = backup_file(str(original))

        assert result["success"] is True
        backup_file_name = Path(result["backup_file"]).name

        # Check format: config.py.backup.20250117_143052
        pattern = r"^config\.py\.backup\.\d{8}_\d{6}$"
        assert re.match(
            pattern, backup_file_name
        ), f"Backup name '{backup_file_name}' doesn't match pattern"

        # Verify timestamp is recent (within last minute)
        timestamp_part = backup_file_name.split(".backup.")[1]
        from datetime import datetime

        backup_time = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
        now = datetime.now()
        time_diff = (now - backup_time).total_seconds()
        assert time_diff < 60, "Backup timestamp is not recent"

    def test_backup_preserves_content(self, tmp_path):
        """Backup preserves exact file content including whitespace."""
        original = tmp_path / "data.txt"
        content = "Line 1\n\nLine 3 with spaces   \n\tTabbed line\n"
        original.write_text(content)

        result = backup_file(str(original))
        assert result["success"] is True

        backup_path = Path(result["backup_file"])
        assert backup_path.read_text() == content

    def test_backup_preserves_metadata(self, tmp_path):
        """Backup preserves file permissions and timestamps."""
        original = tmp_path / "script.sh"
        original.write_text("#!/bin/bash\necho 'test'\n")

        # Set specific permissions
        original.chmod(0o755)
        original_stat = original.stat()

        result = backup_file(str(original))
        assert result["success"] is True

        backup_path = Path(result["backup_file"])
        backup_stat = backup_path.stat()

        # Check permissions preserved (on Unix systems)
        if os.name != "nt":  # Skip on Windows
            assert backup_stat.st_mode == original_stat.st_mode

        # Check modification time preserved (with small tolerance)
        assert abs(backup_stat.st_mtime - original_stat.st_mtime) < 1

    def test_backup_returns_correct_size(self, tmp_path):
        """Backup returns correct file size."""
        original = tmp_path / "data.bin"
        content = b"x" * 1024  # 1KB
        original.write_bytes(content)

        result = backup_file(str(original))
        assert result["success"] is True
        assert result["backup_size"] == 1024

    def test_backup_file_not_found(self, tmp_path):
        """Backup fails if original file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.txt"

        result = backup_file(str(nonexistent))

        assert result["success"] is False
        assert result["error_type"] == "file_not_found"
        assert "not found" in result["error"].lower()

    def test_backup_symlink_rejected(self, tmp_path):
        """Backup rejects symlinks (security policy)."""
        # Create target file
        target = tmp_path / "target.txt"
        target.write_text("target content")

        # Create symlink
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        result = backup_file(str(link))

        assert result["success"] is False
        assert result["error_type"] == "symlink_error"
        assert "symlink" in result["error"].lower()

    def test_backup_binary_file_rejected(self, tmp_path):
        """Backup rejects binary files."""
        binary = tmp_path / "binary.dat"
        binary.write_bytes(b"\x00\x01\x02\x03" * 100)

        result = backup_file(str(binary))

        assert result["success"] is False
        assert result["error_type"] == "binary_file"
        assert "binary" in result["error"].lower()

    def test_backup_no_write_permission(self, tmp_path):
        """Backup fails if no write permission in directory."""
        # Create file in a subdirectory
        subdir = tmp_path / "readonly"
        subdir.mkdir()
        original = subdir / "file.txt"
        original.write_text("content")

        # Make directory read-only (Unix only)
        if os.name != "nt":
            subdir.chmod(0o555)

            result = backup_file(str(original))

            assert result["success"] is False
            assert result["error_type"] == "permission_denied"
            assert "permission" in result["error"].lower()

            # Restore permissions for cleanup
            subdir.chmod(0o755)

    def test_backup_large_file(self, tmp_path):
        """Backup works with large files (< 10MB limit)."""
        original = tmp_path / "large.txt"
        # Create 5MB file
        content = "x" * (5 * 1024 * 1024)
        original.write_text(content)

        result = backup_file(str(original))

        assert result["success"] is True
        assert result["backup_size"] == 5 * 1024 * 1024

    def test_backup_multiple_backups_different_timestamps(self, tmp_path):
        """Multiple backups of same file have different timestamps."""
        original = tmp_path / "test.py"
        original.write_text("version 1")

        # Create first backup
        result1 = backup_file(str(original))
        assert result1["success"] is True

        # Wait briefly to ensure different timestamp
        time.sleep(1.1)

        # Modify file
        original.write_text("version 2")

        # Create second backup
        result2 = backup_file(str(original))
        assert result2["success"] is True

        # Verify different backup files
        assert result1["backup_file"] != result2["backup_file"]

        # Verify both exist
        assert Path(result1["backup_file"]).exists()
        assert Path(result2["backup_file"]).exists()

        # Verify different content
        assert Path(result1["backup_file"]).read_text() == "version 1"
        assert Path(result2["backup_file"]).read_text() == "version 2"


class TestParseBackupFilename:
    """Test parse_backup_filename function."""

    def test_parse_simple_filename(self):
        """Parse simple backup filename."""
        result = parse_backup_filename("file.py.backup.20250117_143052")
        assert result == "file.py"

    def test_parse_filename_with_path(self):
        """Parse backup filename with directory path."""
        backup_path = str(Path("/path/to/file.py.backup.20250117_143052"))
        expected = str(Path("/path/to/file.py"))
        result = parse_backup_filename(backup_path)
        assert result == expected

    def test_parse_filename_with_dots(self):
        """Parse backup filename where original has dots."""
        result = parse_backup_filename("my.config.yaml.backup.20250117_143052")
        assert result == "my.config.yaml"

    def test_parse_invalid_filename(self):
        """Parse returns None for invalid backup filename."""
        assert parse_backup_filename("invalid.txt") is None
        assert parse_backup_filename("file.backup") is None
        assert parse_backup_filename("file.backup.123") is None
        assert parse_backup_filename("file.backup.20250117") is None

    def test_parse_filename_preserves_relative_path(self):
        """Parse preserves relative path structure."""
        backup_path = str(Path("./subdir/file.txt.backup.20250117_143052"))
        expected = str(Path("subdir/file.txt"))
        result = parse_backup_filename(backup_path)
        # Path normalization removes leading ./
        assert result == expected


class TestRestoreBackup:
    """Test restore_backup function."""

    def test_restore_success(self, tmp_path):
        """Restore successfully restores backup to original location."""
        # Create and backup file
        original = tmp_path / "test.py"
        original.write_text("original content")
        backup_result = backup_file(str(original))
        assert backup_result["success"] is True

        # Modify original
        original.write_text("modified content")

        # Restore from backup
        restore_result = restore_backup(backup_result["backup_file"])

        assert restore_result["success"] is True
        assert "restored_to" in restore_result
        assert "restored_size" in restore_result
        assert "Successfully restored" in restore_result["message"]

        # Verify content restored
        assert original.read_text() == "original content"

    def test_restore_auto_detect_target(self, tmp_path):
        """Restore auto-detects target from backup filename."""
        original = tmp_path / "config.yaml"
        original.write_text("version: 1")

        backup_result = backup_file(str(original))
        backup_file_path = backup_result["backup_file"]

        # Delete original
        original.unlink()

        # Restore without specifying target
        restore_result = restore_backup(backup_file_path)

        assert restore_result["success"] is True
        assert original.exists()
        assert original.read_text() == "version: 1"

    def test_restore_to_different_location(self, tmp_path):
        """Restore to explicit target location."""
        original = tmp_path / "source.txt"
        original.write_text("source content")

        backup_result = backup_file(str(original))

        # Restore to different location
        target = tmp_path / "restored.txt"
        restore_result = restore_backup(backup_result["backup_file"], target_file=str(target))

        assert restore_result["success"] is True
        assert target.exists()
        assert target.read_text() == "source content"
        assert original.exists()  # Original unchanged

    def test_restore_force_overwrite(self, tmp_path):
        """Restore with force=True overwrites modified target."""
        original = tmp_path / "test.txt"
        original.write_text("original")

        backup_result = backup_file(str(original))

        # Wait and modify original (to be newer than backup)
        time.sleep(0.1)
        original.write_text("modified")

        # Restore with force
        restore_result = restore_backup(backup_result["backup_file"], force=True)

        assert restore_result["success"] is True
        assert original.read_text() == "original"

    def test_restore_warns_if_target_modified(self, tmp_path):
        """Restore warns if target was modified since backup."""
        original = tmp_path / "test.txt"
        original.write_text("original")

        backup_result = backup_file(str(original))

        # Wait and modify original (to be newer than backup)
        time.sleep(0.1)
        original.write_text("modified")

        # Restore without force
        restore_result = restore_backup(backup_result["backup_file"], force=False)

        assert restore_result["success"] is True
        assert "warning" in restore_result["message"].lower()
        assert original.read_text() == "original"  # Still restored

    def test_restore_backup_not_found(self, tmp_path):
        """Restore fails if backup file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.backup.20250117_143052"

        result = restore_backup(str(nonexistent))

        assert result["success"] is False
        assert result["error_type"] == "file_not_found"
        assert "not found" in result["error"].lower()

    def test_restore_invalid_backup_name(self, tmp_path):
        """Restore fails if backup filename format is invalid."""
        invalid = tmp_path / "invalid.txt"
        invalid.write_text("content")

        result = restore_backup(str(invalid))

        assert result["success"] is False
        assert result["error_type"] == "io_error"
        assert "cannot parse" in result["error"].lower()

    def test_restore_target_is_symlink(self, tmp_path):
        """Restore rejects symlink targets (security policy)."""
        # Create backup
        original = tmp_path / "original.txt"
        original.write_text("content")
        backup_result = backup_file(str(original))

        # Create symlink as target
        target_file = tmp_path / "target.txt"
        target_file.write_text("target")
        link = tmp_path / "link.txt"
        link.symlink_to(target_file)

        result = restore_backup(backup_result["backup_file"], target_file=str(link))

        assert result["success"] is False
        assert result["error_type"] == "symlink_error"
        assert "symlink" in result["error"].lower()

    def test_restore_creates_parent_directory(self, tmp_path):
        """Restore creates parent directory if it doesn't exist."""
        original = tmp_path / "test.txt"
        original.write_text("content")

        backup_result = backup_file(str(original))

        # Restore to path with non-existent parent
        new_location = tmp_path / "new" / "subdir" / "restored.txt"
        restore_result = restore_backup(backup_result["backup_file"], target_file=str(new_location))

        assert restore_result["success"] is True
        assert new_location.exists()
        assert new_location.parent.exists()
        assert new_location.read_text() == "content"

    def test_restore_no_write_permission(self, tmp_path):
        """Restore fails if no write permission to target."""
        original = tmp_path / "test.txt"
        original.write_text("content")

        backup_result = backup_file(str(original))

        # Make file read-only (Unix only)
        if os.name != "nt":
            original.chmod(0o444)

            result = restore_backup(backup_result["backup_file"])

            assert result["success"] is False
            assert result["error_type"] == "permission_denied"
            assert "permission" in result["error"].lower() or "writable" in result["error"].lower()

            # Restore permissions for cleanup
            original.chmod(0o644)

    def test_restore_preserves_metadata(self, tmp_path):
        """Restore preserves metadata from backup."""
        original = tmp_path / "script.sh"
        original.write_text("#!/bin/bash\necho test\n")
        original.chmod(0o755)

        backup_result = backup_file(str(original))
        backup_path = Path(backup_result["backup_file"])
        backup_stat = backup_path.stat()

        # Modify and restore
        original.write_text("modified")
        restore_backup(backup_result["backup_file"])

        restored_stat = original.stat()

        # Check metadata preserved (on Unix systems)
        if os.name != "nt":
            assert restored_stat.st_mode == backup_stat.st_mode


class TestBackupRestoreIntegration:
    """Integration tests for backup and restore workflows."""

    def test_backup_modify_restore_workflow(self, tmp_path):
        """Complete workflow: backup -> modify -> restore."""
        # Step 1: Create file with original content
        file = tmp_path / "config.py"
        original_content = "DEBUG = False\nPORT = 8000\n"
        file.write_text(original_content)

        # Step 2: Create backup
        backup_result = backup_file(str(file))
        assert backup_result["success"] is True
        backup_path = backup_result["backup_file"]

        # Step 3: Modify file
        modified_content = "DEBUG = True\nPORT = 9000\n"
        file.write_text(modified_content)
        assert file.read_text() == modified_content

        # Step 4: Restore from backup
        restore_result = restore_backup(backup_path)
        assert restore_result["success"] is True

        # Step 5: Verify original content restored
        assert file.read_text() == original_content

    def test_multiple_backups_different_timestamps(self, tmp_path):
        """Multiple backups with different timestamps."""
        file = tmp_path / "data.txt"

        # Version 1
        file.write_text("version 1")
        backup1 = backup_file(str(file))
        assert backup1["success"] is True

        time.sleep(1.1)

        # Version 2
        file.write_text("version 2")
        backup2 = backup_file(str(file))
        assert backup2["success"] is True

        time.sleep(1.1)

        # Version 3
        file.write_text("version 3")
        backup3 = backup_file(str(file))
        assert backup3["success"] is True

        # Verify all backups exist
        assert Path(backup1["backup_file"]).exists()
        assert Path(backup2["backup_file"]).exists()
        assert Path(backup3["backup_file"]).exists()

        # Restore from version 1
        restore_backup(backup1["backup_file"])
        assert file.read_text() == "version 1"

        # Restore from version 2
        restore_backup(backup2["backup_file"])
        assert file.read_text() == "version 2"

        # Restore from version 3
        restore_backup(backup3["backup_file"])
        assert file.read_text() == "version 3"

    def test_backup_before_risky_operation(self, tmp_path):
        """Backup before risky operation with rollback on failure."""
        file = tmp_path / "important.py"
        safe_content = "def safe_function():\n    return True\n"
        file.write_text(safe_content)

        # Create backup before risky operation
        backup_result = backup_file(str(file))
        assert backup_result["success"] is True

        try:
            # Simulate risky operation that fails
            risky_content = "def risky_function():\n    raise Exception('fail')\n"
            file.write_text(risky_content)

            # Simulate operation failure
            raise Exception("Operation failed")

        except Exception:
            # Restore from backup on failure
            restore_result = restore_backup(backup_result["backup_file"])
            assert restore_result["success"] is True

        # Verify safe content restored
        assert file.read_text() == safe_content

    def test_backup_restore_chain(self, tmp_path):
        """Chain of backup and restore operations with versioning."""
        file = tmp_path / "test.txt"

        # Create version 1 and backup
        file.write_text("v1")
        time.sleep(1.1)  # Need >1 second for timestamp to differ
        backup1 = backup_file(str(file))
        assert backup1["success"] is True

        # Create version 2 and backup
        file.write_text("v2")
        time.sleep(1.1)  # Need >1 second for timestamp to differ
        backup2 = backup_file(str(file))
        assert backup2["success"] is True

        # Create version 3 and backup
        file.write_text("v3")
        time.sleep(1.1)  # Need >1 second for timestamp to differ
        backup3 = backup_file(str(file))
        assert backup3["success"] is True

        # Verify all backups have different filenames
        assert backup1["backup_file"] != backup2["backup_file"]
        assert backup2["backup_file"] != backup3["backup_file"]
        assert backup1["backup_file"] != backup3["backup_file"]

        # File now contains v3
        assert file.read_text() == "v3"

        # Restore to v1
        restore_backup(backup1["backup_file"])
        assert file.read_text() == "v1"

        # Restore to v2
        restore_backup(backup2["backup_file"])
        assert file.read_text() == "v2"

        # Restore to v3
        restore_backup(backup3["backup_file"])
        assert file.read_text() == "v3"

    def test_restore_to_multiple_locations(self, tmp_path):
        """Restore same backup to multiple locations."""
        original = tmp_path / "template.txt"
        content = "template content"
        original.write_text(content)

        backup_result = backup_file(str(original))
        backup_path = backup_result["backup_file"]

        # Restore to multiple locations
        locations = [tmp_path / f"copy{i}.txt" for i in range(3)]

        for location in locations:
            result = restore_backup(backup_path, target_file=str(location))
            assert result["success"] is True
            assert location.exists()
            assert location.read_text() == content

        # Verify all copies exist
        assert all(loc.exists() for loc in locations)


# ============================================================================
# Error Path Coverage Tests
# ============================================================================


class TestBackupErrorPaths:
    """Tests for uncovered error paths in backup.py to improve coverage."""

    def test_backup_disk_space_check_exception(self, tmp_path, monkeypatch):
        """Test exception during disk space check."""
        original = tmp_path / "test.txt"
        original.write_text("content\n")

        # Mock shutil.disk_usage to raise exception
        import shutil
        def mock_disk_usage(path):
            raise OSError("Cannot check disk space")

        monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

        result = backup_file(str(original))

        # Should fail with io_error
        assert result["success"] is False
        assert result["error_type"] == "io_error"
        assert "disk space" in result["error"].lower()

    def test_backup_insufficient_disk_space_minimum(self, tmp_path, monkeypatch):
        """Test insufficient disk space (below 100MB minimum)."""
        original = tmp_path / "test.txt"
        original.write_text("content\n")

        # Mock disk_usage to return insufficient space
        import shutil
        from collections import namedtuple
        DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])

        def mock_disk_usage(path):
            # Return 50MB free (below 100MB minimum)
            return DiskUsage(total=1000000000, used=950000000, free=50000000)

        monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

        result = backup_file(str(original))

        # Should fail with disk_space_error
        assert result["success"] is False
        assert result["error_type"] == "disk_space_error"
        assert "insufficient" in result["error"].lower()

    def test_backup_insufficient_disk_space_safety_margin(self, tmp_path, monkeypatch):
        """Test insufficient disk space for 110% safety margin."""
        original = tmp_path / "large.txt"
        # Create 1MB file
        content = "x" * (1024 * 1024)
        original.write_text(content)

        # Mock disk_usage to return space > 100MB but < 110% of file size
        import shutil
        from collections import namedtuple
        DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])

        def mock_disk_usage(path):
            # Return 101MB free (above minimum but below 110% of 1MB file)
            # Actually we need less than 1.1MB for a 1MB file
            return DiskUsage(total=1000000000, used=999000000, free=1000000)

        monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

        result = backup_file(str(original))

        # Should fail with disk_space_error
        assert result["success"] is False
        assert result["error_type"] == "disk_space_error"
        assert "safety margin" in result["error"].lower() or "insufficient" in result["error"].lower()

    def test_backup_oserror_disk_full(self, tmp_path, monkeypatch):
        """Test OSError with 'no space' message during backup."""
        original = tmp_path / "test.txt"
        original.write_text("content\n")

        # Mock shutil.copy2 to raise OSError with disk full message
        import shutil
        original_copy2 = shutil.copy2

        def mock_copy2(src, dst):
            raise OSError("No space left on device")

        monkeypatch.setattr(shutil, "copy2", mock_copy2)

        result = backup_file(str(original))

        # Should catch OSError and return disk_space_error
        assert result["success"] is False
        assert result["error_type"] == "disk_space_error"
        assert "disk" in result["error"].lower()

    def test_backup_oserror_generic(self, tmp_path, monkeypatch):
        """Test generic OSError during backup."""
        original = tmp_path / "test.txt"
        original.write_text("content\n")

        # Mock shutil.copy2 to raise generic OSError
        import shutil

        def mock_copy2(src, dst):
            raise OSError("Generic I/O error")

        monkeypatch.setattr(shutil, "copy2", mock_copy2)

        result = backup_file(str(original))

        # Should catch OSError and return io_error
        assert result["success"] is False
        assert result["error_type"] == "io_error"
        assert "I/O error" in result["error"]

    def test_backup_unexpected_exception(self, tmp_path, monkeypatch):
        """Test unexpected exception during backup."""
        original = tmp_path / "test.txt"
        original.write_text("content\n")

        # Mock shutil.copy2 to raise unexpected exception
        import shutil

        def mock_copy2(src, dst):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(shutil, "copy2", mock_copy2)

        result = backup_file(str(original))

        # Should catch exception and return io_error
        assert result["success"] is False
        assert result["error_type"] == "io_error"
        assert "unexpected" in result["error"].lower()

    def test_restore_backup_cleanup_failure(self, tmp_path, monkeypatch):
        """Test restore when backup cleanup fails."""
        original = tmp_path / "test.txt"
        original.write_text("original\n")

        backup_result = backup_file(str(original))
        assert backup_result["success"] is True

        # Modify original
        original.write_text("modified\n")

        # Mock Path.unlink to raise exception (cleanup failure)
        from pathlib import Path
        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if "backup" in str(self):
                raise OSError("Cannot delete backup")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        result = restore_backup(backup_result["backup_file"])

        # Should succeed despite cleanup failure
        assert result["success"] is True
        assert "restored" in result["message"].lower()
        # Verify content was restored
        assert original.read_text() == "original\n"
