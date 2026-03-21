#!/usr/bin/env python3
"""
Android File Handler - Main Entry Point
Simple entry point to launch the Android file transfer application.
"""

try:
    from gui.main_window import main
except ImportError:
    from .gui.main_window import main


if __name__ == "__main__":
    main()
