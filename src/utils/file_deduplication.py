"""
File Deduplication Module
Handles hash-based file comparison and duplicate detection for file transfers.
"""

import os
import hashlib
from typing import Optional, Dict, List, Tuple, Callable


class FileDeduplicator:
    """Handles file hash computation and duplicate detection."""
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None):
        """Initialize the deduplicator with optional callbacks.
        
        Args:
            status_callback: Function to call with status updates
            progress_callback: Function to call with progress updates (0-100)
        """
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        
    def _update_status(self, message: str) -> None:
        """Update status if callback is available."""
        if self.status_callback:
            self.status_callback(message)
            
    def _update_progress(self, percentage: int) -> None:
        """Update progress if callback is available."""
        if self.progress_callback:
            self.progress_callback(percentage)
    
    def compute_local_file_hash(self, file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """Compute hash of a local file.
        
        Args:
            file_path: Path to the local file
            algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
            
        Returns:
            Hex digest of the file hash, or None if error
        """
        try:
            if not os.path.isfile(file_path):
                return None
                
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as file_handle:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: file_handle.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as exception:
            self._update_status(f"Error computing hash for {file_path}: {exception}")
            return None

    def compute_remote_file_hash(self, remote_path: str, algorithm: str = 'sha256',
                                adb_command_runner: Optional[Callable] = None) -> Optional[str]:
        """Compute hash of a file on the Android device using ADB shell.
        
        Args:
            remote_path: Path to the file on the Android device
            algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
            adb_command_runner: Function that runs ADB commands and returns (stdout, stderr, returncode)
            
        Returns:
            Hex digest of the file hash, or None if error
        """
        if not adb_command_runner:
            self._update_status("No ADB command runner provided")
            return None
            
        try:
            # Map algorithm names to Android shell commands
            hash_commands = {
                'md5': 'md5sum',
                'sha1': 'sha1sum', 
                'sha256': 'sha256sum'
            }
            
            if algorithm not in hash_commands:
                self._update_status(f"Unsupported hash algorithm: {algorithm}")
                return None
                
            cmd = ['shell', hash_commands[algorithm], remote_path]
            stdout, stderr, returncode = adb_command_runner(cmd, capture_output=True)
            
            if returncode != 0 or not stdout:
                self._update_status(f"Failed to compute remote hash: {stderr}")
                return None
                
            # Parse output: "hash_value  filename"
            hash_value = stdout.split()[0] if stdout else None
            return hash_value.lower() if hash_value else None
            
        except Exception as exception:
            self._update_status(f"Error computing remote hash for {remote_path}: {exception}")
            return None

    def check_files_identical(self, local_path: str, remote_path: str, 
                             adb_command_runner: Optional[Callable] = None,
                             algorithm: str = 'sha256') -> bool:
        """Check if local and remote files are identical by comparing hashes.
        
        Args:
            local_path: Path to the local file
            remote_path: Path to the remote file
            adb_command_runner: Function that runs ADB commands
            algorithm: Hash algorithm to use
            
        Returns:
            True if files are identical, False otherwise
        """
        local_hash = self.compute_local_file_hash(local_path, algorithm)
        remote_hash = self.compute_remote_file_hash(remote_path, algorithm, adb_command_runner)
        
        if local_hash is None or remote_hash is None:
            return False
            
        return local_hash == remote_hash

    def build_local_file_hash_map(self, file_paths: List[str], 
                                 algorithm: str = 'sha256') -> Dict[str, str]:
        """Build a mapping of local file paths to their hashes.
        
        Args:
            file_paths: List of local file paths to hash
            algorithm: Hash algorithm to use
            
        Returns:
            Dictionary mapping file paths to their hash values
        """
        hash_map = {}
        total_files = len(file_paths)
        
        for index, file_path in enumerate(file_paths):
            file_hash = self.compute_local_file_hash(file_path, algorithm)
            
            if file_hash:
                hash_map[file_path] = file_hash
                
            # Update progress
            if total_files > 0:
                progress_percentage = int((index + 1) * 100 / total_files)
                self._update_progress(progress_percentage)
                self._update_status(f"Computing local hashes... {index + 1}/{total_files}")
            
        return hash_map

    def build_remote_file_hash_map(self, file_paths: List[str], 
                                  adb_command_runner: Optional[Callable] = None,
                                  algorithm: str = 'sha256') -> Dict[str, str]:
        """Build a mapping of remote file paths to their hashes.
        
        Args:
            file_paths: List of remote file paths to hash
            adb_command_runner: Function that runs ADB commands
            algorithm: Hash algorithm to use
            
        Returns:
            Dictionary mapping file paths to their hash values
        """
        if not adb_command_runner:
            self._update_status("No ADB command runner provided")
            return {}
            
        hash_map = {}
        total_files = len(file_paths)
        
        for index, file_path in enumerate(file_paths):
            file_hash = self.compute_remote_file_hash(file_path, algorithm, adb_command_runner)
            
            if file_hash:
                hash_map[file_path] = file_hash
                
            # Update progress
            if total_files > 0:
                progress_percentage = int((index + 1) * 100 / total_files)
                self._update_progress(progress_percentage)
                self._update_status(f"Computing remote hashes... {index + 1}/{total_files}")
            
        return hash_map

    def find_duplicate_files(self, source_files: List[str], target_files: List[str],
                           is_remote_source: bool = False, is_remote_target: bool = False,
                           adb_command_runner: Optional[Callable] = None,
                           algorithm: str = 'sha256') -> Tuple[List[str], List[str]]:
        """Find files that are duplicates between source and target lists.
        
        Args:
            source_files: List of source file paths
            target_files: List of target file paths
            is_remote_source: True if source files are on Android device
            is_remote_target: True if target files are on Android device
            adb_command_runner: Function that runs ADB commands
            algorithm: Hash algorithm to use
            
        Returns:
            Tuple of (files_to_transfer, duplicate_files)
        """
        self._update_status("Building hash maps for duplicate detection...")
        
        # Build hash maps for both source and target
        if is_remote_source:
            source_hashes = self.build_remote_file_hash_map(source_files, adb_command_runner, algorithm)
        else:
            source_hashes = self.build_local_file_hash_map(source_files, algorithm)
            
        if is_remote_target:
            target_hashes = self.build_remote_file_hash_map(target_files, adb_command_runner, algorithm)
        else:
            target_hashes = self.build_local_file_hash_map(target_files, algorithm)
        
        # Find duplicates by comparing hashes
        target_hash_values = set(target_hashes.values())
        files_to_transfer = []
        duplicate_files = []
        
        for source_file in source_files:
            source_hash = source_hashes.get(source_file)
            if source_hash and source_hash in target_hash_values:
                duplicate_files.append(source_file)
            else:
                files_to_transfer.append(source_file)
        
        self._update_status(f"Found {len(duplicate_files)} duplicates, {len(files_to_transfer)} files to transfer")
        
        return files_to_transfer, duplicate_files

    def get_file_size(self, file_path: str, is_remote: bool = False,
                     adb_command_runner: Optional[Callable] = None) -> Optional[int]:
        """Get the size of a file in bytes.
        
        Args:
            file_path: Path to the file
            is_remote: True if file is on Android device
            adb_command_runner: Function that runs ADB commands
            
        Returns:
            File size in bytes, or None if error
        """
        try:
            if is_remote and adb_command_runner:
                cmd = ['shell', 'stat', '-c', '%s', file_path]
                stdout, stderr, returncode = adb_command_runner(cmd, capture_output=True)
                
                if returncode == 0 and stdout.strip().isdigit():
                    return int(stdout.strip())
                else:
                    return None
            else:
                if os.path.isfile(file_path):
                    return os.path.getsize(file_path)
                else:
                    return None
        except Exception:
            return None

    def calculate_transfer_savings(self, duplicate_files: List[str], is_remote: bool = False,
                                 adb_command_runner: Optional[Callable] = None) -> Tuple[int, int]:
        """Calculate the number of bytes and files that would be saved by skipping duplicates.
        
        Args:
            duplicate_files: List of duplicate file paths
            is_remote: True if files are on Android device
            adb_command_runner: Function that runs ADB commands
            
        Returns:
            Tuple of (bytes_saved, files_saved)
        """
        bytes_saved = 0
        files_saved = 0
        
        for file_path in duplicate_files:
            file_size = self.get_file_size(file_path, is_remote, adb_command_runner)
            if file_size is not None:
                bytes_saved += file_size
                files_saved += 1
        
        return bytes_saved, files_saved

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable string.
        
        Args:
            bytes_value: Number of bytes
            
        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"
