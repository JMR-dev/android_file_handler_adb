# Debug Tools

This folder contains debugging utilities for troubleshooting the Android File Handler application.

## Scripts

### `debug_adb.py`

Comprehensive ADB debugging script that helps diagnose device detection issues.

**Usage:**

```bash
poetry run python debug_tools/debug_adb.py
```

**What it checks:**

- ADB binary path and existence
- Direct ADB command execution
- ADBManager device detection functionality
- Manual parsing of ADB output
- ADB version and server status

**When to use:**

- Android device is not being detected
- ADB connectivity issues
- Troubleshooting path problems
- Verifying ADB installation

**Output interpretation:**

- ✅ "Device found: [DEVICE_ID]" means ADB is working correctly
- ❌ "ADB binary not found" indicates path configuration issues
- Empty device list suggests USB debugging is not enabled or device is not connected
