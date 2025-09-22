"""
Tests for platform_tools module.
"""

import os
import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
import pytest

from src.core.platform_tools import (
    is_adb_available, 
    get_adb_binary_path,
    ensure_platform_tools_in_user_dir,
    download_and_extract_adb
)


class TestPlatformTools(unittest.TestCase):
    """Test cases for platform tools management."""

    def test_is_adb_available_true(self):
        """Test adb availability when binary exists."""
        with patch('src.core.platform_tools.get_adb_binary_path', return_value='/path/to/adb'):
            with patch('os.path.isfile', return_value=True):
                result = is_adb_available()
                assert result is True

    def test_is_adb_available_false(self):
        """Test adb availability when binary doesn't exist."""
        with patch('src.core.platform_tools.get_adb_binary_path', return_value=None):
            result = is_adb_available()
            assert result is False

    def test_get_adb_binary_path_user_dir_success(self):
        """Test getting ADB path from user directory."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', return_value='/user/adb'):
            with patch('os.path.isfile', return_value=True):
                result = get_adb_binary_path()
                assert result == '/user/adb'

    def test_get_adb_binary_path_local_fallback(self):
        """Test fallback to local platform-tools."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', side_effect=Exception()):
            with patch('src.core.platform_utils.get_platform_tools_directory', return_value='/local/platform-tools'):
                with patch('src.core.platform_utils.get_adb_binary_name', return_value='adb'):
                    with patch('os.path.isfile', return_value=True):
                        with patch('os.path.join', return_value='/local/platform-tools/adb'):
                            result = get_adb_binary_path()
                            assert result == '/local/platform-tools/adb'

    def test_get_adb_binary_path_windows(self):
        """Test getting ADB path on Windows."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', return_value='/user/adb.exe'):
            with patch('os.path.isfile', return_value=True):
                result = get_adb_binary_path()
                assert result == '/user/adb.exe'

    def test_ensure_platform_tools_simple(self):
        """Test basic platform tools installation."""
        # Just test the function doesn't crash with basic mocking
        with patch('os.makedirs'):
            with patch('os.path.islink', return_value=False):
                with patch('os.path.isdir', return_value=False):
                    with patch('tempfile.mkdtemp', return_value='/tmp/test'):
                        with patch('os.listdir', return_value=['platform-tools']):  # Mock directory listing
                            with patch('requests.get') as mock_get:
                                with patch('builtins.open', mock_open()):
                                    with patch('zipfile.ZipFile') as mock_zip:
                                        with patch('os.path.isdir', side_effect=lambda p: p == '/tmp/test/platform-tools'):
                                            with patch('shutil.move'):
                                                with patch('os.chmod'):
                                                    with patch('os.symlink'):
                                                        with patch('shutil.rmtree'):
                                                            mock_response = Mock()
                                                            mock_response.iter_content.return_value = [b'content']
                                                            mock_response.raise_for_status.return_value = None
                                                            mock_get.return_value = mock_response
                                                            
                                                            result = ensure_platform_tools_in_user_dir()
                                                            assert result is not None

    def test_download_and_extract_adb_linux(self):
        """Test ADB download and extraction on Linux."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', return_value='/test/adb'):
            with patch('os.path.isfile', return_value=True):
                with patch('os.chmod') as mock_chmod:
                    with patch('os.name', 'posix'):
                        result = download_and_extract_adb()
                        assert result is True
                        mock_chmod.assert_called_once_with('/test/adb', 0o755)

    def test_download_and_extract_adb_windows(self):
        """Test ADB download and extraction on Windows."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', return_value='/test/adb.exe'):
            with patch('os.path.isfile', return_value=True):
                with patch('os.name', 'nt'):
                    result = download_and_extract_adb()
                    assert result is True

    def test_download_and_extract_adb_failure(self):
        """Test ADB download failure when file doesn't exist."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', return_value='/test/adb'):
            with patch('os.path.isfile', return_value=False):
                result = download_and_extract_adb()
                assert result is False

    def test_download_and_extract_adb_exception(self):
        """Test ADB download failure with exception."""
        with patch('src.core.platform_tools.ensure_platform_tools_in_user_dir', side_effect=Exception()):
            result = download_and_extract_adb()
            assert result is False


if __name__ == '__main__':
    unittest.main()