"""Tests for ADB command execution module."""

import pytest
import unittest.mock as mock
import subprocess
from unittest.mock import patch, MagicMock

from src.core.adb_command import ADBCommandRunner


class TestADBCommandRunner:
    """Test ADB command runner functionality."""
    
    def test_init(self):
        """Test ADBCommandRunner initialization."""
        runner = ADBCommandRunner()
        assert runner.current_process is None
    
    @patch('src.core.adb_command.get_adb_binary_path')
    @patch('subprocess.run')
    def test_run_adb_command_success(self, mock_subprocess, mock_get_path):
        """Test successful ADB command execution."""
        mock_get_path.return_value = '/path/to/adb'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "device_list"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        runner = ADBCommandRunner()
        stdout, stderr, returncode = runner.run_adb_command(['devices'])
        
        assert returncode == 0
        assert stdout == "device_list"
        assert stderr == ""
        mock_subprocess.assert_called_once_with(
            ['/path/to/adb', 'devices'],
            capture_output=True,
            text=True,
            timeout=15
        )
    
    @patch('src.core.adb_command.get_adb_binary_path')
    @patch('subprocess.run')
    def test_run_adb_command_failure(self, mock_subprocess, mock_get_path):
        """Test ADB command execution failure."""
        mock_get_path.return_value = '/path/to/adb'
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_subprocess.return_value = mock_result
        
        runner = ADBCommandRunner()
        stdout, stderr, returncode = runner.run_adb_command(['invalid'])
        
        assert returncode == 1
        assert stdout == ""
        assert stderr == "error message"
    
    @patch('src.core.adb_command.get_adb_binary_path')
    @patch('subprocess.run')
    def test_run_adb_command_exception(self, mock_subprocess, mock_get_path):
        """Test ADB command execution with exception."""
        mock_get_path.return_value = '/path/to/adb'
        mock_subprocess.side_effect = FileNotFoundError("ADB not found")
        
        runner = ADBCommandRunner()
        stdout, stderr, returncode = runner.run_adb_command(['devices'])
        
        assert returncode == -1
        assert stdout is None
        assert "ADB not found" in stderr
    
    @patch('src.core.adb_command.get_adb_binary_path')
    @patch('subprocess.Popen')
    def test_run_adb_command_no_capture(self, mock_popen, mock_get_path):
        """Test ADB command execution without output capture."""
        mock_get_path.return_value = '/path/to/adb'
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        runner = ADBCommandRunner()
        result = runner.run_adb_command(['devices'], capture_output=False)
        
        assert result == mock_process
        mock_popen.assert_called_once_with(
            ['/path/to/adb', 'devices'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    def test_check_device_no_process(self):
        """Test device check with no current process."""
        runner = ADBCommandRunner()
        result = runner.check_device()
        assert result is None
    
    @patch('src.core.adb_command.get_adb_binary_path')
    @patch('subprocess.run')
    def test_check_device_with_devices(self, mock_subprocess, mock_get_path):
        """Test device check with connected devices."""
        mock_get_path.return_value = '/path/to/adb'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "List of devices attached\ndevice1\tdevice\ndevice2\tdevice"
        mock_subprocess.return_value = mock_result
        
        runner = ADBCommandRunner()
        result = runner.check_device()
        
        assert result == "device1"
    
    @patch('src.core.adb_command.get_adb_binary_path')
    @patch('subprocess.run')
    def test_check_device_no_devices(self, mock_subprocess, mock_get_path):
        """Test device check with no connected devices."""
        mock_get_path.return_value = '/path/to/adb'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "List of devices attached\n"
        mock_subprocess.return_value = mock_result
        
        runner = ADBCommandRunner()
        result = runner.check_device()
        
        assert result is None
    
    def test_parse_progress_valid_percentage(self):
        """Test parsing valid progress percentage."""
        runner = ADBCommandRunner()
        result = runner.parse_progress("Transferring: 45%")
        assert result == 45
    
    def test_parse_progress_valid_fraction(self):
        """Test parsing valid progress fraction."""
        runner = ADBCommandRunner()
        result = runner.parse_progress("1024/2048 KB transferred")
        assert result == 50
    
    def test_parse_progress_valid_bytes(self):
        """Test parsing valid progress bytes."""
        runner = ADBCommandRunner()
        result = runner.parse_progress("2048 KB/s (1048576 bytes in 2.5s)")
        assert result == 100
    
    def test_parse_progress_invalid(self):
        """Test parsing invalid progress string."""
        runner = ADBCommandRunner()
        result = runner.parse_progress("No progress info here")
        assert result is None
    
    def test_parse_progress_empty(self):
        """Test parsing empty progress string."""
        runner = ADBCommandRunner()
        result = runner.parse_progress("")
        assert result is None
    
    def test_cancel_current_operation_no_process(self):
        """Test canceling operation with no current process."""
        runner = ADBCommandRunner()
        result = runner.cancel_current_operation()
        assert result is False
    
    def test_cancel_current_operation_with_process(self):
        """Test canceling operation with active process."""
        runner = ADBCommandRunner()
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        runner.current_process = mock_process
        
        result = runner.cancel_current_operation()
        
        assert result is True
        mock_process.terminate.assert_called_once()
    
    def test_cancel_current_operation_finished_process(self):
        """Test canceling operation with finished process."""
        runner = ADBCommandRunner()
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Process finished
        runner.current_process = mock_process
        
        result = runner.cancel_current_operation()
        
        assert result is False
        mock_process.terminate.assert_not_called()