#!/usr/bin/env python3
"""
Debug successive transfers to understand progress bar issue
"""
import sys
import os
import time

sys.path.insert(0, "src")

from adb_manager import ADBManager


def test_successive_transfers():
    """Test multiple transfers to debug progress issues."""
    print("Testing successive transfer callbacks...")

    # Track progress updates for each transfer
    transfer1_progress = []
    transfer2_progress = []
    current_transfer = 1

    def progress_callback(percentage):
        if current_transfer == 1:
            transfer1_progress.append(percentage)
            print(f"Transfer 1 - Progress: {percentage}%")
        else:
            transfer2_progress.append(percentage)
            print(f"Transfer 2 - Progress: {percentage}%")

    def status_callback(message):
        print(f"Transfer {current_transfer} - Status: {message}")

    # Create ADB manager and set callbacks
    adb = ADBManager()
    adb.set_progress_callback(progress_callback)
    adb.set_status_callback(status_callback)

    # Test first transfer simulation
    print("\n=== FIRST TRANSFER ===")
    current_transfer = 1
    print("Simulating first transfer...")
    adb._update_progress(0)
    time.sleep(0.5)
    adb._update_progress(25)
    time.sleep(0.5)
    adb._update_progress(50)
    time.sleep(0.5)
    adb._update_progress(75)
    time.sleep(0.5)
    adb._update_progress(100)

    print(f"First transfer progress updates: {transfer1_progress}")

    # Test second transfer simulation
    print("\n=== SECOND TRANSFER ===")
    current_transfer = 2
    print("Simulating second transfer...")
    adb._update_progress(0)
    time.sleep(0.5)
    adb._update_progress(30)
    time.sleep(0.5)
    adb._update_progress(60)
    time.sleep(0.5)
    adb._update_progress(90)
    time.sleep(0.5)
    adb._update_progress(100)

    print(f"Second transfer progress updates: {transfer2_progress}")

    # Check if callbacks are still working
    print(f"\nCallback function still set: {adb.progress_callback is not None}")
    print(f"Status callback still set: {adb.status_callback is not None}")


if __name__ == "__main__":
    test_successive_transfers()
