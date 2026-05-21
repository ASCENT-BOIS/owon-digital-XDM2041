# PyInstaller spec template for meter_gui
# Generated minimal spec — adjust paths if needed.

# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['src/meter_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('src/etc/udev/rules.d/99-usbtmc.rules', 'etc/udev/rules.d')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='XDM2041',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='XDM2041',
)
