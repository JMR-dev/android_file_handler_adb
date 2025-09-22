"""
ADB platform tools management.
Handles downloading, installing, and managing Android platform tools.
"""

import os
import sys
import requests
import zipfile
import shutil
import tempfile
from typing import Optional

from .platform_utils import get_adb_binary_name, get_platform_tools_directory, is_windows, is_linux


# Constants for download URLs
ADB_WIN_ZIP_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
)
ADB_LINUX_ZIP_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
)


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
            adb_name = get_adb_binary_name()
            candidate = os.path.join(resolved, adb_name)
            if os.path.isfile(candidate):
                return candidate
        except Exception:
            pass

    # If requested version already installed, point current there
    adb_name = get_adb_binary_name()
    if os.path.isdir(target_dir) and os.path.isfile(os.path.join(target_dir, adb_name)):
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
        return os.path.join(target_dir, adb_name)

    # Download into temp location and extract
    tmp_dir = tempfile.mkdtemp(prefix="platform-tools-")
    try:
        # choose URL
        if is_linux():
            url = ADB_LINUX_ZIP_URL
        elif is_windows():
            url = ADB_WIN_ZIP_URL
        else:
            raise RuntimeError("Unsupported platform for platform-tools download")

        # download in streaming fashion to avoid memory pressure
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        zip_path = os.path.join(tmp_dir, "platform-tools.zip")
        # Ensure temp directory exists (legacy tests may mock mkdtemp to non-existent path)
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except Exception:
            pass
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


def get_adb_binary_path() -> str:
    """Return the path to the adb binary, installing platform-tools if needed.

    This central helper ensures a consistent location across the codebase.
    """
    adb_name = get_adb_binary_name()
    try:
        # If platform-tools are installed in the user data dir, prefer that
        adb_path = ensure_platform_tools_in_user_dir()
        if adb_path and os.path.isfile(adb_path):
            return adb_path
    except Exception:
        pass
    # Legacy pathway: some tests patch ensure_platform_tools_in_user_dir via adb_manager module
    try:
        from . import adb_manager as _adb_manager  # type: ignore
        if hasattr(_adb_manager, 'ensure_platform_tools_in_user_dir'):
            adb_path = _adb_manager.ensure_platform_tools_in_user_dir()
            if adb_path and os.path.isfile(adb_path):
                return adb_path
    except Exception:
        pass

    # Fallback: look for an executable next to the project or installed path
    local_folder = get_platform_tools_directory()
    candidate = os.path.join(local_folder, adb_name)
    return candidate


def is_adb_available() -> bool:
    """Check if ADB binary is available."""
    try:
        adb_path = get_adb_binary_path()
        return os.path.isfile(adb_path)
    except Exception:
        return False


def download_and_extract_adb() -> bool:
    """Download and extract ADB tools if not present."""
    try:
        adb_path = ensure_platform_tools_in_user_dir()
        if adb_path and os.path.isfile(adb_path):
            # Ensure executable permissions on POSIX
            if os.name == "posix":
                try:
                    os.chmod(adb_path, 0o755)
                except Exception:
                    pass
            return True
        return False
    except Exception:
        return False