"""
Main Window Module
Core GUI application window for Android file transfers.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

try:
    # Try relative import first (when used as module)
    from ..adb_manager import (
        ADBManager,
        is_adb_available,
    )
except ImportError:
    # Fall back to direct import (when run directly)
    from adb_manager import (
        ADBManager,
        is_adb_available,
    )

try:
    # Try relative imports first
    from .file_browser import AndroidFileBrowser
except ImportError:
    # Fall back to direct imports
    from src.gui.file_browser import AndroidFileBrowser


class AndroidFileHandlerGUI(tk.Tk):
    """Main GUI application for Android file transfers."""

    def __init__(self):
        super().__init__()

        # Initialize business logic
        self.adb_manager = ADBManager()

        # Transfer tracking for thread safety
        self.current_transfer_id = 0
        self.device_connected = False  # Track device connection state

        # Setup UI
        self._setup_ui()
        self._initialize_components()
        self._initialize_app()

    def _setup_ui(self):
        """Setup the user interface."""
        # Window configuration
        self.title("Android File Handler")
        self.geometry("520x320")
        self.minsize(520, 320)
        self.resizable(True, True)

        # Direction selection
        self.direction_var = tk.StringVar(value="pull")
        direction_frame = tk.Frame(self)
        direction_frame.pack(anchor="w", padx=10, pady=(10, 0))
        tk.Radiobutton(
            direction_frame,
            text="Pull (Android → Computer)",
            variable=self.direction_var,
            value="pull",
        ).pack(side="left")
        tk.Radiobutton(
            direction_frame,
            text="Push (Computer → Android)",
            variable=self.direction_var,
            value="push",
        ).pack(side="left", padx=(20, 0))

        # Remote folder path
        tk.Label(self, text="Remote folder path (Android device):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.remote_path_var = tk.StringVar()
        remote_path_frame = tk.Frame(self)
        remote_path_frame.pack(fill="x", padx=10)
        self.remote_path_entry = tk.Entry(
            remote_path_frame, textvariable=self.remote_path_var, width=50
        )
        self.remote_path_entry.pack(side="left", fill="x", expand=True)

        # Browse button for remote path
        tk.Button(
            remote_path_frame, text="Browse...", command=self.browse_remote_folder
        ).pack(side="right", padx=(5, 0))

        # Local folder path
        tk.Label(self, text="Local destination folder (Computer):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.local_path_var = tk.StringVar()
        local_path_frame = tk.Frame(self)
        local_path_frame.pack(fill="x", padx=10)
        self.local_path_entry = tk.Entry(
            local_path_frame, textvariable=self.local_path_var, width=50
        )
        self.local_path_entry.pack(side="left", fill="x", expand=True)
        tk.Button(
            local_path_frame, text="Browse...", command=self.browse_local_folder
        ).pack(side="right", padx=(5, 0))

        # Status label
        self.status_label = tk.Label(self, text="Status: Idle")
        self.status_label.pack(anchor="w", padx=10, fill="x", pady=(20, 5))

        # Start/Recheck button (will change based on device state)
        self.start_btn = tk.Button(
            self, text="Start Transfer", command=self.handle_button_click
        )
        self.start_btn.pack(pady=10)

        # Window close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _initialize_components(self):
        """Initialize GUI components and handlers."""
        # Transfer animation state
        self.transfer_animation_job = None
        self.transfer_dots = 0
        
        # Set up ADB callbacks to our own methods
        self.adb_manager.set_progress_callback(self._update_progress)
        self.adb_manager.set_status_callback(self._update_status)

        # Browser component
        self.browser = AndroidFileBrowser(
            self, self.adb_manager, self.remote_path_var
        )

    def _update_progress(self, percentage):
        """Handle progress updates (simplified)."""
        # We ignore the percentage and just rely on status updates
        pass

    def _update_status(self, message: str):
        """Update status label (thread-safe)."""
        # Don't update status if transfer animation is running
        if self.transfer_animation_job is not None:
            return  # Ignore ADB status updates during transfer animation
        
        def update_ui():
            self.status_label.config(text=message)
            self.update_idletasks()
        
        self.after(0, update_ui)

    def _start_transfer_animation(self):
        """Start the 'Transferring...' animation."""
        print("[DEBUG] Starting transfer animation")
        self.transfer_dots = 0
        self.transfer_animation_job = True  # Mark as active before starting
        self._animate_transfer_text()

    def _animate_transfer_text(self):
        """Animate the transfer text with dots."""
        if self.transfer_animation_job is not None:
            dots = "." * (self.transfer_dots + 1)
            status_text = f"Transferring{dots}"
            self.status_label.config(text=status_text)
            print(f"[DEBUG] Animation update: {status_text}")  # Debug output
            self.update_idletasks()  # Force immediate UI update
            self.transfer_dots = (self.transfer_dots + 1) % 5  # Cycle 0-4 dots
            # Schedule next update in 500ms
            self.transfer_animation_job = self.after(500, self._animate_transfer_text)

    def _stop_transfer_animation(self):
        """Stop the transfer animation."""
        print("[DEBUG] Stopping transfer animation")
        if self.transfer_animation_job is not None:
            if isinstance(self.transfer_animation_job, str):  # It's an after job ID
                self.after_cancel(self.transfer_animation_job)
            self.transfer_animation_job = None

    def _initialize_app(self):
        """Initialize the application - check ADB and device."""
        # Check adb availability
        if not is_adb_available():
            self.disable_controls()
            self._update_status("ADB not found locally. Downloading...")
            self.update()
            success = self.adb_manager.download_and_extract_adb()
            if success:
                self._update_status("ADB downloaded and ready.")
                self.enable_controls()
            else:
                self._update_status(
                    "Failed to download ADB. Please check your internet and restart."
                )
                messagebox.showerror("Error", "Failed to download ADB tools. Exiting.")
                self.quit()
                return

        # Check device connected
        self.check_device_connection()

    def check_device_connection(self):
        """Check for device connection and update UI accordingly."""
        self._update_status("Checking for connected device...")
        self.update()
        device = self.adb_manager.check_device()
        if not device:
            self.device_connected = False
            self.disable_controls()
            self._update_status(
                "No device detected. Enable USB debugging and connect your device."
            )
            self._switch_to_recheck_mode()
            self.show_enable_debugging_instructions()
        else:
            self.device_connected = True
            self._update_status(f"Device detected: {device}")
            self._switch_to_transfer_mode()
            self.enable_controls()

    def browse_remote_folder(self):
        """Browse remote Android folders."""
        self.browser.show_browser()

    def browse_local_folder(self):
        """Browse for local folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.local_path_var.set(folder)

    def disable_controls(self):
        """Disable UI controls during operations."""
        self.remote_path_entry.config(state="disabled")
        self.local_path_entry.config(state="disabled")
        # Don't disable start_btn here - it will be handled by button mode switching

    def enable_controls(self):
        """Enable UI controls after operations (thread-safe)."""
        # Schedule UI update on main thread
        self.after(0, self._enable_controls_ui)

    def _enable_controls_ui(self):
        """Internal method to enable controls on main thread."""
        self.remote_path_entry.config(state="normal")
        self.local_path_entry.config(state="normal")
        # Button state is handled by mode switching methods

    def _switch_to_recheck_mode(self):
        """Switch button to recheck device mode."""
        self.start_btn.config(
            text="Recheck for connected Android device",
            command=self.recheck_device,
            state="normal",
        )

    def _switch_to_transfer_mode(self):
        """Switch button to transfer mode."""
        self.start_btn.config(
            text="Start Transfer", command=self.start_transfer, state="normal"
        )

    def _switch_to_cancel_mode(self):
        """Switch button to cancel transfer mode."""
        self.start_btn.config(
            text="Cancel Transfer", command=self.cancel_transfer, state="normal"
        )

    def handle_button_click(self):
        """Handle button click - delegates to appropriate method based on device state."""
        if self.device_connected:
            self.start_transfer()
        else:
            self.recheck_device()

    def recheck_device(self):
        """Recheck for connected Android device."""
        # Temporarily disable the button during recheck
        self.start_btn.config(state="disabled")
        self.start_btn.config(text="Checking...")

        # Use after() to allow UI to update before blocking operation
        self.after(100, self._perform_device_recheck)

    def _perform_device_recheck(self):
        """Perform the actual device recheck."""
        self.check_device_connection()

    def cancel_transfer(self):
        """Cancel the current transfer."""
        print("[DEBUG] Cancel transfer requested")
        
        # Cancel the actual ADB process
        cancelled = self.adb_manager.cancel_transfer()
        
        # Increment transfer ID to invalidate current transfer
        self.current_transfer_id += 1
        
        # Stop animation and restore UI
        self._stop_transfer_animation()
        
        # Use after() to ensure status update happens after animation stops
        def update_cancelled_status():
            if cancelled:
                self.status_label.config(text="Transfer cancelled by user.")
            else:
                self.status_label.config(text="Transfer cancellation failed.")
            self.update_idletasks()
        
        self.after(0, update_cancelled_status)
        self.enable_controls()
        
        # Restore proper button state
        if self.device_connected:
            self._switch_to_transfer_mode()
        else:
            self._switch_to_recheck_mode()

    def show_enable_debugging_instructions(self):
        """Show instructions to connect device, enable file transfer, and to enable USB debugging."""
        msg = (
            "Additionally, ensure your device is set to 'File Transfer' mode:\n"
            "1. When you connect your device, swipe down to check the notification panel.\n"
            "2. Look for a 'USB' notification that will tell you what mode the device is in (usually 'Charging over USB') and tap it.\n"
            "3. Select 'File Transfer' or 'MTP' mode.\n\n"
            "Please ensure your Android device is securely connected to the computer at both ends.\n\n"
            "To enable USB debugging:\n"
            "1. Connect your device to the computer via USB.\n"
            "2. Open Settings → About phone.\n"
            "3. Tap 'Build number' seven times to unlock Developer Options.\n"
            "4. Go back to Settings → Developer Options.\n"
            "5. Enable 'USB debugging'.\n"
            "6. Connect your phone via USB and accept the prompt to allow debugging.\n\n"
            "After enabling USB debugging, please click the 'Recheck for connected Android device' button to try again."
        )
        result = messagebox.showinfo(
            "Check device connection and enable USB Debugging", msg
        )
        # After user clicks OK, ensure recheck button is enabled
        self.after(0, self._enable_recheck_after_dialog)

    def _enable_recheck_after_dialog(self):
        """Re-enable recheck button after user dismisses the dialog."""
        if not self.device_connected:
            self._switch_to_recheck_mode()

    def show_disable_debugging_reminder(self):
        """Show reminder to disable USB debugging after transfer (thread-safe)."""
        # Schedule UI update on main thread
        self.after(0, self._show_debugging_reminder_ui)

    def _show_debugging_reminder_ui(self):
        """Internal method to show debugging reminder on main thread."""
        msg = (
            "Transfer completed!\n\n"
            "For security, please disable USB debugging when done:\n"
            "Settings → Developer Options → disable 'USB debugging'."
        )
        messagebox.showinfo("Disable USB Debugging", msg)

    def start_transfer(self):
        """Start the file transfer operation."""
        # Double-check device is still connected before starting transfer
        if not self.device_connected:
            msg = (
                "Android device appears to have been disconnected and/or USB debugging is disabled.\n"
                "Please ensure your Android device is securely connected to the computer at both ends.\n\n"
                "Additionally, ensure your device is set to 'File Transfer' mode:\n"
                "1. When you connect your device, swipe down to check the notification panel.\n"
                "2. Look for a 'USB' notification that will tell you what mode the device is in (usually 'Charging over USB') and tap it.\n"
                "3. Select 'File Transfer' or 'MTP' mode.\n\n"
                "To enable USB debugging:\n"
                "1. Connect your device to the computer via USB.\n"
                "2. Open Settings → About phone.\n"
                "3. Tap 'Build number' seven times to unlock Developer Options.\n"
                "4. Go back to Settings → Developer Options.\n"
                "5. Enable 'USB debugging'.\n"
                "6. Connect your phone via USB and accept the prompt to allow debugging.\n\n"
                "After enabling USB debugging, please click the 'Recheck for connected Android device' button to try again."
            )
            messagebox.showerror("No Android Device Detected", msg)
            self._switch_to_recheck_mode()
            return

        remote_path = self.remote_path_var.get().strip()
        local_path = self.local_path_var.get().strip()
        direction = self.direction_var.get()

        # Validate inputs
        if not remote_path:
            messagebox.showerror("Input Error", "Remote folder path cannot be empty.")
            return
        if not local_path or not os.path.isdir(local_path):
            messagebox.showerror(
                "Input Error", "Please select a valid local destination folder."
            )
            return

        # Final device check before transfer
        device = self.adb_manager.check_device()
        if not device:
            self.device_connected = False
            messagebox.showerror(
                "Device Disconnected",
                "Android device was disconnected. Please reconnect and try again.",
            )
            self._switch_to_recheck_mode()
            return

        # Start transfer
        self.current_transfer_id += 1
        transfer_id = self.current_transfer_id

        self.disable_controls()
        # Switch button to cancel mode during transfer
        self._switch_to_cancel_mode()
        # Start the transfer animation
        self._start_transfer_animation()

        if direction == "pull":
            threading.Thread(
                target=self._pull_thread,
                args=(remote_path, local_path, transfer_id),
                daemon=True,
            ).start()
        elif direction == "push":
            threading.Thread(
                target=self._push_thread,
                args=(local_path, remote_path, transfer_id),
                daemon=True,
            ).start()
        else:
            self.report_error("Invalid transfer direction selected.")
            self.enable_controls()

    def _pull_thread(self, remote_path: str, local_path: str, transfer_id: int):
        """Thread function for pull operations."""
        try:
            # Check if this transfer is still current
            if self.current_transfer_id != transfer_id:
                return

            success = self.adb_manager.pull_folder(remote_path, local_path)
            if success and self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self._update_status("Transfer completed successfully.")
                self.show_disable_debugging_reminder()
        except Exception as e:
            if self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self.report_error(f"Pull operation failed: {e}")
        finally:
            if self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self.enable_controls()
                # Restore proper button state after transfer
                self.after(0, self._restore_button_state)

    def _push_thread(self, local_path: str, remote_path: str, transfer_id: int):
        """Thread function for push operations."""
        try:
            # Check if this transfer is still current
            if self.current_transfer_id != transfer_id:
                return

            success = self.adb_manager.push_folder(local_path, remote_path)
            if success and self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self._update_status("Transfer completed successfully.")
                self.show_disable_debugging_reminder()
        except Exception as e:
            if self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self.report_error(f"Push operation failed: {e}")
        finally:
            if self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self.enable_controls()
                # Restore proper button state after transfer
                self.after(0, self._restore_button_state)

    def _restore_button_state(self):
        """Restore the correct button state based on device connection."""
        if self.device_connected:
            self._switch_to_transfer_mode()
        else:
            self._switch_to_recheck_mode()

    def report_error(self, message: str):
        """Report an error to the user (thread-safe)."""
        # Schedule UI update on main thread
        self.after(0, lambda: self._report_error_ui(message))

    def _report_error_ui(self, message: str):
        """Internal method to report error on main thread."""
        self.status_label.config(text=f"Error: {message}")
        messagebox.showerror("Error", message)
        self.enable_controls()

    def on_close(self):
        """Handle window close event."""
        self.destroy()


def main():
    """Main function to run the application."""
    if sys.platform not in ["win32", "linux"]:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Unsupported OS", "This application only supports Windows or Linux."
        )
        sys.exit(1)

    app = AndroidFileHandlerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
