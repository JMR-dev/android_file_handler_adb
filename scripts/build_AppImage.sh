#!/bin/bash

# Check if an old AppImage exists and remove it
if [ -f "dist/android-file-handler-linux.AppImage" ]; then
    echo "Removing old AppImage..."
    rm -f dist/android-file-handler-linux.AppImage
fi

# Check if required packages are installed
missing_packages=()
for package in fuse libfuse2 curl imagemagick; do
    if ! dpkg -l | grep -q "^ii  $package "; then
        missing_packages+=("$package")
    fi
done

# Only run apt commands if there are missing packages
if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "Installing missing packages: ${missing_packages[*]}"
    sudo apt update
    sudo apt install -y "${missing_packages[@]}"
else
    echo "All required packages are already installed"
fi

mkdir build_temp
cd build_temp || exit 1

# Download portable Python 3.12
echo "Downloading portable Python 3.12..."
PYTHON_VERSION="3.12.5"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"

if ! curl -L "$PYTHON_URL" -o "python-${PYTHON_VERSION}.tgz"; then
    echo "Error: Failed to download Python source"
    exit 1
fi

# For simplicity, let's use a pre-built Python binary instead
echo "Downloading pre-built Python 3.12 for Linux..."
if ! curl -L "https://github.com/indygreg/python-build-standalone/releases/download/20240713/cpython-3.12.4+20240713-x86_64-unknown-linux-gnu-install_only.tar.gz" -o "python-standalone.tar.gz"; then
    echo "Error: Failed to download Python standalone"
    exit 1
fi

# Extract Python
echo "Extracting Python..."
tar -xzf python-standalone.tar.gz

# Rename the extracted directory for consistency
if [ -d "python" ]; then
    mv python python3.12
fi

# Check if extraction was successful
if [ ! -d "python3.12" ]; then
    echo "Error: Python extraction failed"
    exit 1
fi

# 2. Create AppDir structure
mkdir -p AppDir/opt/python3.12
mkdir -p AppDir/usr/share/{applications,icons/hicolor/256x256/apps}
mkdir -p AppDir/opt/android-file-handler

# 3. Copy Python runtime to AppDir
echo "Copying Python runtime..."
if [ -d "python3.12" ]; then
    cp -r python3.12/* AppDir/opt/python3.12/ 2>/dev/null || echo "Failed to copy Python runtime"
else
    echo "Error: Python directory not found"
    exit 1
fi

# Make sure Python binary is executable
chmod +x AppDir/opt/python3.12/bin/python3* 2>/dev/null || true

# 4. Install dependencies using the portable Python
echo "Installing dependencies..."
cd ..

cd build_temp
echo "Installing packages..."
# Install specific packages we need directly
AppDir/opt/python3.12/bin/python3.12 -m pip install requests urllib3 certifi charset-normalizer idna --target AppDir/opt/python3.12/lib/python3.12/site-packages/ --no-deps --force-reinstall

# 5. Copy application source
echo "Copying application source..."
cp -r ../src/* AppDir/opt/android-file-handler/

# Create a launcher script to handle XCB issues
cat > AppDir/opt/android-file-handler/launcher.py << 'EOF'
#!/usr/bin/env python3
"""
Launcher script to handle threading and import issues in AppImage
"""
import os
import sys
import threading

# Critical: Set single-threaded mode BEFORE any imports
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

# XCB environment fixes
os.environ['QT_X11_NO_MITSHM'] = '1'
os.environ['_X11_NO_MITSHM'] = '1'
os.environ['_MITSHM'] = '0'
os.environ['LIBXCB_ALLOW_SLOPPY_LOCK'] = '1'
os.environ['TK_SILENCE_DEPRECATION'] = '1'

def main():
    """Main launcher function with proper thread handling"""
    try:
        # Force single-threaded mode
        threading.current_thread().name = "MainThread"
        
        # Add the application directory to Python path
        app_dir = os.path.dirname(os.path.abspath(__file__))
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        
        # Also ensure packages directory is in path
        packages_dir = os.path.join(os.path.dirname(app_dir), 'python3.12', 'lib', 'python3.12', 'site-packages')
        if os.path.exists(packages_dir) and packages_dir not in sys.path:
            sys.path.insert(0, packages_dir)
        
        # Import tkinter early and set up single-threaded mode
        import tkinter as tk
        
        # Allow default root but ensure single-threaded operation
        # Don't call NoDefaultRoot() - let the app create its own root
        
        try:
            # Import the main application
            import main
            main.main()
            
        except ImportError:
            try:
                # Fallback import path
                from gui.main_window import main as app_main
                app_main()
            except Exception as e:
                print(f"Failed to import application: {e}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Application startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# 6. Create .desktop file
cat > AppDir/android-file-handler.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Android File Handler
Exec=AppRun
Icon=android-file-handler
Categories=Utility;
EOF

# 7. Create AppRun script
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export APPDIR="$HERE"

# Force single-threaded execution
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# Set up Python paths
export PYTHONPATH="$HERE/opt/python3.12/lib/python3.12/site-packages:$HERE/opt/android-file-handler:$PYTHONPATH"
export PATH="$HERE/opt/python3.12/bin:$PATH"

# Python runtime settings
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# XCB and GUI fixes
export QT_X11_NO_MITSHM=1
export _X11_NO_MITSHM=1
export _MITSHM=0
export LIBXCB_ALLOW_SLOPPY_LOCK=1
export TK_SILENCE_DEPRECATION=1

# Additional GUI stability settings
export GDK_BACKEND=x11
export XDG_SESSION_TYPE=x11

# Disable CI mode to prevent threading issues
export CI_MODE=false

# Find Python executable
PYTHON="$HERE/opt/python3.12/bin/python3.12"
if [ ! -f "$PYTHON" ]; then
    PYTHON="$HERE/opt/python3.12/bin/python3"
fi

if [ ! -f "$PYTHON" ]; then
    echo "Error: Python not found in AppImage"
    exit 1
fi

# Change to application directory to ensure proper imports
cd "$HERE/opt/android-file-handler"

# Run with explicit single-threaded mode and ensure Python path is set
PYTHONPATH="$HERE/opt/python3.12/lib/python3.12/site-packages:$HERE/opt/android-file-handler:$PYTHONPATH" exec "$PYTHON" -u launcher.py "$@"
EOF

chmod +x AppDir/AppRun

# 9. Create icon in the correct location for appimagetool
convert -size 256x256 xc:lightblue -pointsize 48 -fill black -gravity center -annotate +0+0 "AFH" AppDir/usr/share/icons/hicolor/256x256/apps/android-file-handler.png 2>/dev/null || true
# Also create icon in AppDir root as appimagetool expects
cp AppDir/usr/share/icons/hicolor/256x256/apps/android-file-handler.png AppDir/android-file-handler.png 2>/dev/null || true

# 10. Download and setup appimagetool
for attempt in 1 2 3; do
    curl -L -o appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage && break
    sleep 5
done
chmod +x appimagetool

# 11. Create AppImage directly in parent dist folder
mkdir -p ../dist
if ! ./appimagetool AppDir ../dist/android-file-handler-linux; then
    echo "AppImage creation failed"
    exit 1
fi

# 12. Clean up (only in local development, not CI/CD)
cd ..
if [ "${CI_CD:-false}" != "true" ]; then
    rm -rf build_temp
fi