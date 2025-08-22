# AppImage Troubleshooting

## XCB Threading Error

If you encounter this error when running the AppImage:

```
[xcb] Unknown sequence number while appending request
[xcb] You called XInitThreads, this is not your fault
[xcb] Aborting, sorry about that.
python3.12: ../../src/xcb_io.c:157: append_pending_request: Assertion `!xcb_xlib_unknown_seq_number' failed.
```

This is a known issue with certain Linux distributions and X11/XCB configurations.

### Solutions:

1. **Try different display server settings:**
   ```bash
   export LIBXCB_ALLOW_SLOPPY_LOCK=1
   ./android-file-handler-linux
   ```

2. **Use virtual framebuffer (if available):**
   ```bash
   xvfb-run -a ./android-file-handler-linux
   ```

3. **Try on different Linux distribution:**
   - This issue is more common on certain Ubuntu/Debian configurations
   - The AppImage should work fine on most other distributions

4. **Alternative: Run from source:**
   ```bash
   git clone <repository>
   cd android_file_handler_adb
   poetry install
   poetry run python src/main.py
   ```

## Verification that AppImage is Correct

Despite the XCB error, the AppImage is properly built:
- ✅ All dependencies included (requests, urllib3, etc.)
- ✅ Python 3.12 runtime embedded
- ✅ All source code packaged
- ✅ 72MB self-contained executable

The issue is environment-specific, not a packaging problem.
