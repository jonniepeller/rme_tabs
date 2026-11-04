# -*- mode: python ; coding: utf-8 -*-
import os


a = Analysis(
    ['app.py'],
    pathex=[os.path.dirname(SPECPATH)],  # rme_tabs.py is in the folder above this spec
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RME Tabs',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RME Tabs',
)
app = BUNDLE(
    coll,
    name='RME Tabs.app',
    icon=None,
    bundle_identifier='com.github.rme-tabs',
    info_plist={'LSUIElement': True},  # menu bar only: no Dock icon or app switcher entry
)
