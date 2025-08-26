#!/bin/sh
set -e

# Post-installation script for android-file-handler
# - update desktop database if available
# - update icon cache if available
# - ensure binary is executable

# Update desktop database if the utility exists
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi

# Update GTK icon cache for hicolor theme if utility exists
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  if [ -d /usr/share/icons/hicolor ]; then
    gtk-update-icon-cache -t -f /usr/share/icons/hicolor || true
  fi
fi

# Ensure installed binary is executable
if [ -f /usr/local/bin/android-file-handler ]; then
  chmod 0755 /usr/local/bin/android-file-handler || true
fi

exit 0
