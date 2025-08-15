#!/usr/bin/env python3
"""
Test script to verify progress callback is working
"""
import sys
import os

sys.path.insert(0, "src")

from adb_manager import ADBManager
import time


def test_progress_callback():
    """Test the progress callback functionality."""
    print("Testing progress callback...")

    # Track progress updates
    progress_updates = []

    def progress_callback(percentage):
        progress_updates.append(percentage)
        print(f"Progress update: {percentage}%")

    def status_callback(message):
        print(f"Status: {message}")

    # Create ADB manager and set callbacks
    adb = ADBManager()
    adb.set_progress_callback(progress_callback)
    adb.set_status_callback(status_callback)

    # Test manual progress updates
    print("\nTesting manual progress updates:")
    for i in range(0, 101, 25):
        adb._update_progress(i)
        time.sleep(0.1)

    print(f"\nProgress updates received: {progress_updates}")
    print(f"Total updates: {len(progress_updates)}")

    # Test progress parsing
    print("\nTesting progress parsing:")
    test_lines = [
        "Pulling: /sdcard/DCIM/Camera/IMG_20250815_123456.jpg... (25%)",
        "/sdcard/Documents/file.txt: 1 file pulled. (50%)",
        "Pulling: /sdcard/Music/song.mp3... (75%)",
        "3 files pulled. (100%)",
        "No progress info here",
        "",
    ]

    for line in test_lines:
        progress = adb.parse_progress(line)
        print(f"Line: {repr(line[:50])} -> Progress: {progress}")


if __name__ == "__main__":
    test_progress_callback()
