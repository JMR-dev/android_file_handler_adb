"""
Debug script for troubleshooting ADB device detection issues.

This script provides comprehensive debugging information for ADB connectivity,
including binary path verification, device detection, and command execution testing.
"""

import os
import sys

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from adb_manager import ADBManager


def main():
    """Run comprehensive ADB debugging tests."""
    print("=== ADB Device Detection Debug ===\n")

    # Test 1: Check if ADB binary exists
    adb_manager = ADBManager()
    from adb_manager import ADB_BINARY_PATH

    adb_path = ADB_BINARY_PATH
    print(f"1. ADB Binary Path: {adb_path}")
    print(f"   ADB Binary Exists: {os.path.exists(adb_path)}\n")

    if not os.path.exists(adb_path):
        print("❌ ADB binary not found! Check the platform-tools directory structure.")
        return

    # Test 2: Run ADB command directly
    print("2. Testing ADB command directly...")
    try:
        import subprocess

        result = subprocess.run(
            [adb_path, "devices"], capture_output=True, text=True, timeout=10
        )
        print(f"   Return code: {result.returncode}")
        print(f"   STDOUT: {repr(result.stdout)}")
        print(f"   STDERR: {repr(result.stderr)}\n")
    except Exception as e:
        print(f"   Error running ADB directly: {e}\n")

    # Test 3: Test ADBManager device detection
    print("3. Testing with ADBManager...")
    try:
        result = adb_manager.run_adb_command(["devices"])
        print(f"   Raw result: {result}")
        print(f"   Raw result type: {type(result)}")

        device = adb_manager.check_device()
        if device:
            print(f"   Device found: {device}\n")
        else:
            print("   No device found by ADBManager\n")
    except Exception as e:
        print(f"   Error with ADBManager: {e}\n")

    # Test 4: Manual parsing for debugging
    print("4. Manual parsing of ADB output:")
    try:
        import subprocess

        result = subprocess.run(
            [adb_path, "devices"], capture_output=True, text=True, timeout=10
        )
        print(f"   Return code: {result.returncode}")

        lines = result.stdout.strip().split("\n")
        print("   Output lines:")
        for i, line in enumerate(lines):
            print(f"     Line {i}: {repr(line)}")
            if "\t" in line and "device" in line:
                device_id = line.split("\t")[0].strip()
                print(f"       ✅ Found device: {device_id}")
        print()
    except Exception as e:
        print(f"   Error in manual parsing: {e}\n")

    # Test 5: Additional ADB info
    print("5. Additional ADB commands for debugging:")
    try:
        import subprocess

        # ADB version
        version_result = subprocess.run(
            [adb_path, "version"], capture_output=True, text=True, timeout=5
        )
        print(f"   ADB Version: {version_result.stdout.strip()}")

        # Restart ADB server
        subprocess.run([adb_path, "kill-server"], capture_output=True, timeout=5)
        subprocess.run([adb_path, "start-server"], capture_output=True, timeout=5)

        # Check devices again after restart
        devices_result = subprocess.run(
            [adb_path, "devices"], capture_output=True, text=True, timeout=10
        )
        print(f"   Restarting ADB server...")
        print(f"   After restart - Return code: {devices_result.returncode}")
        print(f"   After restart - Output: {repr(devices_result.stdout)}")

    except Exception as e:
        print(f"   Error in additional tests: {e}")


if __name__ == "__main__":
    main()
