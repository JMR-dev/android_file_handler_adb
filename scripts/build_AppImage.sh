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

curl -L -o python3.13.0-cp313-cp313-linux_x86_64.AppImage https://github.com/niess/python-appimage/releases/download/python3.13/python3.13.0-cp313-cp313-linux_x86_64.AppImage
chmod +x python3.13.0-cp313-cp313-linux_x86_64.AppImage

# 1. Extract Python AppImage first
./python3.13.0-cp313-cp313-linux_x86_64.AppImage --appimage-extract

# 2. Create AppDir structure
mkdir -p AppDir/usr/bin AppDir/usr/share/{applications,icons/hicolor/256x256/apps}
mkdir -p AppDir/usr/lib/python3.13/site-packages

# 3. Copy Python runtime to AppDir first
cp -r squashfs-root/usr/* AppDir/usr/

# 4. Install dependencies using AppImage Python
export PATH="$PWD/squashfs-root/usr/bin:$PATH"
./squashfs-root/usr/bin/python3 -m pip install poetry
poetry install --no-dev

# 5. Copy application source
cp -r src/ AppDir/usr/bin/

# 6. Copy installed packages to AppDir
cp -r .venv/lib/python3.13/site-packages/* AppDir/usr/lib/python3.13/site-packages/ 2>/dev/null || true

# 7. Create AppRun script (after Python is available)
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export APPDIR="$HERE"
export PYTHONPATH="$HERE/usr/lib/python3.13/site-packages:$PYTHONPATH"
exec "$HERE/usr/bin/python3" "$HERE/usr/bin/src/main.py" "$@"
EOF
chmod +x AppDir/AppRun

# 8. Create .desktop file
cat > AppDir/android-file-handler.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Android File Handler
Exec=AppRun
Icon=android-file-handler
Categories=Utility;
EOF

# 9. Create icon
convert -size 256x256 xc:lightblue -pointsize 48 -fill black -gravity center -annotate +0+0 "AFH" AppDir/usr/share/icons/hicolor/256x256/apps/android-file-handler.png || echo "Icon creation skipped"

# 10. Download and setup appimagetool
for attempt in 1 2 3; do
    curl -L -o appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage && break
    echo "Download attempt $attempt failed, retrying..."
    sleep 5
done
chmod +x appimagetool

# 11. Create AppImage directly in dist folder
mkdir -p dist
if ! ./appimagetool AppDir dist/android-file-handler-linux; then
    echo "AppImage creation failed"
    exit 1
fi