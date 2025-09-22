"""Tests for platform utilities module."""

import pytest
import unittest.mock as mock
import sys
import os
from unittest.mock import patch

from src.core.platform_utils import (
    get_executable_directory,
    get_platform_tools_directory,
    get_platform_type
)


class TestPlatformUtils:
    """Test platform utility functions."""
    
    def test_get_executable_directory_frozen(self):
        """Test get_executable_directory when running as executable."""
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, 'executable', '/path/to/app'):
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
                    # The function calls abspath on the actual platform_utils.py file
                    mock_abspath.assert_called_once()
    
    def test_get_platform_type_linux(self):
        """Test platform type detection for Linux."""
        with patch('sys.platform', 'linux'):
            result = get_platform_type()
            assert result == 'linux'
    
    def test_get_platform_type_windows(self):
        """Test platform type detection for Windows."""
        with patch('sys.platform', 'win32'):
            result = get_platform_type()
            assert result == 'win32'
    
    def test_get_platform_type_darwin(self):
        """Test platform type detection for macOS."""
        with patch('sys.platform', 'darwin'):
            result = get_platform_type()
            assert result == 'darwin'
    
    def test_get_platform_tools_directory_frozen(self):
        """Test platform-tools directory when running as executable."""
        with patch.object(sys, 'frozen', True, create=True):
            with patch('src.core.platform_utils.get_executable_directory', return_value='/app/dir'):
                result = get_platform_tools_directory()
                expected = os.path.join('/app/dir', 'platform-tools')
                assert result == expected
    
    def test_get_platform_tools_directory_src(self):
        """Test platform-tools directory when running from src."""
        with patch.object(sys, 'frozen', False, create=True):
            with patch('src.core.platform_utils.get_executable_directory', return_value='/project/src'):
                result = get_platform_tools_directory()
                expected = os.path.join('/project/src', 'platform-tools')
                assert result == expected
    
    def test_get_platform_tools_directory_gui_subdirectory(self):
        """Test platform-tools directory when running from src/gui."""
        with patch.object(sys, 'frozen', False, create=True):
            with patch('src.core.platform_utils.get_executable_directory', return_value='/project/src/gui'):
                result = get_platform_tools_directory()
                expected = os.path.join('/project/src', 'platform-tools')
                assert result == expected
    
    def test_get_platform_tools_directory_project_root(self):
        """Test platform-tools directory when running from project root."""
        with patch.object(sys, 'frozen', False, create=True):
            with patch('src.core.platform_utils.get_executable_directory', return_value='/project'):
                with patch('os.path.exists', return_value=True):
                    result = get_platform_tools_directory()
                    expected = os.path.join('/project', 'src', 'platform-tools')
                    assert result == expected
    
    def test_get_platform_tools_directory_fallback(self):
        """Test platform-tools directory fallback behavior."""
        with patch.object(sys, 'frozen', False, create=True):
            with patch('src.core.platform_utils.get_executable_directory', return_value='/somewhere'):
                with patch('os.path.exists', return_value=False):
                    result = get_platform_tools_directory()
                    expected = os.path.join('/somewhere', 'src', 'platform-tools')
                    assert result == expected