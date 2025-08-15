"""
Android File Handler - Business Logic Module
Handles ADB operations, device management, and file transfers.
"""

import os
import sys
import subprocess
import requests
import zipfile
import io
import shutil
import glob
import time
import re
from typing import Optional, Tuple, Callable

# Constants
ADB_WIN_ZIP_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
)
ADB_LINUX_ZIP_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
)
LOCAL_ADB_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "platform-tools"
)
OS_TYPE = sys.platform

# Determine ADB binary name based on platform
if OS_TYPE.startswith("linux"):
    ADB_BINARY_NAME = "adb"
elif OS_TYPE.startswith("win"):
    ADB_BINARY_NAME = "adb.exe"
else:
    ADB_BINARY_NAME = "adb"

ADB_BINARY_PATH = os.path.join(LOCAL_ADB_FOLDER, ADB_BINARY_NAME)


class ADBManager:
    """Manages ADB operations and Android device communication."""

    def __init__(self):
        self.progress_callback: Optional[Callable[[int], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[int], None]):
        """Set callback function for progress updates."""
        self.progress_callback = callback

    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback function for status updates."""
        self.status_callback = callback

    def _update_progress(self, percentage: int):
        """Internal method to update progress."""
        if self.progress_callback:
            self.progress_callback(percentage)

    def _update_status(self, message: str):
        """Internal method to update status."""
        if self.status_callback:
            self.status_callback(message)

    def check_local_disk_space(self) -> bool:
        """Check if there's enough disk space for ADB download."""
        try:
            free_space = shutil.disk_usage(LOCAL_ADB_FOLDER)[2]
            if free_space < 50 * 1024 * 1024:  # 50MB minimum
                raise Exception("Insufficient disk space")
            return True
        except OSError:
            # Create directory if it doesn't exist
            os.makedirs(LOCAL_ADB_FOLDER, exist_ok=True)
            return True

    def download_and_extract_adb(self) -> bool:
        """Download and extract ADB tools if not present."""
        if os.path.isfile(ADB_BINARY_PATH):
            return True

        try:
            # Determine the correct URL based on platform
            if OS_TYPE.startswith("linux"):
                adb_zip_url = ADB_LINUX_ZIP_URL
            elif OS_TYPE.startswith("win"):
                adb_zip_url = ADB_WIN_ZIP_URL
            else:
                print("Unsupported platform")
                return False

            if not self.check_local_disk_space():
                return False

            self._update_status("Downloading platform-tools (ADB)...")

            response = requests.get(adb_zip_url, stream=True, timeout=30)
            response.raise_for_status()

            binary_archive = zipfile.ZipFile(io.BytesIO(response.content))
            binary_archive.extractall(LOCAL_ADB_FOLDER)

            if OS_TYPE.startswith("linux"):
                if os.path.exists(ADB_BINARY_PATH):
                    os.chmod(ADB_BINARY_PATH, 0o755)
                else:
                    raise Exception("ADB binary not found after extraction")

            self._update_status("Downloaded and extracted platform-tools.")
            return True
        except Exception as e:
            print(f"Failed to download ADB: {e}")
            return False

    def run_adb_command(self, args: list, capture_output: bool = True):
        """Run an ADB command and return output."""
        cmd = [ADB_BINARY_PATH] + args
        try:
            if capture_output:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return p.stdout.strip(), p.stderr.strip(), p.returncode
            else:
                p = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                return p
        except Exception as e:
            if capture_output:
                return None, str(e), -1
            else:
                return None

    def check_device(self) -> Optional[str]:
        """Check if an Android device is connected."""
        result = self.run_adb_command(["devices"], capture_output=True)
        if isinstance(result, tuple) and len(result) == 3:
            out, err, rc = result
            if rc != 0 or not out:
                return None
            for line in out.splitlines():
                if line.endswith("\tdevice"):
                    return line.split()[0]
        return None

    def parse_progress(self, text_line: str) -> Optional[int]:
        """Parse progress percentage from ADB output."""
        m = re.search(r"\((\d{1,3})%\)", text_line)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct
        return None

    def pull_folder(self, remote_path: str, local_path: str) -> bool:
        """Pull files from Android device to local machine."""
        cmd = [ADB_BINARY_PATH, "pull", remote_path, local_path]

        try:
            # Start with initial progress
            self._update_progress(0)
            self._update_status("Starting transfer...")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            line_count = 0
            last_progress = 0
            if proc.stdout:
                for line in proc.stdout:
                    line_count += 1
                    pct = self.parse_progress(line)
                    if pct is not None:
                        self._update_progress(pct)
                        last_progress = pct
                    else:
                        # If no explicit progress, simulate some progress based on activity
                        if line_count % 5 == 0 and last_progress < 90:
                            estimated_progress = min(last_progress + 5, 90)
                            self._update_progress(estimated_progress)
                            last_progress = estimated_progress

                    self._update_status(line.strip())

            proc.wait()
            if proc.returncode == 0:
                self._update_progress(100)
                self._update_status("Transfer completed successfully.")
                return True
            else:
                self._update_status(f"Transfer failed with code {proc.returncode}")
                return False

        except Exception as e:
            self._update_status(f"Transfer error: {e}")
            return False

    def push_folder(self, local_path: str, remote_path: str) -> bool:
        """Push files from local machine to Android device."""
        cmd = [ADB_BINARY_PATH, "push", local_path, remote_path]

        try:
            # Start with initial progress
            self._update_progress(0)
            self._update_status("Starting transfer...")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self._update_status(f"Failed to start adb: {e}")
            return False

        line_count = 0
        last_progress = 0
        if proc.stdout:
            for line in proc.stdout:
                line_count += 1
                pct = self.parse_progress(line)
                if pct is not None:
                    self._update_progress(pct)
                    last_progress = pct
                else:
                    # If no explicit progress, simulate some progress based on activity
                    if line_count % 5 == 0 and last_progress < 90:
                        estimated_progress = min(last_progress + 5, 90)
                        self._update_progress(estimated_progress)
                        last_progress = estimated_progress

                self._update_status(line.strip())

        proc.wait()
        if proc.returncode == 0:
            self._update_progress(100)
            self._update_status("Transfer completed successfully.")
            return True
        else:
            self._update_status(f"adb push failed with return code {proc.returncode}")
            return False


class LinuxMTPManager:
    """Manages MTP operations on Linux systems."""

    def __init__(self):
        self.mount_point = "/tmp/android_mtp"

    def mount_mtp_device(self) -> Optional[str]:
        """Mount MTP device to filesystem using jmtpfs."""
        try:
            # Create mount point
            os.makedirs(self.mount_point, exist_ok=True)

            # Check if already mounted
            result = subprocess.run(
                ["mountpoint", self.mount_point], capture_output=True, text=True
            )
            if result.returncode == 0:
                return self.mount_point

            # First, try to unmount any existing GVFS MTP mounts
            self._unmount_gvfs_mtp()

            # Kill any existing MTP processes that might be interfering
            subprocess.run(["pkill", "-f", "gvfs-mtp"], capture_output=True)
            subprocess.run(["pkill", "-f", "jmtpfs"], capture_output=True)

            # Wait a moment for processes to clean up
            time.sleep(1)

            # Mount using jmtpfs
            result = subprocess.run(
                ["jmtpfs", self.mount_point], capture_output=True, text=True
            )
            if result.returncode == 0:
                return self.mount_point
            else:
                print(f"Failed to mount MTP device: {result.stderr}")
                return None
        except Exception as e:
            print(f"Error mounting MTP device: {e}")
            return None

    def _unmount_gvfs_mtp(self):
        """Unmount any GVFS MTP mounts."""
        try:
            # Find GVFS MTP mounts
            result = subprocess.run(["mount"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "gvfs" in line and "mtp" in line:
                    # Extract mount point from mount line
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_point = parts[2]
                        subprocess.run(
                            ["fusermount", "-u", mount_point], capture_output=True
                        )

            # Also try to unmount common GVFS locations
            gvfs_locations = ["/run/user/*/gvfs/mtp*", "/media/*", "~/.gvfs/mtp*"]

            for location_pattern in gvfs_locations:
                result = subprocess.run(
                    ["find", "/run/user", "-name", "mtp*", "-type", "d"],
                    capture_output=True,
                    text=True,
                )
                for mount_point in result.stdout.strip().split("\n"):
                    if mount_point:
                        subprocess.run(
                            ["fusermount", "-u", mount_point], capture_output=True
                        )

        except Exception as e:
            print(f"Warning: Could not unmount GVFS MTP: {e}")

    def unmount_mtp_device(self) -> bool:
        """Unmount MTP device."""
        try:
            subprocess.run(["fusermount", "-u", self.mount_point], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to unmount: {e}")
            return False

    def find_gvfs_mtp_mount(self) -> Optional[str]:
        """Find existing GVFS MTP mount point."""
        try:
            # Check common GVFS mount locations (Linux only)
            if sys.platform.startswith("linux"):
                try:
                    if hasattr(os, "getuid"):
                        user_id = os.getuid()  # type: ignore
                        gvfs_patterns = [
                            f"/run/user/{user_id}/gvfs/mtp*",
                            "/media/*android*",
                            "/media/*MTP*",
                        ]
                    else:
                        # Fallback if getuid is not available
                        gvfs_patterns = [
                            "/run/user/*/gvfs/mtp*",
                            "/media/*android*",
                            "/media/*MTP*",
                        ]
                except (AttributeError, OSError):
                    # Fallback if getuid is not available or fails
                    gvfs_patterns = [
                        "/run/user/*/gvfs/mtp*",
                        "/media/*android*",
                        "/media/*MTP*",
                    ]

                for pattern in gvfs_patterns:
                    matches = glob.glob(pattern)
                    if matches:
                        # Return the first valid mount point
                        for mount in matches:
                            if os.path.isdir(mount):
                                return mount
            return None
        except Exception as e:
            print(f"Error finding GVFS mount: {e}")
            return None


# Helper functions for standalone usage
def get_adb_binary_path() -> str:
    """Get the path to the ADB binary."""
    return ADB_BINARY_PATH


def is_adb_available() -> bool:
    """Check if ADB binary is available."""
    return os.path.isfile(ADB_BINARY_PATH)


def get_platform_type() -> str:
    """Get the current platform type."""
    return OS_TYPE
