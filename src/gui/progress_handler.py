"""
Progress Handler Module
Handles progress bar updates and status messages in a thread-safe manner.
"""

import tkinter as tk
from tkinter import ttk


class ProgressHandler:
    """Handles progress bar updates and status messages."""

    def __init__(
        self, parent_widget, progress_bar: ttk.Progressbar, status_label: tk.Label
    ):
        self.parent = parent_widget
        self.progress_bar = progress_bar
        self.status_label = status_label

    def update_progress(self, percentage: int):
        """Update the progress bar (thread-safe)."""
        # Debug output for large transfer troubleshooting
        print(f"[DEBUG] Progress update called: {percentage}%")

        # Schedule UI update on main thread using a proper closure
        def update_ui():
            self._update_progress_ui(percentage)

        self.parent.after(0, update_ui)

    def _update_progress_ui(self, percentage: int):
        """Internal method to update progress bar on main thread."""
        # Ensure percentage is within valid range
        percentage = max(0, min(100, percentage))

        # Debug output for large transfer troubleshooting
        current_value = self.progress_bar["value"]
        print(f"[DEBUG] UI Progress update: {current_value} -> {percentage}%")

        if (
            hasattr(self, "_last_percentage")
            and abs(percentage - self._last_percentage) >= 10
        ):
            print(
                f"[DEBUG] Major progress jump: {self._last_percentage}% -> {percentage}%"
            )
        self._last_percentage = percentage

        try:
            self.progress_bar["value"] = percentage
            self.progress_bar.update()  # Force immediate update
            self.parent.update_idletasks()
            print(f"[DEBUG] Progress bar updated successfully to {percentage}%")
        except Exception as e:
            print(f"[DEBUG] Error updating progress bar: {e}")

    def set_status(self, message: str):
        """Update the status label (thread-safe)."""

        # Schedule UI update on main thread using a proper closure
        def update_ui():
            self._set_status_ui(message)

        self.parent.after(0, update_ui)

    def _set_status_ui(self, message: str):
        """Internal method to update status on main thread."""
        self.status_label.config(text=f"Status: {message}")
        self.parent.update_idletasks()

    def reset_progress(self):
        """Reset progress bar to 0 (thread-safe)."""

        # Schedule UI update on main thread using a proper closure
        def update_ui():
            self._update_progress_ui(0)

        self.parent.after(0, update_ui)
