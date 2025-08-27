block_cipher = None
a = Analysis(
    ['../../src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('../../src/gui', 'gui'),
        ('../../scripts/rhel_postinst.sh', 'scripts'),
    ],
    hiddenimports=[
        'gui',
        'gui.file_browser',
        'gui.license_agreement',
        'gui.main_window',
        'gui.progress_handler',
        'adb_manager'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='android-file-handler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)