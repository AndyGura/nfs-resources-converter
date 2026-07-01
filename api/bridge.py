"""
Native webview bridge replacing Eel.

This module provides a tiny compatibility layer that mimics the small subset of
the Eel API used across the backend, but is implemented on top of a native
``pywebview`` window instead of a Chrome/Chrome-app instance.

Two directions are supported:

* JS -> Python: backend code registers callables via ``bridge.expose(func)``.
  Those callables are later attached to the pywebview window (see
  ``actions/gui_editor.py``) and become available as
  ``window.pywebview.api.<func_name>`` on the frontend.

* Python -> JS: any other attribute access on the bridge (e.g.
  ``bridge.open_arg_file(path)``) returns a callable that invokes the matching
  JS function previously registered on the frontend via the ``eel`` shim
  (``window.__eel_call_exposed``).

Keeping the public surface identical to the previously used ``eel`` module
(``expose`` + attribute-style JS calls) allows the rest of the backend to be
migrated by only changing the import.
"""

import json
import threading


class _WebviewBridge:
    """Eel-compatible bridge backed by a native pywebview window."""

    def __init__(self):
        # Python callables exposed to the frontend (JS -> Python).
        self._exposed = {}
        # The native pywebview window, set once it is created.
        self._window = None
        # The Eel module, set on platforms (Linux) that drive the GUI through
        # Eel instead of a native pywebview window. When set, the bridge routes
        # ``expose`` and Python -> JS calls through Eel (see
        # :meth:`enable_eel_backend`).
        self._eel = None
        # Set once the frontend has signalled that it is ready (see
        # ``FileAPI.on_angular_ready``). Used to decide whether a file opened
        # via the OS (e.g. a macOS "open document" Apple Event) can be pushed to
        # the frontend right away or has to wait for it to load first.
        self.frontend_ready = threading.Event()

    def expose(self, func):
        """Register a Python callable to be callable from JS.

        Mirrors ``eel.expose``. The function is stored by its ``__name__`` and
        is wired into the pywebview window by the GUI launcher.
        """
        self._exposed[func.__name__] = func
        if self.__dict__.get('_eel') is not None:
            self._eel.expose(func)
        return func

    def get_exposed_functions(self):
        """Return all Python callables registered via :meth:`expose`."""
        return list(self._exposed.values())

    def set_window(self, window):
        """Attach the native pywebview window used for Python -> JS calls."""
        self._window = window

    def enable_eel_backend(self):
        """Drive this bridge through the Eel library instead of pywebview.

        Used on Linux, where the GUI keeps running on Eel (a Chrome/Chromium
        app window) as it did historically. Every callable already registered
        via :meth:`expose` is handed to ``eel.expose`` and the bridge is flipped
        into "eel mode", so subsequent Python -> JS attribute calls
        (``bridge.some_js_func(...)``) are dispatched through Eel rather than a
        pywebview window.
        """
        import eel
        self._eel = eel
        for func in self._exposed.values():
            eel.expose(func)

    def get_window(self):
        """Return the native pywebview window, or ``None`` if not yet created.

        Used by endpoints that need to open native dialogs (file/folder pickers)
        which must go through the web view's main GUI thread instead of a
        secondary toolkit such as Tk.
        """
        return self.__dict__.get('_window')

    def __getattr__(self, name):
        """Return a callable that invokes a JS function (Python -> JS).

        This is only triggered for attributes that are not regular members of
        the bridge, which matches Eel's behaviour where ``eel.some_js_func(...)``
        calls the JS function exposed under that name.
        """

        def _call_js(*args):
            eel_backend = self.__dict__.get('_eel')
            if eel_backend is not None:
                return getattr(eel_backend, name)(*args)
            window = self.__dict__.get('_window')
            if window is None:
                return None
            payload = json.dumps(list(args))
            return window.evaluate_js(
                f'window.__eel_call_exposed({json.dumps(name)}, {payload})'
            )

        return _call_js


# Singleton bridge instance imported across the backend as a drop-in for ``eel``.
bridge = _WebviewBridge()
