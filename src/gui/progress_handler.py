"""
Progress Handler Module
Handles progress bar updates and status messages in a thread-safe manner.
"""

import tkinter as tk
from tkinter import ttk


class ProgressHandler:
    """Handles progress bar updates and status messages."""

    def __init__(
        self, parent_widget: tk.Widget, progress_bar: ttk.Progressbar, status_label: tk.Label
    ) -> None:
        """Initialize the progress handler."""
        self.parent = parent_widget
        self.progress_bar = progress_bar  # Don't call as function - it's already created
        self.status_label = status_label
        self._last_percentage: float = 0.0
        self._transfer_active: bool = False  # Track if a transfer is actually active

    def update_progress(self, bytes_transferred_or_percentage, bytes_total=None) -> None:
        """Update the progress bar (thread-safe).
        
        Args:
            bytes_transferred_or_percentage: Either bytes transferred (if bytes_total provided) or percentage (0-100)
            bytes_total: Total number of bytes to transfer (optional)
        """
        if bytes_total is not None:
            # Called with bytes_transferred and bytes_total
            bytes_transferred = bytes_transferred_or_percentage
            if bytes_total > 0:
                percentage = (bytes_transferred / bytes_total) * 100.0
            else:
                percentage = 0.0
        else:
            # Called with just percentage
            percentage = float(bytes_transferred_or_percentage)
        
        # Ensure percentage is within valid range
        percentage = max(0.0, min(100.0, percentage))
        
        # Schedule UI update on main thread using a proper closure
        def update_ui() -> None:
            self._update_progress_ui(percentage)

        self.parent.after(0, update_ui)

    def _update_progress_ui(self, percentage: float) -> None:
        """Internal method to update progress bar on main thread.
        
        Args:
            percentage: Progress percentage (0.0 to 100.0) - used for logging only in indeterminate mode
        """
        
        # Only log significant progress jumps (10% or more)
        if abs(percentage - self._last_percentage) >= 10.0:
            pass  # Could add non-debug logging here if needed
        
        self._last_percentage = percentage

        try:
            # Only start animation if we're in an active transfer and progress > 0
            if self._transfer_active and percentage > 0 and percentage < 100:
                self.progress_bar.start(10)  # 10ms interval for smooth animation
            elif percentage >= 100:
                self.progress_bar.stop()  # Stop animation when complete
                self._transfer_active = False  # Transfer is done
            
            self.parent.update_idletasks()
        except Exception as exception_error:
            pass  # Silent error handling

    def reset_progress(self) -> None:
        """Reset progress bar to 0 (thread-safe)."""
        def update_ui() -> None:
            try:
                self.progress_bar.stop()  # Stop any animation
                self._last_percentage = 0.0
                self._transfer_active = False  # Not in a transfer
                self.parent.update_idletasks()
            except Exception as exception_error:
                pass  # Silent error handling for reset operation

        self.parent.after(0, update_ui)

    def start_transfer(self) -> None:
        """Mark that a transfer is starting (enables progress animation)."""
        self._transfer_active = True

    def set_status(self, message: str) -> None:
        """Set the status label text (thread-safe).
        
        Args:
            message: The status message to display
        """
        # Schedule UI update on main thread
        def update_ui() -> None:
            self._set_status_ui(message)

        self.parent.after(0, update_ui)

    def _set_status_ui(self, message: str) -> None:
        """Internal method to set status label on main thread.
        
        Args:
            message: The status message to display
        """
        try:
            self.status_label.config(text=message)
            self.parent.update_idletasks()
        except Exception as exception_error:
            pass  # Silent error handling