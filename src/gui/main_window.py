"""
Main Window Module
Core GUI application window for Android file transfers.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, scrolledtext

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
    from .license_agreement import LicenseAgreementFrame, check_license_agreement
except ImportError:
    # Fall back to direct imports
    from src.gui.file_browser import AndroidFileBrowser
    from src.gui.license_agreement import LicenseAgreementFrame, check_license_agreement


class AndroidFileHandlerGUI(tk.Tk):
    """Main GUI application for Android file transfers."""

    def __init__(self):
        """Initialize the main GUI application."""
        super().__init__()
        
        # Initialize business logic
        self.adb_manager = ADBManager()
        
        # Transfer tracking for thread safety
        self.current_transfer_id = 0
        self.device_connected = False
        
        # License agreement tracking
        self.license_agreed = check_license_agreement()
        self.license_frame = None
        self.main_ui_created = False
        
        self.troubleshooting_steps = (
            "Android device appears to have been disconnected and/or USB debugging is disabled.\n"
            "Please ensure your Android device is securely connected at both ends.\n\n"
            
            "To enable USB debugging:\n"
            "1. Connect your device to the computer via USB\n"
            "2. Open Settings → About phone\n"
            "3. Tap 'Build number' seven times to unlock Developer Options\n"
            "   (You only need to do this once unless you disable it, reset settings, or wipe your device)\n"
            "4. Navigate back and go to System → Developer Options\n"
            "5. Find and enable 'USB debugging'\n"
            "   (Tip: Use the search icon at the top if you can't find it)\n"
            "6. Connect via USB and tap 'Trust' when prompted\n"
            "   (Checking 'Remember' is recommended for future transfers)\n\n"
            
            "Ensure File Transfer mode is enabled:\n"
            "1. After connecting, swipe down to view notifications\n"
            "2. Look for a USB notification (often shows 'Charging over USB')\n"
            "3. Tap the notification and select 'File Transfer' or 'MTP' mode\n\n"
            
            "Note: Menu names may vary by Android version:\n"
            "• Some devices show 'Developer options' under 'System'\n"
            "• Others may have it directly in the main Settings menu\n"
            "• Samsung devices might show 'Software information' instead of 'About phone'\n\n"
            
            "If you're still having trouble:\n"
            "• Try a different USB cable or port (some cables only support charging)\n"
            "• Restart both your phone and computer\n"
            "• Make sure your phone screen is unlocked when connecting\n"
            "• Set your phone screen timeout to 30 minutes (especially for long transfers)\n\n"
            "• Use a different computer to test if the issue is computer-specific\n"
            
            "Windows users: If you see a driver installation popup, please allow it to complete.\n"
            "Linux users: You may need to run 'sudo usermod -a -G plugdev $USER' and reboot.\n"
            
            "After completing these steps, click 'Recheck for connected Android device' to try again."
        )
        
        # Setup UI based on license status
        self._setup_initial_ui()

    def _setup_initial_ui(self):
        """Setup the initial UI - either license agreement or main interface."""
        # Window configuration
        self.title("Android File Handler")
        self.geometry("520x320")
        self.minsize(520, 320)
        self.resizable(True, True)
        
        if not self.license_agreed:
            # Show license agreement first
            self._show_license_agreement()
        else:
            # Show main interface directly
            self._show_main_interface()

    def _show_license_agreement(self):
        """Show the license agreement interface."""
        # Adjust window size for license agreement
        self.geometry("700x600")
        self.minsize(700, 600)
        
        # Create license agreement frame
        self.license_frame = LicenseAgreementFrame(self, self._on_license_agreed)
    
    def _on_license_agreed(self):
        """Handle when user agrees to license."""
        self.license_agreed = True
        
        # Remove license frame
        if self.license_frame:
            self.license_frame.destroy()
            self.license_frame = None
        
        # Switch to main interface
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
        self.direction_var = tk.StringVar(value="pull")
        direction_frame = tk.Frame(self)
        direction_frame.pack(anchor="w", padx=10, pady=(10, 0))
        tk.Radiobutton(
            direction_frame,
            text="Pull (Android → Computer)",
            variable=self.direction_var,
            value="pull",
            command=self._on_direction_change,
        ).pack(side="left")
        tk.Radiobutton(
            direction_frame,
            text="Push (Computer → Android)",
            variable=self.direction_var,
            value="push",
            command=self._on_direction_change,
        ).pack(side="left", padx=(20, 0))

        # Create a container frame for the path sections that can be reordered
        self.path_container = tk.Frame(self)
        self.path_container.pack(fill="x", padx=10, pady=(10, 0))

        # Create the Android device path section
        self.android_frame = tk.Frame(self.path_container)
        self.android_label = tk.Label(self.android_frame, text="Android device:")
        self.android_label.pack(anchor="w")
        
        android_path_frame = tk.Frame(self.android_frame)
        android_path_frame.pack(fill="x", pady=(0, 10))
        self.remote_path_var = tk.StringVar(value="Please select file or folder ->")
        self.remote_path_display = tk.Label(
            android_path_frame, 
            textvariable=self.remote_path_var, 
            anchor="w"
        )
        self.remote_path_display.pack(side="left", fill="x", expand=True)
        self.remote_browse_btn = tk.Button(
            android_path_frame, text="Browse...", command=self.browse_remote_folder
        )
        self.remote_browse_btn.pack(side="right", padx=(5, 0))

        # Create the Computer path section
        self.computer_frame = tk.Frame(self.path_container)
        self.computer_label = tk.Label(self.computer_frame, text="Computer:")
        self.computer_label.pack(anchor="w")
        
        computer_path_frame = tk.Frame(self.computer_frame)
        computer_path_frame.pack(fill="x", pady=(0, 10))
        self.local_path_var = tk.StringVar(value="Please select file or folder ->")
        self.local_path_display = tk.Label(
            computer_path_frame, 
            textvariable=self.local_path_var, 
            anchor="w"
        )
        self.local_path_display.pack(side="left", fill="x", expand=True)
        self.local_browse_btn = tk.Button(
            computer_path_frame, text="Browse...", command=self.browse_local_folder
        )
        self.local_browse_btn.pack(side="right", padx=(5, 0))

        # Initially arrange for pull (Android on top)
        self._arrange_path_sections()

        # Status label (responsive with word wrapping)
        self.status_label = tk.Label(
            self, 
            text="Status: Idle", 
            wraplength=0,  # Will be set dynamically
            justify="center",
            anchor="center"
        )
        self.status_label.pack(padx=10, fill="x", pady=(20, 5))
        
        # Bind window resize event to update label wrapping
        self.bind("<Configure>", self._on_window_configure)

        # Start/Recheck button (will change based on device state)
        self.start_btn = tk.Button(
            self, text="Start Transfer", command=self.handle_button_click, state="disabled"
        )
        self.start_btn.pack(pady=10)

        # Initially disable browse buttons until device is connected
        self._disable_browse_buttons()

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
            self, self.adb_manager, self.remote_path_var, self._validate_paths_and_update_button
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

    def _on_window_configure(self, event):
        """Handle window resize events to update label wrapping."""
        # Only handle configure events for the main window, not child widgets
        if event.widget == self:
            # Calculate available width for the status label
            # Account for padding (10px on each side) and some margin
            available_width = self.winfo_width() - 40
            if available_width > 100:  # Minimum reasonable width
                self.status_label.config(wraplength=available_width)

    def _validate_paths_and_update_button(self):
        """Check if both paths are selected and update button state accordingly."""
        remote_path = self.remote_path_var.get().strip()
        local_path = self.local_path_var.get().strip()
        
        # Check if both paths are set and not the default placeholder text
        remote_selected = remote_path and remote_path != "Please select file or folder ->"
        local_selected = local_path and local_path != "Please select file or folder ->"
        
        # Only manage state if button is in "Start Transfer" mode
        if self.start_btn.cget("text") == "Start Transfer":
            if remote_selected and local_selected:
                self.start_btn.config(state="normal")
            else:
                self.start_btn.config(state="disabled")

    def _clear_paths_and_disable_button(self):
        """Clear path selections and disable the transfer button."""
        self.remote_path_var.set("Please select file or folder ->")
        self.local_path_var.set("Please select file or folder ->")
        # Only disable if button is in "Start Transfer" mode
        if self.start_btn.cget("text") == "Start Transfer":
            self.start_btn.config(state="disabled")

    def _enable_browse_buttons(self):
        """Enable both browse buttons when device is connected."""
        self.remote_browse_btn.config(state="normal")
        self.local_browse_btn.config(state="normal")

    def _disable_browse_buttons(self):
        """Disable both browse buttons when no device is detected."""
        self.remote_browse_btn.config(state="disabled")
        self.local_browse_btn.config(state="disabled")

    def _start_transfer_animation(self):
        """Start the 'Transferring...' animation."""
        self.transfer_dots = 0
        self.transfer_animation_job = True  # Mark as active before starting
        self._animate_transfer_text()

    def _animate_transfer_text(self):
        """Animate the transfer text with dots."""
        if self.transfer_animation_job is not None:
            dots = "." * (self.transfer_dots + 1)
            status_text = f"Transferring{dots}"
            self.status_label.config(text=status_text)
            self.update_idletasks()  # Force immediate UI update
            self.transfer_dots = (self.transfer_dots + 1) % 5  # Cycle 0-4 dots
            # Schedule next update in 500ms
            self.transfer_animation_job = self.after(500, self._animate_transfer_text)

    def _stop_transfer_animation(self):
        """Stop the transfer animation."""
        if self.transfer_animation_job is not None:
            if isinstance(self.transfer_animation_job, str):  # It's an after job ID
                self.after_cancel(self.transfer_animation_job)
            self.transfer_animation_job = None

    def _initialize_app(self):
        """Initialize the application - check ADB and device."""
        # Check adb availability
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
            
            self.disable_controls()
            self._update_status("ADB not found locally. Downloading...")
            self.update()
            self.adb_manager.download_and_extract_adb()
            success = is_adb_available()
            if success:
                self._update_status("ADB downloaded and ready.")
                self.enable_controls()
            else:
                self._update_status(
                    "Failed to download/access Android Debug Bridge tools. Please check your internet and for any blocking security pop-ups and restart."
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
            self._disable_browse_buttons()
            self._clear_paths_and_disable_button()
            self._update_status(
                "No Android devices detected. Please check the USB connection at both ends is securely inserted, USB debugging is enabled, and that File Transfer mode is turned on."
            )
            self._switch_to_recheck_mode()
            self.show_enable_debugging_instructions()
        else:
            self.device_connected = True
            self._enable_browse_buttons()
            self._update_status(f"Device detected: {device}")
            self._switch_to_transfer_mode()
            self.enable_controls()

    def browse_remote_folder(self):
        """Browse remote Android files and folders."""
        # Pass the current direction to the browser
        direction = self.direction_var.get()
        self.browser.show_browser(direction)

    def show_file_folder_selection_notice(self):
        """Show instructions for file and folder selection in a custom dialog."""
        # Create custom dialog window
        dialog = tk.Toplevel(self)
        dialog.title("File/Folder Selection Notice")
        dialog.geometry("600x250")
        dialog.minsize(600, 250)
        dialog.resizable(True, True)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog on the parent window
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (600 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (250 // 2)
        dialog.geometry(f"600x250+{x}+{y}")
        
        # Track if OK was clicked
        self.dialog_confirmed = False
        
        # Create main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Selection notice text
        notice_text = (
            "This is just a quick note about how file and folder selection works in this application.\n\n"
            "If you want to select a file for transfer, simply click on the file to select it.\n\n"
            "If you want to select a folder for transfer, the folder that you navigate to (the current directory you are viewing, not a highlighted folder) will be selected for transfer.\n\n"
            "You can only transfer one file or one folder at a time."
        )
        
        # Create responsive text label
        text_label = tk.Label(
            main_frame,
            text=notice_text,
            justify="left",
            anchor="nw",
            wraplength=0,  # Will be set dynamically
            font=("Arial", 10)
        )
        text_label.pack(fill="both", expand=True, pady=(0, 20))
        
        # OK button with confirmation callback
        def on_ok_clicked():
            self.dialog_confirmed = True
            dialog.destroy()
        
        ok_button = tk.Button(
            main_frame,
            text="OK",
            command=on_ok_clicked,
            width=10,
            font=("Arial", 10)
        )
        ok_button.pack(pady=10)
        
        # Configure text wrapping on dialog resize
        def on_dialog_configure(event):
            if event.widget == dialog:
                # Calculate available width for text (account for padding and margins)
                available_width = dialog.winfo_width() - 60  # 20px padding * 2 + some margin
                if available_width > 200:  # Minimum reasonable width
                    text_label.config(wraplength=available_width)
        
        dialog.bind("<Configure>", on_dialog_configure)
        
        # Set initial wrap length
        dialog.after(10, lambda: on_dialog_configure(type('Event', (), {'widget': dialog})()))
        
        # Handle window close (X button) - treat as cancel
        def on_dialog_close():
            self.dialog_confirmed = False
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Wait for dialog to close
        dialog.wait_window()

    def browse_local_folder(self):
        """Browse for local folder or file based on direction."""
        import tkinter.filedialog as fd
        import os
        from tkinter import messagebox
        
        # Show helpful notification about folder selection behavior
        self.show_file_folder_selection_notice()
        
        # Only proceed if user clicked OK
        if not getattr(self, 'dialog_confirmed', False):
            return  # User closed dialog without clicking OK
        
        direction = self.direction_var.get()
        
        # Set initial directory to user's home directory
        initial_dir = os.path.expanduser("~")
        
        if direction == "push":
            # For push, show file selection first, then folder selection if cancelled
            
            # First try file selection
            selected_path = fd.askopenfilename(
                title="Select file to push to Android device",
                initialdir=initial_dir,
                filetypes=[("All files", "*.*")]
            )
            
            # If no file was selected, offer folder selection as an alternative
            if not selected_path:
                selected_path = fd.askdirectory(
                    title="Select folder to push to Android device",
                    initialdir=initial_dir
                )
            
            # Only set the path if something was actually selected
            # If user cancels both dialogs, selected_path will be empty and nothing happens
            if selected_path:
                self.local_path_var.set(selected_path)
                self._validate_paths_and_update_button()
                
        else:  # pull direction
            # For pull, only allow folder selection (destination)
            folder = filedialog.askdirectory(
                title="Select destination folder for pulled files",
                initialdir=initial_dir
            )
            if folder:
                self.local_path_var.set(folder)
                self._validate_paths_and_update_button()

    def disable_controls(self):
        """Disable UI controls during operations."""
        # Path displays are already read-only (Labels), no need to disable them
        # Don't disable start_btn here - it will be handled by button mode switching
        pass

    def enable_controls(self):
        """Enable UI controls after operations (thread-safe)."""
        # Schedule UI update on main thread
        self.after(0, self._enable_controls_ui)

    def _enable_controls_ui(self):
        """Internal method to enable controls on main thread."""
        # Path displays are already read-only (Labels), no need to enable them
        # Button state is handled by mode switching methods
        pass

    def _on_direction_change(self):
        """Handle radio button direction change."""
        self._arrange_path_sections()

    def _arrange_path_sections(self):
        """Arrange the Android and Computer path sections based on direction."""
        # Remove both frames from container
        self.android_frame.pack_forget()
        self.computer_frame.pack_forget()
        
        direction = self.direction_var.get()
        if direction == "pull":
            # Pull: Android → Computer (Android on top)
            self.android_frame.pack(fill="x", pady=(0, 5))
            self.computer_frame.pack(fill="x")
        else:  # push
            # Push: Computer → Android (Computer on top)
            self.computer_frame.pack(fill="x", pady=(0, 5))
            self.android_frame.pack(fill="x")

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
            text="Start Transfer", command=self.start_transfer
        )
        # Only enable if both paths are selected, otherwise keep disabled
        self._validate_paths_and_update_button()

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
        # Create custom dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Check device connection and enable USB Debugging")
        dialog.geometry("700x800")  # Increased height for better button spacing
        dialog.minsize(700, 800)  # Set minimum size to ensure all content is visible
        dialog.resizable(True, True)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog on the parent window
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (700 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (450 // 2)
        dialog.geometry(f"700x450+{x}+{y}")
        
        # Create main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create responsive text label
        text_label = tk.Label(
            main_frame,
            text=self.troubleshooting_steps,
            justify="left",
            anchor="nw",
            wraplength=0,  # Will be set dynamically
            font=("Arial", 10)
        )
        text_label.pack(fill="both", expand=True, pady=(0, 20))
        
        # OK button
        ok_button = tk.Button(
            main_frame,
            text="OK",
            command=dialog.destroy,
            width=10,
            font=("Arial", 10)
        )
        ok_button.pack(pady=10)
        
        # Configure text wrapping on dialog resize
        def on_dialog_configure(event):
            if event.widget == dialog:
                # Calculate available width for text (account for padding and margins)
                available_width = dialog.winfo_width() - 60  # 20px padding * 2 + some margin
                if available_width > 200:  # Minimum reasonable width
                    text_label.config(wraplength=available_width)
        
        dialog.bind("<Configure>", on_dialog_configure)
        
        # Set initial wrap length
        dialog.after(10, lambda: on_dialog_configure(type('Event', (), {'widget': dialog})()))
        
        # After user clicks OK, ensure recheck button is enabled
        dialog.protocol("WM_DELETE_WINDOW", lambda: [dialog.destroy(), self.after(0, self._enable_recheck_after_dialog)])
        ok_button.config(command=lambda: [dialog.destroy(), self.after(0, self._enable_recheck_after_dialog)])

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
        # Recheck device connectivity status before starting transfer
        device = self.adb_manager.check_device()
        if not device:
            # Device is no longer connected, update status and reset to recheck mode
            self.device_connected = False
            self._disable_browse_buttons()
            self._clear_paths_and_disable_button()
            self._update_status(
                "No Android devices detected. Please check the USB connection at both ends is securely inserted, USB debugging is enabled, and that File Transfer mode is turned on."
            )
            self._switch_to_recheck_mode()
            self.show_enable_debugging_instructions()
            return
        else:
            # Device is still connected, update status if needed
            if not self.device_connected:
                self.device_connected = True
                self._enable_browse_buttons()
                self._update_status(f"Device detected: {device}")

        # Double-check device is still connected before starting transfer
        if not self.device_connected:
            msg = (
                self.troubleshooting_steps + "\n\n"
            )
            messagebox.showerror("No Android Device Detected", msg)
            self._switch_to_recheck_mode()
            return

        remote_path = self.remote_path_var.get().strip()
        local_path = self.local_path_var.get().strip()
        direction = self.direction_var.get()

        # Validate inputs
        if not remote_path:
            messagebox.showerror("Input Error", "Remote path cannot be empty.")
            return
        
        # For push operations, validate local path
        if direction == "push":
            if not local_path or (not os.path.isfile(local_path) and not os.path.isdir(local_path)):
                messagebox.showerror(
                    "Input Error", "Please select a valid local file or folder."
                )
                return
        else:  # pull operations
            if not local_path or not os.path.isdir(local_path):
                messagebox.showerror(
                    "Input Error", "Please select a valid local destination folder for pulled files."
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

        # Determine if we're dealing with files or folders
        if direction == "pull":
            # For pull, check if remote path is a file
            is_file = self._is_remote_file(remote_path)
            threading.Thread(
                target=self._transfer_thread,
                args=(direction, remote_path, local_path, transfer_id, is_file),
                daemon=True,
            ).start()
        elif direction == "push":
            # For push, check if local path is a file
            is_file = os.path.isfile(local_path)
            threading.Thread(
                target=self._transfer_thread,
                args=(direction, local_path, remote_path, transfer_id, is_file),
                daemon=True,
            ).start()
        else:
            self.report_error("Invalid transfer direction selected.")
            self.enable_controls()

    def _transfer_thread(self, direction: str, source_path: str, dest_path: str, transfer_id: int, is_file: bool):
        """Unified thread function for all transfer operations."""
        try:
            # Check if this transfer is still current
            if self.current_transfer_id != transfer_id:
                return

            # Recheck device connectivity before proceeding with transfer
            device = self.adb_manager.check_device()
            if not device:
                # Device disconnected during transfer setup
                if self.current_transfer_id == transfer_id:
                    self._stop_transfer_animation()
                    self.after(0, self._handle_device_disconnection)
                return

            # Get the appropriate transfer method
            transfer_method, transfer_type = self._get_file_transfer_methods(direction, is_file)
            
            # For pull operations with files, we need to construct the full destination path
            if direction == "pull" and is_file:
                # Extract filename from source and append to destination directory
                filename = source_path.split("/")[-1]
                full_dest_path = os.path.join(dest_path, filename)
                success = transfer_method(source_path, full_dest_path)
            else:
                success = transfer_method(source_path, dest_path)
            
            if success and self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                transfer_desc = "File" if is_file else "Folder"
                self._update_status(f"{transfer_desc} transfer completed successfully. To start another transfer, please select another file or folder.")
                self.show_disable_debugging_reminder()
                # Clear paths and disable button for next transfer
                self.after(0, self._clear_paths_and_disable_button)
        except Exception as e:
            if self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                transfer_desc = "file" if is_file else "folder"
                self.report_error(f"{direction.capitalize()} {transfer_desc} operation failed: {e}")
        finally:
            if self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self.enable_controls()
                # Restore proper button state after transfer
                self.after(0, self._restore_button_state)

    def _pull_thread(self, remote_path: str, local_path: str, transfer_id: int):
        """Thread function for pull operations."""
        try:
            # Check if this transfer is still current
            if self.current_transfer_id != transfer_id:
                return

            success = self.adb_manager.pull_folder(remote_path, local_path)
            if success and self.current_transfer_id == transfer_id:
                self._stop_transfer_animation()
                self._update_status("Transfer completed successfully. To start another transfer, please select another file or folder.")
                self.show_disable_debugging_reminder()
                # Clear paths and disable button for next transfer
                self.after(0, self._clear_paths_and_disable_button)
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
                # Clear paths and disable button for next transfer
                self.after(0, self._clear_paths_and_disable_button)
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

    def _handle_device_disconnection(self):
        """Handle device disconnection during transfers."""
        self.device_connected = False
        self._disable_browse_buttons()
        self._clear_paths_and_disable_button()
        self._update_status(
            "No Android devices detected. Please check the USB connection at both ends is securely inserted, USB debugging is enabled, and that File Transfer mode is turned on."
        )
        self._switch_to_recheck_mode()
        self.enable_controls()
        self.show_enable_debugging_instructions()

    def _is_remote_file(self, remote_path: str) -> bool:
        """Check if the remote path points to a file (not a directory)."""
        try:
            # Use ls -la to check if it's a file
            result = self.adb_manager.run_adb_command(
                ["shell", "ls", "-la", remote_path]
            )
            if isinstance(result, tuple) and len(result) == 3:
                stdout, stderr, returncode = result
                if returncode == 0 and stdout:
                    # If the output starts with '-', it's a regular file
                    return stdout.strip().startswith('-')
            return False
        except Exception:
            return False

    def _get_file_transfer_methods(self, direction: str, is_file: bool):
        """Get the appropriate transfer methods based on direction and type."""
        if direction == "pull":
            if is_file:
                return self.adb_manager.pull_file, "file"
            else:
                return self.adb_manager.pull_folder, "folder"
        else:  # push
            if is_file:
                return self.adb_manager.push_file, "file"
            else:
                return self.adb_manager.push_folder, "folder"

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
    # If running in CI mode, auto-close after 10 seconds
    if os.getenv('CI_MODE') == 'true':
        def auto_close():
            time.sleep(10)
            app.quit()
        
        threading.Thread(target=auto_close, daemon=True).start()
        print("CI Mode: Application will auto-close in 10 seconds")
    app.mainloop()


if __name__ == "__main__":
    main()
