#!/usr/bin/env python3
"""
Debug folder name parsing from ADB ls output
"""

import sys
import subprocess
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from adb_manager import ADB_BINARY_PATH


def debug_folder_parsing():
    """Debug folder name parsing from ls -la output."""

    print("=== DEBUGGING FOLDER NAME PARSING ===")
    print("This will show actual ADB ls output and how it's parsed.\n")

    path = input("Enter Android path to list (e.g., /sdcard): ").strip()
    if not path:
        path = "/sdcard"

    print(f"Running: adb shell ls -la '{path}'\n")

    try:
        cmd = [ADB_BINARY_PATH, "shell", "ls", "-la", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        print(f"Return code: {result.returncode}")
        print(f"Raw output:\n{repr(result.stdout)}")
        print(f"Error output: {repr(result.stderr)}")
        print("\n" + "=" * 50)
        print("PARSED OUTPUT:")
        print("=" * 50)

        if result.stdout and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            print(f"Total lines: {len(lines)}\n")

            for i, line in enumerate(lines):
                print(f"Line {i+1}: {repr(line)}")

                if line.startswith("d"):
                    # Current parsing logic
                    parts = line.split()
                    print(f"  Parts ({len(parts)}): {parts}")

                    if len(parts) >= 8:
                        current_name = " ".join(parts[7:])
                        print(f"  Current parsing result: '{current_name}'")

                        # Improved parsing - try different approaches
                        # Method 1: Find the last occurrence of time pattern and take everything after
                        import re

                        time_pattern = r"\d{2}:\d{2}"
                        time_match = list(re.finditer(time_pattern, line))
                        if time_match:
                            last_time = time_match[-1]
                            improved_name = line[last_time.end() :].strip()
                            print(f"  Improved parsing result: '{improved_name}'")

                            if improved_name != current_name:
                                print(f"  *** DIFFERENCE DETECTED! ***")

                        # Method 2: Manual field parsing (more reliable)
                        # drwxrwxrwx root     root       2024-01-01 12:00 folder_name
                        tokens = line.split()
                        if len(tokens) >= 6:
                            # Skip permissions, links, user, group, size, date, time
                            # Take everything from index 8 (or find after time pattern)
                            manual_name = (
                                " ".join(tokens[8:])
                                if len(tokens) > 8
                                else (tokens[7] if len(tokens) == 8 else "")
                            )
                            print(f"  Manual parsing result: '{manual_name}'")
                    else:
                        print(
                            f"  *** NOT ENOUGH PARTS! Expected >= 8, got {len(parts)}"
                        )

                print()
        else:
            print("No output received!")

    except subprocess.TimeoutExpired:
        print("Command timed out!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_folder_parsing()
