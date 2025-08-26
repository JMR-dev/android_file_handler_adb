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
fpm -s dir -t deb -n android-file-handler -v "$VERSION" \
--architecture amd64 --prefix /usr/local/bin --deb-user root --deb-group root \
-p "dist/android-file-handler_${VERSION}_amd64.deb" -C dist android-file-handler