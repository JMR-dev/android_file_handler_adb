#!/usr/bin/env python3
"""
Android File Handler - Main Entry Point
Simple entry point to launch the Android file transfer application.
"""

try:
    from gui.main_window import main
    from gui.dialogs.license_agreement import run_windows_first_run_if_needed
except ImportError:
    from .gui.main_window import main
    from .gui.dialogs.license_agreement import run_windows_first_run_if_needed


if __name__ == "__main__":
    run_windows_first_run_if_needed()
    main()
