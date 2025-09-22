"""Tests for progress tracking module."""

import pytest
import unittest.mock as mock
import time
from unittest.mock import patch, MagicMock

from src.core.progress_tracker import ProgressTracker


class TestProgressTracker:
    """Test progress tracking functionality."""
    
    def test_init(self):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker()
        assert tracker.start_time is None
        assert tracker.total_bytes == 0
        assert tracker.transferred_bytes == 0
        assert tracker.current_speed == 0.0
        assert tracker.estimated_time_remaining == 0
    
    def test_start_tracking(self):
        """Test starting progress tracking."""
        tracker = ProgressTracker()
        with patch('time.time', return_value=1000.0):
            tracker.start_tracking(1024)
            
            assert tracker.start_time == 1000.0
            assert tracker.total_bytes == 1024
            assert tracker.transferred_bytes == 0
    
    def test_update_progress_first_update(self):
        """Test first progress update."""
        tracker = ProgressTracker()
        with patch('time.time', return_value=1000.0):
            tracker.start_tracking(1024)
            
        with patch('time.time', return_value=1001.0):
            tracker.update_progress(512)
            
            assert tracker.transferred_bytes == 512
            assert tracker.current_speed == 512.0  # 512 bytes in 1 second
    
    def test_update_progress_multiple_updates(self):
        """Test multiple progress updates."""
        tracker = ProgressTracker()
        with patch('time.time', return_value=1000.0):
            tracker.start_tracking(1024)
            
        with patch('time.time', return_value=1001.0):
            tracker.update_progress(256)
            
        with patch('time.time', return_value=1002.0):
            tracker.update_progress(512)
            
            assert tracker.transferred_bytes == 512
            assert tracker.current_speed == 256.0  # Average speed
    
    def test_update_progress_zero_time_elapsed(self):
        """Test progress update with zero time elapsed."""
        tracker = ProgressTracker()
        with patch('time.time', return_value=1000.0):
            tracker.start_tracking(1024)
            tracker.update_progress(512)
            
            assert tracker.transferred_bytes == 512
            assert tracker.current_speed == 0.0  # No time elapsed
    
    def test_get_progress_percentage_no_total(self):
        """Test getting progress percentage with no total bytes."""
        tracker = ProgressTracker()
        assert tracker.get_progress_percentage() == 0.0
    
    def test_get_progress_percentage_with_progress(self):
        """Test getting progress percentage with progress."""
        tracker = ProgressTracker()
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 250
        
        assert tracker.get_progress_percentage() == 25.0
    
    def test_get_progress_percentage_complete(self):
        """Test getting progress percentage when complete."""
        tracker = ProgressTracker()
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 1000
        
        assert tracker.get_progress_percentage() == 100.0
    
    def test_get_progress_percentage_over_100(self):
        """Test getting progress percentage over 100%."""
        tracker = ProgressTracker()
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 1200
        
        assert tracker.get_progress_percentage() == 100.0  # Capped at 100%
    
    def test_estimate_time_remaining_no_speed(self):
        """Test time estimation with no speed."""
        tracker = ProgressTracker()
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 250
        tracker.current_speed = 0.0
        
        assert tracker.estimate_time_remaining() == 0
    
    def test_estimate_time_remaining_with_speed(self):
        """Test time estimation with speed."""
        tracker = ProgressTracker()
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 250
        tracker.current_speed = 125.0  # 125 bytes/second
        
        remaining_time = tracker.estimate_time_remaining()
        assert remaining_time == 6  # (1000-250)/125 = 6 seconds
    
    def test_estimate_time_remaining_complete(self):
        """Test time estimation when transfer is complete."""
        tracker = ProgressTracker()
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 1000
        tracker.current_speed = 100.0
        
        assert tracker.estimate_time_remaining() == 0
    
    def test_reset_tracking(self):
        """Test resetting progress tracking."""
        tracker = ProgressTracker()
        tracker.start_time = 1000.0
        tracker.total_bytes = 1000
        tracker.transferred_bytes = 500
        tracker.current_speed = 100.0
        
        tracker.reset()
        
        assert tracker.start_time is None
        assert tracker.total_bytes == 0
        assert tracker.transferred_bytes == 0
        assert tracker.current_speed == 0.0
        assert tracker.estimated_time_remaining == 0
    
    def test_format_speed_bytes(self):
        """Test formatting speed in bytes per second."""
        tracker = ProgressTracker()
        tracker.current_speed = 512.0
        
        formatted = tracker.format_speed()
        assert formatted == "512.0 B/s"
    
    def test_format_speed_kilobytes(self):
        """Test formatting speed in kilobytes per second."""
        tracker = ProgressTracker()
        tracker.current_speed = 1536.0  # 1.5 KB/s
        
        formatted = tracker.format_speed()
        assert formatted == "1.5 KB/s"
    
    def test_format_speed_megabytes(self):
        """Test formatting speed in megabytes per second."""
        tracker = ProgressTracker()
        tracker.current_speed = 2097152.0  # 2 MB/s
        
        formatted = tracker.format_speed()
        assert formatted == "2.0 MB/s"
    
    def test_format_time_seconds(self):
        """Test formatting time in seconds."""
        tracker = ProgressTracker()
        formatted = tracker.format_time(30)
        assert formatted == "00:30"
    
    def test_format_time_minutes(self):
        """Test formatting time in minutes and seconds."""
        tracker = ProgressTracker()
        formatted = tracker.format_time(150)  # 2:30
        assert formatted == "02:30"
    
    def test_format_time_hours(self):
        """Test formatting time in hours, minutes and seconds."""
        tracker = ProgressTracker()
        formatted = tracker.format_time(3661)  # 1:01:01
        assert formatted == "01:01:01"