"""
Linux Android Browser Module
Provides Android filesystem browsing capabilities for Linux using MTP.
"""

import os
from tkinter import messagebox, filedialog


class LinuxAndroidBrowser:
    """Android filesystem browser for Linux using MTP."""

    def __init__(self, parent_window, mtp_manager, remote_path_var):
        self.parent = parent_window
        self.mtp_manager = mtp_manager
        self.remote_path_var = remote_path_var

    def show_browser(self):
        """Browse remote Android folders via MTP (Linux)"""
        if not self.mtp_manager:
            messagebox.showerror(
                "Error",
                "MTP manager not available. This feature is only supported on Linux.",
            )
            return

        # First try using existing GVFS mount
        gvfs_mount = self.mtp_manager.find_gvfs_mtp_mount()
        if gvfs_mount:
            try:
                folder = filedialog.askdirectory(
                    initialdir=gvfs_mount, title="Select Android folder"
                )
                if folder:
                    # Convert filesystem path back to Android path
                    relative_path = os.path.relpath(folder, gvfs_mount)
                    if relative_path == ".":
                        android_path = "/sdcard"
                    else:
                        android_path = f"/sdcard/{relative_path}".replace("\\", "/")
                    self.remote_path_var.set(android_path)
                return
            except Exception as e:
                print(f"GVFS browse failed: {e}")

        # Fallback to jmtpfs
        mount_point = self.mtp_manager.mount_mtp_device()
        if mount_point:
            try:
                folder = filedialog.askdirectory(
                    initialdir=mount_point, title="Select Android folder"
                )
                if folder:
                    # Convert filesystem path back to Android path
                    relative_path = os.path.relpath(folder, mount_point)
                    if relative_path == ".":
                        android_path = "/sdcard"
                    else:
                        android_path = f"/sdcard/{relative_path}".replace("\\", "/")
                    self.remote_path_var.set(android_path)
            finally:
                self.mtp_manager.unmount_mtp_device()
        else:
            messagebox.showerror(
                "Error",
                "Could not mount Android device via MTP. "
                "Make sure it's connected and set to 'File Transfer' mode.",
            )
