"""
Animation Handler Module
Manages all GUI animations for the Android file transfer application.
"""

import tkinter as tk
from typing import Optional, Dict, Any


class AnimationHandler:
    """Handles all GUI animations including transfer and scanning animations."""
    
    def __init__(self, parent_window: tk.Tk):
        """Initialize the animation handler.
        
        Args:
            parent_window: The main window instance
        """
        self.parent = parent_window
        self.animation_job: Optional[str] = None
        self.animation_dots = 0
        self.scanning_active = False
        
        # File transfer progress tracking
        self.transfer_file_progress = {
            'current': 0,
            'total': 0,
            'active': False
        }
    
    def start_scanning_animation(self) -> None:
        """Start the 'Scanning for duplicates...' animation."""
        self.animation_dots = 0
        self.scanning_active = True
        self.animation_job = self.parent.after(0, self._animate_scanning_text)
    
    def start_transfer_animation(self) -> None:
        """Start the 'Transferring...' animation."""
        self.animation_dots = 0
        self.scanning_active = False
        self.animation_job = self.parent.after(0, self._animate_transfer_text)
    
    def stop_animation(self) -> None:
        """Stop any running animation."""
        if self.animation_job is not None:
            self.parent.after_cancel(self.animation_job)
            self.animation_job = None
        
        self.scanning_active = False
        self._reset_file_progress()
    
    def update_transfer_progress(self, current: int, total: int) -> None:
        """Update the file transfer progress.
        
        Args:
            current: Current number of files transferred
            total: Total number of files to transfer
        """
        self.transfer_file_progress['current'] = current
        self.transfer_file_progress['total'] = total
        self.transfer_file_progress['active'] = True
    
    def _animate_scanning_text(self) -> None:
        """Animate the scanning text with dots."""
        if self.animation_job is not None and self.scanning_active:
            dots = "." * (self.animation_dots + 1)
            status_text = f"Scanning for duplicates{dots}"
            self._update_status_label(status_text)
            self.animation_dots = (self.animation_dots + 1) % 5  # Cycle 0-4 dots
            # Schedule next update in 500ms
            self.animation_job = self.parent.after(500, self._animate_scanning_text)
    
    def _animate_transfer_text(self) -> None:
        """Animate the transfer text with dots."""
        if self.animation_job is not None and not self.scanning_active:
            dots = "." * (self.animation_dots + 1)
            
            # Show file progress if available
            if (self.transfer_file_progress['active'] and 
                self.transfer_file_progress['total'] > 0):
                current = self.transfer_file_progress['current']
                total = self.transfer_file_progress['total']
                status_text = f"Transferring {current} of {total} files{dots}"
            else:
                status_text = f"Transferring{dots}"
                
            self._update_status_label(status_text)
            self.animation_dots = (self.animation_dots + 1) % 5  # Cycle 0-4 dots
            # Schedule next update in 500ms
            self.animation_job = self.parent.after(500, self._animate_transfer_text)
    
    def _update_status_label(self, text: str) -> None:
        """Update the status label with the given text.
        
        Args:
            text: Text to display in the status label
        """
        if hasattr(self.parent, 'status_label'):
            self.parent.status_label.config(text=text)
            self.parent.update_idletasks()
    
    def _reset_file_progress(self) -> None:
        """Reset file progress tracking."""
        self.transfer_file_progress = {
            'current': 0,
            'total': 0,
            'active': False
        }
    
    def is_animation_running(self) -> bool:
        """Check if any animation is currently running.
        
        Returns:
            True if animation is running, False otherwise
        """
        return self.animation_job is not None
    
    def is_scanning(self) -> bool:
        """Check if scanning animation is active.
        
        Returns:
            True if scanning animation is active, False otherwise
        """
        return self.scanning_active