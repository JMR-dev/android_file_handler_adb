"""Tests for device manager functionality."""

import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch, call

from src.managers.device_manager import DeviceManager


class TestDeviceManager:
    """Test DeviceManager class functionality."""
    
    @pytest.fixture
    def mock_parent_window(self):
        """Create a mock parent window for testing."""
        return MagicMock(spec=tk.Tk)
    
    @pytest.fixture
    def mock_status_callback(self):
        """Create a mock status callback for testing."""
        return MagicMock()
    
    @pytest.fixture
    def device_manager(self, mock_parent_window, mock_status_callback):
        """Create a DeviceManager instance for testing."""
        with patch('src.managers.device_manager.ADBManager') as mock_adb:
            manager = DeviceManager(mock_parent_window, mock_status_callback)
            manager.adb_manager = mock_adb.return_value
            return manager
    
    def test_init(self, mock_parent_window, mock_status_callback):
        """Test DeviceManager initialization."""
        with patch('src.managers.device_manager.ADBManager') as mock_adb_class:
            mock_adb_instance = MagicMock()
            mock_adb_class.return_value = mock_adb_instance
            
            device_manager = DeviceManager(mock_parent_window, mock_status_callback)
            
            assert device_manager.parent == mock_parent_window
            assert device_manager.status_callback == mock_status_callback
            assert device_manager.device_connected is False
            
            # Verify ADB callbacks are set
            mock_adb_instance.set_status_callback.assert_called_once()
            mock_adb_instance.set_progress_callback.assert_called_once()
    
    def test_init_without_status_callback(self, mock_parent_window):
        """Test DeviceManager initialization without status callback."""
        with patch('src.managers.device_manager.ADBManager'):
            device_manager = DeviceManager(mock_parent_window)
            assert device_manager.status_callback is None
    
    @patch('src.managers.device_manager.is_adb_available', return_value=True)
    def test_initialize_adb_already_available(self, mock_is_available, device_manager):
        """Test ADB initialization when ADB is already available."""
        result = device_manager.initialize_adb()
        assert result is True
    
    @patch('src.managers.device_manager.is_adb_available')
    @patch('src.managers.device_manager.messagebox.showinfo')
    def test_initialize_adb_needs_download_success(self, mock_showinfo, mock_is_available, device_manager):
        """Test ADB initialization when download is needed and succeeds."""
        # Mock is_adb_available to return False first (triggering download), then True (after download)
        mock_is_available.side_effect = [False, True]
        device_manager.adb_manager.download_and_extract_adb.return_value = True
        
        result = device_manager.initialize_adb()
        
        # Should show welcome message
        mock_showinfo.assert_called_once()
        assert "Welcome to Android File Transfer!" in mock_showinfo.call_args[0][0]
        
        # Should attempt download
        device_manager.adb_manager.download_and_extract_adb.assert_called_once()
        
        assert result is True
    
    @patch('src.managers.device_manager.is_adb_available', return_value=False)
    @patch('src.managers.device_manager.messagebox.showinfo')
    @patch('src.managers.device_manager.messagebox.showerror')
    def test_initialize_adb_needs_download_failure(self, mock_showerror, mock_showinfo, mock_is_available, device_manager):
        """Test ADB initialization when download fails."""
        device_manager.adb_manager.download_and_extract_adb.return_value = False
        
        result = device_manager.initialize_adb()
        
        # Should show welcome message
        mock_showinfo.assert_called_once()
        
        # Should attempt download
        device_manager.adb_manager.download_and_extract_adb.assert_called_once()
        
        # Should show error message
        mock_showerror.assert_called_once()
        
        assert result is False
    
    def test_check_device_connection_connected(self, device_manager):
        """Test device connection check when device is connected."""
        device_manager.adb_manager.check_device.return_value = "ABC123"
        
        result = device_manager.check_device_connection()
        
        assert result == "ABC123"  # Returns the device ID, not a boolean
        assert device_manager.device_connected is True
        device_manager.adb_manager.check_device.assert_called_once()
    
    def test_check_device_connection_not_connected(self, device_manager):
        """Test device connection check when device is not connected."""
        device_manager.adb_manager.check_device.return_value = None
        
        result = device_manager.check_device_connection()
        
        assert result is None  # Returns None, not False
        assert device_manager.device_connected is False
        device_manager.adb_manager.check_device.assert_called_once()
    
    def test_check_device_connection_exception(self, device_manager):
        """Test device connection check when exception occurs."""
        device_manager.adb_manager.check_device.side_effect = Exception("Connection error")
        
        # The method doesn't catch exceptions, so it should raise
        with pytest.raises(Exception, match="Connection error"):
            device_manager.check_device_connection()
    
    def test_device_connected_property_after_connection(self, device_manager):
        """Test device_connected property after successful connection."""
        device_manager.adb_manager.check_device.return_value = "TEST123"
        
        device_id = device_manager.check_device_connection()
        
        assert device_id == "TEST123"
        assert device_manager.device_connected is True
    
    def test_device_connected_property_after_failed_connection(self, device_manager):
        """Test device_connected property after failed connection."""
        device_manager.adb_manager.check_device.return_value = None
        
        device_id = device_manager.check_device_connection()
        
        assert device_id is None
        assert device_manager.device_connected is False
    
    def test_on_adb_status_update_with_callback(self, device_manager):
        """Test ADB status update with callback."""
        device_manager._on_adb_status_update("Test status")
        
        device_manager.status_callback.assert_called_once_with("Test status")
    
    def test_on_adb_status_update_without_callback(self, device_manager):
        """Test ADB status update without callback."""
        device_manager.status_callback = None
        
        # Should not raise an exception
        device_manager._on_adb_status_update("Test status")
    
    def test_on_adb_progress_update(self, device_manager):
        """Test ADB progress update."""
        # This method currently just passes through, so we test it doesn't crash
        device_manager._on_adb_progress_update(50)
        # No assertions needed as the method doesn't do anything currently
    
    def test_is_remote_file_detects_file(self, device_manager):
        """Test is_remote_file correctly identifies a file."""
        # Mock adb command to return file listing (starts with '-' for files)
        device_manager.adb_manager.run_adb_command.return_value = ("-rw-r--r-- 1 root root 1234 test.txt", "", 0)
        
        result = device_manager.is_remote_file("/sdcard/test.txt")
        assert result is True
        
    def test_is_remote_file_detects_directory(self, device_manager):
        """Test is_remote_file correctly identifies a directory."""
        # Mock adb command to return directory listing (starts with 'd' for directories)
        device_manager.adb_manager.run_adb_command.return_value = ("drwxr-xr-x 1 root root 4096 testdir", "", 0)
        
        result = device_manager.is_remote_file("/sdcard/testdir")
        assert result is False
        
    def test_is_remote_file_command_fails(self, device_manager):
        """Test is_remote_file when ADB command fails."""
        device_manager.adb_manager.run_adb_command.return_value = ("", "No such file", 1)
        
        result = device_manager.is_remote_file("/sdcard/nonexistent")
        assert result is False
        
    def test_get_file_transfer_methods_push_file(self, device_manager):
        """Test getting file transfer methods for pushing a file."""
        method_func, transfer_type = device_manager.get_file_transfer_methods("push", True)
        assert transfer_type == "file"
        assert method_func == device_manager.adb_manager.push_file
        
    def test_get_file_transfer_methods_pull_folder(self, device_manager):
        """Test getting file transfer methods for pulling a folder."""
        method_func, transfer_type = device_manager.get_file_transfer_methods("pull", False)
        assert transfer_type == "folder"  
        assert method_func == device_manager.adb_manager.pull_folder_with_dedup
        
    def test_get_file_transfer_methods_pull_file(self, device_manager):
        """Test getting file transfer methods for pulling a file."""
        method_func, transfer_type = device_manager.get_file_transfer_methods("pull", True)
        assert transfer_type == "file"
        assert method_func == device_manager.adb_manager.pull_file
        
    def test_get_file_transfer_methods_push_folder(self, device_manager):
        """Test getting file transfer methods for pushing a folder."""
        method_func, transfer_type = device_manager.get_file_transfer_methods("push", False)
        assert transfer_type == "folder"
        assert method_func == device_manager.adb_manager.push_folder_with_dedup
    
    def test_cancel_current_operation(self, device_manager):
        """Test canceling current ADB operation."""
        # This method returns None, so just test that it calls the right method
        device_manager.cancel_current_operation()
        
        device_manager.adb_manager.cancel_current_operation.assert_called_once()
    
    def test_device_connected_property_access(self, device_manager):
        """Test device_connected property access."""
        # Test initial state
        assert hasattr(device_manager, 'device_connected')
        
        # Test setting the property  
        device_manager.device_connected = True
        assert device_manager.device_connected is True
        
        device_manager.device_connected = False
        assert device_manager.device_connected is False
    
    def test_adb_manager_property_access(self, device_manager):
        """Test accessing ADB manager property."""
        assert hasattr(device_manager, 'adb_manager')
        assert device_manager.adb_manager is not None


class TestDeviceManagerIntegration:
    """Integration tests for DeviceManager."""
    
    def test_full_initialization_flow(self):
        """Test the complete initialization flow."""
        mock_parent = MagicMock(spec=tk.Tk)
        mock_callback = MagicMock()
        
        with patch('src.managers.device_manager.ADBManager') as mock_adb_class:
            with patch('src.managers.device_manager.is_adb_available', return_value=True):
                device_manager = DeviceManager(mock_parent, mock_callback)
                result = device_manager.initialize_adb()
                
                assert result is True
                assert device_manager.device_connected is False
    
    def test_device_connection_workflow(self):
        """Test the device connection workflow."""
        mock_parent = MagicMock(spec=tk.Tk)
        
        with patch('src.managers.device_manager.ADBManager') as mock_adb_class:
            mock_adb_instance = mock_adb_class.return_value
            device_manager = DeviceManager(mock_parent)
            
            # Test connection success - should return device ID, not boolean
            mock_adb_instance.check_device.return_value = "TEST123"
            result = device_manager.check_device_connection()
            assert result == "TEST123"  # Returns device ID
            assert device_manager.device_connected is True
            
            # Test connection failure - should return None, not False
            mock_adb_instance.check_device.return_value = None
            result = device_manager.check_device_connection()
            assert result is None  # Returns None
            assert device_manager.device_connected is False


if __name__ == '__main__':
    pytest.main([__file__])