#!/usr/bin/env python3
"""
Minimal test to verify progress updates work in modular GUI
"""

import sys
import time
import threading
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from gui.main_window import AndroidFileHandlerGUI


def test_minimal_progress():
    """Test minimal progress updates."""
    print("Creating GUI...")
    app = AndroidFileHandlerGUI()

    def test_updates():
        time.sleep(1)  # Wait for GUI to be ready
        print("Starting test updates...")

        # Test direct progress handler calls
        print("Testing progress handler directly...")
        app.progress_handler.update_progress(25)
        time.sleep(0.5)
        app.progress_handler.update_progress(50)
        time.sleep(0.5)
        app.progress_handler.update_progress(75)
        time.sleep(0.5)
        app.progress_handler.update_progress(100)

        time.sleep(1)

        # Test ADB manager calls (should go through callbacks)
        print("Testing through ADB manager...")
        app.adb_manager._update_progress(0)
        time.sleep(0.5)
        app.adb_manager._update_progress(30)
        time.sleep(0.5)
        app.adb_manager._update_progress(60)
        time.sleep(0.5)
        app.adb_manager._update_progress(90)
        time.sleep(0.5)
        app.adb_manager._update_progress(100)

        print("Test completed!")

    # Start test in background
    threading.Thread(target=test_updates, daemon=True).start()

    # Run GUI
    print("Starting GUI mainloop...")
    app.mainloop()


if __name__ == "__main__":
    test_minimal_progress()
