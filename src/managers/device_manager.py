"""
Device Manager Module
Handles Android device connection and ADB operations for the GUI.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable

try:
    from ..core.adb_manager import ADBManager, is_adb_available
except ImportError:
    from core.adb_manager import ADBManager, is_adb_available


class DeviceManager:
    """Manages Android device connections and ADB operations."""
    
    def __init__(self, parent_window: tk.Tk, status_callback: Optional[Callable[[str], None]] = None):
        """Initialize the device manager.
        
        Args:
            parent_window: The main window instance
            status_callback: Callback function for status updates
        """
        self.parent = parent_window
        self.status_callback = status_callback
        self.adb_manager = ADBManager()
        self.device_connected = False
        
        # Set up ADB callbacks
        self.adb_manager.set_status_callback(self._on_adb_status_update)
        self.adb_manager.set_progress_callback(self._on_adb_progress_update)
    
    def initialize_adb(self) -> bool:
        """Initialize ADB and download tools if needed.
        
        Returns:
            True if ADB is available and ready, False otherwise
        """
        if not is_adb_available():
            # Show welcome message when platform-tools need to be downloaded
            messagebox.showinfo(
                "Welcome to Android File Transfer!",
                "Welcome to Android File Transfer! This application simplifies "
                "and speeds up file transfers over USB between computers and Android devices. "
                "Please do not delete or move the platform-tools folder that will be "
                "downloaded. These are tools written by Google "
                "and they are required for this application to function properly."
            )
            
            self._update_status("ADB not found locally. Downloading...")
            self.parent.update()
            self.adb_manager.download_and_extract_adb()
            success = is_adb_available()
            
            if success:
                self._update_status("ADB downloaded and ready.")
                return True
            else:
                self._update_status(
                    "Failed to download/access Android Debug Bridge tools. "
                    "Please check your internet and for any blocking security pop-ups and restart."
                )
                messagebox.showerror("Error", "Failed to download ADB tools. Exiting.")
                return False
        
        return True
    
    def check_device_connection(self) -> Optional[str]:
        """Check for device connection and update status.
        
        Returns:
            Device ID if connected, None otherwise
        """
        self._update_status("Checking for connected device...")
        self.parent.update()
        
        device = self.adb_manager.check_device()
        if device:
            self.device_connected = True
            self._update_status(f"Device detected: {device}")
            return device
        else:
            self.device_connected = False
            self._update_status(
                "No Android devices detected. Please check the USB connection at both ends is "
                "securely inserted, USB debugging is enabled, and that File Transfer mode is turned on."
            )
            return None
    
    def is_remote_file(self, remote_path: str) -> bool:
        """Check if the remote path points to a file (not a directory).
        
        Args:
            remote_path: Path on the Android device
            
        Returns:
            True if it's a file, False if it's a directory or check fails
        """
        try:
            result = self.adb_manager.run_adb_command(["shell", "ls", "-la", remote_path])
            if isinstance(result, tuple) and len(result) == 3:
                stdout, stderr, returncode = result
                if returncode == 0 and stdout:
                    # If the output starts with '-', it's a regular file
                    return stdout.strip().startswith('-')
            return False
        except Exception:
            return False
    
    def get_file_transfer_methods(self, direction: str, is_file: bool):
        """Get the appropriate transfer methods based on direction and type.
        
        Args:
            direction: Transfer direction ('pull' or 'push')
            is_file: Whether transferring a file (True) or folder (False)
            
        Returns:
            Tuple of (transfer_method, transfer_type)
        """
        if direction == "pull":
            if is_file:
                return self.adb_manager.pull_file, "file"
            else:
                return self.adb_manager.pull_folder_with_dedup, "folder"
        else:  # push
            if is_file:
                return self.adb_manager.push_file, "file"
            else:
                return self.adb_manager.push_folder_with_dedup, "folder"
    
    def cancel_current_operation(self) -> None:
        """Cancel the current ADB operation."""
        try:
            self.adb_manager.cancel_current_operation()
        except Exception as e:
            print(f"Error cancelling operation: {e}")
    
    def cancel_transfer(self) -> bool:
        """Cancel the current transfer operation.
        
        Returns:
            True if transfer was cancelled successfully, False otherwise
        """
        return self.adb_manager.cancel_transfer()
    
    def _update_status(self, message: str) -> None:
        """Update status through callback if available.
        
        Args:
            message: Status message to display
        """
        if self.status_callback:
            self.status_callback(message)
    
    def _on_adb_status_update(self, message: str) -> None:
        """Handle status updates from ADB manager.
        
        Args:
            message: Status message from ADB operations
        """
        self._update_status(message)
    
    def _on_adb_progress_update(self, percentage: int) -> None:
        """Handle progress updates from ADB manager.
        
        Args:
            percentage: Progress percentage (0-100)
        """
        # Currently we ignore progress updates and rely on status updates
        pass