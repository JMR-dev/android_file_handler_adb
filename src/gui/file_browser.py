"""
Windows Android Browser Module
Provides Android filesystem browsing capabilities for Windows using ADB.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk


class AndroidFileBrowser:
    """Android filesystem browser for Windows using ADB."""

    def __init__(self, parent_window, adb_manager, remote_path_var):
        self.parent = parent_window
        self.adb_manager = adb_manager
        self.remote_path_var = remote_path_var

    def show_browser(self, direction="pull"):
        """Show a browsable Android folder tree. 
        
        Args:
            direction: "pull" to show files and folders, "push" to show folders only
        """
        # Check if device is connected
        device = self.adb_manager.check_device()
        if not device:
            messagebox.showerror(
                "No Device",
                "No Android device connected. Please connect your device and enable USB debugging.",
            )
            return

        # Create browsable folder dialog
        browser_window = tk.Toplevel(self.parent)
        if direction == "push":
            browser_window.title("Browse Android Folders (Destination)")
            label_text = "Browse Android device folders (select destination):"
        else:
            browser_window.title("Browse Android Files and Folders")
            label_text = "Browse Android device files and folders:"
        
        browser_window.geometry("500x400")
        browser_window.transient(self.parent)
        browser_window.grab_set()

        tk.Label(
            browser_window,
            text=label_text,
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
                        self.parent.after(
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

                        # Parse ls -la output to find directories and files
                        folders = []
                        files = []
                        lines = stdout.strip().split("\n")
                        for line in lines:
                            if line.startswith("d"):
                                # Directory entry
                                parts = line.split()
                                if len(parts) >= 8:
                                    # Method 1: Use regex to find time pattern and extract name after it
                                    import re

                                    time_pattern = r"\d{1,2}:\d{2}"
                                    time_matches = list(re.finditer(time_pattern, line))

                                    if time_matches:
                                        # Take everything after the last time pattern
                                        last_time_match = time_matches[-1]
                                        folder_name = line[
                                            last_time_match.end() :
                                        ].strip()
                                    else:
                                        # Fallback: join from part 8 (skip date/time fields)
                                        folder_name = (
                                            " ".join(parts[8:])
                                            if len(parts) > 8
                                            else parts[7]
                                        )

                                    # Additional validation and cleanup
                                    folder_name = folder_name.strip()

                                    if (
                                        folder_name
                                        and folder_name not in [".", ".."]
                                        and not folder_name.startswith(".")
                                    ):
                                        folders.append(folder_name)
                            elif line.startswith("-") and direction != "push":
                                # Regular file entry - only show files if not in push mode
                                parts = line.split()
                                if len(parts) >= 8:
                                    # Extract file name using same method as folders
                                    import re

                                    time_pattern = r"\d{1,2}:\d{2}"
                                    time_matches = list(re.finditer(time_pattern, line))

                                    if time_matches:
                                        # Take everything after the last time pattern
                                        last_time_match = time_matches[-1]
                                        file_name = line[
                                            last_time_match.end() :
                                        ].strip()
                                    else:
                                        # Fallback: join from part 8 (skip date/time fields)
                                        file_name = (
                                            " ".join(parts[8:])
                                            if len(parts) > 8
                                            else parts[7]
                                        )

                                    # Additional validation and cleanup
                                    file_name = file_name.strip()

                                    if (
                                        file_name
                                        and not file_name.startswith(".")
                                    ):
                                        files.append(file_name)

                        # Add folders to tree first (sorted)
                        if folders:
                            for folder in sorted(folders):
                                folder_path = f"{path.rstrip('/')}/{folder}"
                                item = tree.insert(
                                    parent_item,
                                    "end",
                                    text=f"📁 {folder}",
                                    values=[folder_path, "folder"],
                                )
                                # Add a dummy child to make it expandable
                                tree.insert(item, "end", text="Loading...")
                        
                        # Add files to tree (sorted) - only if not in push mode
                        if files and direction != "push":
                            for file in sorted(files):
                                file_path = f"{path.rstrip('/')}/{file}"
                                tree.insert(
                                    parent_item,
                                    "end",
                                    text=f"📄 {file}",
                                    values=[file_path, "file"],
                                )
                        
                        # If no folders or files found, show indicator
                        if not folders and (not files or direction == "push"):
                            empty_text = "(No Folders)" if direction == "push" else "(Empty Directory)"
                            tree.insert(
                                parent_item, "end", text=empty_text, values=["", ""]
                            )

                    self.parent.after(0, update_tree)

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

                    self.parent.after(0, error_update)

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
                        # Extract folder name - improved parsing to prevent truncation
                        parts = line.split()
                        if len(parts) >= 8:
                            # Method 1: Use regex to find time pattern and extract name after it
                            import re

                            time_pattern = r"\d{1,2}:\d{2}"
                            time_matches = list(re.finditer(time_pattern, line))

                            if time_matches:
                                # Take everything after the last time pattern
                                last_time_match = time_matches[-1]
                                folder_name = line[last_time_match.end() :].strip()
                            else:
                                # Fallback: join from part 8 (skip date/time fields)
                                folder_name = (
                                    " ".join(parts[8:]) if len(parts) > 8 else parts[7]
                                )

                            # Additional validation and cleanup
                            folder_name = folder_name.strip()

                            if (
                                folder_name
                                and folder_name not in [".", ".."]
                                and not folder_name.startswith(".")
                            ):
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

        def select_current_item():
            """Intelligently select the currently highlighted item (file or folder)."""
            selected_item = tree.selection()[0] if tree.selection() else None
            
            if selected_item:
                # Get the item type and path from values
                item_values = tree.item(selected_item, "values")
                if len(item_values) >= 1:
                    item_path = item_values[0]
                    # Check if it's a file or folder (if we have type info)
                    if len(item_values) >= 2 and item_values[1] == "file":
                        if direction == "push":
                            # In push mode, don't allow file selection
                            messagebox.showwarning("Invalid Selection", "Please select a folder as the destination.")
                            return
                        else:
                            # It's a file and we're in pull mode - select the file path directly
                            self.remote_path_var.set(item_path)
                            browser_window.destroy()
                            return
                    elif len(item_values) >= 2 and item_values[1] == "folder":
                        # It's a folder - select the folder path directly
                        self.remote_path_var.set(item_path)
                        browser_window.destroy()
                        return
            
            # Fallback: use current path (for backwards compatibility or when no specific item is selected)
            current_path = current_path_var.get()
            if current_path and current_path.strip():
                self.remote_path_var.set(current_path)
                browser_window.destroy()
            else:
                selection_type = "folder" if direction == "push" else "file or folder"
                messagebox.showwarning("No Selection", f"Please select a {selection_type}.")

        tk.Button(
            button_frame, text="Select", command=select_current_item
        ).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=browser_window.destroy).pack(
            side="left", padx=5
        )
