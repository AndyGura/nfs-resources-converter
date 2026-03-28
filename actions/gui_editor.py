import os
import shutil
import sys
import tempfile

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
    shutil.copytree(_get_frontend_dist_path(), static_path, dirs_exist_ok=True)

    api = API(static_path, file_path)

    if sys.platform == 'darwin':
        try:
            from AppKit import NSApplication, NSObject

            class _AppDelegate(NSObject):
                def application_openFile_(self, app, filename):
                    # check if eel is initialized and running
                    if eel._websockets:
                        eel.open_file(filename)
                    return True

            _app = NSApplication.sharedApplication()
            _delegate = _AppDelegate.alloc().init()
            _app.setDelegate_(_delegate)
        except Exception:
            pass

    eel.init(static_path)
    try:
        eel.start('index.html', port=0)
    except (EnvironmentError, OSError) as e:
        # Fallback to default browser if Chrome/Chromium is not found
        print(f"Failed to start GUI in app mode: {e}")
        print("Retrying in default browser...")
        try:
            eel.start('index.html', port=0, mode='default')
        except Exception as e:
            print(f"Failed to start GUI: {e}")
            sys.exit(1)

    static_dir.cleanup()
