# Arch Linux installation instructions

## Arch Linux installation

These instructions describe how Arch users can install the Linux build produced by the project's `simple-release.yml` workflow. The workflow produces an Arch package named similar to:

```bash
android-file-handler-<VERSION>-1-x86_64.pkg.tar.zst
```

Find that file on the project's GitHub Releases page for the matching version and download it.

### System install (recommended)

Use pacman to install the downloaded package so package scripts run and files are placed in standard system locations:

```bash
# from the directory with the downloaded package
sudo pacman -U ./android-file-handler-1.2.3-1-x86_64.pkg.tar.zst
```

Replace the filename with the actual release artifact you downloaded. After installation you should have:

- Binary: e.g. `/usr/local/bin/android-file-handler`
- Desktop entry: `/usr/share/applications/android-file-handler.desktop`
- Icons: under `/usr/share/icons/hicolor/...`

Launch the app from your application menu (search "Android File Handler") or from a terminal:

```bash
android-file-handler
```

### Non-root / manual install

If you cannot or do not want to install the package system-wide, you can extract and install files into your home directory manually:

1. Extract the package to a temporary folder:

```bash
mkdir -p /tmp/afh_pkg
tar -I zstd -xvf android-file-handler-1.2.3-1-x86_64.pkg.tar.zst -C /tmp/afh_pkg
```

2. Copy the executable and desktop/icon files to your local directories:

```bash
mkdir -p ~/.local/bin ~/.local/share/applications ~/.local/share/icons/hicolor/256x256/apps
cp /tmp/afh_pkg/usr/local/bin/android-file-handler ~/.local/bin/
chmod +x ~/.local/bin/android-file-handler

# Copy desktop entry and icon (paths inside the package may vary)
cp /tmp/afh_pkg/usr/share/applications/android-file-handler.desktop ~/.local/share/applications/
cp /tmp/afh_pkg/usr/share/icons/hicolor/256x256/apps/android-file-handler.png ~/.local/share/icons/hicolor/256x256/apps/
```

3. (Optional) Update desktop and icon caches so the menu picks up the new entry immediately:

```bash
update-desktop-database ~/.local/share/applications || true
gtk-update-icon-cache -t -f ~/.local/share/icons/hicolor || true
```

Now run the app from the menu or with `~/.local/bin/android-file-handler`.

### Verify package contents

To inspect the package contents without installing:

```bash
# list files in the package
pacman -Qlp android-file-handler-1.2.3-1-x86_64.pkg.tar.zst
```

To query package info (after installation):

```bash
pacman -Qi android-file-handler
```

### Troubleshooting

- If the app does not appear in your menu, try logging out/in or run the cache update commands above.
- If icons are missing, ensure the `icons/hicolor/*/apps/android-file-handler.png` entries were copied to the correct theme directories.
- If you manually copied files, ensure `~/.local/bin` is on your PATH; add it to `~/.profile` if necessary:

```bash
export PATH="$HOME/.local/bin:$PATH"
```
