import os
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
    copy_tree(_get_frontend_dist_path(), static_path)

    api = API(static_path, file_path)
    eel.init(static_path)
    eel.start('index.html', port=0)

    static_dir.cleanup()
