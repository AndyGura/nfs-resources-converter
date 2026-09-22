# Test Strategy

## Why this project needs a specific strategy, not a generic one

Two things make this app unusual to test:

1. **The GUI cannot be driven by browser automation in its shipped form.** On macOS/Windows it
   runs inside a native `pywebview` web view (not a Chrome tab); on Linux, production mode opens a
   dedicated Chromium *app* window, and dev mode opens no window at all. A drivable, real Chrome
   tab only exists via the specific Linux dev-mode setup documented in `TEST_ENVIRONMENT.md`. Any
   test strategy for this app has to route around that constraint explicitly instead of assuming
   "open the app, click things" works out of the box.
2. **The interesting risk surface is mostly per-file-format, not per-screen.** The GUI chrome
   (menus, dialogs) is small and static; the *content* rendered inside the editor varies
   enormously by format, and each format is an independent, hand-written parser. A change to one
   format's Python definition can't regress another format's — but it can regress the *generic*
   editor components every format shares (array/compound/enum/etc.), which is a many-to-one risk.

## Testing types, and when they matter here

1. **Smoke testing** — app launches, landing page renders, one file of a common format
   (`.TRI` or `.FSH`) opens and renders without error. Run this first, always; if it fails, nothing
   else in a pass is meaningful.
2. **Corpus regression (read/write round-trip)** — the cheapest, highest-value check this project
   has: iterate `test/golden_corpus/` (small, curated, git-tracked, *every file in it must parse
   without error*) through `library.require_file` + `block.pack`, asserting no exception and no
   `error_class` in the parsed data. See `TEST_ENVIRONMENT.md` for the exact snippet. Run this on
   every change to `library/read_blocks/` or `resources/**` — it is fast (seconds) and catches
   "I broke a shared primitive" immediately, before any GUI test is even worth attempting.
3. **Exploratory GUI testing** — click-driven, using the Linux dev-mode + real Chrome technique.
   Highest value on: the menu/dialog chrome (small surface, easy to fully cover), the *generic*
   editor components (shared by every format — a regression here is silent and wide), and any
   workflow spanning multiple components (open → edit → undo → save → reload).
4. **Functional UI testing** — targeted scenarios from `TEST_PLAN.md`, run when touching a specific
   area (e.g. "changed the Converter form" → run the Converter scenarios, not the whole plan).
5. **Negative / error-path testing** — opening an unsupported/corrupt file, converting an empty or
   nonexistent input path, saving with no write permission, cancelling every dialog mid-flow. Under
   tested by nature (nobody writes negative cases first) — treat as first-class in `TEST_PLAN.md`,
   not an afterthought.
6. **Boundary testing** — empty directories/files, an archive with 0 or 1000+ items (the TRI viewer
   already renders arrays that large — confirmed it doesn't choke on 1000 items, see
   `TEST_HISTORY.md`), very long file paths, non-ASCII paths (Unknown — not tested).
7. **Persistence / state testing** — recent-files list survives a full page reload (Confirmed, see
   `TEST_HISTORY.md`); config (Blender/FFmpeg paths) persists across the app restarting; unsaved
   changes are correctly lost on Close/Reload and correctly kept on Undo/Redo.
8. **Error handling** — does a backend exception surface as a scoped error (inline resourceError,
   or a snackbar) or does it silently swallow / take down the whole session? The one confirmed bug
   found this pass (see `KNOWN_ISSUES.md`) is exactly this category: an unhandled backend exception
   correctly gets caught and returned as `{success: false, error: ...}` rather than crashing the
   process — the *conversion feature* is broken, but the *app* degrades gracefully. Verify this
   pattern holds for other RPCs, don't assume it from one example.
9. **Keyboard/mouse interaction** — menu keyboard navigation, Escape-to-close on dialogs/menus
   (used throughout this pass without issue), any app-level keyboard shortcuts (Unknown — none
   found documented; don't assume any exist beyond standard Angular Material menu/dialog behavior).
10. **File / import-export behavior** — the actual conversion and serialize/deserialize actions;
    highest real-world stakes (this is the product's whole purpose) and, per the CLAUDE.md
    warning, the editor "does not make backups" — so testing Save/serialize against throwaway
    copies only, never originals.
11. **API/UI consistency** — `test/api/*.py` exercises the Python-side API endpoints directly
    (see `TEST_PLAN.md` for what they cover); cross-check that the Angular UI actually calls those
    endpoints the way the tests assume, rather than assuming API coverage implies UI coverage.
12. **Visual/UI sanity** — screenshots are the primary tool, with the WebGL caveat in
    `KNOWN_ISSUES.md`. Don't chase pixel-perfect layout; watch for backdrop/overlap glitches,
    truncated text, and obviously-wrong states (e.g. a disabled button that should be enabled).
13. **Recovery after invalid operations** — after a custom action fails, the app reloads the
    resource from disk (Confirmed (code) in `custom-action.service.ts`) — verify this actually
    fires on a real failure, and that it doesn't also discard *unrelated* unsaved edits elsewhere
    in the same resource (Unknown).

## Priority model

Rank by **user impact × how silently it could regress**, not by feature size:

- **P0** — app won't launch; landing page doesn't render; a common/representative file
  (`.TRI`, `.FSH`, `.QFS`, `.FFN`) fails to open; Save corrupts a file.
- **P1** — a generic editor component (array/compound/enum/etc.) misbehaves (impacts *every*
  format); Undo/Redo/Save inconsistent; Converter produces wrong output or silently skips files
  without reporting them.
- **P2** — a single bespoke viewer (3D map, font, audio) misbehaves; Config/Converter dialog
  field-level bugs; dev-mode-only issues that don't reach packaged builds (like the confirmed bug
  in this pass).
- **P3** — cosmetic/layout issues; missing tooltips; non-blocking console warnings.

## When to run what

- **Every iteration (small, local change)**: smoke test + corpus round-trip (#1, #2) always;
  add the specific `TEST_PLAN.md` scenarios for whatever area changed.
- **Before a release**: full `TEST_PLAN.md` pass + a `games/`-directory-scale corpus round-trip if
  `library/read_blocks` or a widely-shared `resources/` module changed (see
  `test/resources/test_games_directory.py`, currently `@unittest.skip`'d because it's slow —
  un-skip it locally for a release check, don't enable it in CI without discussing the runtime
  cost).
- **After a significant architectural change** (e.g. bridge/API shape, build tooling, Angular
  version): re-verify the whole `TEST_ENVIRONMENT.md` setup still works *before* trusting any GUI
  test result from it — the setup itself is a dependency.
- **After a bug fix**: the specific repro from `KNOWN_ISSUES.md`, plus the P0/P1 smoke scenarios
  (fixes regress adjacent things surprisingly often in a shared-primitive codebase like this one).

Don't run a fixed checklist mechanically — `REGRESSION.md` describes how to *derive* the right
scope from an actual diff.
