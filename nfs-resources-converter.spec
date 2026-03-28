# -*- mode: python ; coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.abspath('.'))
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

from version import __version__
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
    name=f'nfs-resources-converter-{__version__}',
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
    name=f'nfs-resources-converter-{__version__}',
)
app = BUNDLE(
    coll,
    name=f'NFS Resources Converter-{__version__}.app',
    icon=None,
    bundle_identifier='com.andygura.nfs-resources-converter',
    info_plist={
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'AS4 Audio File',
                'CFBundleTypeExtensions': ['as4'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'ASF Audio File',
                'CFBundleTypeExtensions': ['asf'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'BNK Sound Bank File',
                'CFBundleTypeExtensions': ['bnk'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'CFM Car 3D Model File',
                'CFBundleTypeExtensions': ['cfm'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'COL Track Data File',
                'CFBundleTypeExtensions': ['col'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'EAS Audio File',
                'CFBundleTypeExtensions': ['eas'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'ENV Image Archive File',
                'CFBundleTypeExtensions': ['env'],
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
                'CFBundleTypeName': 'FFN Bitmap Font File',
                'CFBundleTypeExtensions': ['ffn'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'FRD Track File',
                'CFBundleTypeExtensions': ['frd'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'FSH Image Archive File',
                'CFBundleTypeExtensions': ['fsh'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'GEO Car 3D Model File',
                'CFBundleTypeExtensions': ['geo'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'MSK Archive File',
                'CFBundleTypeExtensions': ['msk'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'PBS Car Physics File',
                'CFBundleTypeExtensions': ['pbs'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'PDN Car Characteristic File',
                'CFBundleTypeExtensions': ['pdn'],
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
                'CFBundleTypeName': 'TGV Video File',
                'CFBundleTypeExtensions': ['tgv'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'TRI Track File',
                'CFBundleTypeExtensions': ['tri'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'TRK Track File',
                'CFBundleTypeExtensions': ['trk'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'UV Video File',
                'CFBundleTypeExtensions': ['uv'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'VIV Archive File',
                'CFBundleTypeExtensions': ['viv'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'CRP Geometry File',
                'CFBundleTypeExtensions': ['crp'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
        ],
    },
)
