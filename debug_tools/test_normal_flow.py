#!/usr/bin/env python3
"""
Debug test following normal application flow
"""

import sys
import os
import time
import threading

sys.path.insert(0, "src")

from gui.main_window import AndroidFileHandlerGUI


def test_normal_flow():
    """Test following the normal application flow exactly."""
    app = AndroidFileHandlerGUI()

    def debug_transfer():
        # Wait for app to initialize
        time.sleep(2)

        print("=== DEBUGGING NORMAL APPLICATION FLOW ===")
        print(f"App ADB manager: {app.adb_manager}")
        print(f"App progress handler: {app.progress_handler}")
        print(f"ADB manager progress callback: {app.adb_manager.progress_callback}")
        print(f"ADB manager status callback: {app.adb_manager.status_callback}")

        # Set up a test transfer
        app.remote_path_var.set("/sdcard/Download")
        app.local_path_var.set(r"C:\temp")

        print("\n=== SIMULATING START TRANSFER BUTTON CLICK ===")

        # Check if local path exists
        if not os.path.exists(r"C:\temp"):
            os.makedirs(r"C:\temp", exist_ok=True)

        # Test the exact method that gets called
        app.current_transfer_id += 1
        transfer_id = app.current_transfer_id
        print(f"Transfer ID: {transfer_id}")

        app.disable_controls()
        app.progress_handler.reset_progress()

        print("\n=== TESTING PROGRESS UPDATES DIRECTLY ===")
        app.adb_manager._update_progress(25)
        app.update()
        time.sleep(0.5)

        app.adb_manager._update_progress(50)
        app.update()
        time.sleep(0.5)

        app.adb_manager._update_progress(75)
        app.update()
        time.sleep(0.5)

        app.adb_manager._update_progress(100)
        app.update()

        print("=== PROGRESS UPDATES COMPLETED ===")

        app.enable_controls()

    # Start debug in background
    threading.Thread(target=debug_transfer, daemon=True).start()

    app.mainloop()


if __name__ == "__main__":
    test_normal_flow()
