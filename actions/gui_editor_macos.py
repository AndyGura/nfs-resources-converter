import functools
import http.server
import os
import socketserver
import sys
import tempfile
import threading
import shutil

import webview

from api.api import API
from api.bridge import bridge
from library.utils.logging_setup import setup_logging

# Port of the auxiliary static HTTP server used only in development mode (see
# ``run_gui_editor``). It matches the ``target`` in ``frontend/src/proxy.conf.json``
# so the Angular dev server can proxy ``/eel.js`` and ``/resources`` to it.
_DEV_STATIC_SERVER_PORT = 8000


class _StaticFilesHandler(http.server.SimpleHTTPRequestHandler):
    """Quiet static handler with permissive CORS and disabled caching.

    Used in development mode to serve the ``eel.js`` shim and the serialized
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


_pointer_lock_patched = False

# Whether the macOS "open document" Apple Event handler has been installed on
# pywebview's application delegate (see ``_enable_macos_open_file``).
_open_file_patched = False

# The API instance backing the currently running GUI window. Set by
# ``run_gui_editor`` so the macOS open-file handler can route files the OS hands
# to the app into the running editor.
_current_api = None

# Byte offset of the ``invoke`` function pointer inside an Objective-C block
# (``struct Block_literal``) on 64-bit platforms: isa(8) + flags(4) + reserved(4).
_BLOCK_INVOKE_OFFSET = 16


def _call_bool_completion_block(block_obj, value):
    """Invoke an Objective-C ``void (^)(BOOL)`` block directly via its ABI.

    WebKit hands the pointer-lock completion handler to us as a block. Under
    pyobjc 11 such a block can only be *called* from Python if it carries a
    readable type signature; WebKit's ``makeBlockPtr`` block does not expose one
    that pyobjc can read, so ``block(True)`` raises ``TypeError: cannot call
    block without a signature`` (and, being uncaught across the Objective-C
    boundary, crashes the whole app). ``registerMetaDataForSelector`` does not
    help here either — it cannot retrofit a signature onto a signature-less
    incoming block.

    Instead we call the block the way the Objective-C runtime does: every block
    stores its ``invoke`` function pointer at a fixed offset in its memory
    layout, so we read that pointer and call it directly through ctypes, passing
    the block itself as the implicit first argument and the ``BOOL`` as the
    second. This sidesteps pyobjc's signature requirement entirely.
    """
    import ctypes
    import objc

    block_ptr = objc.pyobjc_id(block_obj)
    invoke_addr = ctypes.c_void_p.from_address(block_ptr + _BLOCK_INVOKE_OFFSET).value
    invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_bool)(invoke_addr)
    invoke(block_ptr, value)


def _enable_macos_pointer_lock():
    """Re-enable the Pointer Lock API inside the macOS native web view.

    pywebview uses a ``WKWebView`` on macOS, and WebKit only grants
    ``element.requestPointerLock()`` when the web view's UI delegate implements
    the private ``_webViewDidRequestPointerLock:completionHandler:`` selector and
    invokes the supplied completion handler with ``YES``. If the delegate does
    not implement it WebKit immediately denies the request (see
    ``UIDelegate::UIClient::requestPointerLock`` in WebKit), which is exactly
    what happened after migrating away from the Chrome app: the 3D viewers
    (``obj-viewer``, ``frd``/``tri``/``trk`` maps) request pointer lock for their
    free-fly camera and silently got denied.

    Note that the older ``_webViewRequestPointerLock:`` selector is *not* usable:
    current WebKit calls it and then unconditionally denies the request
    (``completionHandler(false)``), so only the completion-handler variant can
    grant pointer lock.

    pywebview's shared delegate class (``BrowserView.BrowserDelegate``) does not
    implement this selector, so here we extend it (via an Objective-C category)
    with a granting ``_webViewDidRequestPointerLock:completionHandler:`` and a
    no-op ``_webViewDidLosePointerLock:``. This must run before pywebview creates
    the window (i.e. before ``webview.start()``), because WebKit caches which
    delegate selectors are available when the UI delegate is assigned.

    (The related macOS "funk" beep that WebKit emits for held keyboard keys while
    the pointer is locked is suppressed in JavaScript from the eel.js shim by
    calling ``preventDefault`` on key events while ``document.pointerLockElement``
    is set, which is far more robust than trying to intercept the native
    responder chain: the actual first responder is an internal ``WKContentView``,
    not pywebview's ``WebKitHost``, so a native ``noResponderFor:`` override never
    fires for those key events.)

    The whole thing is macOS-only and best-effort: on Windows (WebView2/Chromium)
    and Linux (WebKitGTK) pointer lock already works, and any failure here must
    never prevent the GUI from starting.
    """
    global _pointer_lock_patched
    if _pointer_lock_patched or sys.platform != 'darwin':
        return
    try:
        import objc
        from webview.platforms import cocoa

        browser_delegate_cls = cocoa.BrowserView.BrowserDelegate

        # pyobjc requires a category's class name to match the class it extends.
        class BrowserDelegate(objc.Category(browser_delegate_cls)):
            def _webViewDidRequestPointerLock_completionHandler_(self, webview_, handler):
                # Grant every pointer lock request. The web view is the user's
                # own standalone application window, so there is no untrusted
                # content to guard against, and the OS/WebKit still let the user
                # escape the lock with the Esc key. The completion handler is a
                # signature-less block, so it must be invoked through its ABI
                # rather than called as a normal pyobjc block (which would raise
                # "cannot call block without a signature" and crash the app).
                try:
                    _call_bool_completion_block(handler, True)
                except Exception:
                    pass

            def _webViewDidLosePointerLock_(self, webview_):
                pass

        _pointer_lock_patched = True
    except Exception:
        # Pointer lock is a nice-to-have for the 3D viewers; never let a failure
        # to patch the delegate stop the application from launching.
        pass


def _is_own_launch_path(path):
    """Return whether ``path`` is the app's own executable/script, not a document.

    On macOS AppKit fires ``application:openFile:`` once at launch with the path
    of the running program itself (``sys.argv[0]`` — the ``run.py`` script when
    run from source, or the bundle's executable when frozen). That is not a file
    the user asked to open, so it must be ignored to avoid trying to parse the
    executable and failing on a plain, argument-less launch.
    """
    try:
        target = os.path.realpath(path)
    except Exception:
        return False
    candidates = []
    for candidate in (sys.argv[0] if sys.argv else None, sys.executable):
        if candidate:
            try:
                candidates.append(os.path.realpath(candidate))
            except Exception:
                pass
    return target in candidates


def _handle_macos_open_file(path):
    """Route a file the OS asked the app to open into the running GUI.

    Called from the macOS ``application:openFile(s):`` delegate methods (see
    ``_enable_macos_open_file``). Two situations are handled:

    * The app was *launched* by opening the file: the delegate fires before the
      Angular frontend has loaded, so we can't push anything to it yet. We stash
      the path as the ``initial_file_path`` and let ``FileAPI.on_angular_ready``
      open it once the frontend signals it is ready.
    * The app was *already running*: the frontend is ready, so we open the file
      live via the same ``open_arg_file`` JS hook used for the initial file, and
      bring the window to the front.
    """
    api = _current_api
    if not path or api is None:
        return
    path = str(path)
    # macOS delivers a spurious ``application:openFile:`` at launch whose path is
    # the running executable/script itself (``sys.argv[0]``), not a document the
    # user asked to open. Ignore it so a plain launch (``python run.py`` or
    # double-clicking the app) shows the landing page instead of trying to parse
    # the executable and failing.
    if _is_own_launch_path(path):
        return
    if bridge.frontend_ready.is_set():
        try:
            bridge.open_arg_file(path)
            # Bring the app forward: the user just asked to open a document, so
            # the existing window should come to focus.
            import AppKit
            AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            # If the live push fails for any reason, fall back to the buffered
            # path so at least the next readiness signal picks it up.
            api.initial_file_path = path
    else:
        api.initial_file_path = path


def _enable_macos_open_file():
    """Handle the macOS "open document" Apple Event so Finder can open files.

    The app registers document types (``tri``, ``fsh``, ``viv`` …) in its
    ``Info.plist``, so double-clicking such a file in Finder, or using "Open
    With", tells macOS to launch/forward it to this app. Unlike other platforms,
    macOS does *not* pass the file path on ``argv``: it sends the
    ``kAEOpenDocuments`` ("odoc") Apple Event, which the application delegate
    must handle via ``application:openFile:`` / ``application:openFiles:``.

    pywebview's shared application delegate (``BrowserView.AppDelegate``) does
    not implement these selectors, so with no handler macOS reports
    "<app> cannot open files in the <type> format" even though the app supports
    them. Here we extend that delegate (via an Objective-C category) with the
    two selectors and forward the paths into the running GUI.

    Must run before pywebview creates the window (i.e. before
    ``webview.start()``), because the delegate instance is created and assigned
    to the shared application during window creation. It is macOS-only and
    best-effort: any failure here must never prevent the GUI from starting.
    """
    global _open_file_patched
    if _open_file_patched or sys.platform != 'darwin':
        return
    try:
        import objc
        from webview.platforms import cocoa

        app_delegate_cls = cocoa.BrowserView.AppDelegate

        # pyobjc requires a category's class name to match the class it extends.
        class AppDelegate(objc.Category(app_delegate_cls)):
            def application_openFile_(self, app, filename):
                try:
                    _handle_macos_open_file(filename)
                except Exception:
                    pass
                return True

            def application_openFiles_(self, app, filenames):
                try:
                    for filename in filenames:
                        _handle_macos_open_file(filename)
                finally:
                    # NSApplicationDelegateReplySuccess == 0. Always reply so the
                    # OS does not consider the open request as failed/timed out.
                    try:
                        app.replyToOpenOrPrint_(0)
                    except Exception:
                        pass

        _open_file_patched = True
    except Exception:
        # Never let a failure to patch the delegate stop the application from
        # launching; the GUI still works when files are opened from within it.
        pass


def _get_frontend_dist_path():
    """Return path to frontend/dist/gui, works both normally and when bundled by PyInstaller."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'frontend', 'dist', 'gui')


# Compatibility shim served as ``/eel.js``.
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
  window._eel_exposed_functions = window._eel_exposed_functions || {};

  // Invoked from Python through window.evaluate_js to call an exposed JS function.
  window.__eel_call_exposed = function (name, args) {
    var fn = window._eel_exposed_functions[name];
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

  // Suppress the macOS system "funk" beep while the pointer is locked.
  //
  // The 3D viewers (obj-viewer, frd/tri/trk maps) lock the pointer for their
  // free-fly WASD camera and handle the keys themselves, but they do not call
  // preventDefault on the key events. On macOS the native web view (WKWebView)
  // then forwards each "unhandled" key to the AppKit responder chain, which
  // rings the system bell on every key repeat while a key (e.g. W) is held.
  //
  // Calling preventDefault marks the key event as handled, so WebKit no longer
  // passes it to the native responder chain and the beep stops. preventDefault
  // does not stop propagation, so the engine's own key listeners still run and
  // movement keeps working. We skip events carrying Cmd/Ctrl so application
  // shortcuts (copy/paste/quit/close) are never swallowed, and only act while a
  // pointer lock is actually active so normal typing is completely unaffected.
  function suppressPointerLockBeep(e) {
    if (document.pointerLockElement && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
    }
  }
  window.addEventListener('keydown', suppressPointerLockBeep, true);
  window.addEventListener('keyup', suppressPointerLockBeep, true);

  var bridgeTarget = {
    // eel.expose(fn, name): register a JS function callable from Python.
    expose: function (fn, name) {
      var key = name || fn.name;
      window._eel_exposed_functions[key] = fn;
    },
    // Dummy websocket: native window lifecycle is handled by pywebview, so the
    // frontend's close-detection loop just needs a truthy object to latch onto.
    _websocket: {},
  };

  // Proxy implementing eel['py_func'](args)() -> Promise semantics.
  window.eel = new Proxy(bridgeTarget, {
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
    # build; in development just the eel.js shim and serialized resources. In
    # both cases serialized resources are written here by the backend.
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    dev_mode = bool(dev_server_url)
    httpd = None

    if not dev_mode:
        setup_logging(redirect_stdout=True)

    if dev_mode:
        # Development mode. The UI itself is served (with live reload and source
        # maps) by the Angular dev server, so we don't copy the production
        # build. We still must serve two things the frontend asks for over
        # HTTP: the `/breelidge.js` shim and the serialized `/resources/...` files.
        # A tiny static server on _DEV_STATIC_SERVER_PORT does that, and the
        # dev server's proxy.conf.json forwards `/eel` and `/resources` to it.
        with open(os.path.join(static_path, 'eel.js'), 'w', encoding='utf-8') as f:
            f.write(_EEL_SHIM_JS)
        httpd = _start_static_server(static_path, _DEV_STATIC_SERVER_PORT)
        window_url = dev_server_url
    else:
        # Production mode: copy the frontend build and drop the shim alongside.
        src = _get_frontend_dist_path()
        shutil.copytree(src, static_path, dirs_exist_ok=True)
        # The frontend's index.html loads `/eel.js`; provide our shim under that name.
        with open(os.path.join(static_path, 'eel.js'), 'w', encoding='utf-8') as f:
            f.write(_EEL_SHIM_JS)
        window_url = os.path.join(static_path, 'index.html')

    api = API(static_path, file_path)
    # Expose the API to the macOS open-file handler so files the OS hands to the
    # app (Finder double-click / "Open With") can be routed into this window.
    global _current_api
    _current_api = api

    window = webview.create_window(
        'NFS Resources Converter',
        url=window_url,
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    # Allow the frontend to drive the native window title (it updates
    # ``document.title`` whenever the opened file/tab changes). The eel.js shim
    # observes ``document.title`` and calls this through ``window.pywebview.api``.
    def set_window_title(title):
        window.set_title(title)

    # Wire the bridge to the window (Python -> JS) and expose backend endpoints
    # (JS -> Python) collected during API initialization.
    bridge.set_window(window)
    window.expose(set_window_title, *bridge.get_exposed_functions())

    # Restore pointer lock support (used by the 3D viewers' free-fly camera),
    # which the native macOS web view denies by default. Must run before the
    # window is created by webview.start().
    _enable_macos_pointer_lock()

    # Handle the macOS "open document" Apple Event so double-clicking a
    # registered file in Finder (or "Open With") actually opens it. Must also
    # run before the window is created by webview.start().
    _enable_macos_open_file()

    try:
        # ``debug=True`` enables the native web view's developer tools (right
        # click -> Inspect Element), which is what makes frontend debugging
        # possible inside the standalone window.
        webview.start(debug=dev_mode)
    finally:
        if httpd is not None:
            httpd.shutdown()
        static_dir.cleanup()
