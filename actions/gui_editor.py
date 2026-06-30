import functools
import http.server
import os
import socketserver
import sys
import tempfile
import threading
from distutils.dir_util import copy_tree

import webview

from api.api import API
from api.bridge import bridge

# Port of the auxiliary static HTTP server used only in development mode (see
# ``run_gui_editor``). It matches the ``target`` in ``frontend/src/proxy.conf.json``
# so the Angular dev server can proxy ``/bridge.js`` and ``/resources`` to it.
_DEV_STATIC_SERVER_PORT = 8000


class _StaticFilesHandler(http.server.SimpleHTTPRequestHandler):
    """Quiet static handler with permissive CORS and disabled caching.

    Used in development mode to serve the ``bridge.js`` shim and the serialized
    resource files (``/resources/...``) that the GUI requests, so the Angular
    dev server's proxy has something to forward to now that the production
    web view no longer runs an HTTP backend.
    """

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, *args):
        # Keep the console clean; this server is a dev-only helper.
        pass


class _ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _start_static_server(root, port):
    """Start a background static file server rooted at ``root`` on ``port``."""
    handler = functools.partial(_StaticFilesHandler, directory=root)
    httpd = _ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _get_frontend_dist_path():
    """Return path to frontend/dist/gui, works both normally and when bundled by PyInstaller."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'frontend', 'dist', 'gui')


# Compatibility shim served as ``/bridge.js``.
#
# The compiled Angular frontend was built against the Eel client and references
# a global ``eel`` object (``eel.expose``, ``eel['py_func'](args)()``,
# ``eel._websocket``). Instead of rebuilding the frontend, we ship this small
# shim that implements the very same ``eel`` surface on top of the native
# ``window.pywebview.api`` bridge, so the existing frontend keeps working inside
# a native web view.
_EEL_SHIM_JS = r"""
(function () {
  'use strict';

  // JS functions exposed to Python (Python -> JS direction).
  window._bridge_exposed_functions = window._bridge_exposed_functions || {};

  // Invoked from Python through window.evaluate_js to call an exposed JS function.
  window.__eel_call_exposed = function (name, args) {
    var fn = window._bridge_exposed_functions[name];
    if (typeof fn === 'function') {
      try {
        return fn.apply(null, args || []);
      } catch (e) {
        console.error('Error in exposed JS function "' + name + '"', e);
      }
    } else {
      console.warn('No exposed JS function named "' + name + '"');
    }
  };

  // Resolve once the native pywebview bridge is available.
  function whenReady() {
    return new Promise(function (resolve) {
      if (window.pywebview && window.pywebview.api) {
        resolve();
      } else {
        window.addEventListener('pywebviewready', function () { resolve(); }, { once: true });
      }
    });
  }

  // Mirror document.title onto the native window title. In a browser/Chrome-app
  // the tab/window title tracks document.title automatically, but a native web
  // view does not, so we observe changes and forward them to Python.
  function syncTitle() {
    var last = null;
    function push() {
      var t = document.title;
      if (t === last) {
        return;
      }
      last = t;
      whenReady().then(function () {
        window.pywebview.api.set_window_title(t);
      });
    }
    push();
    var titleEl = document.querySelector('title');
    if (titleEl) {
      new MutationObserver(push).observe(titleEl, { childList: true });
    }
    // Fallback: in case the <title> element is replaced wholesale.
    new MutationObserver(function () {
      var el = document.querySelector('title');
      if (el && el !== titleEl) {
        titleEl = el;
        new MutationObserver(push).observe(titleEl, { childList: true });
      }
      push();
    }).observe(document.head || document.documentElement, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncTitle);
  } else {
    syncTitle();
  }

  var bridgeTarget = {
    // eel.expose(fn, name): register a JS function callable from Python.
    expose: function (fn, name) {
      var key = name || fn.name;
      window._bridge_exposed_functions[key] = fn;
    },
    // Dummy websocket: native window lifecycle is handled by pywebview, so the
    // frontend's close-detection loop just needs a truthy object to latch onto.
    _websocket: {},
  };

  // Proxy implementing eel['py_func'](args)() -> Promise semantics.
  window.bridge = new Proxy(bridgeTarget, {
    get: function (target, prop) {
      if (prop in target) {
        return target[prop];
      }
      if (typeof prop !== 'string') {
        return undefined;
      }
      return function () {
        var callArgs = Array.prototype.slice.call(arguments);
        return function () {
          return whenReady().then(function () {
            var api = window.pywebview.api;
            return api[prop].apply(api, callArgs);
          });
        };
      };
    },
  });
})();
"""


def run_gui_editor(file_path=None, dev_server_url=None):
    """
    Run the GUI editor inside a native web view (pywebview).

    Args:
        file_path: Optional path to a file to open
        dev_server_url: When provided, run in development mode: instead of the
            bundled production build, the native window loads this Angular dev
            server URL (``ng serve``, typically ``http://localhost:4200``) with
            developer tools enabled, so the frontend can be edited with live
            reload and debugged directly inside the web view.
    """
    # Directory holding files needed by the GUI: in production the frontend
    # build; in development just the bridge.js shim and serialized resources. In
    # both cases serialized resources are written here by the backend.
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    dev_mode = bool(dev_server_url)
    httpd = None

    if dev_mode:
        # Development mode. The UI itself is served (with live reload and source
        # maps) by the Angular dev server, so we don't copy the production
        # build. We still must serve two things the frontend asks for over
        # HTTP: the `/bridge.js` shim and the serialized `/resources/...` files.
        # A tiny static server on _DEV_STATIC_SERVER_PORT does that, and the
        # dev server's proxy.conf.json forwards `/bridge` and `/resources` to it.
        with open(os.path.join(static_path, 'bridge.js'), 'w', encoding='utf-8') as f:
            f.write(_EEL_SHIM_JS)
        httpd = _start_static_server(static_path, _DEV_STATIC_SERVER_PORT)
        window_url = dev_server_url
    else:
        # Production mode: copy the frontend build and drop the shim alongside.
        src = _get_frontend_dist_path()
        copy_tree(src, static_path)
        # The frontend's index.html loads `/bridge.js`; provide our shim under that name.
        with open(os.path.join(static_path, 'bridge.js'), 'w', encoding='utf-8') as f:
            f.write(_EEL_SHIM_JS)
        window_url = os.path.join(static_path, 'index.html')

    api = API(static_path, file_path)

    window = webview.create_window(
        'NFS Resources Converter',
        url=window_url,
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    # Allow the frontend to drive the native window title (it updates
    # ``document.title`` whenever the opened file/tab changes). The bridge.js shim
    # observes ``document.title`` and calls this through ``window.pywebview.api``.
    def set_window_title(title):
        window.set_title(title)

    # Wire the bridge to the window (Python -> JS) and expose backend endpoints
    # (JS -> Python) collected during API initialization.
    bridge.set_window(window)
    window.expose(set_window_title, *bridge.get_exposed_functions())

    try:
        # ``debug=True`` enables the native web view's developer tools (right
        # click -> Inspect Element), which is what makes frontend debugging
        # possible inside the standalone window.
        webview.start(debug=dev_mode)
    finally:
        if httpd is not None:
            httpd.shutdown()
        static_dir.cleanup()
