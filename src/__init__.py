"""
Android File Handler - Package Initialization
Exposes the main components of the Android file handler application.
"""

from .adb_manager import (
    ADBManager,
    LinuxMTPManager,
    get_adb_binary_path,
    is_adb_available,
    get_platform_type,
)
from .gui import AndroidFileHandlerGUI, main

__all__ = [
    "ADBManager",
    "LinuxMTPManager",
    "AndroidFileHandlerGUI",
    "get_adb_binary_path",
    "is_adb_available",
    "get_platform_type",
    "main",
]
