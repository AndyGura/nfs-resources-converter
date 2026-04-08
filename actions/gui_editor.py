import glob
import os
import shutil
import sys
import tempfile
from distutils.dir_util import copy_tree

import eel

from api.api import API


def _get_frontend_dist_path():
    """Return path to frontend/dist/gui, works both normally and when bundled by PyInstaller."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'frontend', 'dist', 'gui')


def run_gui_editor(file_path=None):
    """
    Run the GUI editor with the new API structure.

    Args:
        file_path: Optional path to a file to open
    """
    # Create directory for all files needed by GUI
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    src = _get_frontend_dist_path()
    # copy only eel.*.js
    for f in glob.glob(os.path.join(src, "eel.*.js")):
        shutil.copy2(f, static_path)
    api = API(static_path, file_path)
    eel.init(static_path)
    # copy all files
    copy_tree(src, static_path)
    eel.start('index.html', port=0)

    static_dir.cleanup()
