"""
Android File Handler - GUI Module
Provides the user interface for the Android file transfer application.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, simpledialog
from typing import Optional

try:
    # Try relative import first (when used as module)
    from .adb_manager import (
        ADBManager,
        LinuxMTPManager,
        get_platform_type,
        is_adb_available,
    )
except ImportError:
    # Fall back to direct import (when run directly)
    from adb_manager import (
        ADBManager,
        LinuxMTPManager,
        get_platform_type,
        is_adb_available,
    )


class AndroidFileHandlerGUI(tk.Tk):
    """Main GUI application for Android file transfers."""

    def __init__(self):
        super().__init__()

        # Initialize business logic
        self.adb_manager = ADBManager()
        self.adb_manager.set_progress_callback(self.update_progress)
        self.adb_manager.set_status_callback(self.set_status)

        if get_platform_type().startswith("linux"):
            self.mtp_manager = LinuxMTPManager()
        else:
            self.mtp_manager = None

        # Setup UI
        self._setup_ui()
        self._initialize_app()

    def _setup_ui(self):
        """Setup the user interface."""
        # Window configuration
        self.title("Android Folder Puller")
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

        # Progress bar
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(20, 5))

        # Status label
        self.status_label = tk.Label(self, text="Status: Idle")
        self.status_label.pack(anchor="w", padx=10, fill="x")

        # Start button
        self.start_btn = tk.Button(
            self, text="Start Transfer", command=self.start_transfer
        )
        self.start_btn.pack(pady=10)

        # Window close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _initialize_app(self):
        """Initialize the application - check ADB and device."""
        # Check adb availability
        if not is_adb_available():
            self.disable_controls()
            self.set_status("ADB not found locally. Downloading...")
            self.update()
            success = self.adb_manager.download_and_extract_adb()
            if success:
                self.set_status("ADB downloaded and ready.")
                self.enable_controls()
            else:
                self.set_status(
                    "Failed to download ADB. Please check your internet and restart."
                )
                messagebox.showerror("Error", "Failed to download ADB tools. Exiting.")
                self.quit()
                return

        # Check device connected
        self.set_status("Checking for connected device...")
        self.update()
        device = self.adb_manager.check_device()
        if not device:
            self.disable_controls()
            self.set_status(
                "No device detected. Enable USB debugging and connect your device."
            )
            self.show_enable_debugging_instructions()
        else:
            self.set_status(f"Device detected: {device}")

    def browse_remote_folder(self):
        """Browse remote Android folders via MTP (Linux)"""
        # For Linux - use MTP browsing
        if get_platform_type().startswith("linux") and self.mtp_manager:
            # First try using existing GVFS mount
            gvfs_mount = self.mtp_manager.find_gvfs_mtp_mount()
            if gvfs_mount:
                try:
                    folder = filedialog.askdirectory(
                        initialdir=gvfs_mount, title="Select Android folder"
                    )
                    if folder:
                        # Convert filesystem path back to Android path
                        relative_path = os.path.relpath(folder, gvfs_mount)
                        if relative_path == ".":
                            android_path = "/sdcard"
                        else:
                            android_path = f"/sdcard/{relative_path}".replace("\\", "/")
                        self.remote_path_var.set(android_path)
                    return
                except Exception as e:
                    print(f"GVFS browse failed: {e}")

            # Fallback to jmtpfs
            mount_point = self.mtp_manager.mount_mtp_device()
            if mount_point:
                try:
                    folder = filedialog.askdirectory(
                        initialdir=mount_point, title="Select Android folder"
                    )
                    if folder:
                        # Convert filesystem path back to Android path
                        relative_path = os.path.relpath(folder, mount_point)
                        if relative_path == ".":
                            android_path = "/sdcard"
                        else:
                            android_path = f"/sdcard/{relative_path}".replace("\\", "/")
                        self.remote_path_var.set(android_path)
                finally:
                    self.mtp_manager.unmount_mtp_device()
            else:
                messagebox.showerror(
                    "Error",
                    "Could not mount Android device via MTP. "
                    "Make sure it's connected and set to 'File Transfer' mode.",
                )
        else:
            # For Windows - show common Android paths dialog
            self._show_android_filesystem_tree()

    def _show_android_filesystem_tree(self):
        """Show a browsable Android folder tree for Windows users."""
        # Check if device is connected
        device = self.adb_manager.check_device()
        if not device:
            messagebox.showerror(
                "No Device",
                "No Android device connected. Please connect your device and enable USB debugging.",
            )
            return

        # Create browsable folder dialog
        browser_window = tk.Toplevel(self)
        browser_window.title("Browse Android Folders")
        browser_window.geometry("500x400")
        browser_window.transient(self)
        browser_window.grab_set()

        tk.Label(
            browser_window,
            text="Browse Android device folders:",
            font=("Arial", 10, "bold"),
        ).pack(pady=10)

        # Create treeview for folder browsing
        tree_frame = tk.Frame(browser_window)
        tree_frame.pack(fill="both", expand=True, padx=10)

        # Treeview with scrollbars
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = tk.Scrollbar(tree_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
        )
        tree.pack(side="left", fill="both", expand=True)

        tree_scroll_y.config(command=tree.yview)
        tree_scroll_x.config(command=tree.xview)

        # Current path display
        path_frame = tk.Frame(browser_window)
        path_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(path_frame, text="Current path:").pack(side="left")
        current_path_var = tk.StringVar(value="/sdcard")
        current_path_label = tk.Label(
            path_frame, textvariable=current_path_var, font=("Courier", 9)
        )
        current_path_label.pack(side="left", padx=(5, 0))

        def load_folders_async(parent_item, path):
            """Load folders asynchronously to avoid UI freezing."""

            def load_in_thread():
                try:
                    # Ensure path ends with / for proper directory listing
                    list_path = path if path.endswith("/") else path + "/"

                    # Use ls -la to get detailed listing with file type information
                    result = self.adb_manager.run_adb_command(
                        ["shell", "ls", "-la", list_path]
                    )

                    if not isinstance(result, tuple) or len(result) != 3:
                        self.after(
                            0,
                            lambda: tree.insert(
                                parent_item,
                                "end",
                                text="(Error loading folders)",
                                values=[""],
                            ),
                        )
                        return

                    stdout, stderr, returncode = result

                    # Update UI in main thread - always remove Loading... first
                    def update_tree():
                        # First, remove any existing dummy children
                        children = tree.get_children(parent_item)
                        for child in children:
                            child_text = tree.item(child, "text")
                            if child_text in [
                                "Loading...",
                                "(No Folders)",
                                "(Error loading folders)",
                                "(Permission denied)",
                            ]:
                                tree.delete(child)

                        # Check for errors
                        if returncode != 0:
                            if stderr and "Permission denied" in stderr:
                                tree.insert(
                                    parent_item,
                                    "end",
                                    text="(Permission denied)",
                                    values=[""],
                                )
                            else:
                                tree.insert(
                                    parent_item,
                                    "end",
                                    text="(Error loading folders)",
                                    values=[""],
                                )
                            return

                        if not stdout or not stdout.strip():
                            tree.insert(
                                parent_item, "end", text="(No Folders)", values=[""]
                            )
                            return

                        # Parse ls -la output to find directories
                        folders = []
                        lines = stdout.strip().split("\n")
                        for line in lines:
                            if line.startswith("d"):
                                # Extract folder name (last part after spaces)
                                parts = line.split()
                                if (
                                    len(parts) >= 8
                                ):  # Android ls -la typically has 8+ parts
                                    folder_name = " ".join(
                                        parts[7:]
                                    )  # Handle names with spaces (start from column 8)
                                    if folder_name not in [
                                        ".",
                                        "..",
                                    ] and not folder_name.startswith("."):
                                        folders.append(folder_name)

                        # Add folders to tree
                        if folders:
                            for folder in sorted(folders):
                                folder_path = f"{path.rstrip('/')}/{folder}"
                                item = tree.insert(
                                    parent_item,
                                    "end",
                                    text=folder,
                                    values=[folder_path],
                                )
                                # Add a dummy child to make it expandable
                                tree.insert(item, "end", text="Loading...")
                        else:
                            # No folders found, show indicator
                            tree.insert(
                                parent_item, "end", text="(No Folders)", values=[""]
                            )

                    self.after(0, update_tree)

                except Exception as e:
                    print(f"Error loading folders from {path}: {e}")

                    def error_update():
                        # Remove Loading... even on error
                        children = tree.get_children(parent_item)
                        for child in children:
                            child_text = tree.item(child, "text")
                            if child_text == "Loading...":
                                tree.delete(child)
                        tree.insert(
                            parent_item,
                            "end",
                            text="(Error loading folders)",
                            values=[""],
                        )

                    self.after(0, error_update)

            # Run in background thread
            threading.Thread(target=load_in_thread, daemon=True).start()

        def load_folders(parent_item, path):
            """Load folders from Android device using ADB (legacy sync version for initial load)."""
            # First, remove any existing dummy children
            children = tree.get_children(parent_item)
            for child in children:
                child_text = tree.item(child, "text")
                if child_text in [
                    "Loading...",
                    "(No Folders)",
                    "(Error loading folders)",
                    "(Permission denied)",
                ]:
                    tree.delete(child)

            try:
                # Ensure path ends with / for proper directory listing
                list_path = path if path.endswith("/") else path + "/"

                # Use ls -la to get detailed listing with file type information
                result = self.adb_manager.run_adb_command(
                    ["shell", "ls", "-la", list_path]
                )

                if not isinstance(result, tuple) or len(result) != 3:
                    tree.insert(
                        parent_item, "end", text="(Error loading folders)", values=[""]
                    )
                    return []

                stdout, stderr, returncode = result
                if returncode != 0:
                    if stderr and "Permission denied" in stderr:
                        tree.insert(
                            parent_item, "end", text="(Permission denied)", values=[""]
                        )
                    else:
                        tree.insert(
                            parent_item,
                            "end",
                            text="(Error loading folders)",
                            values=[""],
                        )
                    return []

                if not stdout or not stdout.strip():
                    tree.insert(parent_item, "end", text="(No Folders)", values=[""])
                    return []

                # Parse ls -la output to find directories
                folders = []
                lines = stdout.strip().split("\n")
                for line in lines:
                    if line.startswith("d"):
                        # Extract folder name (last part after spaces)
                        parts = line.split()
                        if len(parts) >= 8:  # Android ls -la typically has 8+ parts
                            folder_name = " ".join(
                                parts[7:]
                            )  # Handle names with spaces (start from column 8)
                            if folder_name not in [
                                ".",
                                "..",
                            ] and not folder_name.startswith("."):
                                folders.append(folder_name)

                # Add folders to tree
                if folders:
                    for folder in sorted(folders):
                        folder_path = f"{path.rstrip('/')}/{folder}"
                        item = tree.insert(
                            parent_item, "end", text=folder, values=[folder_path]
                        )
                        # Add a dummy child to make it expandable
                        tree.insert(item, "end", text="Loading...")
                else:
                    # No folders found, show indicator
                    tree.insert(parent_item, "end", text="(No Folders)", values=[""])

                return folders
            except Exception as e:
                print(f"Error loading folders from {path}: {e}")
                tree.insert(
                    parent_item, "end", text="(Error loading folders)", values=[""]
                )
                return []

        def on_tree_expand(event):
            """Handle tree expansion - load subfolders dynamically."""
            item = tree.selection()[0] if tree.selection() else tree.focus()
            if not item:
                return

            # Get the path
            folder_path = (
                tree.item(item, "values")[0] if tree.item(item, "values") else None
            )
            if not folder_path:  # Skip items without valid paths (like "(No Folders)")
                return

            current_path_var.set(folder_path)

            # Check if we need to load subfolders
            children = tree.get_children(item)
            has_loading = any(
                tree.item(child, "text") == "Loading..." for child in children
            )

            # Only load if we have a "Loading..." placeholder - use async version
            if has_loading:
                load_folders_async(item, folder_path)

        def on_tree_select(event):
            """Handle tree selection - update current path."""
            item = tree.selection()[0] if tree.selection() else None
            if item:
                folder_path = (
                    tree.item(item, "values")[0] if tree.item(item, "values") else None
                )
                if folder_path:  # Only update if valid path
                    current_path_var.set(folder_path)

        # Bind events
        tree.bind("<<TreeviewOpen>>", on_tree_expand)
        tree.bind("<<TreeviewSelect>>", on_tree_select)

        # Determine which path to use - prefer /sdcard, fallback to /storage/emulated/0
        primary_path = "/sdcard"
        fallback_path = "/storage/emulated/0"

        # Test if /sdcard is accessible (with trailing slash for directory listing)
        test_result = self.adb_manager.run_adb_command(
            ["shell", "ls", "-la", primary_path + "/"]
        )
        if (
            isinstance(test_result, tuple)
            and len(test_result) == 3
            and test_result[2] == 0
        ):
            # /sdcard is accessible
            android_path = primary_path
        else:
            # /sdcard not accessible, use fallback
            android_path = fallback_path

        # Create single "Android" root item
        android_item = tree.insert("", "end", text="Android", values=[android_path])
        tree.insert(android_item, "end", text="Loading...")

        # Set initial path
        current_path_var.set(android_path)

        # Expand and load the Android root immediately
        tree.item(android_item, open=True)
        load_folders(android_item, android_path)

        # Select the Android item
        tree.selection_set(android_item)

        # Buttons
        button_frame = tk.Frame(browser_window)
        button_frame.pack(pady=10)

        def select_current_folder():
            """Select the currently highlighted folder."""
            current_path = current_path_var.get()
            if current_path and current_path.strip():
                self.remote_path_var.set(current_path)
                browser_window.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a valid folder.")

        def enter_custom_path():
            """Allow user to enter a custom path."""
            browser_window.destroy()
            custom_path = simpledialog.askstring(
                "Custom Path",
                "Enter custom Android folder path:",
                initialvalue="/sdcard/",
            )
            if custom_path:
                self.remote_path_var.set(custom_path.strip())

        tk.Button(
            button_frame, text="Select This Folder", command=select_current_folder
        ).pack(side="left", padx=5)
        tk.Button(
            button_frame, text="Enter Custom Path", command=enter_custom_path
        ).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=browser_window.destroy).pack(
            side="left", padx=5
        )

    def browse_local_folder(self):
        """Browse for local folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.local_path_var.set(folder)

    def disable_controls(self):
        """Disable UI controls during operations."""
        self.remote_path_entry.config(state="disabled")
        self.local_path_entry.config(state="disabled")
        self.start_btn.config(state="disabled")

    def enable_controls(self):
        """Enable UI controls after operations."""
        self.remote_path_entry.config(state="normal")
        self.local_path_entry.config(state="normal")
        self.start_btn.config(state="normal")

    def show_enable_debugging_instructions(self):
        """Show instructions for enabling USB debugging."""
        msg = (
            "To enable USB debugging:\n"
            "1. Open Settings → About phone.\n"
            "2. Tap 'Build number' seven times to unlock Developer Options.\n"
            "3. Go back to Settings → Developer Options.\n"
            "4. Enable 'USB debugging'.\n"
            "5. Connect your phone via USB and accept the prompt to allow debugging.\n\n"
            "After enabling, restart this app."
        )
        messagebox.showinfo("Enable USB Debugging", msg)

    def show_disable_debugging_reminder(self):
        """Show reminder to disable USB debugging after transfer."""
        msg = (
            "Transfer completed.\n\n"
            "For security, disable USB debugging when done:\n"
            "Settings → Developer Options → disable 'USB debugging'."
        )
        messagebox.showinfo("Disable USB Debugging", msg)

    def start_transfer(self):
        """Start the file transfer operation."""
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

        # Start transfer
        self.disable_controls()
        self.progress["value"] = 0

        if direction == "pull":
            self.set_status("Starting pull transfer...")
            threading.Thread(
                target=self._pull_thread, args=(remote_path, local_path), daemon=True
            ).start()
        elif direction == "push":
            self.set_status("Starting push transfer...")
            threading.Thread(
                target=self._push_thread, args=(local_path, remote_path), daemon=True
            ).start()
        else:
            self.report_error("Invalid transfer direction selected.")
            self.enable_controls()

    def _pull_thread(self, remote_path: str, local_path: str):
        """Thread function for pull operations."""
        try:
            success = self.adb_manager.pull_folder(remote_path, local_path)
            if success:
                self.show_disable_debugging_reminder()
        except Exception as e:
            self.report_error(f"Pull operation failed: {e}")
        finally:
            self.enable_controls()

    def _push_thread(self, local_path: str, remote_path: str):
        """Thread function for push operations."""
        try:
            success = self.adb_manager.push_folder(local_path, remote_path)
            if success:
                self.show_disable_debugging_reminder()
        except Exception as e:
            self.report_error(f"Push operation failed: {e}")
        finally:
            self.enable_controls()

    def update_progress(self, percentage: int):
        """Update the progress bar."""
        self.progress["value"] = percentage
        self.update_idletasks()

    def set_status(self, message: str):
        """Update the status label."""
        self.status_label.config(text=f"Status: {message}")
        self.update_idletasks()

    def report_error(self, message: str):
        """Report an error to the user."""
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
