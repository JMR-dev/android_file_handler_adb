"""Tests for file deduplication utility."""

import pytest
import hashlib
import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open

from src.utils.file_deduplication import FileDeduplicator


class TestFileDeduplicator:
    """Test FileDeduplicator class functionality."""
    
    @pytest.fixture
    def deduplicator(self):
        """Create a FileDeduplicator instance for testing."""
        return FileDeduplicator()
    
    @pytest.fixture
    def deduplicator_with_callbacks(self):
        """Create a FileDeduplicator instance with callbacks for testing."""
        status_callback = MagicMock()
        progress_callback = MagicMock()
        return FileDeduplicator(status_callback, progress_callback), status_callback, progress_callback
    
    def test_init_without_callbacks(self, deduplicator):
        """Test FileDeduplicator initialization without callbacks."""
        assert deduplicator.status_callback is None
        assert deduplicator.progress_callback is None
    
    def test_init_with_callbacks(self):
        """Test FileDeduplicator initialization with callbacks."""
        status_callback = MagicMock()
        progress_callback = MagicMock()
        deduplicator = FileDeduplicator(status_callback, progress_callback)
        
        assert deduplicator.status_callback == status_callback
        assert deduplicator.progress_callback == progress_callback
    
    def test_update_status_with_callback(self, deduplicator_with_callbacks):
        """Test status update with callback."""
        deduplicator, status_callback, _ = deduplicator_with_callbacks
        deduplicator._update_status("Test message")
        status_callback.assert_called_once_with("Test message")
    
    def test_update_status_without_callback(self, deduplicator):
        """Test status update without callback."""
        # Should not raise an exception
        deduplicator._update_status("Test message")
    
    def test_update_progress_with_callback(self, deduplicator_with_callbacks):
        """Test progress update with callback."""
        deduplicator, _, progress_callback = deduplicator_with_callbacks
        deduplicator._update_progress(75)
        progress_callback.assert_called_once_with(75)
    
    def test_update_progress_without_callback(self, deduplicator):
        """Test progress update without callback."""
        # Should not raise an exception
        deduplicator._update_progress(75)
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'test file content')
    @patch('os.path.isfile', return_value=True)
    def test_compute_local_file_hash_small_file(self, mock_isfile, mock_file, deduplicator):
        """Test file hash computation for small file."""
        expected_hash = hashlib.sha256(b'test file content').hexdigest()
        result = deduplicator.compute_local_file_hash('/fake/path/file.txt')
        
        assert result == expected_hash
        mock_file.assert_called_once_with('/fake/path/file.txt', 'rb')
        mock_isfile.assert_called_once_with('/fake/path/file.txt')
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile', return_value=True)
    def test_compute_local_file_hash_large_file(self, mock_isfile, mock_file, deduplicator_with_callbacks):
        """Test file hash computation for large file with progress updates."""
        deduplicator, status_callback, progress_callback = deduplicator_with_callbacks
        
        # Mock reading chunks
        mock_file.return_value.__enter__.return_value.read.side_effect = [
            b'chunk1' * 1000,  # First chunk
            b'chunk2' * 1000,  # Second chunk
            b'',               # EOF
        ]
        
        result = deduplicator.compute_local_file_hash('/fake/path/largefile.txt')
        
        # Should return a valid hash
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex digest length
    
    @patch('os.path.isfile', return_value=False)
    def test_compute_local_file_hash_nonexistent_file(self, mock_isfile, deduplicator):
        """Test file hash computation for nonexistent file."""
        result = deduplicator.compute_local_file_hash('/fake/nonexistent/file.txt')
        assert result is None
        mock_isfile.assert_called_once_with('/fake/nonexistent/file.txt')
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    @patch('os.path.isfile', return_value=True)
    def test_compute_local_file_hash_permission_error(self, mock_isfile, mock_file, deduplicator):
        """Test file hash computation with permission error."""
        result = deduplicator.compute_local_file_hash('/fake/protected/file.txt')
        assert result is None
    
    def test_check_files_identical_same_hash(self, deduplicator):
        """Test file comparison with identical hashes."""
        with patch.object(deduplicator, 'compute_local_file_hash') as mock_hash:
            mock_hash.return_value = 'abc123'
            with patch.object(deduplicator, 'compute_remote_file_hash') as mock_remote_hash:
                mock_remote_hash.return_value = 'abc123'
                result = deduplicator.check_files_identical('/file1.txt', '/file2.txt')
                assert result is True
    
    def test_check_files_identical_different_hash(self, deduplicator):
        """Test file comparison with different hashes."""
        with patch.object(deduplicator, 'compute_local_file_hash') as mock_hash:
            mock_hash.return_value = 'abc123'
            with patch.object(deduplicator, 'compute_remote_file_hash') as mock_remote_hash:
                mock_remote_hash.return_value = 'def456'
                result = deduplicator.check_files_identical('/file1.txt', '/file2.txt')
                assert result is False
    
    def test_check_files_identical_one_hash_none(self, deduplicator):
        """Test file comparison with one hash being None."""
        with patch.object(deduplicator, 'compute_local_file_hash') as mock_hash:
            mock_hash.return_value = 'abc123'
            with patch.object(deduplicator, 'compute_remote_file_hash') as mock_remote_hash:
                mock_remote_hash.return_value = None
                result = deduplicator.check_files_identical('/file1.txt', '/file2.txt')
                assert result is False
    
    def test_check_files_identical_both_hashes_none(self, deduplicator):
        """Test file comparison with both hashes being None."""
        with patch.object(deduplicator, 'compute_local_file_hash') as mock_hash:
            mock_hash.return_value = None
            with patch.object(deduplicator, 'compute_remote_file_hash') as mock_remote_hash:
                mock_remote_hash.return_value = None
                result = deduplicator.check_files_identical('/file1.txt', '/file2.txt')
                assert result is False
    
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.isfile')
    def test_build_local_file_hash_map(self, mock_isfile, mock_listdir, mock_exists, deduplicator):
        """Test getting local file hashes from directory."""
        mock_exists.return_value = True
        mock_listdir.return_value = ['file1.txt', 'file2.jpg', 'subdir']
        mock_isfile.side_effect = lambda x: not x.endswith('subdir')
        
        file_paths = ['/fake/directory/file1.txt', '/fake/directory/file2.jpg']
        
        with patch.object(deduplicator, 'compute_local_file_hash') as mock_hash:
            mock_hash.side_effect = ['hash1', 'hash2']
            
            result = deduplicator.build_local_file_hash_map(file_paths)
            
            expected = {
                '/fake/directory/file1.txt': 'hash1',
                '/fake/directory/file2.jpg': 'hash2'
            }
            assert result == expected
    
    @patch('os.path.exists', return_value=False)
    def test_build_local_file_hash_map_nonexistent_files(self, mock_exists, deduplicator):
        """Test getting local file hashes from nonexistent files."""
        result = deduplicator.build_local_file_hash_map(['/fake/nonexistent'])
        assert result == {}
    
    def test_find_duplicate_files_with_duplicates(self, deduplicator):
        """Test finding duplicates when duplicates exist."""
        local_files = ['/local/file1.txt', '/local/file2.jpg', '/local/file3.txt']
        remote_files = ['/remote/remote1.txt', '/remote/remote2.jpg', '/remote/remote3.txt']
        
        with patch.object(deduplicator, 'build_local_file_hash_map') as mock_local:
            with patch.object(deduplicator, 'build_remote_file_hash_map') as mock_remote:
                mock_local.return_value = {
                    '/local/file1.txt': 'hash1',
                    '/local/file2.jpg': 'hash2', 
                    '/local/file3.txt': 'hash3'
                }
                mock_remote.return_value = {
                    '/remote/remote1.txt': 'hash1',  # Duplicate of file1.txt
                    '/remote/remote2.jpg': 'hash4',  # Unique
                    '/remote/remote3.txt': 'hash3'   # Duplicate of file3.txt
                }
                
                files_to_transfer, duplicates = deduplicator.find_duplicate_files(
                    local_files, remote_files, is_remote_target=True)
                
                # Should find 2 duplicates: file1.txt and file3.txt
                assert len(duplicates) == 2
                assert '/local/file1.txt' in duplicates
                assert '/local/file3.txt' in duplicates
                # file2.jpg should be transferred since it's not a duplicate
                assert len(files_to_transfer) == 1
                assert '/local/file2.jpg' in files_to_transfer
    
    def test_find_duplicate_files_no_duplicates(self, deduplicator):
        """Test finding duplicates when no duplicates exist."""
        local_files = ['/local/file1.txt', '/local/file2.jpg']
        remote_files = ['/remote/remote1.txt', '/remote/remote2.jpg']
        
        with patch.object(deduplicator, 'build_local_file_hash_map') as mock_local:
            with patch.object(deduplicator, 'build_remote_file_hash_map') as mock_remote:
                mock_local.return_value = {
                    '/local/file1.txt': 'hash1',
                    '/local/file2.jpg': 'hash2'
                }
                mock_remote.return_value = {
                    '/remote/remote1.txt': 'hash3',
                    '/remote/remote2.jpg': 'hash4'
                }
                
                files_to_transfer, duplicates = deduplicator.find_duplicate_files(
                    local_files, remote_files, is_remote_target=True)
                assert duplicates == []
                assert files_to_transfer == local_files
    
    def test_find_duplicate_files_empty_collections(self, deduplicator):
        """Test finding duplicates with empty collections."""
        files_to_transfer, duplicates = deduplicator.find_duplicate_files([], [])
        assert duplicates == []
        assert files_to_transfer == []


class TestFileDeduplicatorIntegration:
    """Integration tests for FileDeduplicator with real files."""
    
    def test_real_file_hash_computation(self):
        """Test hash computation with real temporary files."""
        deduplicator = FileDeduplicator()
        
        # Create temporary files with known content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf1:
            tf1.write("test content 1")
            temp_file1 = tf1.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf2:
            tf2.write("test content 1")  # Same content
            temp_file2 = tf2.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf3:
            tf3.write("test content 2")  # Different content
            temp_file3 = tf3.name
        
        try:
            hash1 = deduplicator.compute_local_file_hash(temp_file1)
            hash2 = deduplicator.compute_local_file_hash(temp_file2)
            hash3 = deduplicator.compute_local_file_hash(temp_file3)
            
            # Same content should have same hash
            assert hash1 == hash2
            # Different content should have different hash
            assert hash1 != hash3
            
            # Test file comparison - since check_files_identical expects local/remote,
            # we'll just compare hashes directly for local files
            assert hash1 == hash2  # Same files should have same hash
            assert hash1 != hash3  # Different files should have different hash
            
        finally:
            # Clean up
            os.unlink(temp_file1)
            os.unlink(temp_file2)
            os.unlink(temp_file3)
    
    def test_real_directory_hash_computation(self):
        """Test directory hash computation with real temporary directory."""
        deduplicator = FileDeduplicator()
        
        # Create temporary directory with files
        with tempfile.TemporaryDirectory() as temp_dir:
            file1_path = os.path.join(temp_dir, 'file1.txt')
            file2_path = os.path.join(temp_dir, 'file2.txt')
            
            with open(file1_path, 'w') as f1:
                f1.write("content 1")
            with open(file2_path, 'w') as f2:
                f2.write("content 2")
            
            hashes = deduplicator.build_local_file_hash_map([file1_path, file2_path])
            
            assert file1_path in hashes
            assert file2_path in hashes
            assert len(hashes) == 2
            assert hashes[file1_path] != hashes[file2_path]


if __name__ == '__main__':
    pytest.main([__file__])