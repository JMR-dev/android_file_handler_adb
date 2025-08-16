"""
Debug large transfer ADB output
"""

import sys
import subprocess
import re
import time
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from src.adb_manager import ADB_BINARY_PATH


def debug_large_transfer_output():
    """Debug what ADB output looks like for large transfers."""

    print("=== DEBUGGING LARGE TRANSFER ADB OUTPUT ===")
    print("This will show you what ADB actually outputs during large transfers.")
    print("Use Ctrl+C to stop when you see enough output.\n")

    # Get user input for paths
    remote_path = input("Enter remote path (e.g., /sdcard/DCIM): ").strip()
    if not remote_path:
        remote_path = "/sdcard/DCIM"

    local_path = input("Enter local path (e.g., C:\\temp\\debug_transfer): ").strip()
    if not local_path:
        local_path = "C:\\temp\\debug_transfer"

    print(f"\nDebugging transfer: {remote_path} -> {local_path}")
    print("ADB output analysis:\n")

    cmd = [ADB_BINARY_PATH, "pull", remote_path, local_path]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        line_count = 0
        progress_lines = []

        if proc.stdout:
            for line in proc.stdout:
                line_count += 1
                line_clean = line.strip()

                # Check for progress information
                progress_match = re.search(r"\((\d{1,3})%\)", line)

                # Log interesting lines
                if (
                    progress_match
                    or "%" in line
                    or line_count <= 20
                    or line_count % 100 == 0
                ):
                    print(f"Line {line_count:4d}: {line_clean}")

                    if progress_match:
                        pct = int(progress_match.group(1))
                        progress_lines.append((line_count, pct, line_clean))

                # Show periodic updates for very long transfers
                if line_count % 500 == 0:
                    print(f"... ({line_count} lines processed) ...")

        proc.wait()

        print(f"\n=== TRANSFER COMPLETED ===")
        print(f"Total lines: {line_count}")
        print(f"Return code: {proc.returncode}")
        print(f"Progress lines found: {len(progress_lines)}")

        if progress_lines:
            print("\nProgress line analysis:")
            for line_num, pct, text in progress_lines:
                print(f"  Line {line_num}: {pct}% - {text}")
        else:
            print("No explicit progress percentages found in output!")
            print("This explains why large transfers don't show progress.")

    except KeyboardInterrupt:
        print(f"\n\nStopped at line {line_count}")
        if proc:
            proc.terminate()

        if progress_lines:
            print(f"Progress lines found so far: {len(progress_lines)}")
            for line_num, pct, text in progress_lines[-5:]:  # Show last 5
                print(f"  Line {line_num}: {pct}% - {text}")

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Debug large transfer functionality."""
    print("Choose debug option:")
    print("1. Debug large transfer ADB output")
    print("2. Run original ADB detection tests")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        debug_large_transfer_output()
    else:
        debug_original_adb_detection()


def debug_original_adb_detection():
    """Original ADB debugging functionality."""
    from src.adb_manager import ADBManager

    print("=== ADB Device Detection Debug ===\n")

    # Test 1: Check if ADB binary exists
    adb_manager = ADBManager()

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
