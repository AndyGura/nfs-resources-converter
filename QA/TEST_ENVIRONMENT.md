# Test Environment

## The core problem this file solves

This app's GUI cannot be driven by browser automation (e.g. a Chrome-extension-based agent tool)
in any of its normally-documented run modes:

- **macOS / Windows** (any mode, including `--dev`): the GUI is a **native web view**
  (`pywebview`/WKWebView or WebView2) — not a Chrome tab. No browser-automation tool can attach to
  it.
- **Linux, production mode**: opens a dedicated **Chromium app window** (`eel.start(..., mode=
  'chrome-app'-equivalent)`) — needs a real Chrome/Chromium binary, and is still a separate app
  window rather than a normal tab in most automation setups.
- **Linux, `--dev` mode**: opens **no window at all** — it only starts the backend on port 8000
  for the Angular dev server's proxy to reach. This is the one mode where a real browser tab
  pointed at `http://localhost:4200` gets a **fully functional** app (confirmed live — real
  backend calls, real parsing, real rendering), because Linux drives the whole bridge through the
  actual `Eel` Python library over a plain WebSocket, which any browser can speak.

**Conclusion**: to interactively test this GUI with browser automation, run it via the Linux
`--dev` flow, in a real browser, regardless of what platform the person/agent doing the testing is
actually on. The recipe below does this inside Docker so it doesn't require a native Linux
machine.

## Recipe: a drivable instance via Docker

```dockerfile
# Dockerfile
FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
CMD ["bash"]
```

```bash
docker build -t nfs-qa-linux -f Dockerfile .
docker run -d --name nfs-qa -p 4200:4200 -p 8000:8000 \
  -v /path/to/nfs-resources-converter:/app -w /app nfs-qa-linux bash -lc "sleep infinity"

docker exec nfs-qa bash -lc "python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt"
docker exec nfs-qa bash -lc "cd frontend && npm install"

# Backend (Eel dev server on :8000)
docker exec -d nfs-qa bash -lc "/opt/venv/bin/python run.py --dev > /tmp/backend.log 2>&1"
# Frontend (Angular dev server on :4200, proxies /eel and /resources to :8000)
docker exec -d nfs-qa bash -lc "cd frontend && npm run start -- --host 0.0.0.0 --port 4200 > /tmp/ng.log 2>&1"
```

Then point real Chrome (e.g. via the `claude-in-chrome` MCP tools) at `http://localhost:4200/`.
Give the Angular dev server ~15-20s to finish its first compile before navigating.

**Why bind-mount the whole repo instead of copying it in**: `require_file`/`convert` calls made
from inside the container need to resolve paths like `/app/test/golden_corpus/AL1.TRI` — mount the
repo at `/app` and use container-relative paths (`/app/...`) everywhere you type a path into the
GUI, since the browser-side JS has no idea it's talking to a container.

### Driving native Open/Save/Select-Directory dialogs headlessly

These three RPCs (`open_file_dialog`, `save_file_dialog`, `select_directory_dialog`) fall back to
**Tkinter** on Linux (no pywebview window to own a native dialog) — see
`api/endpoints/file_dialog_api.py`. Tkinter needs a real X11 display, which a bare container
doesn't have. Two things you need on top of the base recipe:

```bash
docker exec nfs-qa bash -lc "apt-get update -qq && apt-get install -y -qq xvfb xdotool tk"
docker exec -d nfs-qa bash -lc "Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp"
# restart the backend with DISPLAY set so Tkinter has somewhere to draw:
docker exec -d nfs-qa bash -lc "export DISPLAY=:99; /opt/venv/bin/python run.py --dev > /tmp/backend.log 2>&1"
```

Then, after clicking the real "Open File" (or Browse/Save-as) button in the browser — which opens
the Tk dialog on the virtual display — drive the dialog **from the shell, not the browser** (there
is no way to screenshot/interact with an off-screen X11 window through browser-automation tools):

```bash
docker exec nfs-qa bash -lc "export DISPLAY=:99; xdotool search --name ." # find the dialog window id
docker exec nfs-qa bash -lc "export DISPLAY=:99; xdotool windowfocus <id>; \
  xdotool key ctrl+a; xdotool type --delay 20 '/app/test/golden_corpus/AL1.TRI'; xdotool key Return"
```

`xdotool windowactivate` fails with *"windowmanager claims not to support _NET_ACTIVE_WINDOW"*
under bare Xvfb (no window manager running) — use `windowfocus` instead, which doesn't need one.
Typing a full valid path into Tk's `askopenfilename`/`asksaveasfilename` and pressing Return
submits it directly, without needing to navigate the file browser widget.

**This genuinely round-trips through the real button click and the real backend RPC** — confirmed
live by opening `AL1.TRI` this way and observing the correct window title, real
`/resources/.../terrain_chunk_N.obj` HTTP requests in the backend log, and the real TRI 3D viewer
rendering. This is meaningfully different from (and more trustworthy than) calling
`eel.open_file(path)()` directly from the browser console: that reaches the Python endpoint and
gets real data back, but **does not update the Angular UI**, because the UI-side state
(`openedResourcePath$` etc.) is set by the TypeScript wrapper around that call
(`ApiDelegateImplService`), not by the raw RPC response — bypassing the button bypasses that
wrapper too. Use the real dialog-automation technique above whenever the test needs to assert
anything about UI state, not just backend behavior.

### Known friction with this setup

- `computer` screenshot capture can hang (CDP `Page.captureScreenshot` times out) on a tab that
  has hosted a 3D/WebGL viewer, even after navigating away within the same tab — see
  `KNOWN_ISSUES.md` KI-3. Open a fresh tab rather than retrying.
- `window.ng` (Angular DevTools globals) is unavailable — see `KNOWN_ISSUES.md` KI-2 — so you
  cannot grab a component instance from the console to drive it directly; drive through real
  clicks/`eel.*` RPCs instead.
- Angular Material menus re-measure between renders; a coordinate from a screenshot taken even a
  moment earlier can be stale. Prefer `find` + click-by-ref for menu items.
- The MCP browser tab group can silently disappear after closing what looks like a non-last tab
  (observed once, cause not identified) — if `tabs_context_mcp` reports no group, just recreate
  one with `createIfEmpty: true` and re-navigate.

## Recipe: headless corpus/library testing (no GUI needed at all)

For anything that's really a **parsing library** question rather than a **GUI** question, skip
Docker/Xvfb entirely — run straight on the host:

```bash
./.venv/bin/python - <<'EOF'
import os
from library import require_file

corpus = 'test/golden_corpus'
files = sorted(f for f in os.listdir(corpus) if os.path.isfile(os.path.join(corpus, f)) and not f.startswith('.'))
bad = []
for f in files:
    path = os.path.join(corpus, f)
    try:
        name, block, data = require_file(path)
        if isinstance(data, dict) and 'error_class' in data:
            bad.append((f, 'error-block', data.get('error_text')))
            continue
        block.pack(data, name=name)  # write round-trip
    except Exception as e:
        bad.append((f, type(e).__name__, str(e)))
print(f"{len(files)} files, {len(bad)} problems")
for b in bad:
    print(' -', b)
EOF
```

Every file in `test/golden_corpus/` is expected to be **fully supported** — any failure here is a
regression, full stop (see `test/test_gui_golden_corpus.sh` for the existing manual/visual
counterpart of this same corpus, and `TEST_HISTORY.md` for the last run's result). Some parsers
print internal caught-exception tracebacks to stderr as part of normal control flow (e.g. an enum
fallback path in `library/read_blocks/delegates.py`) — these are noise, not failures; only trust
the script's own `bad` list.

For the much larger, git-ignored `games/` directory (full real game installs — not tracked in git,
personal/local only), see `test/resources/test_games_directory.py` (currently
`@unittest.skip`'d because it's slow — a few minutes over ~8,000 files). **If you add a file from
`games/` to any git-tracked test fixture location (e.g. `test/golden_corpus/`), copy it in
explicitly** — `games/` itself is `.gitignore`d, so referencing a path under it from a checked-in
test would break for anyone else who clones the repo.

## Build/launch reference (for completeness — see root `README.md`/`CLAUDE.md` for full detail)

- Python **3.14**, venv at `./.venv`; `./.venv/bin/python -m unittest` for the backend suite.
- Frontend: `cd frontend && npm install`; `npm run start` (dev server on :4200); `npm run build`
  (production bundle to `frontend/dist/gui`).
- `python run.py` — production GUI; `python run.py --dev [--dev-server URL]` — dev GUI;
  `python run.py convert <in> --out <out>` — headless converter; `python run.py show_settings` —
  print the settings file path; `python run.py uncompress <file>` — decompress a QFS-family file.
- `ffmpeg` and Blender 4+ are optional; their absence degrades specific conversion options rather
  than failing the app (confirmed live, see `APPLICATION_MAP.md`).
- No secrets/credentials are involved anywhere in this app — it's a local file-processing tool.
