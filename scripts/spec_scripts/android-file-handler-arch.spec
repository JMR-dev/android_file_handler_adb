import os
block_cipher = None
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
SRC_DIR = os.path.normpath(os.path.join(SPEC_DIR, '..', '..', 'src'))
a = Analysis(
    [os.path.join(SRC_DIR, 'main.py')],
    pathex=[SRC_DIR],
    binaries=[],
    datas=[
        (os.path.join(SRC_DIR, 'gui'), 'gui'),
    ],
    hiddenimports=[
        # GUI modules
        'gui',
        'gui.main_window',
        'gui.progress_handler',
        'gui.components',
        'gui.components.file_browser',
        'gui.components.ui_components',
        'gui.dialogs',
        'gui.dialogs.dialog_manager',
        'gui.dialogs.license_agreement',
        'gui.handlers',
        'gui.handlers.animation_handler',
        # Core modules
        'core',
        'core.adb_manager',
        'core.adb_command',
        'core.file_transfer',
        'core.platform_tools',
        'core.platform_utils',
        'core.progress_tracker',
        # Manager modules
        'managers',
        'managers.device_manager',
        'managers.transfer_manager',
        # Utility modules
        'utils',
        'utils.file_deduplication',
        'utils.security_utils'
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