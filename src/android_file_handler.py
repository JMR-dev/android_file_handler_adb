import os
import sys
import threading
import subprocess
import requests
import zipfile
import io
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

ADB_WIN_ZIP_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
ADB_LINUX_ZIP_URL = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
LOCAL_ADB_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools")
if sys.platform.startswith("linux"):
    ADB_BINARY_NAME = "adb"
else:
    ADB_BINARY_NAME = "adb.exe"

ADB_BINARY_PATH = os.path.join(LOCAL_ADB_FOLDER, "platform-tools", ADB_BINARY_NAME)

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
        if sys.platform.startswith("linux"):
            ADB_ZIP_URL = ADB_LINUX_ZIP_URL
        elif sys.platform.startswith("win"):
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
        self.geometry("520x220")
        self.resizable(False, False)
                # Add to __init__
        self.direction_var = tk.StringVar(value="pull")
        direction_frame = tk.Frame(self)
        direction_frame.pack(anchor="w", padx=10, pady=(10,0))
        tk.Radiobutton(direction_frame, text="Pull (Android → PC)", 
                    variable=self.direction_var, value="pull").pack(side="left")
        tk.Radiobutton(direction_frame, text="Push (PC → Android)", 
                    variable=self.direction_var, value="push").pack(side="left", padx=(20,0))

        # UI Elements
        tk.Label(self, text="Remote folder path (Android device):").pack(anchor="w", padx=10, pady=(10,0))
        self.remote_path_var = tk.StringVar(value="/sdcard")
        self.remote_path_entry = tk.Entry(self, textvariable=self.remote_path_var, width=60)
        self.remote_path_entry.pack(padx=10)

        tk.Label(self, text="Local destination folder (Windows PC):").pack(anchor="w", padx=10, pady=(10,0))
        self.local_path_var = tk.StringVar()
        local_path_frame = tk.Frame(self)
        local_path_frame.pack(fill="x", padx=10)
        self.local_path_entry = tk.Entry(local_path_frame, textvariable=self.local_path_var, width=50)
        self.local_path_entry.pack(side="left", fill="x", expand=True)
        tk.Button(local_path_frame, text="Browse...", command=self.browse_local_folder).pack(side="right", padx=(5,0))

        self.progress = ttk.Progressbar(self, orient="horizontal", length=500, mode="determinate")
        self.progress.pack(padx=10, pady=(20, 5))

        self.status_label = tk.Label(self, text="Status: Idle")
        self.status_label.pack(anchor="w", padx=10)

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

        if not remote_path:
            messagebox.showerror("Input Error", "Remote folder path cannot be empty.")
            return
        if not local_path or not os.path.isdir(local_path):
            messagebox.showerror("Input Error", "Please select a valid local destination folder.")
            return

        self.disable_controls()
        self.progress["value"] = 0
        self.status_label.config(text="Starting transfer...")
        threading.Thread(target=self.pull_folder, args=(remote_path, local_path), daemon=True).start()

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

    def push_folder_or_file(self, remote_path, local_path):
        # Run adb push command with progress parsing
        cmd = [ADB_BINARY_PATH, "push", f"{remote_path}", f"{local_path}"]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except Exception as e:
            self.report_error(f"Failed to start adb: {e}")
            return

        total_progress = 0
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
