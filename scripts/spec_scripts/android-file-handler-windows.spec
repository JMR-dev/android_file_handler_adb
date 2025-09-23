# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
a = Analysis(
    ['../../src/main.py'],
    pathex=['../..'],
    binaries=[],
    datas=[
        ('../../src/gui', 'gui'), 
        ('../../src/platform-tools', 'platform-tools'),
        ('../windows/first_run_install.ps1', 'scripts/windows')
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
        'utils.file_deduplication'
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
    name='android-file-handler-windows',
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
    icon='../../icon_media/robot_files_256.ico',
)