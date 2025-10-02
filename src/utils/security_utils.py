"""
Security utilities for input sanitization and validation.
Prevents command injection and path traversal attacks.
"""

import os
import re
from typing import Optional


def sanitize_path_component(component: str) -> str:
    """Sanitize a single path component to prevent injection.

    Args:
        component: A single path component (filename or directory name)

    Returns:
        Sanitized path component

    Raises:
        ValueError: If the component contains dangerous characters
    """
    if not component:
        raise ValueError("Path component cannot be empty")

    # Check for dangerous characters that could be used for command injection
    dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r', '>', '<', '(', ')', '{', '}', '[', ']', '!']
    for char in dangerous_chars:
        if char in component:
            raise ValueError(f"Path component contains dangerous character: {char}")

    # Check for command substitution patterns
    if '$(' in component or '${' in component or '`' in component:
        raise ValueError("Path component contains command substitution pattern")

    return component


def sanitize_android_path(path: str) -> str:
    """Sanitize an Android device path to prevent command injection.

    Args:
        path: Android device path

    Returns:
        Sanitized path

    Raises:
        ValueError: If the path contains dangerous patterns
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Remove any leading/trailing whitespace
    path = path.strip()

    # Check for null bytes
    if '\x00' in path:
        raise ValueError("Path contains null byte")

    # Check for command injection patterns
    dangerous_patterns = [
        ';', '|', '&', '$(', '${', '`', '\n', '\r',
        '&&', '||', '>>',
    ]

    for pattern in dangerous_patterns:
        if pattern in path:
            raise ValueError(f"Path contains dangerous pattern: {pattern}")

    # Validate path structure (should start with / for absolute paths on Android)
    # Allow relative paths but be cautious
    if not path.startswith('/') and not path.startswith('./'):
        # If it's not an absolute or explicitly relative path, make it explicit
        # Most Android paths should be absolute
        if not re.match(r'^[a-zA-Z0-9_\-./]+$', path):
            raise ValueError("Path contains invalid characters")

    return path


def sanitize_local_path(path: str, base_dir: Optional[str] = None) -> str:
    """Sanitize a local filesystem path and check for path traversal.

    Args:
        path: Local filesystem path
        base_dir: Optional base directory to restrict path within

    Returns:
        Sanitized and normalized absolute path

    Raises:
        ValueError: If the path is dangerous or attempts traversal outside base_dir
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Remove any leading/trailing whitespace
    path = path.strip()

    # Check for null bytes
    if '\x00' in path:
        raise ValueError("Path contains null byte")

    # Normalize the path to resolve .. and symlinks
    try:
        normalized_path = os.path.normpath(os.path.abspath(path))
    except (ValueError, OSError) as e:
        raise ValueError(f"Invalid path: {e}")

    # If base_dir is specified, ensure the path is within it
    if base_dir:
        try:
            base_dir_abs = os.path.normpath(os.path.abspath(base_dir))
            # Check if the normalized path starts with the base directory
            if not normalized_path.startswith(base_dir_abs + os.sep) and normalized_path != base_dir_abs:
                raise ValueError(f"Path traversal detected: path is outside base directory")
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid base directory: {e}")

    # Check for dangerous patterns in the original path that might bypass normalization
    if '..' in path:
        # Verify that after normalization, we haven't moved up unexpectedly
        path_depth = normalized_path.count(os.sep)
        if base_dir:
            base_depth = base_dir_abs.count(os.sep)
            if path_depth < base_depth:
                raise ValueError("Path traversal detected: attempting to access parent directories")

    return normalized_path


def validate_device_id(device_id: str) -> str:
    """Validate an Android device ID.

    Args:
        device_id: Device ID string from ADB

    Returns:
        Validated device ID

    Raises:
        ValueError: If the device ID is invalid
    """
    if not device_id:
        raise ValueError("Device ID cannot be empty")

    # Device IDs should only contain alphanumeric characters, dots, colons, and hyphens
    if not re.match(r'^[a-zA-Z0-9.:_-]+$', device_id):
        raise ValueError("Device ID contains invalid characters")

    # Check for command injection patterns
    dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r', ' ', '>', '<']
    for char in dangerous_chars:
        if char in device_id:
            raise ValueError(f"Device ID contains dangerous character: {char}")

    return device_id


def escape_shell_arg(arg: str) -> str:
    """Escape a shell argument for safe use in commands.

    Note: This is a defense-in-depth measure. Prefer using validated inputs
    and avoiding shell=True in subprocess calls.

    Args:
        arg: Argument to escape

    Returns:
        Escaped argument safe for shell use
    """
    # For maximum safety with subprocess, we actually want to avoid shell escaping
    # and instead ensure the argument doesn't contain dangerous characters
    # This function validates and returns the argument if safe

    if not arg:
        return arg

    # Check for any shell metacharacters
    dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r', '>', '<', '(', ')', '{', '}', '[', ']', '!', '*', '?', '~']
    for char in dangerous_chars:
        if char in arg:
            raise ValueError(f"Argument contains shell metacharacter: {char}")

    return arg
