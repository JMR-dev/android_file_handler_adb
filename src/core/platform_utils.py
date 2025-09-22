"""
Platform-specific utilities for Android File Handler.
Handles path resolution and platform detection.
"""

import os
import sys
from typing import Optional


def get_executable_directory() -> str:
    """Get the directory containing the executable or script."""
    if getattr(sys, 'frozen', False):
        # Running as executable (PyInstaller, cx_Freeze, etc.)
        return os.path.dirname(sys.executable)
    else:
        # Running as script - use the script's directory
        return os.path.dirname(os.path.abspath(__file__))


def get_platform_tools_directory() -> str:
    """Get platform-tools directory."""
    base_dir = get_executable_directory()
    
    # Check if we're in development mode (running from src/ directory)
    if not getattr(sys, 'frozen', False):
        # Running as script - check if we're in src/ directory or subdirectory
        if base_dir.endswith('src'):
            # Already in src directory - place platform-tools here
            return os.path.join(base_dir, "platform-tools")
        elif base_dir.endswith('gui') or os.path.basename(base_dir) in ['gui']:
            # In src/gui subdirectory - go up one level to src
            src_dir = os.path.dirname(base_dir)
            return os.path.join(src_dir, "platform-tools")
        else:
            # Not in src structure - assume we need to find/create src directory
            # This handles cases where the script might be run from project root
            current_dir = base_dir
            src_dir = os.path.join(current_dir, "src")
            if os.path.exists(src_dir):
                return os.path.join(src_dir, "platform-tools")
            else:
                # Fallback to current directory
                return os.path.join(base_dir, "src", "platform-tools")
    
    # Running as executable - use directory next to binary
    return os.path.join(base_dir, "platform-tools")


def get_platform_type() -> str:
    """Get the current platform type."""
    return sys.platform


def get_adb_binary_name() -> str:
    """Get the ADB binary name for current platform."""
    if sys.platform.startswith("win"):
        return "adb.exe"
    else:
        return "adb"


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform.startswith("win")


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform.startswith("darwin")