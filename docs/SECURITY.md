# Security Design Document

## Overview

This document describes the security design, threat model, and known limitations of the Android File Handler ADB application. The application implements defense-in-depth security controls to protect against command injection, path traversal, and other common attack vectors.

## Threat Model

### Assets Protected
1. **Local Filesystem**: User's files and directories on the host system
2. **Android Device Data**: Files and directories on the connected Android device
3. **System Integrity**: Protection against arbitrary command execution
4. **User Privacy**: Prevention of unauthorized access to sensitive files

### Threat Actors
1. **Malicious Files**: Specially-crafted filenames designed to exploit command injection vulnerabilities
2. **Compromised Android Device**: A device that may attempt to exploit the host system through malicious file metadata
3. **Malicious Input**: User-provided paths or device IDs containing attack payloads
4. **Man-in-the-Middle**: Attacks during ADB platform-tools download (partial mitigation)

### Attack Vectors

#### 1. Command Injection
**Description**: Attacker attempts to inject shell commands through user-controlled inputs (paths, device IDs, filenames).

**Mitigations**:
- Input sanitization with regex-based dangerous character detection
- Subprocess execution without `shell=True` (arguments passed as list, not string)
- Validation of all user-controlled inputs before use
- Specific error messages for rejected inputs

**Examples Blocked**:
```
/sdcard/file; rm -rf /
/sdcard/$(whoami)
device123; malicious_command
```

#### 2. Path Traversal
**Description**: Attacker attempts to access files outside of intended directories using `..` or symbolic links.

**Mitigations**:
- Path normalization using `os.path.normpath()` and `os.path.realpath()`
- Symlink resolution to detect symlink-based escape attempts
- Base directory validation for local paths
- Rejection of null bytes in paths

**Examples Blocked**:
```
/tmp/safe/../../../etc/passwd
[symlink from /tmp/safe/escape -> /etc/]
/tmp/file\x00.txt
```

#### 3. Zip Bomb / Archive Bomb
**Description**: Maliciously crafted compressed files that expand to consume excessive disk space.

**Mitigations**:
- Size limit checks on downloaded files
- Extraction size validation
- Disk space checks before download

**Implementation**: See `src/core/platform_tools.py` download validation.

#### 4. Redirect Attacks
**Description**: Malicious redirects during platform-tools download that could lead to downloading malware.

**Mitigations**:
- URL validation for redirects
- HTTPS enforcement
- Domain validation for official sources

**Implementation**: See `src/core/platform_tools.py` download validation.

## Security Controls

### Input Sanitization Functions

#### `sanitize_path_component(component: str)`
**Purpose**: Validates individual path components (filenames, directory names).

**Checks**:
- Non-empty string
- No null bytes (`\x00`)
- No shell metacharacters: `;`, `|`, `&`, `$`, `` ` ``, `\n`, `\r`, `>`, `<`, `(`, `)`, `{`, `}`, `[`, `]`, `!`
- No command substitution patterns: `$(`, `${`

**Usage**: Used for validating individual filename components.

#### `sanitize_android_path(path: str)`
**Purpose**: Validates full paths on Android devices.

**Checks**:
- Non-empty string
- No null bytes (`\x00`)
- No dangerous patterns: `;`, `|`, `&`, `` ` ``, `\n`, `\r`, `$(`, `${`, `&&`, `||`, `>>`
- **Allows**: Spaces, Unicode characters, forward slashes, dots

**Usage**: Used for all Android device paths before passing to ADB commands.

**Rationale**: Android filesystems support Unicode and spaces in filenames. We only block patterns that could enable command injection.

#### `sanitize_local_path(path: str, base_dir: Optional[str])`
**Purpose**: Validates and normalizes local filesystem paths.

**Checks**:
- Non-empty string
- No null bytes (`\x00`)
- Path normalization via `os.path.normpath(os.path.realpath())`
- Symlink resolution to detect escapes
- Optional base directory containment validation

**Usage**: Used for local filesystem paths, especially when restricting operations to specific directories.

**Rationale**: Using `realpath()` instead of `abspath()` ensures symbolic links are resolved before validation, preventing symlink-based path traversal.

#### `validate_device_id(device_id: str)`
**Purpose**: Validates Android device IDs.

**Checks**:
- Non-empty string
- Alphanumeric characters, dots, colons, underscores, hyphens only
- No shell metacharacters
- No spaces

**Usage**: Validates device IDs before using in ADB commands with `-s` flag.

**Valid Examples**:
```
ABC123DEF456          (serial number)
192.168.1.100:5555   (network device)
emulator-5554        (emulator)
```

### Subprocess Execution

**Safe Pattern**:
```python
# SAFE: Arguments as list, no shell=True
subprocess.run([adb_path, "-s", device_id, "shell", "ls", path])
```

**Unsafe Pattern** (NOT USED):
```python
# UNSAFE: Shell=True enables command injection
subprocess.run(f"adb -s {device_id} shell ls {path}", shell=True)
```

**Implementation**: All ADB commands use argument lists without `shell=True`, preventing shell interpretation of metacharacters.

### Error Handling

**Logging**: Validation failures are logged with specific error messages to help detect attack attempts and debug legitimate issues.

**User Feedback**: Failed operations return descriptive error messages indicating why paths or device IDs were rejected.

**Silent Failures**: Removed in favor of explicit logging (see `src/core/adb_manager.py` methods `list_files()` and `get_file_info()`).

## Known Limitations

### 1. Android Device Trust
**Limitation**: The application trusts the connected Android device to return valid data.

**Risk**: A compromised or malicious device could return crafted data through ADB responses.

**Mitigation**: Input sanitization is applied to user-provided inputs, but responses from `adb shell` commands are parsed but not fully sanitized. The subprocess argument list pattern prevents command injection even with malicious device responses.

**Residual Risk**: Low. Device responses are parsed but not executed as commands.

### 2. ADB Binary Trust
**Limitation**: The application trusts the ADB binary downloaded from Google's servers.

**Risk**: If download is intercepted (MITM) or if Google's servers are compromised, malicious ADB binary could be installed.

**Mitigation**:
- HTTPS is used for downloads
- URL validation for redirects
- Downloads only from official Google domains

**Residual Risk**: Low to Medium. Consider adding SHA-256 hash verification in future versions.

### 3. Local Filesystem Permissions
**Limitation**: The application runs with the same permissions as the user who launched it.

**Risk**: If user has write access to system directories, the application could be used to overwrite important files (though not through exploitation).

**Mitigation**: Application uses standard OS permissions. Users should not run the application with elevated privileges unless necessary.

**Residual Risk**: Low. This is standard behavior for desktop applications.

### 4. Unicode Normalization
**Limitation**: Unicode characters are allowed but not normalized (e.g., no NFC/NFD conversion).

**Risk**: Different Unicode representations of the same visual character could bypass filters or cause confusion.

**Mitigation**: Characters are checked for dangerous patterns regardless of Unicode form.

**Residual Risk**: Very Low. Path validation is performed before use.

### 5. Race Conditions
**Limitation**: Time-of-check to time-of-use (TOCTOU) race conditions are possible with filesystem operations.

**Risk**: A symlink or file could be changed between validation and use.

**Mitigation**: Paths are validated immediately before use. Symlinks are resolved during validation.

**Residual Risk**: Very Low. Window for exploitation is extremely small and requires local access.

### 6. Platform-Specific Behavior
**Limitation**: Path handling differs between Windows, Linux, and macOS.

**Risk**: Platform-specific path normalization could behave unexpectedly.

**Mitigation**:
- Use of `os.path` functions for cross-platform compatibility
- Comprehensive tests for different path formats
- Separate handling for Windows root paths in file transfer module

**Residual Risk**: Low. Extensive testing covers common scenarios.

## Security Testing

### Test Coverage
The security validation suite includes tests for:

1. **Command Injection Prevention**
   - Shell metacharacters in paths
   - Command substitution patterns
   - Backtick substitution
   - Newline injection

2. **Path Traversal Prevention**
   - `..` sequences
   - Absolute path escapes
   - Symlink-based escapes
   - Null byte injection

3. **Unicode Handling**
   - Chinese, Russian, Arabic, Emoji characters
   - Accented characters
   - Mixed Unicode and spaces

4. **Edge Cases**
   - Very long paths (100+ directory levels)
   - Very long filenames (255+ characters)
   - Paths with multiple dots
   - Hidden files (leading dot)

5. **Cross-Platform**
   - Windows-style paths (`C:\Users\...`)
   - Unix-style paths (`/tmp/...`)
   - Mixed path separators
   - Platform-specific normalization

6. **Device ID Validation**
   - Serial numbers
   - Network addresses with ports
   - Emulator IDs
   - Invalid characters

### Test Location
All security tests are located in: `tests/utils/test_security_utils.py`

Run tests with:
```bash
poetry run pytest tests/utils/test_security_utils.py -v
```

## Security Maintenance

### Regular Reviews
Security controls should be reviewed:
- When adding new features that accept user input
- When modifying path handling or subprocess execution
- After discovering vulnerabilities in similar applications
- At least annually

### Dependency Updates
Keep dependencies updated to patch security vulnerabilities:
```bash
poetry update
poetry run pytest  # Verify no regressions
```

### Vulnerability Reporting
Security issues should be reported via GitHub Issues with the `security` label.

## Compliance and Best Practices

### OWASP Guidelines
This implementation follows OWASP recommendations for:
- Input validation (positive security model where possible)
- Output encoding (subprocess argument lists)
- Command injection prevention
- Path traversal prevention

### Python Security Best Practices
- No use of `eval()`, `exec()`, or `compile()`
- No `shell=True` in subprocess calls
- Type hints for all security-critical functions
- Comprehensive error handling

### Defense in Depth
Multiple layers of security:
1. Input validation (first line of defense)
2. Subprocess argument lists (prevent shell interpretation)
3. Path normalization (prevent traversal)
4. Symlink resolution (prevent escapes)
5. Logging (detection and debugging)

## Future Enhancements

### Recommended Improvements
1. **SHA-256 Hash Verification**: Verify ADB binary downloads against known-good hashes
2. **Code Signing**: Sign application binaries for distribution
3. **Sandboxing**: Consider running ADB operations in a restricted environment
4. **Rate Limiting**: Prevent brute-force attempts on path validation
5. **Audit Logging**: Enhanced logging for security-relevant events
6. **Unicode Normalization**: Normalize Unicode strings to prevent bypass attempts

### Not Recommended
1. **Filename Whitelisting**: Too restrictive for international users
2. **Path Length Limits**: Android supports long paths; artificial limits harm usability
3. **Blocking All Special Characters**: Many legitimate filenames use special characters

## References

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html)
- [Android File System Permissions](https://source.android.com/docs/core/permissions/filesystem)

## Version History

- **v1.0** (2025-10-15): Initial security design documentation
  - Command injection prevention
  - Path traversal prevention
  - Symlink resolution
  - Comprehensive test coverage
  - Error logging for validation failures
