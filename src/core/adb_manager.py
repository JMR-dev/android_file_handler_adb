"""
Android File Handler - ADB Manager Module
Main interface for ADB operations, device management, and file transfers.
"""

import os
import sys
import shutil
import subprocess
import logging
from typing import Optional, Tuple, Callable

# Import our modular components
from .platform_tools import (
    ensure_platform_tools_in_user_dir, 
    get_adb_binary_path, 
    is_adb_available,
    download_and_extract_adb
)
from .platform_utils import get_platform_tools_directory, get_platform_type
from .file_transfer import ADBFileTransfer
from .adb_command import ADBCommandRunner
from .progress_tracker import ProgressTracker

try:
    from utils.file_deduplication import FileDeduplicator
except ImportError:
    from ..utils.file_deduplication import FileDeduplicator

try:
    from ..utils.security_utils import sanitize_android_path, validate_device_id
except ImportError:
    from utils.security_utils import sanitize_android_path, validate_device_id


OS_TYPE = sys.platform

logger = logging.getLogger(__name__)


class ADBManager:
    """Main interface for ADB operations, device management, and file transfers."""
    
    def __init__(self):
        """Initialize the ADB manager."""
        self.command_runner = ADBCommandRunner()
        self.file_transfer = ADBFileTransfer()
        self.progress_tracker = ProgressTracker()
        self.selected_device = None
        self.current_process = None
        # Provide legacy deduplicator attribute expected by some tests
        try:
            self.deduplicator = FileDeduplicator()
        except Exception:
            self.deduplicator = None
        
        # Progress and status callbacks for compatibility
        self.progress_callback = None
        self.status_callback = None
        
        # Transfer progress tracking
        self.transfer_progress = {
            'current_file': 0,
            'total_files': 0,
            'transferred_bytes': 0,
            'total_bytes': 0
        }
        
        # Lazily initialize ADB binary path to reduce side effects during init
        self._adb_path: Optional[str] = None

    @property
    def adb_path(self) -> Optional[str]:
        if self._adb_path is None:
            try:
                self._adb_path = get_adb_binary_path()
            except Exception:
                self._adb_path = None
        return self._adb_path

    @adb_path.setter
    def adb_path(self, value: Optional[str]) -> None:
        self._adb_path = value
    
    def is_available(self) -> bool:
        """Check if ADB is available."""
        return is_adb_available()
    
    def ensure_adb_installed(self) -> bool:
        """Ensure ADB is installed and available."""
        try:
            if self.is_available():
                return True
            
            # Try to download and install ADB
            self.adb_path = ensure_platform_tools_in_user_dir()
            if self.adb_path and os.path.exists(self.adb_path):
                return True
                
        except Exception as e:
            print(f"Error ensuring ADB installation: {e}")
            
        return False
    
    def get_devices(self) -> list[str]:
        """Get list of connected Android devices."""
        try:
            args = ["devices"]
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            
            if returncode != 0:
                return []
            
            devices = []
            for line in stdout.split('\n')[1:]:  # Skip first line "List of devices attached"
                line = line.strip()
                if line and '\t' in line:
                    device_id = line.split('\t')[0]
                    if device_id:
                        devices.append(device_id)
            
            return devices
        except Exception:
            return []
    
    def is_device_connected(self, device_id: Optional[str] = None) -> bool:
        """Check if a specific device is connected."""
        devices = self.get_devices()
        if not devices:
            return False
            
        if device_id:
            return device_id in devices
        else:
            # Check if any device is connected
            return len(devices) > 0
    
    def select_device(self, device_id: str) -> None:
        """Select a specific device for operations."""
        self.selected_device = device_id
    
    def get_selected_device(self) -> Optional[str]:
        """Get the currently selected device."""
        return self.selected_device
    
    def list_files(self, path: str, device_id: Optional[str] = None) -> list[dict]:
        """List files in the specified path on the device."""
        # Sanitize inputs to prevent command injection
        try:
            sanitized_path = sanitize_android_path(path)
        except ValueError as e:
            # Log validation error and return empty list
            logger.warning(f"Invalid path rejected in list_files: {str(e)}")
            return []

        device_args = []
        target_device = device_id or self.selected_device
        if target_device:
            try:
                validated_device = validate_device_id(target_device)
                device_args = ["-s", validated_device]
            except ValueError as e:
                logger.warning(f"Invalid device ID rejected in list_files: {str(e)}")
                return []

        args = device_args + ["shell", "ls", "-la", sanitized_path]
        
        try:
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            if returncode != 0:
                return []
            
            files = []
            for line in stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('total '):
                    continue
                    
                # Parse ls -la output
                parts = line.split()
                if len(parts) < 9:
                    continue
                    
                permissions = parts[0]
                size_str = parts[4]
                
                # Join filename parts (handles spaces in filenames)
                name = ' '.join(parts[8:])
                
                # Skip current and parent directory entries
                if name in ['.', '..']:
                    continue
                
                file_type = 'folder' if permissions.startswith('d') else 'file'
                
                try:
                    size = int(size_str) if file_type == 'file' else 0
                except ValueError:
                    size = 0
                
                # Combine date and time parts
                modified = ' '.join(parts[5:8]) if len(parts) >= 8 else ''
                
                files.append({
                    'name': name,
                    'type': file_type,
                    'size': size,
                    'permissions': permissions,
                    'modified': modified
                })
            
            return files
        except Exception:
            return []
    
    def pull_file(self, remote_path: str, local_path: str,
                  progress_callback: Optional[Callable[[int, int], None]] = None,
                  device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Pull a file from device to local system."""
        try:
            # Create local directory if it doesn't exist
            local_dir = os.path.dirname(local_path)
            if local_dir:
                try:
                    os.makedirs(local_dir, exist_ok=True)
                except Exception:
                    # Normalize error message for tests
                    return False, "Failed to pull file"
            
            # Use our file transfer module
            success = self.file_transfer.pull_file(remote_path, local_path)
            if success:
                return True, f"File pulled successfully to {local_path}"
            else:
                return False, "Failed to pull file"
        except Exception as e:
            return False, "Failed to pull file"
    
    def pull_folder(self, remote_path: str, local_path: str,
                    progress_callback: Optional[Callable[[int, int], None]] = None,
                    device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Pull a folder from device to local system."""
        try:
            # Create local directory
            try:
                os.makedirs(local_path, exist_ok=True)
            except Exception:
                return False, "Failed to pull folder"
            
            # Use our file transfer module
            success = self.file_transfer.pull_folder(remote_path, local_path)
            if success:
                return True, f"Folder pulled successfully to {local_path}"
            else:
                return False, "Failed to pull folder"
        except Exception as e:
            return False, "Failed to pull folder"
    
    def push_file(self, local_path: str, remote_path: str,
                  progress_callback: Optional[Callable[[int, int], None]] = None,
                  device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Push a file from local system to device."""
        try:
            if not os.path.exists(local_path):
                return False, f"Local file not found: {local_path}"
            
            # Use our file transfer module
            success = self.file_transfer.push_file(local_path, remote_path)
            if success:
                return True, f"File pushed successfully to {remote_path}"
            else:
                return False, "Failed to push file"
        except Exception as e:
            return False, f"Error pushing file: {str(e)}"
    
    def push_folder(self, local_path: str, remote_path: str,
                    progress_callback: Optional[Callable[[int, int], None]] = None,
                    device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Push a folder from local system to device."""
        try:
            if not os.path.exists(local_path):
                return False, f"Local folder not found: {local_path}"
            
            # Use our file transfer module
            success = self.file_transfer.push_folder(local_path, remote_path)
            if success:
                return True, f"Folder pushed successfully to {remote_path}"
            else:
                return False, "Failed to push folder"
        except Exception as e:
            return False, f"Error pushing folder: {str(e)}"
    
    def delete_file(self, remote_path: str, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Delete a file on the device."""
        # Sanitize inputs to prevent command injection
        try:
            sanitized_path = sanitize_android_path(remote_path)
        except ValueError as e:
            return False, f"Invalid path: {str(e)}"

        device_args = []
        target_device = device_id or self.selected_device
        if target_device:
            try:
                validated_device = validate_device_id(target_device)
                device_args = ["-s", validated_device]
            except ValueError as e:
                return False, f"Invalid device ID: {str(e)}"

        args = device_args + ["shell", "rm", "-f", sanitized_path]

        try:
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            if returncode == 0:
                return True, f"File deleted: {remote_path}"
            else:
                return False, f"Failed to delete file: {stderr}"
        except Exception as e:
            return False, f"Error deleting file: {str(e)}"

    def create_folder(self, remote_path: str, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Create a folder on the device."""
        # Sanitize inputs to prevent command injection
        try:
            sanitized_path = sanitize_android_path(remote_path)
        except ValueError as e:
            return False, f"Invalid path: {str(e)}"

        device_args = []
        target_device = device_id or self.selected_device
        if target_device:
            try:
                validated_device = validate_device_id(target_device)
                device_args = ["-s", validated_device]
            except ValueError as e:
                return False, f"Invalid device ID: {str(e)}"

        args = device_args + ["shell", "mkdir", "-p", sanitized_path]

        try:
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            if returncode == 0:
                return True, f"Folder created: {remote_path}"
            else:
                return False, f"Failed to create folder: {stderr}"
        except Exception as e:
            return False, f"Error creating folder: {str(e)}"

    def delete_folder(self, remote_path: str, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Delete a folder on the device."""
        # Sanitize inputs to prevent command injection
        try:
            sanitized_path = sanitize_android_path(remote_path)
        except ValueError as e:
            return False, f"Invalid path: {str(e)}"

        device_args = []
        target_device = device_id or self.selected_device
        if target_device:
            try:
                validated_device = validate_device_id(target_device)
                device_args = ["-s", validated_device]
            except ValueError as e:
                return False, f"Invalid device ID: {str(e)}"

        args = device_args + ["shell", "rm", "-rf", sanitized_path]

        try:
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            if returncode == 0:
                return True, f"Folder deleted: {remote_path}"
            else:
                return False, f"Failed to delete folder: {stderr}"
        except Exception as e:
            return False, f"Error deleting folder: {str(e)}"

    def move_item(self, old_path: str, new_path: str, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Move/rename a file or folder on the device."""
        # Sanitize inputs to prevent command injection
        try:
            sanitized_old_path = sanitize_android_path(old_path)
            sanitized_new_path = sanitize_android_path(new_path)
        except ValueError as e:
            return False, f"Invalid path: {str(e)}"

        device_args = []
        target_device = device_id or self.selected_device
        if target_device:
            try:
                validated_device = validate_device_id(target_device)
                device_args = ["-s", validated_device]
            except ValueError as e:
                return False, f"Invalid device ID: {str(e)}"

        args = device_args + ["shell", "mv", sanitized_old_path, sanitized_new_path]

        try:
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            if returncode == 0:
                return True, f"Item moved from {old_path} to {new_path}"
            else:
                return False, f"Failed to move item: {stderr}"
        except Exception as e:
            return False, f"Error moving item: {str(e)}"

    def get_file_info(self, remote_path: str, device_id: Optional[str] = None) -> Optional[dict]:
        """Get information about a file or folder on the device."""
        # Sanitize inputs to prevent command injection
        try:
            sanitized_path = sanitize_android_path(remote_path)
        except ValueError as e:
            logger.warning(f"Invalid path rejected in get_file_info: {str(e)}")
            return None

        device_args = []
        target_device = device_id or self.selected_device
        if target_device:
            try:
                validated_device = validate_device_id(target_device)
                device_args = ["-s", validated_device]
            except ValueError as e:
                logger.warning(f"Invalid device ID rejected in get_file_info: {str(e)}")
                return None

        args = device_args + ["shell", "ls", "-la", sanitized_path]
        
        try:
            stdout, stderr, returncode = self.command_runner.run_adb_command(args)
            if returncode != 0:
                return None
            
            lines = stdout.strip().split('\n')
            if not lines:
                return None
            
            # Parse the first non-empty line (should be the file info)
            for line in lines:
                line = line.strip()
                if line and not line.startswith('total '):
                    parts = line.split()
                    if len(parts) >= 9:
                        permissions = parts[0]
                        size_str = parts[4]
                        name = ' '.join(parts[8:])
                        
                        file_type = 'folder' if permissions.startswith('d') else 'file'
                        
                        try:
                            size = int(size_str) if file_type == 'file' else 0
                        except ValueError:
                            size = 0
                        
                        modified = ' '.join(parts[5:8]) if len(parts) >= 8 else ''
                        
                        return {
                            'name': name,
                            'type': file_type,
                            'size': size,
                            'permissions': permissions,
                            'modified': modified
                        }
            
            return None
        except Exception:
            return None
    
    def pull_folder_with_dedup(self, remote_path: str, local_path: str,
                              progress_callback: Optional[Callable[[int, int], None]] = None,
                              device_id: Optional[str] = None) -> Tuple[bool, Optional[dict]]:
        """Pull a folder from device with deduplication support.

        Args:
            remote_path: Remote folder path on device
            local_path: Local destination path
            progress_callback: Optional progress callback
            device_id: Optional specific device ID

        Returns:
            Tuple of (success, stats_dict) where stats contains transfer information
        """
        # For now, just call the regular pull_folder
        # TODO: Implement actual deduplication logic
        success, message = self.pull_folder(remote_path, local_path, progress_callback, device_id)
        stats = {'message': message} if success else None
        return success, stats

    def push_folder_with_dedup(self, local_path: str, remote_path: str,
                              progress_callback: Optional[Callable[[int, int], None]] = None,
                              device_id: Optional[str] = None) -> Tuple[bool, Optional[dict]]:
        """Push a folder to device with deduplication support.

        Args:
            local_path: Local folder path
            remote_path: Remote destination path on device
            progress_callback: Optional progress callback
            device_id: Optional specific device ID

        Returns:
            Tuple of (success, stats_dict) where stats contains transfer information
        """
        # For now, just call the regular push_folder
        # TODO: Implement actual deduplication logic
        success, message = self.push_folder(local_path, remote_path, progress_callback, device_id)
        stats = {'message': message} if success else None
        return success, stats

    def deduplicate_files(self, folder_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> Tuple[int, list]:
        """Find and optionally remove duplicate files in a folder."""
        deduplicator = FileDeduplicator()

        if progress_callback:
            deduplicator.set_progress_callback(progress_callback)

        duplicates = deduplicator.find_duplicates(folder_path)

        if duplicates:
            removed_count = deduplicator.remove_duplicates(duplicates)
            return removed_count, duplicates

        return 0, []

    # --- Legacy/compatibility helpers expected by older tests ---
    def set_progress_callback(self, callback: Callable[[int], None]) -> None:
        self.progress_callback = callback
        # propagate to subcomponents if they use it
        try:
            self.file_transfer.set_progress_callback(callback)
        except Exception:
            pass

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        self.status_callback = callback
        try:
            self.file_transfer.set_status_callback(callback)
        except Exception:
            pass

    def _update_progress(self, value: int) -> None:
        if self.progress_callback:
            self.progress_callback(value)

    def _update_status(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)

    def _update_transfer_progress(self, current_file: int, total_files: int) -> None:
        self.transfer_progress['current_file'] = current_file
        self.transfer_progress['total_files'] = total_files
        if self.status_callback:
            self.status_callback(f"TRANSFER_PROGRESS:{current_file}:{total_files}")

    def _reset_transfer_progress(self) -> None:
        self.transfer_progress['current_file'] = 0
        self.transfer_progress['total_files'] = 0
        self.transfer_progress['files_to_transfer'] = 0

    def check_local_disk_space(self) -> bool:
        tools_dir = get_platform_tools_directory()
        total, used, free = shutil.disk_usage(tools_dir)
        # Require at least 50MB free
        if free < 50 * 1024 * 1024:
            raise Exception("Insufficient disk space")
        return True

    def run_adb_command(self, args: list, capture_output: bool = True):
        cmd = [get_adb_binary_path()] + args
        try:
            if capture_output:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return p.stdout, p.stderr, p.returncode
            else:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.current_process = p
                return p
        except Exception as e:
            if capture_output:
                return None, str(e), -1
            return None

    def check_device(self) -> Optional[str]:
        out, err, rc = self.run_adb_command(['devices'], capture_output=True)
        if rc != 0 or not out:
            return None
        for line in str(out).splitlines():
            if line.endswith("\tdevice"):
                return line.split("\t")[0]
        return None

    def parse_progress(self, text_line: str) -> Optional[int]:
        return self.command_runner.parse_progress(text_line)

    def cancel_transfer(self) -> bool:
        if self.current_process is not None:
            try:
                # If already finished, don't terminate
                if self.current_process.poll() is not None:
                    self.current_process = None
                    return False
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
                    self.current_process.wait()
                self.current_process = None
                return True
            except Exception:
                return False
        return False
