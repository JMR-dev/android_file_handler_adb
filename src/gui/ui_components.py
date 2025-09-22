"""
UI Components Module
Contains reusable UI components for the Android file transfer application.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

try:
    from .license_agreement import LicenseAgreementFrame, check_license_agreement
except ImportError:
    from license_agreement import LicenseAgreementFrame, check_license_agreement


class PathSelectorFrame:
    """Frame component for path selection with browse button."""
    
    def __init__(self, parent: tk.Widget, label_text: str, browse_command: Callable):
        """Initialize the path selector frame.
        
        Args:
            parent: Parent widget
            label_text: Text for the label
            browse_command: Command to execute when browse button is clicked
        """
        self.frame = tk.Frame(parent)
        self.label = tk.Label(self.frame, text=label_text)
        self.label.pack(anchor="w")
        
        # Path frame with label and button
        path_frame = tk.Frame(self.frame)
        path_frame.pack(fill="x", pady=(0, 10))
        
        self.path_var = tk.StringVar(value="Please select file or folder ->")
        self.path_display = tk.Label(
            path_frame, 
            textvariable=self.path_var, 
            anchor="w"
        )
        self.path_display.pack(side="left", fill="x", expand=True)
        
        self.browse_btn = tk.Button(
            path_frame, 
            text="Browse...", 
            command=browse_command
        )
        self.browse_btn.pack(side="right", padx=(5, 0))
    
    def pack(self, **kwargs):
        """Pack the frame."""
        self.frame.pack(**kwargs)
    
    def pack_forget(self):
        """Remove the frame from packing."""
        self.frame.pack_forget()
    
    def set_path(self, path: str) -> None:
        """Set the displayed path.
        
        Args:
            path: Path to display
        """
        self.path_var.set(path)
    
    def get_path(self) -> str:
        """Get the current path.
        
        Returns:
            Current path string
        """
        return self.path_var.get().strip()
    
    def is_path_selected(self) -> bool:
        """Check if a valid path is selected.
        
        Returns:
            True if path is selected and not the default placeholder
        """
        path = self.get_path()
        return path and path != "Please select file or folder ->"
    
    def clear_path(self) -> None:
        """Clear the path selection."""
        self.path_var.set("Please select file or folder ->")
    
    def enable_browse(self) -> None:
        """Enable the browse button."""
        self.browse_btn.config(state="normal")
    
    def disable_browse(self) -> None:
        """Disable the browse button."""
        self.browse_btn.config(state="disabled")


class DirectionSelector:
    """Component for selecting transfer direction (pull/push)."""
    
    def __init__(self, parent: tk.Widget, on_change_command: Optional[Callable] = None):
        """Initialize the direction selector.
        
        Args:
            parent: Parent widget
            on_change_command: Command to execute when direction changes
        """
        self.direction_var = tk.StringVar(value="pull")
        
        self.frame = tk.Frame(parent)
        self.frame.pack(anchor="w", padx=10, pady=(10, 0))
        
        tk.Radiobutton(
            self.frame,
            text="Pull (Android → Computer)",
            variable=self.direction_var,
            value="pull",
            command=on_change_command,
        ).pack(side="left")
        
        tk.Radiobutton(
            self.frame,
            text="Push (Computer → Android)",
            variable=self.direction_var,
            value="push",
            command=on_change_command,
        ).pack(side="left", padx=(20, 0))
    
    def get_direction(self) -> str:
        """Get the current direction.
        
        Returns:
            Current direction ('pull' or 'push')
        """
        return self.direction_var.get()


class StatusLabel:
    """Responsive status label with word wrapping."""
    
    def __init__(self, parent: tk.Widget, initial_text: str = "Status: Idle"):
        """Initialize the status label.
        
        Args:
            parent: Parent widget
            initial_text: Initial status text
        """
        self.label = tk.Label(
            parent,
            text=initial_text,
            wraplength=0,  # Will be set dynamically
            justify="center",
            anchor="center"
        )
        self.label.pack(padx=10, fill="x", pady=(20, 5))
        
        # Bind parent window resize to update wrapping
        parent.bind("<Configure>", self._on_window_configure)
    
    def set_text(self, text: str) -> None:
        """Set the status text.
        
        Args:
            text: Text to display
        """
        self.label.config(text=text)
    
    def get_text(self) -> str:
        """Get the current status text.
        
        Returns:
            Current status text
        """
        return self.label.cget("text")
    
    def _on_window_configure(self, event) -> None:
        """Handle window resize events to update label wrapping.
        
        Args:
            event: Configure event
        """
        # Only handle configure events for the main window, not child widgets
        if hasattr(event.widget, 'winfo_toplevel') and event.widget == event.widget.winfo_toplevel():
            # Calculate available width for the status label
            # Account for padding (10px on each side) and some margin
            available_width = event.widget.winfo_width() - 40
            if available_width > 100:  # Minimum reasonable width
                self.label.config(wraplength=available_width)


class TransferButton:
    """Multi-mode transfer button that changes text and behavior based on state."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize the transfer button.
        
        Args:
            parent: Parent widget
        """
        self.button = tk.Button(
            parent,
            text="Start Transfer",
            state="disabled"
        )
        self.button.pack(pady=10)
        
        self.current_mode = "transfer"  # transfer, recheck, cancel
    
    def set_transfer_mode(self, command: Callable, enabled: bool = True) -> None:
        """Set button to transfer mode.
        
        Args:
            command: Command to execute on button click
            enabled: Whether button should be enabled
        """
        self.current_mode = "transfer"
        self.button.config(
            text="Start Transfer",
            command=command,
            state="normal" if enabled else "disabled"
        )
    
    def set_recheck_mode(self, command: Callable) -> None:
        """Set button to recheck device mode.
        
        Args:
            command: Command to execute on button click
        """
        self.current_mode = "recheck"
        self.button.config(
            text="Recheck for connected Android device",
            command=command,
            state="normal"
        )
    
    def set_cancel_mode(self, command: Callable) -> None:
        """Set button to cancel transfer mode.
        
        Args:
            command: Command to execute on button click
        """
        self.current_mode = "cancel"
        self.button.config(
            text="Cancel Transfer",
            command=command,
            state="normal"
        )
    
    def set_checking_mode(self) -> None:
        """Set button to temporary checking state."""
        self.button.config(
            text="Checking...",
            state="disabled"
        )
    
    def enable(self) -> None:
        """Enable the button."""
        self.button.config(state="normal")
    
    def disable(self) -> None:
        """Disable the button."""
        self.button.config(state="disabled")
    
    def get_mode(self) -> str:
        """Get the current button mode.
        
        Returns:
            Current mode string ('transfer', 'recheck', 'cancel')
        """
        return self.current_mode


class LicenseManager:
    """Manages license agreement display and main interface switching."""
    
    def __init__(self, parent_window: tk.Tk):
        """Initialize the license manager.
        
        Args:
            parent_window: The main window instance
        """
        self.parent = parent_window
        self.license_agreed = check_license_agreement()
        self.license_frame = None
        self.on_agreed_callback: Optional[Callable] = None
    
    def needs_license_agreement(self) -> bool:
        """Check if license agreement is needed.
        
        Returns:
            True if license agreement needs to be shown, False otherwise
        """
        return not self.license_agreed
    
    def show_license_agreement(self, on_agreed_callback: Callable) -> None:
        """Show the license agreement interface.
        
        Args:
            on_agreed_callback: Callback to execute when license is agreed
        """
        self.on_agreed_callback = on_agreed_callback
        
        # Adjust window size for license agreement
        self.parent.geometry("700x600")
        self.parent.minsize(700, 600)
        
        # Create license agreement frame
        self.license_frame = LicenseAgreementFrame(self.parent, self._on_license_agreed)
    
    def _on_license_agreed(self) -> None:
        """Handle when user agrees to license."""
        self.license_agreed = True
        
        # Remove license frame
        if self.license_frame:
            self.license_frame.destroy()
            self.license_frame = None
        
        # Execute callback
        if self.on_agreed_callback:
            self.on_agreed_callback()