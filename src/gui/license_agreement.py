"""
License Agreement Module
Handles MIT license agreement functionality.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext


def get_license_file_path():
    """Get the path to the license agreement file."""
    # Get the directory where the application is running from
    if getattr(sys, 'frozen', False):
        # Running as executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script - use directory containing the main script
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(app_dir, "license_agreed.ini")


def check_license_agreement():
    """Check if user has already agreed to the license."""
    license_file = get_license_file_path()
    try:
        if os.path.exists(license_file):
            with open(license_file, 'r') as f:
                content = f.read().strip()
                return content == "1"
        return False
    except Exception:
        return False


def save_license_agreement():
    """Save that the user has agreed to the license."""
    license_file = get_license_file_path()
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(license_file), exist_ok=True)
        with open(license_file, 'w') as f:
            f.write("1")
        return True
    except Exception:
        return False


def get_mit_license_text():
    """Get the MIT license text."""
    return """MIT License

Copyright (c) 2025 Jason Ross

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


class LicenseAgreementFrame(tk.Frame):
    """License agreement UI frame that can be embedded in the main window."""
    
    def __init__(self, parent, on_agree_callback):
        """Initialize the license agreement frame.
        
        Args:
            parent: Parent widget
            on_agree_callback: Function to call when user agrees to license
        """
        super().__init__(parent)
        self.on_agree_callback = on_agree_callback
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the license agreement UI."""
        # Configure the frame to fill the window
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = tk.Label(
            self, 
            text="License Agreement", 
            font=("Arial", 16, "bold")
        )
        header_label.pack(pady=(0, 10))
        
        # Instruction
        instruction_label = tk.Label(
            self, 
            text="Please read and accept the license agreement to continue using Android File Handler:",
            font=("Arial", 10),
            wraplength=500
        )
        instruction_label.pack(pady=(0, 15))
        
        # License text area
        text_frame = tk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.license_text = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=20,
            font=("Courier", 9),
            state=tk.DISABLED,
            bg="#f8f8f8",
            relief=tk.SUNKEN,
            bd=2
        )
        self.license_text.pack(fill=tk.BOTH, expand=True)
        
        # Insert license text
        self.license_text.config(state=tk.NORMAL)
        self.license_text.insert(tk.END, get_mit_license_text())
        self.license_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        self.agree_btn = tk.Button(
            button_frame, 
            text="I Agree", 
            command=self.on_agree,
            bg="#4CAF50",
            fg="white", 
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        )
        self.agree_btn.pack(side=tk.LEFT)
        
        self.disagree_btn = tk.Button(
            button_frame, 
            text="Disagree & Exit", 
            command=self.on_disagree,
            bg="#ff6b6b",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        )
        self.disagree_btn.pack(side=tk.RIGHT)
        
        # Center text
        center_label = tk.Label(
            button_frame,
            text="You must agree to the license terms to use this software",
            font=("Arial", 9),
            fg="#666666"
        )
        center_label.pack(expand=True)
    
    def on_agree(self):
        """Handle user clicking Agree."""
        if save_license_agreement():
            self.on_agree_callback()
        else:
            messagebox.showerror(
                "Error", 
                "Could not save license agreement. Please check file permissions and try again."
            )
    
    def on_disagree(self):
        """Handle user clicking Disagree."""
        # Ask for confirmation
        result = messagebox.askyesno(
            "Exit Application",
            "Are you sure you want to exit? You must agree to the license terms to use this software.",
            icon="warning"
        )
        if result:
            sys.exit(0)
