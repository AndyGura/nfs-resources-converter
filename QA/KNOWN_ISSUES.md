# Known Issues

Classification used below: **Confirmed bug**, **Suspected bug**, **Expected behavior**, or
**Unclear / needs product decision**. Don't reclassify a "Suspected" to "Expected" without actual
evidence of intent — leave it Suspected/Unclear instead.

---

## KI-1 — Convert Files fails in Linux `--dev` mode: `AttributeError: module 'eel' has no attribute 'update_conversion_progress'`

**Status**: Confirmed bug (reproducible), but **scope is narrower than "the Converter is broken"**
— see Root cause. Severity: **P2** (breaks a documented contributor workflow; does not obviously
reach packaged/production builds — not yet verified against one, see Follow-up).

**Reproduction** (see `TEST_ENVIRONMENT.md` for the full setup):
1. Run the app per the README's Linux dev-mode instructions: `ng serve` (frontend) + `python
   run.py --dev` (backend), open `http://localhost:4200` in a real browser.
2. Tools → Converter to common formats.
3. Fill Input Directory and Output Directory with any valid paths.
4. Click **Convert Files**.

**Actual**: The dialog does nothing visible (no progress bar, no snackbar); the output directory
stays empty (0 files converted). Backend log shows:
```
ERROR: File "api/endpoints/conversion_api.py", line 139, in convert_files
ERROR:     bridge.update_conversion_progress(0, self.total_files)
ERROR: File "api/bridge.py", line 102, in _call_js
ERROR:     return getattr(eel_backend, name)(*args)
ERROR: AttributeError: module 'eel' has no attribute 'update_conversion_progress'
```
The exception is caught by `convert_files`'s outer `try/except` and returned as
`{"success": False, "error": "..."}`, so **zero files get converted** — this aborts before the
file loop even starts (the failing call is the very first progress push, at `current_progress =
0`).

**Root cause** (traced, not just observed): the real `eel` Python package learns which JS function
names it may call (`open_arg_file`, `update_conversion_progress`, `on_append_changes` — all
registered via `eel.expose(...)` inside `api-delegate-impl.service.ts`) by **statically scanning
the JS files under the directory passed to `eel.init(...)`** at startup — it does not learn them
via any runtime handshake. `actions/gui_editor_linux.py`'s **production** path works around this
correctly: before calling `eel.init(static_path)`, it explicitly copies just the lazy `eel.*.js`
chunk (the one containing those `eel.expose()` calls) into `static_path`, so the scan finds them,
*then* copies the rest of the build. In **dev mode**, that early-copy step is skipped entirely
(`if not dev_mode: <copy eel.*.js>` — dev mode takes neither branch), so `eel.init()` scans an
empty temp directory and never learns any JS-exposed function name. Any Python→JS *push* call
(the three names above) will fail this way in dev mode; anything that instead relies on the
`eel.js` runtime object being present in the browser page is unaffected in the same code path,
since that's the *client's* copy of eel.js, unrelated to the Python-side static scan just described.
This is also consistent with why it doesn't affect macOS/Windows dev mode at all: those platforms
never touch the real `eel` package — their `evaluate_js`-based shim (`api/bridge.py`) looks up the
JS function by name in a plain JS object at call time, with no Python-side pre-registration step.

**Blast radius (from the same root cause, not yet individually reproduced)**:
- `update_conversion_progress` — confirmed above; breaks Convert Files entirely in this mode.
- `open_arg_file` — used to push an OS-level "open this file" event into an already-running
  session (e.g. macOS Finder "Open With"). Likely unreachable in the Linux dev flow anyway (no
  OS file-association event fires against a bare `ng serve`+backend), so probably latent rather
  than practically hit — **Unknown**, not tested.
- `on_append_changes` — pushes externally-appended change entries to the frontend. Trigger path
  not identified this pass — **Unknown** whether/when this fires in normal use, so severity of this
  half of the bug is unclear.

**Follow-up needed** (not done this pass — flag for whoever picks this up):
- Verify whether a **production** Linux build (`ng build` + `python run.py`, no `--dev`) also hits
  this — the code reading above says it shouldn't (the early `eel.*.js` copy should make
  `update_conversion_progress` resolve correctly), but this was reasoned from source, not observed
  end-to-end (doing so needs a real/headless Chromium in the test environment, which the Docker
  setup in `TEST_ENVIRONMENT.md` doesn't currently include).
- Verify Convert Files actually works end-to-end on macOS/Windows dev mode (`--dev`, native
  webview) — expected to work per the root-cause analysis (no static-scan dependency there), not
  independently confirmed.
- If confirmed production-safe, the fix is dev-mode-only: mirror production's early `eel.*.js`
  copy step (or an equivalent pre-registration) in the `dev_mode` branch of
  `actions/gui_editor_linux.py`.

---

## KI-2 — `environment.production` is hardcoded `true` in both Angular environment files; no dev-mode override exists

**Status**: Suspected bug (behavior is very likely unintentional, but no direct evidence of
intent either way — filing as Suspected, not Confirmed).

**Observation**: `frontend/src/environments/environment.ts` (the file Angular's **development**
build configuration uses as-is — only the **production** configuration's `fileReplacements` swaps
in `environment.prod.ts`) contains `production: true`. `environment.prod.ts` also contains
`production: true`. There is no `environment.development.ts` or equivalent providing `production:
false` for the dev build. Consequence, Confirmed (live): `window.ng` (Angular's dev-mode debug
global, `ng.getComponent()` etc.) is unavailable even under `ng serve`, consistent with the app
always running as if in production mode regardless of build configuration.

**Impact on the product itself**: `AppComponent`'s dev-only **"Changes (n)"** staged-changes debug
menu (`@if (!isProduction)` in `app.component.html`) can never render, in *any* build — see
`UI_MAP.md`. Whatever this menu was meant to help debug currently has no UI path to it at all.

**Impact on testing**: Angular DevTools-style console introspection (`window.ng.getComponent(...)`)
is unavailable for driving the app from a browser console; use the app's own exposed `eel.*` RPCs
or real UI interaction instead (see `TEST_ENVIRONMENT.md`).

**Not yet done**: confirming whether this is a known/accepted tradeoff (e.g. debug menu considered
abandoned/not worth wiring up) — needs a product decision, don't assume either way.

---

## KI-3 — A 3D (WebGL) viewer can leave the browser tab unable to produce screenshots afterward

**Status**: Unclear / needs product decision (could be a real resource-cleanup bug in the 3D
viewer's teardown, or purely an artifact of headless Chrome + CDP screenshot capture that would
never affect a real user).

**Observation**: After opening a `.TRI` file (3D WebGL viewer + minimap), then closing the file
(File → Close, back to Landing Page — a page with no 3D content), `Page.captureScreenshot` via
Chrome DevTools Protocol began timing out (30s) on that tab, repeatably (3 attempts), while the
page's own JS execution (`javascript_tool`) and DOM introspection (`get_page_text`, `find`)
continued to work normally throughout. A **freshly opened tab** navigated to the same URL had no
such problem. Closing the wedged tab and using a new one was the only recovery found; no in-tab
recovery was attempted (e.g. forcing a GC, or explicitly disposing the WebGL context via console).

**Why this matters even if it turns out to be a test-tooling artifact**: it's exactly the
signature you'd see from a WebGL context / render-loop not being disposed on component teardown
(`obj-viewer`, minimap, or the `gg-web-engine` library they're built on) — worth a real developer
checking whether `ngOnDestroy` on those components calls something like `renderer.dispose()` /
`cancelAnimationFrame()` and removes the canvas's GL context, before dismissing this as tooling
noise.

**Practical guidance for testers in the meantime**: don't reuse a browser tab across a 3D-viewer
scenario and a subsequent scenario that needs a screenshot — open a new tab instead.

---

## Unknown / not yet investigated (flagged, not silently assumed fine)

- Byte-for-byte round-trip mismatches on compressed formats (QFS-family) in the golden-corpus
  check — **Expected behavior**, not a bug: QFS's LZ-style compressor is not guaranteed to
  reproduce the exact original byte stream on re-compression (multiple valid encodings of the same
  decompressed content exist); the check that matters for these is decompressed-content equality,
  which was not separately asserted this pass (only "no exception" was) — worth adding if a
  stronger corpus check is written later.
- macOS-specific native behaviors (pointer lock for 3D free-fly camera, Finder "Open With" /
  file-association open events, the pointer-lock "funk beep" suppression) — read from code
  (`actions/gui_editor_macos.py`), never exercised live this pass (this pass ran entirely inside a
  Linux container).
- File → Close with unsaved changes: does it warn, or silently discard? Not verified — see
  `TEST_PLAN.md` F-9.
- Archive viewer (generic, non-`Wwww` container) and its add/edit-item dialogs: no sample file
  identified this pass that renders it — coverage is currently zero, live or otherwise.
