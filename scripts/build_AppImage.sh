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
curl -L -o python3.12.7-cp312-cp312-linux_x86_64.AppImage https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.7-cp312-cp312-linux_x86_64.AppImage
chmod +x python3.12.7-cp312-cp312-linux_x86_64.AppImage

# 1. Extract Python AppImage first
./python3.12.7-cp312-cp312-linux_x86_64.AppImage --appimage-extract

# 2. Create AppDir structure
mkdir -p AppDir/usr/bin AppDir/usr/share/{applications,icons/hicolor/256x256/apps}
mkdir -p AppDir/usr/lib/python3.12/site-packages

# 3. Copy Python runtime to AppDir first
if [ -d "squashfs-root/usr" ]; then
    cp -r squashfs-root/usr/* AppDir/usr/ 2>/dev/null || echo "Failed to copy Python runtime"
else
    echo "Error: Python AppImage extraction failed"
    exit 1
fi

# Alternative copy method if the first failed
if [ ! -f "AppDir/usr/bin/python3" ] && [ ! -f "AppDir/usr/bin/python" ]; then
    # Try copying from different possible locations
    if [ -d "squashfs-root/opt/python3.12" ]; then
        mkdir -p AppDir/opt/
        cp -r squashfs-root/opt/* AppDir/opt/ 2>/dev/null || true
    fi
    
    # Try to find and copy any Python executable
    find squashfs-root/ -name "python*" -type f -executable 2>/dev/null | while read python_file; do
        target_dir="AppDir/usr/bin"
        mkdir -p "$target_dir"
        cp "$python_file" "$target_dir/" 2>/dev/null || true
    done
    
    # If still no Python, try using system Python as fallback
    if [ ! -f "AppDir/usr/bin/python3" ] && [ ! -f "AppDir/usr/bin/python" ]; then
        which python3.12 >/dev/null && cp "$(which python3.12)" AppDir/usr/bin/python3
        which python3 >/dev/null && cp "$(which python3)" AppDir/usr/bin/python3
    fi
fi

# 4. Go back to project root and install dependencies using system poetry
cd ..
poetry lock  # Update lock file if needed
poetry install --no-dev

# 4.5. Ensure essential packages are available by installing them directly
cd build_temp

# Install essential packages using system python
python3 -m pip install requests --target AppDir/usr/lib/python3.12/site-packages/ --no-deps --quiet 2>/dev/null || true

# Install project dependencies
python3 -c "
import subprocess
import sys
packages = ['requests', 'urllib3', 'certifi', 'charset-normalizer', 'idna']
for pkg in packages:
    subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '--target', 'AppDir/usr/lib/python3.12/site-packages/', '--quiet'], check=False)
"

cd ..

# 5. Copy application source to a separate app directory
mkdir -p build_temp/AppDir/opt/android-file-handler
cp -r src/ build_temp/AppDir/opt/android-file-handler/

# 6. Also copy platform-tools if it exists
if [ -d "src/platform-tools" ]; then
    cp -r src/platform-tools/ build_temp/AppDir/opt/android-file-handler/
fi

# 7. Copy installed packages to AppDir
# Find where Poetry actually installed packages
VENV_PATH=$(poetry env info --path)

if [ -d "$VENV_PATH/lib" ]; then
    # Find the actual site-packages directory
    SITE_PACKAGES=$(find "$VENV_PATH/lib" -name "site-packages" -type d | head -1)
    if [ -d "$SITE_PACKAGES" ]; then
        cp -r "$SITE_PACKAGES"/* build_temp/AppDir/usr/lib/python3.12/site-packages/ 2>/dev/null || true
    fi
fi

# Fallback to .venv directory
if [ -d ".venv/lib/python3.12/site-packages" ]; then
    cp -r .venv/lib/python3.12/site-packages/* build_temp/AppDir/usr/lib/python3.12/site-packages/ 2>/dev/null || true
else
    # Try to find site-packages for any Python version
    for py_dir in .venv/lib/python*/site-packages; do
        if [ -d "$py_dir" ]; then
            cp -r "$py_dir"/* build_temp/AppDir/usr/lib/python3.12/site-packages/ 2>/dev/null || true
            break
        fi
    done
    
    if [ ! -d "build_temp/AppDir/usr/lib/python3.12/site-packages/requests" ]; then
        # Alternative: Use poetry to install directly into the AppImage
        poetry export -f requirements.txt --output requirements.txt --without-hashes
        if [ -f requirements.txt ]; then
            # Use the AppImage Python to install packages directly
            cd build_temp
            ../squashfs-root/usr/bin/python3 -m pip install -r ../requirements.txt --target AppDir/usr/lib/python3.12/site-packages/ 2>/dev/null || true
            cd ..
        fi
    fi
fi

# Verify critical packages are present
if [ -d "build_temp/AppDir/usr/lib/python3.12/site-packages/requests" ]; then
    true  # requests package found
else
    # Install requests as last resort
    cd build_temp
    curl -s https://files.pythonhosted.org/packages/9d/be/10918a2eac4ae9f02f6cfe6414b7a155ccd8f7f9d4380d62fd5b955065c3/requests-2.31.0-py3-none-any.whl -o requests.whl
    unzip -q requests.whl -d AppDir/usr/lib/python3.12/site-packages/ 2>/dev/null || true
    rm -f requests.whl
    cd ..
fi

# 7. Go back to build directory
cd build_temp

# 8. Install requests package directly into site-packages using pip
# Ensure requests package is available (critical for our app)
pip install --target="build_temp/AppDir/usr/lib/python3.12/site-packages" requests urllib3 2>/dev/null || true

# Ensure Python executables have correct permissions
find AppDir/usr/bin/ -name "python*" -type f -exec chmod +x {} \; 2>/dev/null || true

# 9. Create .desktop file
cat > AppDir/android-file-handler.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Android File Handler
Exec=AppRun
Icon=android-file-handler
Categories=Utility;
EOF

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