#!/usr/bin/env python3
"""
Test improved progress calculation for large transfers
"""

import sys
import time
import threading

sys.path.insert(0, "src")

from gui.main_window import AndroidFileHandlerGUI


def test_large_transfer_progress():
    """Test improved progress calculation."""

    class TestApp(AndroidFileHandlerGUI):
        def __init__(self):
            super().__init__()
            self.progress_updates = []

            # Capture progress updates
            original_update = self.progress_handler.update_progress

            def capture_progress(percentage):
                self.progress_updates.append((time.time(), percentage))
                print(f"Progress: {percentage}%")
                return original_update(percentage)

            self.progress_handler.update_progress = capture_progress
            self.adb_manager.set_progress_callback(
                self.progress_handler.update_progress
            )

    app = TestApp()

    def simulate_large_transfer():
        """Simulate a large transfer with many output lines."""
        time.sleep(1)

        print("=== Testing Large Transfer Progress ===")

        # Simulate the internal progress logic without actual ADB
        start_time = time.time()
        last_update_time = start_time
        last_progress = 0

        print("Simulating 2000 lines of output (like a large transfer)...")

        for line_count in range(1, 2001):
            current_time = time.time()

            # Simulate the improved progress logic
            elapsed_time = current_time - start_time
            time_since_last_update = current_time - last_update_time

            should_update = False
            new_progress = last_progress

            # Time-based progress (update every 2 seconds)
            if time_since_last_update >= 2.0 and last_progress < 95:
                if line_count > 100:
                    activity_factor = min(line_count / 1000, 50)
                    time_factor = min(elapsed_time / 60, 40)
                    new_progress = min(activity_factor + time_factor, 95)
                else:
                    new_progress = min(last_progress + 10, 95)
                should_update = True

            # Line-based progress
            elif line_count % 50 == 0 and last_progress < 90:
                increment = max(1, min(5, 90 // (line_count // 50 + 1)))
                new_progress = min(last_progress + increment, 90)
                should_update = True

            if should_update and new_progress > last_progress:
                app.adb_manager._update_progress(int(new_progress))
                last_progress = new_progress
                last_update_time = current_time

            # Speed up simulation
            if line_count % 100 == 0:
                time.sleep(0.1)

        # Complete the transfer
        app.adb_manager._update_progress(100)

        print(f"\nTotal progress updates: {len(app.progress_updates)}")
        print("Progress timeline:")
        start_time = app.progress_updates[0][0] if app.progress_updates else time.time()
        for timestamp, percentage in app.progress_updates[-10:]:  # Show last 10
            elapsed = timestamp - start_time
            print(f"  {elapsed:.1f}s: {percentage}%")

    threading.Thread(target=simulate_large_transfer, daemon=True).start()

    # Run for limited time
    app.after(15000, app.destroy)  # Close after 15 seconds
    app.mainloop()


if __name__ == "__main__":
    test_large_transfer_progress()
