#!/usr/bin/env python3
"""
Test script to debug folder parsing
"""
import sys
import os

sys.path.insert(0, "src")

from adb_manager import ADBManager


def main():
    adb = ADBManager()
    print("Testing folder parsing...")

    result = adb.run_adb_command(["shell", "ls", "-la", "/sdcard/"])
    print(f"Return code: {result[2]}")

    lines = result[0].strip().split("\n")
    print(f"Total lines: {len(lines)}")
    print("\nFirst 10 lines:")
    for i, line in enumerate(lines[:10]):
        print(f"  {i}: {repr(line)}")

    print("\nParsing directories:")
    folders = []
    for i, line in enumerate(lines):
        if line.startswith("d"):
            parts = line.split()
            print(f"  Line {i}: {len(parts)} parts")
            if len(parts) >= 8:  # Changed from 9 to 8
                folder_name = " ".join(parts[7:])  # Changed from 8 to 7
                print(f"    Folder name: {repr(folder_name)}")
                if folder_name not in [".", ".."]:
                    folders.append(folder_name)
                    print(f"    ✅ Added: {repr(folder_name)}")
                else:
                    print(f"    ❌ Skipped: {repr(folder_name)}")

    print(f"\nFinal folders list ({len(folders)} items):")
    for folder in sorted(folders):
        print(f"  - {repr(folder)}")


if __name__ == "__main__":
    main()
