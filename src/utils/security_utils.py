"""
Security utilities for input sanitization and validation.
Prevents command injection and path traversal attacks.
"""

import os
import re
from typing import Optional

# Pre-compiled regex patterns for performance
_DANGEROUS_CHAR_PATTERN = re.compile(r'[;|&$`\n\r><(){}[\]!]')
_DANGEROUS_PATH_PATTERN = re.compile(r'[;|&`\n\r]|\$[({]|&&|\|\||>>')


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

    # Check for null bytes
    if '\x00' in component:
        raise ValueError("Path component contains null byte")

    # Check for dangerous characters using pre-compiled regex
    # Matches any shell metacharacters that could be used for command injection
    match = _DANGEROUS_CHAR_PATTERN.search(component)
    if match:
        raise ValueError(f"Path component contains dangerous character: {match.group()}")

    # Check for command substitution patterns
    if '$(' in component or '${' in component:
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

    # Check for command injection patterns using pre-compiled regex
    # Note: We check for shell metacharacters that could be used for command injection
    # We allow spaces and most characters that are valid in Android paths
    # Pattern matches: semicolon, pipe, ampersand, dollar-paren, dollar-brace,
    # backtick, newline, carriage return, double-ampersand, double-pipe, double-redirect
    match = _DANGEROUS_PATH_PATTERN.search(path)
    if match:
        raise ValueError(f"Path contains dangerous pattern: {match.group()}")

    # Note: We allow spaces, Unicode characters, and other characters that are
    # valid in Android filesystem paths. The dangerous pattern check above is
    # sufficient to prevent command injection since we pass paths as arguments
    # to subprocess (not through shell=True).

    return path


def sanitize_local_path(path: str, base_dir: Optional[str] = None, allow_nonexistent: bool = True) -> str:
    """Sanitize a local filesystem path and check for path traversal.

    Args:
        path: Local filesystem path
        base_dir: Optional base directory to restrict path within
        allow_nonexistent: If True, allow paths that don't exist yet (uses abspath instead of realpath)

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
    # For non-existent paths, use abspath to avoid CWD resolution issues
    # For existing paths, use realpath to resolve symlinks and prevent escapes
    try:
        if allow_nonexistent and not os.path.exists(path):
            # Path doesn't exist yet (e.g., pull destination) - use abspath
            normalized_path = os.path.normpath(os.path.abspath(path))
        else:
            # Path exists or we're strict - use realpath to resolve symlinks
            normalized_path = os.path.normpath(os.path.realpath(path))
    except (ValueError, OSError) as e:
        raise ValueError(f"Invalid path: {e}")

    # If base_dir is specified, ensure the path is within it
    # This check is sufficient - after normalization, if the path doesn't start
    # with base_dir, it's outside the allowed directory tree
    if base_dir:
        try:
            # Use same resolution strategy for base_dir
            if allow_nonexistent and not os.path.exists(base_dir):
                base_dir_abs = os.path.normpath(os.path.abspath(base_dir))
            else:
                base_dir_abs = os.path.normpath(os.path.realpath(base_dir))
            # Check if the normalized path starts with the base directory
            if not normalized_path.startswith(base_dir_abs + os.sep) and normalized_path != base_dir_abs:
                raise ValueError(f"Path traversal detected: path is outside base directory")
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid base directory: {e}")

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
