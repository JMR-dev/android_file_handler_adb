#!/bin/bash
set -euo pipefail

poetry lock
poetry install

# Build using the Linux spec so the build is reproducible and uses the project spec
poetry run pyinstaller /home/jasonross/workspace/android_file_handler_adb/scripts/spec_scripts/android-file-handler-linux.spec --distpath dist

# Package into a Linux .deb using fpm
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
VERSION="$(poetry version -s)"
mkdir -p dist
chmod +x dist/android-file-handler
# explicit filename into dist/ (Linux .(binary type))
# change directory into dist and package the binary named 'android-file-handler'
# this ensures the package installs /usr/local/bin/android-file-handler (no extra dist/ prefix)

# Linux
# Prepare packaging layout in a separate directory to avoid clobbering build artifacts
PKG_DIR="pkg_dist"
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/usr/local/bin" \
				 "$PKG_DIR/usr/share/applications" \
				 "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy built binary
cp dist/android-file-handler "$PKG_DIR/usr/local/bin/android-file-handler"
chmod 0755 "$PKG_DIR/usr/local/bin/android-file-handler"

# ...existing code...
# Copy icon if present in repo (fallback optional) — do this before creating the .desktop
ICON_SRC="icon_media/robot_files_256.png"
ICON_DST="$PKG_DIR/usr/share/icons/hicolor/256x256/apps/android-file-handler.png"
ICON_INCLUDED=false
if [ -f "$ICON_SRC" ]; then
  mkdir -p "$(dirname "$ICON_DST")"
  cp "$ICON_SRC" "$ICON_DST"
  chmod 644 "$ICON_DST"
  ICON_INCLUDED=true
else
  echo "Warning: icon not found at $ICON_SRC; packaging without icon"
fi

# Create .desktop file (icon name matches installed icon)
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

# Build the Linux package and include postinst script
PKG_ITEMS=( "usr/local/bin/android-file-handler" "usr/share/applications/android-file-handler.desktop" )
if [ "$ICON_INCLUDED" = true ]; then
  PKG_ITEMS+=( "usr/share/icons/hicolor/256x256/apps/android-file-handler.png" )
fi

# Debug listing
echo "Packaging the following items (relative to $PKG_DIR):"
printf ' - %s\n' "${PKG_ITEMS[@]}"
for p in "${PKG_ITEMS[@]}"; do ls -la "$PKG_DIR/$p" || echo "  (missing) $PKG_DIR/$p"; done

fpm -s dir -t deb -n android-file-handler -v "$VERSION" \
  --architecture amd64 --deb-user root --deb-group root \
  --after-install scripts/linux_postinst.sh \
  -p "dist/android-file-handler_${VERSION}_amd64.deb" -C "$PKG_DIR" "${PKG_ITEMS[@]}"

echo "Package created at dist/android-file-handler_${VERSION}_amd64.deb"