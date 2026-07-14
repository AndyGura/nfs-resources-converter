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
    + collect_submodules('webview')
    + collect_submodules('bottle')
)

datas = (
    collect_data_files('webview')
    + [('frontend/dist/gui', 'frontend/dist/gui')]
)

from version import __version__
from file_associations import FILE_ASSOCIATIONS
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
    icon='frontend/dist/gui/favicon.ico',
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
    icon='frontend/dist/gui/favicon.ico',
    bundle_identifier='com.andygura.nfs-resources-converter',
    info_plist={
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': entry['name'],
                'CFBundleTypeExtensions': [entry['extension']],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            }
            for entry in FILE_ASSOCIATIONS
        ],
    },
)
