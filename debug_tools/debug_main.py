#!/usr/bin/env python3
"""
Debug version of main window with console output
"""

import sys
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from src.main_window import AndroidFileHandlerGUI


class DebugAndroidFileHandlerGUI(AndroidFileHandlerGUI):
    """Debug version with console output."""

    def _initialize_components(self):
        """Initialize GUI components and handlers with debug output."""
        super()._initialize_components()

        # Wrap the progress callback with debug output
        original_update_progress = self.progress_handler.update_progress

        def debug_update_progress(percentage):
            print(f"DEBUG: Progress update called with {percentage}%")
            return original_update_progress(percentage)

        # Wrap the status callback with debug output
        original_set_status = self.progress_handler.set_status

        def debug_set_status(message):
            print(f"DEBUG: Status update called with '{message}'")
            return original_set_status(message)

        # Replace the callbacks
        self.progress_handler.update_progress = debug_update_progress
        self.progress_handler.set_status = debug_set_status

        # Update ADB manager callbacks
        self.adb_manager.set_progress_callback(self.progress_handler.update_progress)
        self.adb_manager.set_status_callback(self.progress_handler.set_status)

        print("DEBUG: Callbacks set up with debug wrappers")


def main():
    """Main function to run the debug application."""
    if sys.platform not in ["win32", "linux"]:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Unsupported OS", "This application only supports Windows or Linux."
        )
        sys.exit(1)

    app = DebugAndroidFileHandlerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
