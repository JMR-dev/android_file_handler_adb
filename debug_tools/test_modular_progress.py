#!/usr/bin/env python3
"""
Debug test for progress callback in modular GUI
"""

import sys
import os

sys.path.insert(0, "src")

from gui.main_window import AndroidFileHandlerGUI


def test_callbacks():
    """Test if callbacks are being set properly."""
    app = AndroidFileHandlerGUI()

    print("Testing callback setup...")
    print(f"ADB Manager progress callback: {app.adb_manager.progress_callback}")
    print(f"ADB Manager status callback: {app.adb_manager.status_callback}")
    print(f"Progress handler: {app.progress_handler}")
    print(
        f"Progress handler update_progress method: {app.progress_handler.update_progress}"
    )
    print(f"Progress handler set_status method: {app.progress_handler.set_status}")

    # Test direct call
    print("\nTesting direct progress update...")
    app.progress_handler.update_progress(50)
    app.update()

    print("\nTesting direct status update...")
    app.progress_handler.set_status("Testing status")
    app.update()

    print(
        "\nTest completed. Check if progress bar shows 50% and status shows 'Testing status'"
    )

    app.mainloop()


if __name__ == "__main__":
    test_callbacks()
