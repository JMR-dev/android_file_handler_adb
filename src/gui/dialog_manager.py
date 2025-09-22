"""
Dialog Manager Module
Handles various dialog boxes and message windows for the application.
"""

import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
import os
from typing import Optional, Tuple


class DialogManager:
    """Manages various dialog boxes and user interactions."""
    
    def __init__(self, parent_window: tk.Tk):
        """Initialize the dialog manager.
        
        Args:
            parent_window: The main window instance
        """
        self.parent = parent_window
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
    
    def show_file_folder_selection_notice(self) -> bool:
        """Show instructions for file and folder selection in a custom dialog.
        
        Returns:
            True if user clicked OK, False if user cancelled or closed dialog
        """
        # Create custom dialog window
        dialog = tk.Toplevel(self.parent)
        dialog.title("File/Folder Selection Notice")
        dialog.geometry("600x250")
        dialog.minsize(600, 250)
        dialog.resizable(True, True)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog on the parent window
        dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (600 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (250 // 2)
        dialog.geometry(f"600x250+{x}+{y}")
        
        # Track if OK was clicked
        dialog_confirmed = False
        
        # Create main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Selection notice text
        notice_text = (
            "How file and folder selection works in this application\n\n"
            "If you want to select a file for transfer, simply click on the file to select it.\n\n"
            "If you want to select a folder for transfer, the folder that you navigate to "
            "(the current directory you are viewing, not a highlighted folder) will be selected for transfer.\n\n"
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
            nonlocal dialog_confirmed
            dialog_confirmed = True
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
            nonlocal dialog_confirmed
            dialog_confirmed = False
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return dialog_confirmed
    
    def show_enable_debugging_instructions(self, callback: Optional[callable] = None) -> None:
        """Show instructions to connect device, enable file transfer, and enable USB debugging.
        
        Args:
            callback: Optional callback to execute after dialog is closed
        """
        # Create custom dialog window
        dialog = tk.Toplevel(self.parent)
        dialog.title("Check device connection and enable USB Debugging")
        dialog.geometry("700x800")  # Increased height for better button spacing
        dialog.minsize(700, 800)  # Set minimum size to ensure all content is visible
        dialog.resizable(True, True)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog on the parent window
        dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (700 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (450 // 2)
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
        
        # Handle dialog close
        def on_close():
            dialog.destroy()
            if callback:
                callback()
        
        # After user clicks OK, ensure callback is executed
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        ok_button.config(command=on_close)
    
    def show_disable_debugging_reminder(self) -> None:
        """Show reminder to disable USB debugging after transfer."""
        msg = (
            "Transfer completed!\n\n"
            "For security, please disable USB debugging when done:\n"
            "Settings → Developer Options → disable 'USB debugging'."
        )
        messagebox.showinfo("Disable USB Debugging", msg)
    
    def show_transfer_stats(self, stats: dict, operation: str, deduplicator=None) -> None:
        """Show transfer statistics dialog.
        
        Args:
            stats: Dictionary containing transfer statistics
            operation: Type of operation ("Pull" or "Push")
            deduplicator: Optional deduplicator instance for byte formatting
        """
        # Format bytes saved
        bytes_saved_str = ""
        if stats['bytes_saved'] > 0:
            if deduplicator and hasattr(deduplicator, 'format_bytes'):
                bytes_saved_str = f" ({deduplicator.format_bytes(stats['bytes_saved'])} saved)"
            else:
                bytes_saved_str = f" ({stats['bytes_saved']} bytes saved)"
        
        # Build message
        title = f"{operation} Transfer Complete"
        
        if stats['total_files'] == 0:
            message = "No files were found to transfer."
        else:
            message_parts = [
                f"Transfer completed successfully!\n",
                f"Files found: {stats['total_files']}",
                f"Files transferred: {stats['transferred']}",
                f"Duplicate files skipped: {stats['skipped']}{bytes_saved_str}"
            ]
            
            if stats['skipped'] > 0:
                message_parts.append(f"\nDuplicate detection helped avoid unnecessary transfers!")
            
            message = "\n".join(message_parts)
        
        # Show dialog
        messagebox.showinfo(title, message)
    
    def show_error(self, title: str, message: str) -> None:
        """Show an error dialog.
        
        Args:
            title: Dialog title
            message: Error message to display
        """
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str) -> None:
        """Show an info dialog.
        
        Args:
            title: Dialog title
            message: Info message to display
        """
        messagebox.showinfo(title, message)
    
    def browse_local_file_or_folder(self, direction: str, initial_dir: Optional[str] = None) -> Optional[str]:
        """Browse for local file or folder based on transfer direction.
        
        Args:
            direction: Transfer direction ('pull' or 'push')
            initial_dir: Initial directory to open browser in
            
        Returns:
            Selected path or None if cancelled
        """
        if initial_dir is None:
            initial_dir = os.path.expanduser("~")
        
        # Show helpful notification about folder selection behavior
        if not self.show_file_folder_selection_notice():
            return None  # User cancelled the notice dialog
        
        if direction == "push":
            # For push, show file selection first, then folder selection if cancelled
            
            # First try file selection
            selected_path = filedialog.askopenfilename(
                title="Select file to push to Android device",
                initialdir=initial_dir,
                filetypes=[("All files", "*.*")]
            )
            
            # If no file was selected, offer folder selection as an alternative
            if not selected_path:
                selected_path = filedialog.askdirectory(
                    title="Select folder to push to Android device",
                    initialdir=initial_dir
                )
            
            return selected_path if selected_path else None
            
        else:  # pull direction
            # For pull, only allow folder selection (destination)
            folder = filedialog.askdirectory(
                title="Select destination folder for pulled files",
                initialdir=initial_dir
            )
            return folder if folder else None
    
    def show_file_folder_choice(self, on_file_callback, on_folder_callback):
        """Show a dialog to choose between file or folder selection.
        
        Args:
            on_file_callback: Callback for file selection
            on_folder_callback: Callback for folder selection
        """
        # Ask user whether they want to select a file or folder
        choice_window = tk.Toplevel(self.parent)
        choice_window.title("Select File or Folder")
        choice_window.geometry("350x150")
        choice_window.resizable(False, False)
        choice_window.transient(self.parent)
        choice_window.grab_set()
        
        # Center the window
        choice_window.geometry("+{}+{}".format(
            self.parent.winfo_x() + 100,
            self.parent.winfo_y() + 100
        ))
        
        main_frame = tk.Frame(choice_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="What would you like to select?", 
                font=("Arial", 11)).pack(pady=(0, 15))
        
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        def select_file():
            choice_window.destroy()
            on_file_callback()
        
        def select_folder():
            choice_window.destroy()
            on_folder_callback()
        
        def cancel_selection():
            choice_window.destroy()
        
        tk.Button(button_frame, text="📄 File", command=select_file, 
                 width=12, font=("Arial", 10)).pack(side="left", padx=(0, 10))
        tk.Button(button_frame, text="📁 Folder", command=select_folder, 
                 width=12, font=("Arial", 10)).pack(side="left", padx=(0, 10))
        tk.Button(button_frame, text="Cancel", command=cancel_selection, 
                 width=12).pack(side="right")
    
    def show_transfer_stats(self, stats: dict, operation: str):
        """Show transfer statistics in a dialog.
        
        Args:
            stats: Dictionary containing transfer statistics
            operation: Description of the operation performed
        """
        if not stats:
            return
            
        stats_window = tk.Toplevel(self.parent)
        stats_window.title("Transfer Statistics")
        stats_window.geometry("400x300")
        stats_window.resizable(True, True)
        stats_window.transient(self.parent)
        stats_window.grab_set()
        
        # Center the window
        stats_window.geometry("+{}+{}".format(
            self.parent.winfo_x() + 60,
            self.parent.winfo_y() + 60
        ))
        
        main_frame = tk.Frame(stats_window)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Title
        title_label = tk.Label(main_frame, text=f"📊 Transfer Complete - {operation.title()}", 
                              font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Stats display
        stats_text = tk.Text(main_frame, wrap=tk.WORD, font=("Courier", 10), 
                            height=12, width=50)
        stats_text.pack(fill="both", expand=True, pady=(0, 15))
        
        # Format and insert stats
        stats_content = []
        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            stats_content.append(f"{formatted_key}: {value}")
        
        stats_text.insert(tk.END, "\n".join(stats_content))
        stats_text.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(main_frame, text="Close", 
                 command=stats_window.destroy).pack()
    
    def show_disable_debugging_reminder(self):
        """Show reminder about disabling USB debugging after transfer."""
        messagebox.showinfo(
            "Security Reminder", 
            "Transfer complete!\n\nFor security, consider disabling USB debugging when not needed:\n"
            "Settings → Developer Options → USB debugging (toggle off)\n\n"
            "Keep it enabled if you plan to transfer files again soon."
        )