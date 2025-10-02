"""
ADB command execution and communication.
Handles low-level ADB command execution and device detection.
"""

import os
import subprocess
import re
from typing import Optional, Tuple, Union

from .platform_tools import get_adb_binary_path

try:
    from ..utils.security_utils import validate_device_id, sanitize_android_path
except ImportError:
    from utils.security_utils import validate_device_id, sanitize_android_path


class ADBCommandRunner:
    """Handles ADB command execution and device communication."""
    
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
    
    def run_adb_command(self, args: list, capture_output: bool = True) -> Union[Tuple[str, str, int], subprocess.Popen, Tuple[None, str, int]]:
        """Run an ADB command and return output."""
        cmd = [get_adb_binary_path()] + args
        try:
            if capture_output:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return p.stdout.strip(), p.stderr.strip(), p.returncode
            else:
                p = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                return p
        except Exception as e:
            if capture_output:
                return None, str(e), -1
            else:
                return None
    
    def check_device(self) -> Optional[str]:
        """Check if an Android device is connected."""
        result = self.run_adb_command(["devices"], capture_output=True)
        if isinstance(result, tuple) and len(result) == 3:
            out, err, rc = result
            if rc != 0 or not out:
                return None
            for line in out.splitlines():
                if line.endswith("\tdevice"):
                    return line.split()[0]
        return None
    
    def parse_progress(self, text_line: str) -> Optional[int]:
        """Parse progress percentage from ADB output.

        Supports multiple formats commonly seen in adb output:
        - "(XX%)"
        - "XX% complete"
        - "transferred XX%"
        - "N files pulled/pushed (XX%)"
        - "A/B ..." style fractions (e.g., "1024/2048 KB transferred")
        - Lines containing "(NNN bytes in ...)": treated as complete and returns 100
        """
        # Original pattern: (XX%)
        m = re.search(r"\((\d{1,3})%\)", text_line)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Additional patterns for large transfers
        # Pattern: XX% complete
        m = re.search(r"(\d{1,3})%\s+complete", text_line, re.IGNORECASE)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Pattern: transferred XX%
        m = re.search(r"transferred\s+(\d{1,3})%", text_line, re.IGNORECASE)
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Pattern: XX files pulled/pushed (XX%)
        m = re.search(
            r"\d+\s+files?\s+(?:pulled|pushed).*?\((\d{1,3})%\)",
            text_line,
            re.IGNORECASE,
        )
        if m:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return pct

        # Pattern: fraction A/B possibly with units (e.g., "1024/2048 KB transferred")
        m = re.search(r"(\d+)\s*/\s*(\d+)", text_line)
        if m:
            try:
                a = int(m.group(1))
                b = int(m.group(2))
                if b > 0:
                    pct = int((a / b) * 100)
                    # clamp
                    if pct < 0:
                        pct = 0
                    if pct > 100:
                        pct = 100
                    return pct
            except Exception:
                pass

        # Pattern: generic percentage after a transferring label e.g., "Transferring: 45%"
        if re.search(r"transferr?ing", text_line, re.IGNORECASE):
            m = re.search(r"(\d{1,3})%", text_line)
            if m:
                pct = int(m.group(1))
                if 0 <= pct <= 100:
                    return pct

        # Pattern: contains bytes info like "(1048576 bytes in 2.5s)"; treat as finished (100%)
        if re.search(r"\(\s*\d+\s+bytes\b", text_line):
            return 100

        return None
    
    def cancel_current_operation(self) -> bool:
        """Cancel the current ADB operation.

        Returns True if a running process was terminated, False if no process
        was running or it had already finished.
        """
        if self.current_process is not None:
            try:
                # If already finished, don't terminate
                try:
                    if self.current_process.poll() is not None:
                        # process finished
                        self.current_process = None
                        return False
                except Exception:
                    # If poll not available or errors, continue best-effort terminate
                    pass

                # Terminate the process
                self.current_process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.current_process.kill()
                    self.current_process.wait()
                
                self.current_process = None
                return True
            except Exception:
                return False
        return False