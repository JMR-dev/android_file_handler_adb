#!/usr/bin/env python3
"""
Android File Handler - Main Entry Point
Simple entry point to launch the Android file transfer application.
"""

try:
    # Try relative import first (when used as module)
    from .gui import main
except ImportError:
    # Fall back to direct import (when run directly)
    from gui import main

if __name__ == "__main__":
    main()
