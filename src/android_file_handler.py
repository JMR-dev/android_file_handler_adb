import os
import sys
import threading
import subprocess
import requests # type: ignore
import zipfile
import io
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

ADB_WIN_ZIP_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
ADB_LINUX_ZIP_URL = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
LOCAL_ADB_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools")
OS_TYPE = f"{sys.platform}"

if OS_TYPE.startswith("linux"):
    ADB_BINARY_NAME = "adb"
elif OS_TYPE.startswith("win32"):
    ADB_BINARY_NAME = "adb.exe"

ADB_BINARY_PATH = os.path.join(LOCAL_ADB_FOLDER, ADB_BINARY_NAME)

def check_local_disk_space():
    try:
        # Check available disk space
        free_space = shutil.disk_usage(LOCAL_ADB_FOLDER)[2]
        if free_space < 50 * 1024 * 1024:  # 50MB minimum
            raise Exception("Insufficient disk space")
    except OSError:
        # Create directory if it doesn't exist
        os.makedirs(LOCAL_ADB_FOLDER, exist_ok=True)
def download_and_extract_adb():
    if os.path.isfile(ADB_BINARY_PATH):
        return True
    try:
        # Determine the correct URL based on platform
        if OS_TYPE.startswith("linux"):
            ADB_ZIP_URL = ADB_LINUX_ZIP_URL
        elif OS_TYPE.startswith("win"):
            ADB_ZIP_URL = ADB_WIN_ZIP_URL
        else:
            print("Unsupported platform")
            return False
        
        check_local_disk_space()

        print("Downloading platform-tools (ADB)...")
        
        response = requests.get(ADB_ZIP_URL, stream=True, timeout=30)

        response.raise_for_status()
        
        binaryArchive = zipfile.ZipFile(io.BytesIO(response.content))
        
        binaryArchive.extractall(LOCAL_ADB_FOLDER)

        if OS_TYPE.startswith("linux"):
            if os.path.exists(ADB_BINARY_PATH):
                os.chmod(ADB_BINARY_PATH, 0o755)
            elif not os.path.exists(ADB_BINARY_PATH):
                check_local_disk_space()
                download_and_extract_adb()
            else:
                raise Exception("ADB binary not found after extraction")
            
        print("Downloaded and extracted platform-tools.")
        return True
    except Exception as e:
        print(f"Failed to download ADB: {e}")
        return False

def run_adb_command(args, capture_output=True):
    cmd = [ADB_BINARY_PATH] + args
    try:
        if capture_output:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return p.stdout.strip(), p.stderr.strip(), p.returncode
        else:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            return p
    except Exception as e:
        return None, str(e), -1

def check_device():
    out, err, rc = run_adb_command(["devices"])
    if rc != 0:
        return None
    for line in out.splitlines():
        if line.endswith("\tdevice"):
            return line.split()[0]
    return None

class App(tk.Tk,):

    def __init__(self):
        super().__init__()
        self.title("Android Folder Puller")
        self.geometry("520x320")
        self.minsize(520, 320)  # Set minimum window size with more vertical space
        self.resizable(True, True)  # Make window resizable
                # Add to __init__
        self.direction_var = tk.StringVar(value="pull")
        direction_frame = tk.Frame(self)
        direction_frame.pack(anchor="w", padx=10, pady=(10,0))
        tk.Radiobutton(direction_frame, text="Pull (Android → Computer)", 
                    variable=self.direction_var, value="pull").pack(side="left")
        tk.Radiobutton(direction_frame, text="Push (Computer → Android)", 
                    variable=self.direction_var, value="push").pack(side="left", padx=(20,0))
        

        # UI Elements
        tk.Label(self, text="Remote folder path (Android device):").pack(anchor="w", padx=10, pady=(10,0))
        self.remote_path_var = tk.StringVar()
        remote_path_frame = tk.Frame(self)
        remote_path_frame.pack(fill="x", padx=10)
        self.remote_path_entry = tk.Entry(remote_path_frame, textvariable=self.remote_path_var, width=50)
        self.remote_path_entry.pack(side="left", fill="x", expand=True)
        
        if OS_TYPE.startswith("linux"):
            tk.Button(remote_path_frame, text="Browse...", command=self.linux_browse_remote_folder).pack(side="right", padx=(5,0))
        else:
            tk.Button(remote_path_frame, text="Browse...", command=self.browse_local_folder).pack(side="right", padx=(5,0))

        tk.Label(self, text="Local destination folder (Computer):").pack(anchor="w", padx=10, pady=(10,0))
        self.local_path_var = tk.StringVar()
        local_path_frame = tk.Frame(self)
        local_path_frame.pack(fill="x", padx=10)
        self.local_path_entry = tk.Entry(local_path_frame, textvariable=self.local_path_var, width=50)
        self.local_path_entry.pack(side="left", fill="x", expand=True)
        tk.Button(local_path_frame, text="Browse...", command=self.browse_local_folder).pack(side="right", padx=(5,0))

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(20, 5))

        self.status_label = tk.Label(self, text="Status: Idle")
        self.status_label.pack(anchor="w", padx=10, fill="x")

        self.start_btn = tk.Button(self, text="Start Transfer", command=self.start_transfer)
        self.start_btn.pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Check adb availability
        if not os.path.isfile(ADB_BINARY_PATH):
            self.disable_controls()
            self.status_label.config(text="ADB not found locally. Downloading...")
            self.update()
            success = download_and_extract_adb()
            if success:
                self.status_label.config(text="ADB downloaded and ready.")
                self.enable_controls()
            else:
                self.status_label.config(text="Failed to download ADB. Please check your internet and restart.")
                messagebox.showerror("Error", "Failed to download ADB tools. Exiting.")
                self.quit()
                return

        # Check device connected
        self.status_label.config(text="Checking for connected device...")
        self.update()
        device = check_device()
        if not device:
            self.disable_controls()
            self.status_label.config(text="No device detected. Enable USB debugging and connect your device.")
            self.show_enable_debugging_instructions()
        else:
            self.status_label.config(text=f"Device detected: {device}")
    def linux_mount_mtp_device(self):
        """Mount MTP device to filesystem using jmtpfs"""
        mount_point = "/tmp/android_mtp"
        try:
            # Create mount point
            os.makedirs(mount_point, exist_ok=True)
            
            # Check if already mounted
            result = subprocess.run(["mountpoint", mount_point], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                return mount_point
            
            # First, try to unmount any existing GVFS MTP mounts
            self._unmount_gvfs_mtp()
            
            # Kill any existing MTP processes that might be interfering
            subprocess.run(["pkill", "-f", "gvfs-mtp"], capture_output=True)
            subprocess.run(["pkill", "-f", "jmtpfs"], capture_output=True)
            
            # Wait a moment for processes to clean up
            import time
            time.sleep(1)
            
            # Mount using jmtpfs
            result = subprocess.run(["jmtpfs", mount_point], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                return mount_point
            else:
                print(f"Failed to mount MTP device: {result.stderr}")
                return None
        except Exception as e:
            print(f"Error mounting MTP device: {e}")
            return None

    def _unmount_gvfs_mtp(self):
        """Unmount any GVFS MTP mounts"""
        try:
            # Find GVFS MTP mounts
            result = subprocess.run(["mount"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "gvfs" in line and "mtp" in line:
                    # Extract mount point from mount line
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_point = parts[2]
                        subprocess.run(["fusermount", "-u", mount_point], 
                                     capture_output=True)
            
            # Also try to unmount common GVFS locations
            gvfs_locations = [
                "/run/user/*/gvfs/mtp*",
                "/media/*",
                "~/.gvfs/mtp*"
            ]
            
            for location_pattern in gvfs_locations:
                result = subprocess.run(["find", "/run/user", "-name", "mtp*", "-type", "d"], 
                                      capture_output=True, text=True)
                for mount_point in result.stdout.strip().split('\n'):
                    if mount_point:
                        subprocess.run(["fusermount", "-u", mount_point], 
                                     capture_output=True)
                        
        except Exception as e:
            print(f"Warning: Could not unmount GVFS MTP: {e}")

    def linux_unmount_mtp_device(self):
        """Unmount MTP device"""
        mount_point = "/tmp/android_mtp"
        try:
            subprocess.run(["fusermount", "-u", mount_point], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to unmount: {e}")
            return False

    def linux_browse_remote_folder(self):
        """Browse remote Android folders via MTP"""
        # First try using existing GVFS mount
        gvfs_mount = self._find_gvfs_mtp_mount()
        if gvfs_mount:
            try:
                folder = filedialog.askdirectory(initialdir=gvfs_mount, 
                                            title="Select Android folder")
                if folder:
                    # Convert filesystem path back to Android path
                    relative_path = os.path.relpath(folder, gvfs_mount)
                    # Clean up the path for Android
                    if relative_path == ".":
                        android_path = "/sdcard"
                    else:
                        android_path = f"/sdcard/{relative_path}".replace("\\", "/")
                    self.remote_path_var.set(android_path)
                return
            except Exception as e:
                print(f"GVFS browse failed: {e}")
        
        # Fallback to jmtpfs
        mount_point = self.linux_mount_mtp_device()
        if mount_point:
            try:
                folder = filedialog.askdirectory(initialdir=mount_point, 
                                            title="Select Android folder")
                if folder:
                    # Convert filesystem path back to Android path
                    relative_path = os.path.relpath(folder, mount_point)
                    if relative_path == ".":
                        android_path = "/sdcard"
                    else:
                        android_path = f"/sdcard/{relative_path}".replace("\\", "/")
                    self.remote_path_var.set(android_path)
            finally:
                self.linux_unmount_mtp_device()
        else:
            messagebox.showerror("Error", "Could not mount Android device via MTP. Make sure it's connected and set to 'File Transfer' mode.")

    def _find_gvfs_mtp_mount(self):
        """Find existing GVFS MTP mount point"""
        try:
            # Check common GVFS mount locations
            import glob
            user_id = os.getuid()
            gvfs_patterns = [
                f"/run/user/{user_id}/gvfs/mtp*",
                "/media/*android*",
                "/media/*MTP*"
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

    def browse_local_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.local_path_var.set(folder)

    def disable_controls(self):
        self.remote_path_entry.config(state="disabled")
        self.local_path_entry.config(state="disabled")
        self.start_btn.config(state="disabled")

    def enable_controls(self):
        self.remote_path_entry.config(state="normal")
        self.local_path_entry.config(state="normal")
        self.start_btn.config(state="normal")

    def show_enable_debugging_instructions(self):
        msg = (
            "To enable USB debugging:\n"
            "1. Open Settings → About phone.\n"
            "2. Tap 'Build number' seven times to unlock Developer Options.\n"
            "3. Go back to Settings → Developer Options.\n"
            "4. Enable 'USB debugging'.\n"
            "5. Connect your phone via USB and accept the prompt to allow debugging.\n\n"
            "After enabling, restart this app."
        )
        messagebox.showinfo("Enable USB Debugging", msg)

    def show_disable_debugging_reminder(self):
        msg = (
            "Transfer completed.\n\n"
            "For security, disable USB debugging when done:\n"
            "Settings → Developer Options → disable 'USB debugging'."
        )
        messagebox.showinfo("Disable USB Debugging", msg)

    def start_transfer(self):
        remote_path = self.remote_path_var.get().strip()
        local_path = self.local_path_var.get().strip()
        direction = self.direction_var.get()

        if not remote_path:
            messagebox.showerror("Input Error", "Remote folder path cannot be empty.")
            return
        if not local_path or not os.path.isdir(local_path):
            messagebox.showerror("Input Error", "Please select a valid local destination folder.")
            return

        self.disable_controls()
        self.progress["value"] = 0
        
        if direction == "pull":
            self.status_label.config(text="Starting pull transfer...")
            threading.Thread(target=self.pull_folder, args=(remote_path, local_path), daemon=True).start()
        elif direction == "push":
            self.status_label.config(text="Starting push transfer...")
            threading.Thread(target=self.push_folder, args=(local_path, remote_path), daemon=True).start()
        else:
            self.report_error("Invalid transfer direction selected.")
            self.enable_controls()

    def pull_folder(self, remote_path, local_path):
        cmd = [ADB_BINARY_PATH, "pull", remote_path, local_path]
        
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                text=True, bufsize=1)
            
            for line in proc.stdout:
                pct = self.parse_progress(line)
                if pct is not None:
                    self.update_progress(pct)
                self.set_status(line.strip())
            
            proc.wait()
            if proc.returncode == 0:
                self.update_progress(100)
                self.set_status("Transfer completed successfully.")
                self.show_disable_debugging_reminder()
            else:
                self.report_error(f"Transfer failed with code {proc.returncode}")
                
        except Exception as e:
            self.report_error(f"Transfer error: {e}")
        finally:
            self.enable_controls()

    def push_folder(self, local_path,remote_path):
        # Run adb push command with progress parsing
        cmd = [ADB_BINARY_PATH, "push", f"{local_path}", f"{remote_path}" ]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except Exception as e:
            self.report_error(f"Failed to start adb: {e}")
            return

        self.set_status("Transferring files...")

        for line in proc.stdout:
            # adb progress lines look like:
            #   12345 KB/s (100%)
            # or partial output, parse percentage from line
            pct = self.parse_progress(line)
            if pct is not None:
                self.update_progress(pct)
            self.set_status(line.strip())

        proc.wait()
        if proc.returncode == 0:
            self.update_progress(100)
            self.set_status("Transfer completed successfully.")
            self.enable_controls()
            self.show_disable_debugging_reminder()
        else:
            self.report_error(f"adb pull failed with return code {proc.returncode}")

    def parse_progress(self, text_line):
        import re
        m = re.search(r"\((\d{1,3})%\)", text_line)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct
        return None

    def update_progress(self, pct):
        self.progress["value"] = pct
        self.update_idletasks()

    def set_status(self, msg):
        self.status_label.config(text="Status: " + msg)
        self.update_idletasks()

    def report_error(self, message):
        self.status_label.config(text="Error: " + message)
        messagebox.showerror("Error", message)
        self.enable_controls()

    def on_close(self):
        self.destroy()

if __name__ == "__main__":
    if sys.platform not in ["win32", "linux"]:
        tk.Tk().withdraw()
        messagebox.showerror("Unsupported OS", "This application only supports Windows or Linux.")
        sys.exit(1)

    app = App()
    app.mainloop()
