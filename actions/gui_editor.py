import tempfile
from distutils.dir_util import copy_tree

import eel

from api.api import API


def run_gui_editor(file_path=None):
    """
    Run the GUI editor with the new API structure.

    Args:
        file_path: Optional path to a file to open
    """
    # Create directory for all files needed by GUI
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    copy_tree('frontend/dist/gui', static_path)

    api = API(static_path, file_path)
    eel.init(static_path)
    eel.start('index.html', port=0)

    static_dir.cleanup()
