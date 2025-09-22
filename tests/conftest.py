"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_tkinter_root():
    """Create a mock Tkinter root window for GUI tests."""
    import unittest.mock
    return unittest.mock.MagicMock()


@pytest.fixture(autouse=True)
def mock_tkinter_imports():
    """Mock tkinter imports to avoid GUI dependencies in tests."""
    import unittest.mock
    
    # Mock tkinter modules
    mock_tk = unittest.mock.MagicMock()
    mock_messagebox = unittest.mock.MagicMock()
    mock_filedialog = unittest.mock.MagicMock()
    
    modules_to_mock = {
        'tkinter': mock_tk,
        'tkinter.messagebox': mock_messagebox,
        'tkinter.filedialog': mock_filedialog,
        'tkinter.ttk': unittest.mock.MagicMock(),
    }
    
    with unittest.mock.patch.dict('sys.modules', modules_to_mock):
        yield


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    import tempfile
    import os
    
    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    yield temp_path
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass