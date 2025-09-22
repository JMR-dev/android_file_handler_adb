"""
Progress tracking utilities for file transfers.
Handles progress callbacks and transfer statistics.
"""

import time
from typing import Optional, Callable, Dict, Any


class ProgressTracker:
    """Tracks progress for file transfer operations."""
    
    def __init__(self):
        self.progress_callback: Optional[Callable[[int], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None

        # Byte-based tracking state expected by tests
        self.start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None
        self.total_bytes: int = 0
        self.transferred_bytes: int = 0
        self.current_speed: float = 0.0
        self.estimated_time_remaining: int = 0
        self.transfer_progress: Dict[str, int] = {
            'current_file': 0,
            'total_files': 0,
            'files_to_transfer': 0
        }
    
    def set_progress_callback(self, callback: Callable[[int], None]):
        """Set callback function for progress updates."""
        self.progress_callback = callback

    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback function for status updates."""
        self.status_callback = callback

    def start_tracking(self, total_bytes: int) -> None:
        """Start byte-based progress tracking."""
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.total_bytes = max(0, int(total_bytes))
        self.transferred_bytes = 0
        self.current_speed = 0.0
        self.estimated_time_remaining = 0

    def update_progress(self, value: int) -> None:
        """Update progress.

        If total_bytes > 0, treat value as bytes transferred so far and update
        speed and remaining time. Otherwise treat value as percentage and
        forward to the callback for UI updates.
        """
        if self.total_bytes > 0:
            new_transferred = max(0, min(int(value), self.total_bytes))
            now = time.time()
            elapsed = 0.0
            if self.last_update_time is not None:
                elapsed = max(0.0, now - self.last_update_time)

            delta = new_transferred - self.transferred_bytes
            if elapsed > 0 and delta >= 0:
                self.current_speed = float(delta) / elapsed

            self.transferred_bytes = new_transferred
            self.last_update_time = now

            if self.current_speed > 0 and self.transferred_bytes < self.total_bytes:
                remaining = self.total_bytes - self.transferred_bytes
                self.estimated_time_remaining = int(remaining / self.current_speed)
            else:
                self.estimated_time_remaining = 0

            if self.progress_callback:
                self.progress_callback(int(self.get_progress_percentage()))
        else:
            if self.progress_callback:
                self.progress_callback(int(value))

    def update_status(self, message: str):
        """Update status message."""
        if self.status_callback:
            self.status_callback(message)

    def update_transfer_progress(self, current_file: int, total_files: int):
        """Update transfer progress for file counting."""
        self.transfer_progress['current_file'] = current_file
        self.transfer_progress['total_files'] = total_files
        # Send progress update through status callback with special format
        progress_message = f"TRANSFER_PROGRESS:{current_file}:{total_files}"
        if self.status_callback:
            self.status_callback(progress_message)

    def reset_transfer_progress(self):
        """Reset transfer progress counters."""
        self.transfer_progress = {
            'current_file': 0,
            'total_files': 0,
            'files_to_transfer': 0
        }
    
    def set_files_to_transfer(self, count: int):
        """Set the total number of files to transfer."""
        self.transfer_progress['files_to_transfer'] = count

    # Utilities expected by tests/UI
    def get_progress_percentage(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        pct = (self.transferred_bytes / max(1, self.total_bytes)) * 100.0
        if pct < 0.0:
            return 0.0
        if pct > 100.0:
            return 100.0
        return float(pct)

    def estimate_time_remaining(self) -> int:
        if self.total_bytes <= 0 or self.transferred_bytes >= self.total_bytes:
            return 0
        if self.current_speed <= 0:
            return 0
        remaining = self.total_bytes - self.transferred_bytes
        return int(remaining / self.current_speed)

    def reset(self) -> None:
        self.start_time = None
        self.last_update_time = None
        self.total_bytes = 0
        self.transferred_bytes = 0
        self.current_speed = 0.0
        self.estimated_time_remaining = 0

    def format_speed(self) -> str:
        bps = float(self.current_speed)
        if bps < 1024:
            return f"{bps:.1f} B/s"
        kbps = bps / 1024.0
        if kbps < 1024:
            return f"{kbps:.1f} KB/s"
        mbps = kbps / 1024.0
        return f"{mbps:.1f} MB/s"

    def format_time(self, seconds: int) -> str:
        if seconds < 0:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"


class TransferProgressEstimator:
    """Estimates transfer progress based on various factors."""
    
    @staticmethod
    def estimate_progress_from_time(start_time: float, last_progress: int, 
                                  elapsed_threshold: float = 1.0, 
                                  max_increment: int = 20,
                                  max_progress: int = 90) -> Optional[int]:
        """Estimate progress based on elapsed time."""
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        if elapsed_time >= elapsed_threshold and last_progress < max_progress:
            new_progress = min(last_progress + max_increment, max_progress)
            return int(new_progress)
        
        return None
    
    @staticmethod
    def estimate_progress_from_activity(line_count: int, last_progress: int,
                                      activity_threshold: int = 50,
                                      increment: int = 5,
                                      max_progress: int = 90) -> Optional[int]:
        """Estimate progress based on output line activity."""
        if line_count % activity_threshold == 0 and last_progress < max_progress:
            calculated_increment = max(1, min(increment, max_progress // (line_count // activity_threshold + 1)))
            new_progress = min(last_progress + calculated_increment, max_progress)
            return int(new_progress)
        
        return None
    
    @staticmethod
    def estimate_complex_progress(line_count: int, elapsed_time: float, 
                                last_progress: int) -> Optional[int]:
        """Estimate progress using complex algorithm for large transfers."""
        if elapsed_time >= 2.0 and last_progress < 95:
            if line_count > 100:
                activity_factor = min(line_count / 1000, 50)
                time_factor = min(elapsed_time / 60, 40)
                new_progress = min(activity_factor + time_factor, 95)
            else:
                new_progress = min(last_progress + 10, 95)
            
            return int(new_progress)
        
        return None