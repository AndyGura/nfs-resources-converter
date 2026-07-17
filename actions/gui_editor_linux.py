import glob
import os
import shutil
import sys
import tempfile

import eel

from api.api import API
from api.bridge import bridge
from library.utils.logging_setup import setup_logging

# Port Eel listens on in development mode. It matches the ``target`` in
# ``frontend/src/proxy.conf.json`` so the Angular dev server (``ng serve``, on
# :4200) can proxy ``/eel`` (the ``eel.js`` client + websocket bridge) and
# ``/resources`` (serialized resource previews) to it. Note we use a fixed
# ``8000`` here instead of ``0`` (random port), which is what the production
# window uses, precisely so the dev server's proxy has a stable target.
_DEV_SERVER_PORT = 8000


def _get_frontend_dist_path():
    """Return path to frontend/dist/gui, works both normally and when bundled by PyInstaller."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'frontend', 'dist', 'gui')


def run_gui_editor(file_path=None, dev_server_url=None):
    """
    Run the GUI editor on Linux using Eel (a Chrome/Chromium application window).

    Unlike macOS and Windows (which embed the frontend in a native web view),
    Linux keeps driving the GUI through Eel, exactly as the project did
    historically. Eel serves the compiled Angular build and the serialized
    resources over HTTP and bridges JS <-> Python over a websocket.

    Args:
        file_path: Optional path to a file to open.
        dev_server_url: When provided, run in development mode.

    Debugging on Linux works differently from the native-window platforms.
    There is no window worth inspecting: in development mode we do NOT open the
    Eel/Chrome window at all (``mode=None``). Eel merely acts as the backend web
    server, listening on :data:`_DEV_SERVER_PORT` (8000) so the Angular dev
    server's proxy can reach ``/eel`` and ``/resources``. To debug, ignore Eel's
    own window entirely and open the app in a regular browser tab at the dev
    server URL (``http://localhost:4200``), where you get full DevTools together
    with live reload and source maps.
    """
    # Directory holding all files served to the GUI. Serialized resources are
    # written here by the backend in both modes.
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    dev_mode = bool(dev_server_url)

    # if not dev_mode:
    #     setup_logging(redirect_stdout=True)

    src = _get_frontend_dist_path()
    if not dev_mode:
        # Copy only eel.*.js first so Eel can pick up the client early, then the
        # rest of the production build below (mirrors the original behaviour).
        for f in glob.glob(os.path.join(src, "eel.*.js")):
            shutil.copy2(f, static_path)

    api = API(static_path, file_path)
    # On Linux the shared backend bridge is driven by Eel: this registers every
    # endpoint exposed via ``bridge.expose`` with ``eel.expose`` and routes all
    # Python -> JS calls (``bridge.some_js_func(...)``) through Eel.
    bridge.enable_eel_backend()

    eel.init(static_path)

    if dev_mode:
        # Development mode: the UI is served with live reload by the Angular dev
        # server, so we neither copy the production build nor open a window. Eel
        # only needs to be the backend the dev server proxies to, on a fixed
        # port. Debug in a browser tab at ``dev_server_url`` (see docstring).
        eel.start(port=_DEV_SERVER_PORT, mode=None, block=True)
    else:
        # Production mode: serve the whole frontend build through Eel and open
        # it in a dedicated Chrome/Chromium app window.
        shutil.copytree(src, static_path, dirs_exist_ok=True)

        def on_close(page, sockets):
            os.system("pkill -f 'eel_chrome_profile'")
            sys.exit(0)

        user_data_dir = os.path.join(tempfile.gettempdir(), 'eel_chrome_profile')
        eel.start('index.html',
                  port=0,
                  close_callback=on_close,
                  cmdline_args=[
                      f'--user-data-dir={user_data_dir}',
                      '--no-first-run',
                  ])

    static_dir.cleanup()
