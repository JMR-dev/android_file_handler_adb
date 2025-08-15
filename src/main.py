#!/usr/bin/env python3
"""
Android File Handler - Main Entry Point
Simple entry point to launch the Android file transfer application.
"""

try:
    # Try relative import first (when used as module)
    from .gui.main_window import main
except ImportError:
    # Fall back to direct import (when run directly)
    try:
        from gui.main_window import main
    except ImportError:
        from gui import AndroidFileHandlerGUI
        import sys

        def main():
            """Main function to run the application."""
            if sys.platform not in ["win32", "linux"]:
                import tkinter as tk
                from tkinter import messagebox

                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "Unsupported OS", "This application only supports Windows or Linux."
                )
                sys.exit(1)

            app = AndroidFileHandlerGUI()
            app.mainloop()


if __name__ == "__main__":
    main()
