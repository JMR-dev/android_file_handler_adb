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
import tempfile
from typing import Optional
import hashlib

def get_executable_directory() -> str:
    """Get the directory containing the executable or script."""
    if getattr(sys, 'frozen', False):
        # Running as executable (PyInstaller, cx_Freeze, etc.)
        return os.path.dirname(sys.executable)
    else:
        # Running as script - use the script's directory
        return os.path.dirname(os.path.abspath(__file__))
    
def ensure_platform_tools_in_user_dir(version_tag: Optional[str] = "latest") -> str:
    """Ensure platform-tools installed in a per-user data dir and return adb path.

    Behavior:
    - Uses platformdirs.user_data_dir('android-file-handler') if available,
      else falls back to ~/.local/share/android-file-handler (POSIX) or
      %LOCALAPPDATA% on Windows via expanduser.
    - Installs into <data_dir>/platform-tools/<version>/ and creates/update
      a symlink <data_dir>/platform-tools/current -> <version>.
    - Downloads into a temp dir and moves atomically to avoid partial installs.
    - Sets executable permissions on adb binary.
    - Returns absolute path to adb binary (no PATH modification required).
    """
    try:
        from platformdirs import user_data_dir  # type: ignore
    except Exception:
        user_data_dir = None

    # Determine base data dir
    if user_data_dir:
        data_root = os.path.join(user_data_dir("android-file-handler"), "platform-tools")
    else:
        # Fallback: use home-based location
        home = os.path.expanduser("~")
        data_root = os.path.join(home, ".local", "share", "android-file-handler", "platform-tools")

    os.makedirs(data_root, exist_ok=True)

    target_version = version_tag or "latest"
    target_dir = os.path.join(data_root, target_version)
    current_link = os.path.join(data_root, "current")

    # If current symlink exists and points to a valid adb, return it
    if os.path.islink(current_link):
        try:
            resolved = os.path.realpath(current_link)
            adb_name = "adb.exe" if sys.platform.startswith("win") else "adb"
            candidate = os.path.join(resolved, adb_name)
            if os.path.isfile(candidate):
                return candidate
        except Exception:
            pass

    # If requested version already installed, point current there
    if os.path.isdir(target_dir) and os.path.isfile(os.path.join(target_dir, "adb" if not sys.platform.startswith("win") else "adb.exe")):
        # update symlink atomically
        if os.path.islink(current_link) or os.path.exists(current_link):
            try:
                os.remove(current_link)
            except Exception:
                pass
        try:
            os.symlink(target_dir, current_link)
        except Exception:
            # best-effort, ignore if unable to create symlink
            pass
        return os.path.join(target_dir, "adb.exe" if sys.platform.startswith("win") else "adb")

    # Download into temp location and extract
    tmp_dir = tempfile.mkdtemp(prefix="platform-tools-")
    try:
        # choose URL
        if sys.platform.startswith("linux"):
            url = ADB_LINUX_ZIP_URL
        elif sys.platform.startswith("win"):
            url = ADB_WIN_ZIP_URL
        else:
            raise RuntimeError("Unsupported platform for platform-tools download")

        # download in streaming fashion to avoid memory pressure
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        zip_path = os.path.join(tmp_dir, "platform-tools.zip")
        with open(zip_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)

        # extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        # the zip contains a top-level platform-tools directory; move that into target_dir
        extracted_dir = os.path.join(tmp_dir, "platform-tools")
        if not os.path.isdir(extracted_dir):
            # try to find a platform-tools directory inside temp
            for entry in os.listdir(tmp_dir):
                candidate = os.path.join(tmp_dir, entry)
                if os.path.isdir(candidate) and entry.lower().startswith("platform-tools"):
                    extracted_dir = candidate
                    break

        if not os.path.isdir(extracted_dir):
            raise RuntimeError("Platform-tools not found in archive")

        # Atomic install: move extracted_dir -> target_dir (remove existing backup first)
        if os.path.isdir(target_dir):
            backup = f"{target_dir}.bak"
            shutil.rmtree(backup, ignore_errors=True)
            shutil.move(target_dir, backup)
        shutil.move(extracted_dir, target_dir)

        # Ensure adb executable perms on POSIX
        adb_name = "adb.exe" if sys.platform.startswith("win") else "adb"
        adb_path = os.path.join(target_dir, adb_name)
        if os.path.isfile(adb_path) and os.name == "posix":
            os.chmod(adb_path, 0o755)

        # Atomically update 'current' symlink
        tmp_link = f"{current_link}.tmp"
        try:
            if os.path.exists(tmp_link):
                os.remove(tmp_link)
            os.symlink(target_dir, tmp_link)
            os.replace(tmp_link, current_link)
        except OSError:
            # fallback: remove and recreate
            try:
                if os.path.exists(current_link):
                    os.remove(current_link)
                os.symlink(target_dir, current_link)
            except Exception:
                pass

        return adb_path
    finally:
        # Clean temp dir
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
        except Exception:
            pass

def get_platform_tools_directory() -> str:
    """Get platform-tools directory."""
    base_dir = get_executable_directory()
    
    # Check if we're in development mode (running from src/ directory)
    if not getattr(sys, 'frozen', False):
        # Running as script - check if we're in src/ directory or subdirectory
        if base_dir.endswith('src'):
            # Already in src directory - place platform-tools here
            return os.path.join(base_dir, "platform-tools")
        elif base_dir.endswith('gui') or os.path.basename(base_dir) in ['gui']:
            # In src/gui subdirectory - go up one level to src
            src_dir = os.path.dirname(base_dir)
            return os.path.join(src_dir, "platform-tools")
        else:
            # Not in src structure - assume we need to find/create src directory
            # This handles cases where the script might be run from project root
            current_dir = base_dir
            src_dir = os.path.join(current_dir, "src")
            if os.path.exists(src_dir):
                return os.path.join(src_dir, "platform-tools")
            else:
                # Fallback to current directory
                return os.path.join(base_dir, "src", "platform-tools")
    
    # Running as executable - use directory next to binary
    return os.path.join(base_dir, "platform-tools")


# Constants
ADB_WIN_ZIP_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
)
ADB_LINUX_ZIP_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
)
OS_TYPE = sys.platform

# Determine ADB binary name based on platform
if OS_TYPE.startswith("linux"):
    ADB_BINARY_NAME = "adb"
elif OS_TYPE.startswith("win"):
    ADB_BINARY_NAME = "adb.exe"
else:
    ADB_BINARY_NAME = "adb"

# ADB binary path is resolved at runtime via get_adb_binary_path() to avoid
# duplicate logic and to centralize platform-tools installation behavior.


def get_adb_binary_path() -> str:
    """Return the path to the adb binary, installing platform-tools if needed.

    This central helper ensures a consistent location across the codebase.
    """
    adb_name = "adb.exe" if sys.platform.startswith("win") else "adb"
    try:
        # If platform-tools are installed in the user data dir, prefer that
        adb_path = ensure_platform_tools_in_user_dir()
        if adb_path and os.path.isfile(adb_path):
            return adb_path
    except Exception:
        pass

    # Fallback: look for an executable next to the project or installed path
    local_folder = get_platform_tools_directory()
    candidate = os.path.join(local_folder, adb_name)
    return candidate


class ADBManager:
    """Manages ADB operations and Android device communication."""

    def __init__(self):
        self.progress_callback: Optional[Callable[[int], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        self.current_process: Optional[subprocess.Popen] = None

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
            free_space = shutil.disk_usage(get_platform_tools_directory())[2]
            if free_space < 50 * 1024 * 1024:  # 50MB minimum
                raise Exception("Insufficient disk space")
            return True
        except OSError:
            # Create directory if it doesn't exist
            os.makedirs(get_platform_tools_directory(), exist_ok=True)
            return True

    def download_and_extract_adb(self) -> bool:
        """Download and extract ADB tools if not present."""
        # Use the centralized installer which will return the adb path (and
        # perform a download if needed). If it returns a valid path, report
        # success; otherwise return False.
        try:
            adb_path = ensure_platform_tools_in_user_dir()
            if adb_path and os.path.isfile(adb_path):
                # Ensure executable permissions on POSIX
                if os.name == "posix":
                    try:
                        os.chmod(adb_path, 0o755)
                    except Exception:
                        pass
                self._update_status("ADB available at: " + adb_path)
                return True
            return False
        except Exception as e:
            self._update_status(f"Failed to ensure platform-tools: {e}")
            return False

    def run_adb_command(self, args: list, capture_output: bool = True):
        """Run an ADB command and return output."""
        cmd = [get_adb_binary_path()] + args
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
        """Parse progress percentage from ADB output with enhanced patterns for large transfers."""
        # Original pattern: (XX%)
        m = re.search(r"\((\d{1,3})%\)", text_line)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Additional patterns for large transfers
        # Pattern: XX% complete
        m = re.search(r"(\d{1,3})%\s+complete", text_line, re.IGNORECASE)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Pattern: transferred XX%
        m = re.search(r"transferred\s+(\d{1,3})%", text_line, re.IGNORECASE)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Pattern: XX files pulled/pushed (XX%)
        m = re.search(
            r"\d+\s+files?\s+(?:pulled|pushed).*?\((\d{1,3})%\)",
            text_line,
            re.IGNORECASE,
        )
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        return None

    def pull_folder(self, remote_path: str, local_path: str) -> bool:
        """Pull files from Android device to local machine."""
        # Normalize paths and prepare
        local_path = os.path.normpath(local_path)
        remote_path = remote_path.strip()

        try:
            os.makedirs(local_path, exist_ok=True)
        except Exception as e:
            self._update_status(f"Failed to create local directory: {e}")
            return False

        # Warn if writing to root drive on Windows
        if os.name == "nt":
            normalized_path = os.path.abspath(local_path)
            drive_root = os.path.splitdrive(normalized_path)[0] + os.sep
            if normalized_path == drive_root:
                self._update_status(
                    "Warning: Transferring to root drive. Consider using a subfolder."
                )

        cmd = [get_adb_binary_path(), "pull", remote_path, local_path]
        self._update_status(f"Command: adb pull '{remote_path}' '{local_path}'")

        try:
            self._update_progress(0)
            self._update_status("Starting transfer...")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.current_process = proc

            line_count = 0
            last_progress = 0
            start_time = time.time()
            last_update_time = start_time

            if proc.stdout:
                for line in proc.stdout:
                    line_count += 1
                    current_time = time.time()
                    pct = self.parse_progress(line)

                    if pct is not None:
                        self._update_progress(pct)
                        last_progress = pct
                        last_update_time = current_time
                    else:
                        elapsed_time = current_time - start_time
                        time_since_last_update = current_time - last_update_time

                        should_update = False
                        new_progress = last_progress

                        if time_since_last_update >= 2.0 and last_progress < 95:
                            if line_count > 100:
                                activity_factor = min(line_count / 1000, 50)
                                time_factor = min(elapsed_time / 60, 40)
                                new_progress = min(activity_factor + time_factor, 95)
                            else:
                                new_progress = min(last_progress + 10, 95)
                            should_update = True
                        elif line_count % 50 == 0 and last_progress < 90:
                            increment = max(1, min(5, 90 // (line_count // 50 + 1)))
                            new_progress = min(last_progress + increment, 90)
                            should_update = True

                        if should_update and new_progress > last_progress:
                            self._update_progress(int(new_progress))
                            last_progress = new_progress
                            last_update_time = current_time

                    self._update_status(line.strip())

            proc.wait()
            if proc.returncode == 0:
                self._update_progress(100)
                self._update_status("Transfer completed successfully.")
                self.current_process = None
                return True
            else:
                error_msg = f"Transfer failed with code {proc.returncode}"
                if hasattr(proc, "stderr") and proc.stderr:
                    try:
                        stderr_output = proc.stderr.read()
                        if stderr_output:
                            error_msg += f". Error: {stderr_output}"
                    except Exception:
                        pass
                self._update_status(error_msg)
                self.current_process = None
                return False
        except Exception as e:
            self._update_status(f"Transfer error: {e}")
            self.current_process = None
            return False

    def push_folder(self, local_path: str, remote_path: str) -> bool:
        """Push files from local machine to Android device."""
        local_path = os.path.normpath(local_path)
        remote_path = remote_path.strip()

        if not os.path.exists(local_path):
            self._update_status(f"Local path does not exist: {local_path}")
            return False

        if os.name == "nt":
            normalized_path = os.path.abspath(local_path)
            drive_root = os.path.splitdrive(normalized_path)[0] + os.sep
            if normalized_path == drive_root:
                self._update_status(
                    "Warning: Pushing from root drive. Consider using a subfolder."
                )

        cmd = [get_adb_binary_path(), "push", local_path, remote_path]
        self._update_status(f"Command: adb push '{local_path}' '{remote_path}'")

        try:
            self._update_progress(0)
            self._update_status("Starting transfer...")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.current_process = proc
        except Exception as e:
            self._update_status(f"Failed to start adb: {e}")
            return False

        line_count = 0
        last_progress = 0
        start_time = time.time()
        last_update_time = start_time

        if proc.stdout:
            for line in proc.stdout:
                line_count += 1
                current_time = time.time()
                pct = self.parse_progress(line)

                if pct is not None:
                    self._update_progress(pct)
                    last_progress = pct
                    last_update_time = current_time
                else:
                    elapsed_time = current_time - start_time
                    if elapsed_time >= 1.0 and last_progress < 90:
                        new_progress = min(last_progress + 20, 90)
                        self._update_progress(int(new_progress))
                        last_progress = new_progress
                        last_update_time = current_time

                self._update_status(line.strip())

        proc.wait()
        if proc.returncode == 0:
            self._update_progress(100)
            self._update_status("Transfer completed successfully.")
            self.current_process = None
            return True
        else:
            error_msg = f"Push failed with code {proc.returncode}"
            if hasattr(proc, "stderr") and proc.stderr:
                try:
                    stderr_output = proc.stderr.read()
                    if stderr_output:
                        error_msg += f". Error: {stderr_output}"
                except Exception:
                    pass
            self._update_status(error_msg)
            self.current_process = None
            return False

    def pull_file(self, remote_file_path: str, local_file_path: str) -> bool:
        """Pull a single file from Android device to local machine."""
        # Normalize paths for better compatibility
        local_file_path = os.path.normpath(local_file_path)
        remote_file_path = remote_file_path.strip()

        # Ensure local directory exists
        local_dir = os.path.dirname(local_file_path)
        try:
            if local_dir:  # Only create if there's a directory part
                os.makedirs(local_dir, exist_ok=True)
        except Exception as e:
            self._update_status(f"Failed to create local directory: {e}")
            return False

        # For Windows root drives, ensure proper formatting
        if os.name == "nt":
            # Check if this is a root drive (like C:\, D:\, etc.)
            normalized_path = os.path.abspath(local_dir)
            drive_root = os.path.splitdrive(normalized_path)[0] + os.sep
            if normalized_path == drive_root:
                # Root drive path like C:\ - this might cause issues with ADB
                self._update_status(
                    "Warning: Transferring to root drive. Consider using a subfolder."
                )

        cmd = [get_adb_binary_path(), "pull", remote_file_path, local_file_path]

        # Debug output for troubleshooting
        self._update_status(f"Command: adb pull '{remote_file_path}' '{local_file_path}'")

        try:
            # Start with initial progress
            self._update_progress(0)
            self._update_status("Starting file transfer...")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.current_process = proc

            line_count = 0
            last_progress = 0
            start_time = time.time()
            last_update_time = start_time

            if proc.stdout:
                for line in proc.stdout:
                    line_count += 1
                    current_time = time.time()
                    pct = self.parse_progress(line)

                    if pct is not None:
                        # Use explicit progress when available
                        self._update_progress(pct)
                        last_progress = pct
                        last_update_time = current_time
                    else:
                        # For single files, use simpler progress estimation
                        elapsed_time = current_time - start_time
                        if elapsed_time >= 1.0 and last_progress < 90:
                            # Simple time-based progress for files
                            new_progress = min(last_progress + 20, 90)
                            self._update_progress(int(new_progress))
                            last_progress = new_progress
                            last_update_time = current_time

                    self._update_status(line.strip())

            proc.wait()
            if proc.returncode == 0:
                self._update_progress(100)
                self._update_status("File transfer completed successfully.")
                self.current_process = None
                return True
            else:
                # Capture error output for better debugging
                error_msg = f"File transfer failed with code {proc.returncode}"
                if hasattr(proc, "stderr") and proc.stderr:
                    try:
                        stderr_output = proc.stderr.read()
                        if stderr_output:
                            error_msg += f". Error: {stderr_output}"
                    except:
                        pass
                self._update_status(error_msg)
                self.current_process = None
                return False

        except Exception as e:
            self._update_status(f"File transfer error: {e}")
            self.current_process = None
            return False

    def push_file(self, local_file_path: str, remote_file_path: str) -> bool:
        """Push a single file from local machine to Android device."""
        # Normalize paths for better compatibility
        local_file_path = os.path.normpath(local_file_path)
        remote_file_path = remote_file_path.strip()

        # Validate local file exists
        if not os.path.isfile(local_file_path):
            self._update_status(f"Local file does not exist: {local_file_path}")
            return False

        # For Windows root drives, ensure proper formatting
        if os.name == "nt":
            # Check if this is a root drive (like C:\, D:\, etc.)
            normalized_path = os.path.abspath(local_file_path)
            drive_root = os.path.splitdrive(normalized_path)[0] + os.sep
            if os.path.dirname(normalized_path) == drive_root.rstrip(os.sep):
                # File in root drive - this might cause issues with ADB
                self._update_status(
                    "Warning: Pushing from root drive. Consider using a subfolder."
                )

        cmd = [get_adb_binary_path(), "push", local_file_path, remote_file_path]

        # Debug output for troubleshooting
        self._update_status(f"Command: adb push '{local_file_path}' '{remote_file_path}'")

        try:
            # Start with initial progress
            self._update_progress(0)
            self._update_status("Starting file transfer...")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.current_process = proc
        except Exception as e:
            self._update_status(f"Failed to start adb: {e}")
            return False

        line_count = 0
        last_progress = 0
        start_time = time.time()
        last_update_time = start_time

        if proc.stdout:
            for line in proc.stdout:
                line_count += 1
                current_time = time.time()
                pct = self.parse_progress(line)

                if pct is not None:
                    # Use explicit progress when available
                    self._update_progress(pct)
                    last_progress = pct
                    last_update_time = current_time
                else:
                    # For single files, use simpler progress estimation
                    elapsed_time = current_time - start_time
                    if elapsed_time >= 1.0 and last_progress < 90:
                        # Simple time-based progress for files
                        new_progress = min(last_progress + 20, 90)
                        self._update_progress(int(new_progress))
                        last_progress = new_progress
                        last_update_time = current_time

                self._update_status(line.strip())

        proc.wait()
        if proc.returncode == 0:
            self._update_progress(100)
            self._update_status("File transfer completed successfully.")
            self.current_process = None
            return True
        else:
            # Capture error output for better debugging
            error_msg = f"File push failed with code {proc.returncode}"
            if hasattr(proc, "stderr") and proc.stderr:
                try:
                    stderr_output = proc.stderr.read()
                    if stderr_output:
                        error_msg += f". Error: {stderr_output}"
                except:
                    pass
            self._update_status(error_msg)
            self.current_process = None
            return False

    def cancel_transfer(self) -> bool:
        """Cancel the current transfer operation."""
        if self.current_process is not None:
            try:
                # Terminate the process
                self.current_process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.current_process.kill()
                    self.current_process.wait()
                
                self.current_process = None
                self._update_status("Transfer cancelled by user")
                return True
            except Exception as e:
                self._update_status(f"Error cancelling transfer: {e}")
                return False
        return False

    # (Method intentionally removed - use top-level ensure_platform_tools_in_user_dir)


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
def is_adb_available() -> bool:
    """Check if ADB binary is available using the centralized resolver."""
    try:
        adb_path = get_adb_binary_path()
        return os.path.isfile(adb_path)
    except Exception:
        return False


def get_platform_type() -> str:
    """Get the current platform type."""
    return OS_TYPE


