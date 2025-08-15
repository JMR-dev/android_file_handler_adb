#!/usr/bin/env python3
"""
Test successive transfers with modular GUI
"""

import sys
import time
import threading

sys.path.insert(0, "src")

from gui.main_window import AndroidFileHandlerGUI


def simulate_transfer(app, transfer_name):
    """Simulate a transfer with progress updates."""
    print(f"Starting {transfer_name}")
    app.progress_handler.set_status(f"Starting {transfer_name}...")
    app.progress_handler.reset_progress()

    # Simulate progress updates
    for i in range(0, 101, 10):
        time.sleep(0.1)  # Simulate work
        app.progress_handler.update_progress(i)
        app.progress_handler.set_status(f"{transfer_name}: {i}% complete")

    app.progress_handler.set_status(f"{transfer_name} completed!")
    print(f"Completed {transfer_name}")


def test_successive_transfers():
    """Test successive transfers to ensure progress bar works correctly."""
    app = AndroidFileHandlerGUI()

    def run_transfers():
        time.sleep(1)  # Wait for GUI to be ready
        simulate_transfer(app, "Transfer 1")
        time.sleep(0.5)
        simulate_transfer(app, "Transfer 2")
        time.sleep(0.5)
        simulate_transfer(app, "Transfer 3")
        print("All transfers completed!")

    # Start transfers in background thread
    threading.Thread(target=run_transfers, daemon=True).start()

    app.mainloop()


if __name__ == "__main__":
    test_successive_transfers()
