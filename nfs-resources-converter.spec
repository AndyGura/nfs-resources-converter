# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hidden_imports = (
    collect_submodules('resources')
    + collect_submodules('serializers')
    + collect_submodules('library')
    + collect_submodules('actions')
    + collect_submodules('games')
    + collect_submodules('eel')
    + collect_submodules('bottle')
    + collect_submodules('engineio')
    + collect_submodules('socketio')
)

datas = (
    collect_data_files('eel')
    + [('frontend/dist/gui', 'frontend/dist/gui')]
)

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['viztracer'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nfs-resources-converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='nfs-resources-converter',
)
app = BUNDLE(
    coll,
    name='NFS Resources Converter.app',
    icon=None,
    bundle_identifier='com.andygura.nfs-resources-converter',
    info_plist={
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'FSH Image Archive File',
                'CFBundleTypeExtensions': ['fsh'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'FAM Archive File',
                'CFBundleTypeExtensions': ['fam'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'QFS Compressed image Archive File',
                'CFBundleTypeExtensions': ['qfs'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'TRI Track File',
                'CFBundleTypeExtensions': ['tri'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
        ],
    },
)
