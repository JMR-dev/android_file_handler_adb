"""
Main Window Module - Refactored
Core GUI application window for Android file transfers using modular components.
"""

import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog

try:
    # Try relative import first (when used as module)
    from ..core.adb_manager import ADBManager, is_adb_available
except ImportError:
    # Fall back to direct import (when run directly)
    from core.adb_manager import ADBManager, is_adb_available

try:
    # Try relative imports first
    from .components.file_browser import AndroidFileBrowser
    from .handlers.animation_handler import AnimationHandler
    from .dialogs.dialog_manager import DialogManager
    from .components.ui_components import (
        PathSelectorFrame, DirectionSelector, StatusLabel,
        TransferButton, LicenseManager
    )
    from ..managers.device_manager import DeviceManager
    from ..managers.transfer_manager import TransferManager
except ImportError:
    # Fall back to direct imports
    from components.file_browser import AndroidFileBrowser
    from handlers.animation_handler import AnimationHandler
    from dialogs.dialog_manager import DialogManager
    from components.ui_components import (
        PathSelectorFrame, DirectionSelector, StatusLabel,
        TransferButton, LicenseManager
    )
    from managers.device_manager import DeviceManager
    from managers.transfer_manager import TransferManager


class AndroidFileHandlerGUI(tk.Tk):
    """Main GUI application for Android file transfers."""

    def __init__(self):
        """Initialize the main GUI application."""
        super().__init__()
        
        # Transfer tracking for thread safety
        self.current_transfer_id = 0
        self.device_connected = False
        
        # Initialize modular components
        self.license_manager = LicenseManager(self)
        self.device_manager = DeviceManager(self)  # Creates its own ADBManager
        self.dialog_manager = DialogManager(self)
        self.animation_handler = AnimationHandler(self)
        self.transfer_manager = TransferManager(
            self,
            self.device_manager, 
            self.animation_handler, 
            self.dialog_manager
        )
        
        # Get ADB manager reference from device manager
        self.adb_manager = self.device_manager.adb_manager
        
        # Initialize UI and start application
        self._setup_initial_ui()

    def _setup_initial_ui(self):
        """Setup the initial UI - either license agreement or main interface."""
        # Window configuration
        self.title("Android File Handler")
        self.geometry("520x320")
        self.minsize(520, 320)
        self.resizable(True, True)
        
        if self.license_manager.needs_license_agreement():
            # Show license agreement first
            self.license_manager.show_license_agreement(self._show_main_interface)
        else:
            # Show main interface directly
            self._show_main_interface()

    def _show_main_interface(self):
        """Show the main application interface."""
        # Reset window size for main interface
        self.geometry("520x320")
        self.minsize(520, 320)
        
        # Setup main UI
        self._setup_main_ui()
        self._initialize_components()
        self._initialize_app()

    def _setup_main_ui(self):
        """Setup the main user interface."""
        # Direction selection
        self.direction_selector = DirectionSelector(self, self._on_direction_change)
        
        # Create a container frame for the path sections that can be reordered
        self.path_container = tk.Frame(self)
        self.path_container.pack(fill="x", padx=10, pady=(10, 0))

        # Create path selector components
        self.android_path_selector = PathSelectorFrame(
            self.path_container, 
            "Android device:",
            self.browse_remote_folder
        )
        
        self.computer_path_selector = PathSelectorFrame(
            self.path_container,
            "Computer:",
            self.browse_local_folder
        )

        # Initially arrange for pull (Android on top)
        self._arrange_path_sections()

        # Status label (responsive with word wrapping)
        self.status_label = StatusLabel(self, "Status: Idle")

        # Transfer button with multi-mode functionality
        self.transfer_button = TransferButton(self)
        
        # Initially disable components until device is connected
        self._disable_browse_buttons()

        # Window close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _initialize_components(self):
        """Initialize GUI components and handlers."""
        # Set up ADB callbacks directly
        self.adb_manager.set_progress_callback(lambda x: None)  # Ignore progress for now
        self.adb_manager.set_status_callback(self._update_status)
        
        # Connect transfer manager callbacks
        self.transfer_manager.set_status_callback(self._update_status)
        self.transfer_manager.set_ui_callback('disable_controls', self.disable_controls)
        self.transfer_manager.set_ui_callback('enable_controls', self.enable_controls)
        self.transfer_manager.set_ui_callback('show_error', self.report_error)
        self.transfer_manager.set_ui_callback('show_stats', self._show_transfer_stats)
        self.transfer_manager.set_ui_callback('show_reminder', self._show_debugging_reminder)

    def _update_status(self, message: str):
        """Update the status label from any thread.
        
        Args:
            message: Status message to display
        """
        try:
            # Ensure UI updates happen on main thread
            if threading.current_thread() == threading.main_thread():
                self.status_label.set_text(message)
                self.update_idletasks()
            else:
                self.after(0, lambda: self._update_status(message))
        except Exception as e:
            # If there's an error updating the UI, print to console
            print(f"Error updating status: {e}")

    def _validate_paths_and_update_button(self):
        """Validate selected paths and update button state accordingly."""
        android_path_valid = self.android_path_selector.is_path_selected()
        computer_path_valid = self.computer_path_selector.is_path_selected()
        
        if android_path_valid and computer_path_valid and self.device_connected:
            self.transfer_button.set_transfer_mode(self.start_transfer, enabled=True)
        else:
            self.transfer_button.set_transfer_mode(self.start_transfer, enabled=False)

    def _clear_paths_and_disable_button(self):
        """Clear all path selections and disable the start button."""
        self.android_path_selector.clear_path()
        self.computer_path_selector.clear_path()
        self.transfer_button.disable()

    def _enable_browse_buttons(self):
        """Enable path browse buttons when device is connected."""
        self.android_path_selector.enable_browse()
        self.computer_path_selector.enable_browse()

    def _disable_browse_buttons(self):
        """Disable path browse buttons when device is not connected."""
        self.android_path_selector.disable_browse()
        self.computer_path_selector.disable_browse()

    def _initialize_app(self):
        """Initialize the application and check device connection."""
        # Initialize ADB and check device connection
        self.device_manager.initialize_adb()
        self.device_connected = self.device_manager.check_device_connection()
        
        if self.device_connected:
            self._update_status("Status: Android device detected. Ready for file transfer.")
            self._enable_browse_buttons()
            self._validate_paths_and_update_button()
        else:
            self._update_status("Status: No Android device detected. Please connect your device and enable USB debugging.")
            self.transfer_button.set_recheck_mode(self.recheck_device)

    def _on_direction_change(self):
        """Handle transfer direction change."""
        self._arrange_path_sections()
    
    def _arrange_path_sections(self):
        """Arrange path sections based on transfer direction."""
        # Remove both sections first
        self.android_path_selector.pack_forget()
        self.computer_path_selector.pack_forget()
        
        if self.direction_selector.get_direction() == "pull":
            # Pull: Android (source) on top, Computer (destination) on bottom
            self.android_path_selector.pack(fill="x", pady=(0, 0))
            self.computer_path_selector.pack(fill="x", pady=(0, 0))
        else:
            # Push: Computer (source) on top, Android (destination) on bottom
            self.computer_path_selector.pack(fill="x", pady=(0, 0))
            self.android_path_selector.pack(fill="x", pady=(0, 0))

    def browse_remote_folder(self):
        """Open the Android file browser for remote path selection."""
        def on_path_selected(path):
            self.android_path_selector.set_path(path)
            self._validate_paths_and_update_button()
            
        browser = AndroidFileBrowser(self, self.adb_manager, on_path_selected)
        
    def browse_local_folder(self):
        """Browse for local file or folder selection."""
        def on_file_selected():
            filename = filedialog.askopenfilename(
                title="Select a file to transfer",
                initialdir=os.path.expanduser("~")
            )
            if filename:
                self.computer_path_selector.set_path(filename)
                self._validate_paths_and_update_button()
        
        def on_folder_selected():
            foldername = filedialog.askdirectory(
                title="Select a folder to transfer",
                initialdir=os.path.expanduser("~")
            )
            if foldername:
                self.computer_path_selector.set_path(foldername)
                self._validate_paths_and_update_button()
        
        # Show file/folder selection dialog
        self.dialog_manager.show_file_folder_choice(on_file_selected, on_folder_selected)

    def recheck_device(self):
        """Recheck for connected Android device."""
        self.transfer_button.set_checking_mode()
        self.animation_handler.start_scanning_animation("Status: Scanning")
        
        def perform_recheck():
            self.device_connected = self.device_manager.check_device_connection()
            self.after(0, self._handle_device_recheck_result)
        
        threading.Thread(target=perform_recheck, daemon=True).start()

    def _handle_device_recheck_result(self):
        """Handle the result of device recheck."""
        self.animation_handler.stop_animation()
        
        if self.device_connected:
            self._update_status("Status: Android device detected. Ready for file transfer.")
            self._enable_browse_buttons()
            self._validate_paths_and_update_button()
        else:
            self._update_status("Status: No Android device detected. Please connect your device and enable USB debugging.")
            self.transfer_button.set_recheck_mode(self.recheck_device)

    def start_transfer(self):
        """Start the file transfer process."""
        try:
            # Get current values
            direction = self.direction_selector.get_direction()
            remote_path = self.android_path_selector.get_path()
            local_path = self.computer_path_selector.get_path()
            
            # Validate paths
            if not self.android_path_selector.is_path_selected():
                messagebox.showerror("Error", "Please select an Android device path.")
                return
                
            if not self.computer_path_selector.is_path_selected():
                messagebox.showerror("Error", "Please select a computer path.")
                return
            
            # Check device connection
            if not self.device_manager.check_device_connection():
                messagebox.showerror("Error", "Android device not connected. Please check your connection and try again.")
                self._handle_device_disconnection()
                return
            
            # Switch to cancel mode and start transfer
            self.transfer_button.set_cancel_mode(self.cancel_transfer)
            self.animation_handler.start_transfer_animation("Status: Transferring")
            
            # Start transfer using transfer manager
            self.transfer_manager.start_transfer(
                direction, 
                remote_path, 
                local_path,
                self._on_transfer_complete
            )
            
        except Exception as e:
            self.report_error(f"Error starting transfer: {str(e)}")

    def cancel_transfer(self):
        """Cancel ongoing file transfer."""
        try:
            self.transfer_manager.cancel_transfer()
            self.animation_handler.stop_animation()
            self._update_status("Status: Transfer cancelled by user.")
            self.enable_controls()
            self._validate_paths_and_update_button()
            
        except Exception as e:
            self.report_error(f"Error cancelling transfer: {str(e)}")

    def _on_transfer_complete(self, success: bool, stats: dict, operation: str):
        """Handle transfer completion."""
        self.animation_handler.stop_animation()
        
        if success:
            self._update_status(f"Status: Transfer complete! Successfully {operation}.")
            if stats:
                self._show_transfer_stats(stats, operation)
            self._show_debugging_reminder()
        else:
            self._update_status("Status: Transfer failed. Please check your connection and try again.")
            messagebox.showerror("Transfer Failed", "The file transfer was not successful. Please check your device connection and try again.")
        
        self.enable_controls()
        self._validate_paths_and_update_button()

    def _handle_device_disconnection(self):
        """Handle when device gets disconnected."""
        self.device_connected = False
        self._clear_paths_and_disable_button()
        self._disable_browse_buttons()
        self.transfer_button.set_recheck_mode(self.recheck_device)
        self._update_status("Status: Device disconnected. Please reconnect and enable USB debugging.")

    def disable_controls(self):
        """Disable UI controls during transfer."""
        if threading.current_thread() != threading.main_thread():
            self.after(0, self._disable_controls_ui)
        else:
            self._disable_controls_ui()

    def enable_controls(self):
        """Enable UI controls after transfer."""
        if threading.current_thread() != threading.main_thread():
            self.after(0, self._enable_controls_ui)
        else:
            self._enable_controls_ui()

    def _disable_controls_ui(self):
        """Disable controls on UI thread."""
        self._disable_browse_buttons()
        
    def _enable_controls_ui(self):
        """Enable controls on UI thread."""
        self._enable_browse_buttons()

    def report_error(self, message: str):
        """Report an error message to the user."""
        if threading.current_thread() != threading.main_thread():
            self.after(0, lambda: self._report_error_ui(message))
        else:
            self._report_error_ui(message)

    def _report_error_ui(self, message: str):
        """Show error message on UI thread."""
        print(f"Error: {message}")
        self._update_status(f"Status: Error - {message}")
        messagebox.showerror("Error", message)

    def _show_transfer_stats(self, stats: dict, operation: str):
        """Show transfer statistics in a dialog."""
        self.dialog_manager.show_transfer_stats(stats, operation)

    def _show_debugging_reminder(self):
        """Show reminder about disabling USB debugging after transfer."""
        self.after(100, lambda: self.dialog_manager.show_disable_debugging_reminder())

    def on_close(self):
        """Handle window close event."""
        try:
            # Cancel any ongoing transfers
            if hasattr(self, 'transfer_manager'):
                self.transfer_manager.cancel_transfer()
            
            # Stop any animations
            if hasattr(self, 'animation_handler'):
                self.animation_handler.stop_animation()
            
            self.destroy()
        except Exception as e:
            print(f"Error during close: {e}")
            self.destroy()


def main():
    """Main entry point for the application."""
    app = AndroidFileHandlerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()