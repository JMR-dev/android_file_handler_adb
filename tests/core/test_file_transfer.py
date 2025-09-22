"""Tests for file transfer module."""

import pytest
import unittest.mock as mock
import os
from unittest.mock import patch, MagicMock

from src.core.file_transfer import ADBFileTransfer


class TestADBFileTransfer:
    """Test ADB file transfer functionality."""
    
    def test_init(self):
        """Test ADBFileTransfer initialization."""
        transfer = ADBFileTransfer()
        assert transfer.progress_callback is None
        assert transfer.current_process is None
    
    def test_validate_windows_root_path_valid(self):
        """Test Windows root path validation with valid path."""
        transfer = ADBFileTransfer()
        # Should not raise exception
        transfer._validate_windows_root_path("C:/Users/test", "push")
    
    def test_validate_windows_root_path_invalid_push(self):
        """Test Windows root path validation with invalid path for push."""
        transfer = ADBFileTransfer()
        with pytest.raises(ValueError, match="Cannot push to Windows root"):
            transfer._validate_windows_root_path("C:", "push")
    
    def test_validate_windows_root_path_invalid_pull(self):
        """Test Windows root path validation with invalid path for pull."""
        transfer = ADBFileTransfer()
        with pytest.raises(ValueError, match="Cannot pull from Windows root"):
            transfer._validate_windows_root_path("C:", "pull")
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    def test_pull_file_success(self, mock_exists, mock_command_runner):
        """Test successful file pull operation."""
        mock_exists.return_value = False  # Remote file doesn't exist locally
        mock_runner = MagicMock()
        mock_runner.run_adb_command.return_value = ("", "", 0)
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.pull_file("/sdcard/test.txt", "/local/test.txt")
        
        assert result is True
        mock_runner.run_adb_command.assert_called_with(['pull', '/sdcard/test.txt', '/local/test.txt'])
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    def test_pull_file_already_exists(self, mock_exists, mock_command_runner):
        """Test file pull when local file already exists."""
        mock_exists.return_value = True
        mock_runner = MagicMock()
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.pull_file("/sdcard/test.txt", "/local/test.txt")
        
        assert result is False
        mock_runner.run_adb_command.assert_not_called()
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    def test_pull_file_command_failure(self, mock_exists, mock_command_runner):
        """Test file pull with ADB command failure."""
        mock_exists.return_value = False
        mock_runner = MagicMock()
        mock_runner.run_adb_command.return_value = ("", "Error", 1)
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.pull_file("/sdcard/test.txt", "/local/test.txt")
        
        assert result is False
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_push_file_success(self, mock_isfile, mock_exists, mock_command_runner):
        """Test successful file push operation."""
        mock_exists.return_value = True  # Local file exists
        mock_isfile.return_value = True
        mock_runner = MagicMock()
        mock_runner.run_adb_command.return_value = ("", "", 0)
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.push_file("/local/test.txt", "/sdcard/test.txt")
        
        assert result is True
        mock_runner.run_adb_command.assert_called_with(['push', '/local/test.txt', '/sdcard/test.txt'])
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    def test_push_file_not_exists(self, mock_exists, mock_command_runner):
        """Test file push when local file doesn't exist."""
        mock_exists.return_value = False
        mock_runner = MagicMock()
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.push_file("/local/test.txt", "/sdcard/test.txt")
        
        assert result is False
        mock_runner.run_adb_command.assert_not_called()
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_push_file_not_a_file(self, mock_isfile, mock_exists, mock_command_runner):
        """Test file push when local path is not a file."""
        mock_exists.return_value = True
        mock_isfile.return_value = False  # It's a directory, not a file
        mock_runner = MagicMock()
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.push_file("/local/test", "/sdcard/test.txt")
        
        assert result is False
        mock_runner.run_adb_command.assert_not_called()
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_pull_folder_success(self, mock_isdir, mock_exists, mock_command_runner):
        """Test successful folder pull operation."""
        mock_exists.return_value = False  # Local folder doesn't exist
        mock_isdir.return_value = True
        mock_runner = MagicMock()
        mock_runner.run_adb_command.return_value = ("", "", 0)
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.pull_folder("/sdcard/Documents", "/local/Documents")
        
        assert result is True
        mock_runner.run_adb_command.assert_called_with(['pull', '/sdcard/Documents', '/local/Documents'])
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    def test_pull_folder_already_exists(self, mock_exists, mock_command_runner):
        """Test folder pull when local folder already exists."""
        mock_exists.return_value = True
        mock_runner = MagicMock()
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.pull_folder("/sdcard/Documents", "/local/Documents")
        
        assert result is False
        mock_runner.run_adb_command.assert_not_called()
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_push_folder_success(self, mock_isdir, mock_exists, mock_command_runner):
        """Test successful folder push operation."""
        mock_exists.return_value = True  # Local folder exists
        mock_isdir.return_value = True
        mock_runner = MagicMock()
        mock_runner.run_adb_command.return_value = ("", "", 0)
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.push_folder("/local/Documents", "/sdcard/Documents")
        
        assert result is True
        mock_runner.run_adb_command.assert_called_with(['push', '/local/Documents', '/sdcard/Documents'])
    
    @patch('src.core.file_transfer.ADBCommandRunner')
    @patch('os.path.exists')
    def test_push_folder_not_exists(self, mock_exists, mock_command_runner):
        """Test folder push when local folder doesn't exist."""
        mock_exists.return_value = False
        mock_runner = MagicMock()
        mock_command_runner.return_value = mock_runner
        
        transfer = ADBFileTransfer()
        result = transfer.push_folder("/local/Documents", "/sdcard/Documents")
        
        assert result is False
        mock_runner.run_adb_command.assert_not_called()
    
    def test_cancel_transfer_no_process(self):
        """Test canceling transfer with no current process."""
        transfer = ADBFileTransfer()
        result = transfer.cancel_transfer()
        assert result is False
    
    def test_cancel_transfer_with_process(self):
        """Test canceling transfer with active process."""
        transfer = ADBFileTransfer()
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        transfer.current_process = mock_process
        
        result = transfer.cancel_transfer()
        
        assert result is True
        mock_process.terminate.assert_called_once()
    
    def test_cancel_transfer_finished_process(self):
        """Test canceling transfer with finished process."""
        transfer = ADBFileTransfer()
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Process finished
        transfer.current_process = mock_process
        
        result = transfer.cancel_transfer()
        
        assert result is False
        mock_process.terminate.assert_not_called()