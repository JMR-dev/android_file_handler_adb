"""
Transfer Manager Module
Handles file transfer operations and coordination between GUI and ADB manager.
"""

import threading
import os
from typing import Optional, Callable, Tuple, Dict, Any

try:
    from .device_manager import DeviceManager
    from ..gui.handlers.animation_handler import AnimationHandler
    from ..gui.dialogs.dialog_manager import DialogManager
except ImportError:
    from device_manager import DeviceManager
    from gui.handlers.animation_handler import AnimationHandler
    from gui.dialogs.dialog_manager import DialogManager


class TransferManager:
    """Manages file transfer operations and coordination."""
    
    def __init__(self, parent_window, device_manager: DeviceManager, 
                 animation_handler: AnimationHandler, dialog_manager: DialogManager):
        """Initialize the transfer manager.
        
        Args:
            parent_window: The main window instance
            device_manager: Device manager instance
            animation_handler: Animation handler instance
            dialog_manager: Dialog manager instance
        """
        self.parent = parent_window
        self.device_manager = device_manager
        self.animation_handler = animation_handler
        self.dialog_manager = dialog_manager
        
        # Transfer tracking
        self.current_transfer_id = 0
        
        # UI callbacks
        self.ui_callbacks = {}
        
    def set_ui_callback(self, name: str, callback: Callable) -> None:
        """Set a UI callback function.
        
        Args:
            name: Name of the callback
            callback: Function to call
        """
        self.ui_callbacks[name] = callback
        
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set the status update callback.
        
        Args:
            callback: Function to call for status updates
        """
        self.ui_callbacks['status'] = callback
        self.status_callback = callback
    
    def set_controls_callback(self, callback: Callable[[], None]) -> None:
        """Set the controls update callback.
        
        Args:
            callback: Function to call for enabling/disabling controls
        """
        self.controls_callback = callback
    
    def start_transfer(self, direction: str, source_path: str, dest_path: str, 
                      completion_callback: Optional[Callable] = None) -> bool:
        """Start a file transfer operation.
        
        Args:
            direction: Transfer direction ('pull' or 'push')
            source_path: Source file or folder path
            dest_path: Destination path
            completion_callback: Callback to call when transfer completes
            
        Returns:
            True if transfer was started successfully, False otherwise
        """
        # Increment transfer ID for cancellation support
        self.current_transfer_id += 1
        transfer_id = self.current_transfer_id
        
        # Determine if transferring a file or folder
        if direction == "pull":
            is_file = self._is_remote_file(source_path)
        else:
            is_file = os.path.isfile(source_path)
            
        # Disable controls during transfer
        if 'disable_controls' in self.ui_callbacks:
            self.ui_callbacks['disable_controls']()
        
        # Start transfer in background thread
        transfer_thread = threading.Thread(
            target=self._transfer_thread,
            args=(direction, source_path, dest_path, transfer_id, is_file, completion_callback),
            daemon=True
        )
        transfer_thread.start()
        return True
    
    def cancel_transfer(self) -> None:
        """Cancel the current transfer operation."""
        # Increment transfer ID to invalidate current transfer
        self.current_transfer_id += 1
        
        # Cancel ADB operation
        self.device_manager.cancel_current_operation()
        
    def _is_remote_file(self, remote_path: str) -> bool:
        """Check if a remote path is a file.
        
        Args:
            remote_path: Path on Android device
            
        Returns:
            True if path is a file, False if it's a folder
        """
        try:
            # Use device manager to check if path is a file
            return self.device_manager.is_remote_file(remote_path)
        except Exception:
            # If we can't determine, assume it's a folder for safety
            return False
    
    def _transfer_thread(self, direction: str, source_path: str, dest_path: str, 
                        transfer_id: int, is_file: bool, completion_callback: Optional[Callable]):
        """Handle file transfer in background thread.
        
        Args:
            direction: Transfer direction ('pull' or 'push')
            source_path: Source file or folder path
            dest_path: Destination path
            transfer_id: Transfer ID for cancellation
            is_file: True if transferring a file
            completion_callback: Callback for completion
        """
        try:
            # Check if transfer is still valid
            if transfer_id != self.current_transfer_id:
                return
                
            # Get ADB manager from device manager
            adb_manager = self.device_manager.adb_manager
            
            # Perform the transfer
            if direction == "pull":
                if is_file:
                    success, stats = adb_manager.pull_file(source_path, dest_path)
                else:
                    success, stats = adb_manager.pull_folder(source_path, dest_path)
                operation = "pulled from Android device"
            else:  # push
                if is_file:
                    success, stats = adb_manager.push_file(source_path, dest_path)
                else:
                    success, stats = adb_manager.push_folder(source_path, dest_path)
                operation = "pushed to Android device"
            
            # Check if transfer was cancelled
            if transfer_id != self.current_transfer_id:
                return
            
            # Call completion callback on main thread
            if completion_callback:
                self.parent.after(0, lambda: completion_callback(success, stats, operation))
                
        except Exception as e:
            # Handle errors on main thread
            if transfer_id == self.current_transfer_id and 'show_error' in self.ui_callbacks:
                self.parent.after(0, lambda: self.ui_callbacks["show_error"](f"Transfer error: {str(e)}"))
        
        # Start transfer in background thread
        self.current_transfer_id += 1
        transfer_id = self.current_transfer_id
        
        threading.Thread(
            target=self._transfer_thread,
            args=(direction, source_path, dest_path, transfer_id, is_file),
            daemon=True
        ).start()
        
        return True
    
    def cancel_transfer(self) -> bool:
        """Cancel the current transfer operation.
        
        Returns:
            True if transfer was cancelled successfully, False otherwise
        """
        # Cancel the actual ADB process
        cancelled = self.device_manager.cancel_transfer()
        
        # Increment transfer ID to invalidate current transfer
        self.current_transfer_id += 1
        
        # Stop animation and restore UI
        self.animation_handler.stop_animation()
        
        # Update status
        status = "Transfer cancelled by user." if cancelled else "Transfer cancellation failed."
        self._update_status(status)
        
        return cancelled
    
    def _validate_transfer_paths(self, direction: str, source_path: str, dest_path: str) -> bool:
        """Validate transfer paths based on direction.
        
        Args:
            direction: Transfer direction ('pull' or 'push')
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            True if paths are valid, False otherwise
        """
        if not source_path or not dest_path:
            self.dialog_manager.show_error("Input Error", "Both source and destination paths are required.")
            return False
        
        if direction == "push":
            # For push operations, validate local source path exists
            if not os.path.exists(source_path):
                self.dialog_manager.show_error(
                    "Input Error", 
                    f"Source path does not exist: {source_path}"
                )
                return False
        else:  # pull operations
            # For pull operations, validate local destination is a directory
            if not os.path.isdir(dest_path):
                self.dialog_manager.show_error(
                    "Input Error", 
                    "Destination must be a valid directory for pulled files."
                )
                return False
        
        return True
    
    def _transfer_thread(self, direction: str, source_path: str, dest_path: str, 
                        transfer_id: int, is_file: bool) -> None:
        """Background thread function for transfer operations.
        
        Args:
            direction: Transfer direction ('pull' or 'push')
            source_path: Source path
            dest_path: Destination path
            transfer_id: Transfer ID for thread safety
            is_file: True if transferring a file, False for folder
        """
        try:
            # Check if this transfer is still current
            if self.current_transfer_id != transfer_id:
                return
            
            # Recheck device connectivity before proceeding
            device = self.device_manager.adb_manager.check_device()
            if not device:
                if self.current_transfer_id == transfer_id:
                    self.animation_handler.stop_animation()
                    self.parent.after(0, self._handle_device_disconnection)
                return
            
            # Get the appropriate transfer method
            transfer_method, transfer_type = self.device_manager.get_file_transfer_methods(direction, is_file)
            
            # Perform the transfer
            success, stats = self._execute_transfer(
                direction, source_path, dest_path, transfer_method, transfer_type, is_file
            )
            
            if success and self.current_transfer_id == transfer_id:
                self.animation_handler.stop_animation()
                transfer_desc = "File" if is_file else "Folder"
                self._update_status(
                    f"{transfer_desc} transfer completed successfully. "
                    "To start another transfer, please select another file or folder."
                )
                
                # Show debugging reminder and transfer statistics
                self.parent.after(0, self.dialog_manager.show_disable_debugging_reminder)
                
                if stats is not None:
                    self.parent.after(0, lambda: self.dialog_manager.show_transfer_stats(
                        stats, direction.capitalize(), self.device_manager.adb_manager.deduplicator
                    ))
                
        except Exception as e:
            if self.current_transfer_id == transfer_id:
                self.animation_handler.stop_animation()
                transfer_desc = "file" if is_file else "folder"
                error_msg = f"{direction.capitalize()} {transfer_desc} operation failed: {e}"
                self.parent.after(0, lambda: self.dialog_manager.show_error("Transfer Error", error_msg))
        finally:
            if self.current_transfer_id == transfer_id:
                self.animation_handler.stop_animation()
                if self.controls_callback:
                    self.parent.after(0, self.controls_callback)
    
    def _execute_transfer(self, direction: str, source_path: str, dest_path: str,
                         transfer_method: Callable, transfer_type: str, is_file: bool) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Execute the actual transfer operation.
        
        Args:
            direction: Transfer direction
            source_path: Source path
            dest_path: Destination path
            transfer_method: Transfer method to call
            transfer_type: Type of transfer ('file' or 'folder')
            is_file: True if transferring a file
            
        Returns:
            Tuple of (success, stats_dict or None)
        """
        if direction == "pull" and is_file:
            # For pull operations with files, construct the full destination path
            filename = source_path.split("/")[-1]
            full_dest_path = os.path.join(dest_path, filename)
            success = transfer_method(source_path, full_dest_path)
            return success, None
        else:
            # For folder transfers or push operations
            if transfer_type == "folder":
                # Folder transfers return (success, stats)
                return transfer_method(source_path, dest_path)
            else:
                # File transfers return just success
                success = transfer_method(source_path, dest_path)
                return success, None
    
    def _handle_device_disconnection(self) -> None:
        """Handle device disconnection during transfers."""
        self.device_manager.device_connected = False
        self._update_status(
            "No Android devices detected. Please check the USB connection at both ends is "
            "securely inserted, USB debugging is enabled, and that File Transfer mode is turned on."
        )
        self.dialog_manager.show_enable_debugging_instructions()
    
    def _update_status(self, message: str) -> None:
        """Update status through callback if available.
        
        Args:
            message: Status message to display
        """
        if self.status_callback:
            self.status_callback(message)
    
    def handle_adb_status_update(self, message: str) -> None:
        """Handle status updates from ADB operations.
        
        Args:
            message: Status message from ADB
        """
        # Check for transfer progress updates
        if message.startswith("TRANSFER_PROGRESS:"):
            parts = message.split(":")
            if len(parts) == 3:
                current = int(parts[1])
                total = int(parts[2])
                self.animation_handler.update_transfer_progress(current, total)
                return
        
        # Check for animation state changes
        if self.animation_handler.is_animation_running():
            if "Scanning for duplicates" in message and not self.animation_handler.is_scanning():
                # Already scanning, ignore duplicate messages
                return
            elif "Starting transfer" in message or "Transferring" in message:
                # Switch from scanning to transfer animation
                self.animation_handler.stop_animation()
                self.animation_handler.start_transfer_animation()
                return
            elif ("Duplicate scan complete" in message or 
                  "No duplicates found" in message or
                  "All files already exist" in message):
                # Allow these messages to show briefly before transfer starts
                self.animation_handler.stop_animation()
                self._update_status(message)
                return
            else:
                # Don't update status if animation is running (except for specific cases)
                return
        elif "Scanning for duplicates" in message:
            # Start scanning animation
            self.animation_handler.start_scanning_animation()
            return
        
        # Normal status update
        self._update_status(message)