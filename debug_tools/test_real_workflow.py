#!/usr/bin/env python3
"""
Test real transfer workflow
"""

import sys
import os
import time
import threading

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from gui.main_window import AndroidFileHandlerGUI


def test_real_transfer_workflow():
    """Test the real transfer workflow with console output."""

    # Add debug output to see what's happening
    class DebugApp(AndroidFileHandlerGUI):
        def __init__(self):
            super().__init__()

            # Wrap callbacks with debug output
            original_progress = self.adb_manager.progress_callback
            original_status = self.adb_manager.status_callback

            def debug_progress(percentage):
                print(f"PROGRESS: {percentage}%")
                if original_progress:
                    original_progress(percentage)

            def debug_status(message):
                print(f"STATUS: {message}")
                if original_status:
                    original_status(message)

            self.adb_manager.set_progress_callback(debug_progress)
            self.adb_manager.set_status_callback(debug_status)

    app = DebugApp()

    def simulate_transfer():
        time.sleep(2)  # Wait for app to be ready

        print("=== SIMULATING BUTTON CLICK ===")

        # Set up paths (use a path that doesn't exist to avoid actual transfer)
        app.remote_path_var.set("/nonexistent/path")
        app.local_path_var.set(r"C:\temp")

        # Create temp dir if needed
        os.makedirs(r"C:\temp", exist_ok=True)

        # Call start_transfer method directly
        print("Calling start_transfer()...")
        app.start_transfer()

    # Start simulation
    threading.Thread(target=simulate_transfer, daemon=True).start()

    print("Starting app...")
    app.mainloop()


if __name__ == "__main__":
    test_real_transfer_workflow()
