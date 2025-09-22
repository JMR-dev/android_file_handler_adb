"""Tests for core ADB manager functionality."""

import pytest
import unittest.mock as mock
import sys
from unittest.mock import MagicMock, patch, mock_open

from src.core.adb_manager import (
    ADBManager,
    get_executable_directory,
    is_adb_available,
    get_platform_type,
    ensure_platform_tools_in_user_dir
)


class TestADBManagerUtilityFunctions:
    """Test utility functions in adb_manager module."""
    
    def test_get_executable_directory_frozen(self):
        """Test get_executable_directory when running as frozen executable."""
        with patch.object(sys, 'frozen', True, create=True):
            with patch('sys.executable', '/path/to/executable'):
                result = get_executable_directory()
                assert result == '/path/to'
    
    def test_get_executable_directory_script(self):
        """Test get_executable_directory when running as script."""
        with patch.object(sys, 'frozen', False, create=True):
            with patch('os.path.abspath') as mock_abspath:
                with patch('os.path.dirname') as mock_dirname:
                    mock_abspath.return_value = '/path/to/script.py'
                    mock_dirname.return_value = '/path/to'
                    result = get_executable_directory()
                    assert result == '/path/to'
    
    def test_get_platform_type(self):
        """Test platform type detection."""
        # Test current platform (should be linux based on test output)
        result = get_platform_type()
        assert result in ['linux', 'windows', 'darwin']
        
        # Test mocked platforms by patching the OS_TYPE variable
        with patch('src.core.adb_manager.OS_TYPE', 'win32'):
            result = get_platform_type()
            assert result == 'win32'
        
        with patch('src.core.adb_manager.OS_TYPE', 'darwin'):
            result = get_platform_type()
            assert result == 'darwin'
    
    @patch('src.core.adb_manager.ensure_platform_tools_in_user_dir')
    @patch('os.path.isfile')
    def test_is_adb_available_system_path(self, mock_isfile, mock_ensure):
        """Test ADB availability check when ADB binary is found."""
        # Mock ensure_platform_tools_in_user_dir to return a path
        mock_ensure.return_value = '/path/to/adb'
        mock_isfile.return_value = True  # File exists
        
        result = is_adb_available()
        assert result is True
        mock_ensure.assert_called_once()
        # isfile might be called multiple times (once inside ensure_platform_tools_in_user_dir)
        assert mock_isfile.called
        mock_isfile.assert_any_call('/path/to/adb')
    
    @patch('shutil.which')
    @patch('os.path.isfile')
    def test_is_adb_available_platform_tools(self, mock_isfile, mock_which):
        """Test ADB availability check from platform-tools directory."""
        mock_which.return_value = None  # Not in PATH
        mock_isfile.return_value = True  # But exists in platform-tools
        assert is_adb_available() is True
    
    @patch('shutil.which')
    @patch('os.path.isfile')
    def test_is_adb_available_not_found(self, mock_isfile, mock_which):
        """Test ADB availability check when ADB is not found."""
        mock_which.return_value = None
        mock_isfile.return_value = False
        assert is_adb_available() is False


class TestADBManager:
    """Test ADBManager class functionality."""
    
    @pytest.fixture
    def adb_manager(self):
        """Create an ADBManager instance for testing."""
        with patch('src.core.adb_manager.is_adb_available', return_value=True):
            return ADBManager()
    
    def test_init(self, adb_manager):
        """Test ADBManager initialization."""
        assert adb_manager.progress_callback is None
        assert adb_manager.status_callback is None
        assert adb_manager.current_process is None
        assert adb_manager.deduplicator is not None
        assert 'current_file' in adb_manager.transfer_progress
        assert 'total_files' in adb_manager.transfer_progress
    
    def test_set_progress_callback(self, adb_manager):
        """Test setting progress callback."""
        callback = MagicMock()
        adb_manager.set_progress_callback(callback)
        assert adb_manager.progress_callback == callback
    
    def test_set_status_callback(self, adb_manager):
        """Test setting status callback."""
        callback = MagicMock()
        adb_manager.set_status_callback(callback)
        assert adb_manager.status_callback == callback
    
    def test_update_progress(self, adb_manager):
        """Test progress update with callback."""
        callback = MagicMock()
        adb_manager.set_progress_callback(callback)
        adb_manager._update_progress(50)
        callback.assert_called_once_with(50)
    
    def test_update_progress_no_callback(self, adb_manager):
        """Test progress update without callback."""
        # Should not raise an exception
        adb_manager._update_progress(50)
    
    def test_update_status(self, adb_manager):
        """Test status update with callback."""
        callback = MagicMock()
        adb_manager.set_status_callback(callback)
        adb_manager._update_status("Test status")
        callback.assert_called_once_with("Test status")
    
    def test_update_status_no_callback(self, adb_manager):
        """Test status update without callback."""
        # Should not raise an exception
        adb_manager._update_status("Test status")
    
    def test_update_transfer_progress(self, adb_manager):
        """Test transfer progress calculation."""
        status_callback = MagicMock()
        adb_manager.set_status_callback(status_callback)
        
        adb_manager._update_transfer_progress(3, 10)
        
        # Should update internal progress tracking
        assert adb_manager.transfer_progress['current_file'] == 3
        assert adb_manager.transfer_progress['total_files'] == 10
        
        # Should call status callback with special format
        status_callback.assert_called_once_with("TRANSFER_PROGRESS:3:10")
    
    def test_reset_transfer_progress(self, adb_manager):
        """Test transfer progress reset."""
        # Set some progress values
        adb_manager.transfer_progress['current_file'] = 5
        adb_manager.transfer_progress['total_files'] = 10
        adb_manager.transfer_progress['files_to_transfer'] = 10
        
        adb_manager._reset_transfer_progress()
        
        assert adb_manager.transfer_progress['current_file'] == 0
        assert adb_manager.transfer_progress['total_files'] == 0
        assert adb_manager.transfer_progress['files_to_transfer'] == 0
    
    @patch('shutil.disk_usage')
    @patch('src.core.adb_manager.get_platform_tools_directory')
    def test_check_local_disk_space_sufficient(self, mock_get_dir, mock_disk_usage, adb_manager):
        """Test disk space check with sufficient space."""
        mock_get_dir.return_value = '/fake/path'
        mock_disk_usage.return_value = (1000*1024*1024, 500*1024*1024, 200*1024*1024)  # total, used, free (200MB)
        assert adb_manager.check_local_disk_space() is True
    
    @patch('shutil.disk_usage')
    @patch('src.core.adb_manager.get_platform_tools_directory')
    def test_check_local_disk_space_insufficient(self, mock_get_dir, mock_disk_usage, adb_manager):
        """Test disk space check with insufficient space."""
        mock_get_dir.return_value = '/fake/path'
        mock_disk_usage.return_value = (1000*1024*1024, 980*1024*1024, 20*1024*1024)  # total, used, free (20MB < 50MB)
        
        with pytest.raises(Exception, match="Insufficient disk space"):
            adb_manager.check_local_disk_space()
    
    @patch('src.core.adb_manager.get_adb_binary_path')
    @patch('subprocess.run')
    def test_run_adb_command_success(self, mock_run, mock_get_path, adb_manager):
        """Test successful ADB command execution."""
        mock_get_path.return_value = '/fake/adb'
        mock_result = MagicMock()
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        stdout, stderr, returncode = adb_manager.run_adb_command(['devices'])
        
        assert returncode == 0
        assert stdout == "success output"
        assert stderr == ""
    
    @patch('src.core.adb_manager.get_adb_binary_path')
    @patch('subprocess.run')
    def test_run_adb_command_failure(self, mock_run, mock_get_path, adb_manager):
        """Test failed ADB command execution."""
        mock_get_path.return_value = '/fake/adb'
        mock_run.side_effect = Exception("Command failed")
        
        stdout, stderr, returncode = adb_manager.run_adb_command(['devices'])
        
        assert stdout is None
        assert "Command failed" in stderr
        assert returncode == -1
    
    @patch('src.core.adb_manager.ADBManager.run_adb_command')
    def test_check_device_connected(self, mock_run_command, adb_manager):
        """Test device detection when device is connected."""
        mock_run_command.return_value = ("ABC123\tdevice\n", "", 0)
        
        device_id = adb_manager.check_device()
        
        assert device_id == "ABC123"
        mock_run_command.assert_called_once_with(['devices'], capture_output=True)
    
    @patch('src.core.adb_manager.ADBManager.run_adb_command')
    def test_check_device_not_connected(self, mock_run_command, adb_manager):
        """Test device detection when no device is connected."""
        mock_run_command.return_value = ("List of devices attached\n\n", "", 0)
        
        device_id = adb_manager.check_device()
        
        assert device_id is None
    
    def test_parse_progress_valid(self, adb_manager):
        """Test progress parsing with valid input."""
        test_line = "/sdcard/test.txt: (100%)"
        result = adb_manager.parse_progress(test_line)
        assert result == 100
        
        test_line = "/sdcard/folder/file.jpg: (45%)"
        result = adb_manager.parse_progress(test_line)
        assert result == 45
        
        # Test other patterns
        test_line = "75% complete"
        result = adb_manager.parse_progress(test_line)
        assert result == 75
        
        test_line = "transferred 50%"
        result = adb_manager.parse_progress(test_line)
        assert result == 50
    
    def test_parse_progress_invalid(self, adb_manager):
        """Test progress parsing with invalid input."""
        test_line = "Some random text"
        result = adb_manager.parse_progress(test_line)
        assert result is None
        
        test_line = "[ 50%] invalid format"
        result = adb_manager.parse_progress(test_line)
        assert result is None
    
    def test_cancel_transfer(self, adb_manager):
        """Test transfer cancellation."""
        # Set up a mock process
        mock_process = MagicMock()
        adb_manager.current_process = mock_process
        
        result = adb_manager.cancel_transfer()
        
        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()
        assert adb_manager.current_process is None


class TestEnsurePlatformToolsInUserDir:
    """Test the ensure_platform_tools_in_user_dir function."""
    
    @patch('src.core.adb_manager.get_platform_type')
    @patch('requests.get')
    @patch('tempfile.mkdtemp')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.move')
    @patch('os.symlink')
    @patch('os.path.islink')
    @patch('os.unlink')
    def test_ensure_platform_tools_download_success(
        self, mock_unlink, mock_islink, mock_symlink, mock_move, 
        mock_makedirs, mock_exists, mock_mkdtemp, mock_get, mock_platform_type
    ):
        """Test successful platform tools download and installation."""
        # Setup mocks
        mock_platform_type.return_value = 'linux'
        mock_exists.return_value = False
        mock_mkdtemp.return_value = '/tmp/test'
        mock_islink.return_value = False
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake zip content'
        mock_get.return_value = mock_response
        
        # Mock zipfile extraction
        with patch('zipfile.ZipFile') as mock_zip:
            mock_zip_instance = MagicMock()
            mock_zip.return_value.__enter__.return_value = mock_zip_instance
            
            # Mock file operations
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('os.listdir') as mock_listdir:
                    mock_listdir.return_value = ['platform-tools']  # Simulate extracted folder
                    with patch('os.path.isdir') as mock_isdir:
                        # Return True for the candidate directory check
                        mock_isdir.return_value = True
                        with patch('os.path.expanduser') as mock_expanduser:
                            mock_expanduser.return_value = '/home/user/.local/share/android-file-handler'
                    
                            
                            result = ensure_platform_tools_in_user_dir()
                            
                            # Verify the result is a path to adb
                            assert 'adb' in result
                            
                            # Verify download was attempted
                            mock_get.assert_called_once()
                            
                            # Verify extraction was attempted
                            mock_zip_instance.extractall.assert_called_once()
if __name__ == '__main__':
    pytest.main([__file__])