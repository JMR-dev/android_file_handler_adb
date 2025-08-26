#!/bin/bash
set -euo pipefail

poetry lock
poetry install

# Build using the Linux spec so the build is reproducible and uses the project spec
poetry run pyinstaller /home/jasonross/workspace/android_file_handler_adb/scripts/spec_scripts/android-file-handler-linux.spec --distpath dist

# Package into a Debian .deb using fpm
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
VERSION="$(poetry version -s)"
mkdir -p dist
chmod +x dist/android-file-handler
# explicit filename into dist/ (Debian .deb)
# change directory into dist and package the binary named 'android-file-handler'
# this ensures the package installs /usr/local/bin/android-file-handler (no extra dist/ prefix)

# Debian
# Prepare packaging layout in a separate directory to avoid clobbering build artifacts
PKG_DIR="pkg_dist"
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/usr/local/bin" \
				 "$PKG_DIR/usr/share/applications" \
				 "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy built binary
cp dist/android-file-handler "$PKG_DIR/usr/local/bin/android-file-handler"
chmod 0755 "$PKG_DIR/usr/local/bin/android-file-handler"

# Create .desktop file
cat > "$PKG_DIR/usr/share/applications/android-file-handler.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Android File Handler
Comment=Manage Android device files via ADB
Exec=/usr/local/bin/android-file-handler %U
Icon=android-file-handler
Terminal=false
Categories=Utility;Development;
StartupNotify=true
EOF
chmod 644 "$PKG_DIR/usr/share/applications/android-file-handler.desktop"

# Copy icon if present in repo (fallback optional)
if [ -f "assets/icons/android-file-handler-256.png" ]; then
	cp assets/icons/android-file-handler-256.png "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/android-file-handler.png"
	chmod 644 "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/android-file-handler.png"
fi

# Build the Debian package and include postinst script
fpm -s dir -t deb -n android-file-handler -v "$VERSION" \
	--architecture amd64 --prefix /usr/local/bin --deb-user root --deb-group root \
	--after-install scripts/debian/postinst.sh \
	-p "dist/android-file-handler_${VERSION}_amd64.deb" -C "$PKG_DIR" usr/local/bin/android-file-handler usr/share/applications/android-file-handler.desktop usr/share/icons/hicolor/256x256/apps/android-file-handler.png