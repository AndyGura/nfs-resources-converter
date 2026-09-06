# Test Plan

Scenarios derived from `APPLICATION_MAP.md` / `UI_MAP.md`. **Status** reflects this pass only —
update in place on every future run rather than re-deriving from scratch (append results instead
to `TEST_HISTORY.md`, but if a scenario's *steps* turn out wrong/incomplete, fix them here).

Legend — Priority: P0/P1/P2/P3 per `TEST_STRATEGY.md`. Regression: ✅ = good candidate for the
standing regression set (`REGRESSION.md`), — = one-off/exploratory only.

## Smoke

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| S-1 | Launch | Start the app (any platform/mode) | Landing page renders, no console errors, menu bar present | P0 | ✅ | **Pass** (Confirmed live, Linux dev-mode) |
| S-2 | Open common file | Open a `.TRI` file from golden_corpus | Editor renders TRI viewer (3D + minimap + data panel), window title updates to filename | P0 | ✅ | **Pass** (Confirmed live) |
| S-3 | Corpus round-trip | Run the golden_corpus read+write snippet (`TEST_ENVIRONMENT.md`) | All files: no exception, no `error_class`, `block.pack()` succeeds | P0 | ✅ | **Pass** — 31/31 (see `TEST_HISTORY.md`) |

## File lifecycle

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| F-1 | Open via dialog | File → Open, pick a file | File loads, appears in Recent Files, title updates | P0 | ✅ | **Pass** (Confirmed live, via Tk-dialog automation — see `TEST_ENVIRONMENT.md`) |
| F-2 | Recent Files persistence | Open a file, reload the whole page (`F5`-equivalent) | File still listed under Recent Files | P1 | ✅ | **Pass** (Confirmed live) |
| F-3 | Close | File → Close with a file open | Returns to Landing Page; toolbar reverts to no-file-open state | P1 | ✅ | **Pass** (Confirmed live) |
| F-4 | Reload from disk | Edit a field, then File → Reload from disk | In-memory edit is discarded, field reverts to on-disk value | P1 | ✅ | Not run — Unknown |
| F-5 | Save | Edit a field, File → Save | File is enabled only once dirty; after save, file on disk reflects the edit and dirty flag clears | P0 | ✅ | Not run — Unknown |
| F-6 | New File | File → New..., pick each of FFN/FSH/QFS, save-as a temp path | A minimal valid file of that format is created and re-openable | P2 | ✅ | Not run |
| F-7 | Open unsupported/corrupt file | Open a file with no matching format (e.g. a `.txt`) or a truncated/garbage binary | Inline error state in the editor pane (not a crash, not a silent no-op) | P0 | ✅ | Not run — see also `KNOWN_ISSUES.md` "Unknown" list |
| F-8 | Undo/Redo across a session | Make 3+ edits, Undo twice, Redo once, Save | Final saved state matches the edit that was current after the Redo | P1 | ✅ | Not run |
| F-9 | Close with unsaved changes | Edit a field, File → Close (no confirmation dialog observed in code for this path) | **Unknown**: does it warn before discarding, or silently drop edits? Verify against code (`AppComponent.closeFile`) before assuming either | P1 | — | Not run |

## Converter

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| C-1 | Open dialog | Tools → Converter to common formats | Dialog renders with empty required fields, Convert Files disabled | P1 | ✅ | **Pass** (Confirmed live) |
| C-2 | Manual path entry | Type paths directly into Input/Output fields (no Browse) | Fields accept typed text, Convert Files enables once both non-empty | P2 | ✅ | **Pass** (Confirmed live) |
| C-3 | Convert a small directory | Point Input at `test/samples`, Output at an empty temp dir, click Convert Files | Output directory populated with converted files per format; success snackbar; output dir opens | P0 | ✅ | **FAIL in Linux dev-mode** — see `KNOWN_ISSUES.md` KI-1. Not yet re-verified against a packaged/production build. |
| C-4 | Convert with Blender/FFmpeg unset | Same as C-3 in an environment with neither tool configured | Non-3D/audio/video files still convert; skipped items land in a `skipped.txt`, no crash | P1 | ✅ | Blocked by KI-1 |
| C-5 | Convert nonexistent input path | Type a path that doesn't exist, click Convert Files | Snackbar/error: "Input path does not exist: …", no crash | P1 | ✅ | Not run (code shows this exact check exists — `conversion_api.py` line ~123) |
| C-6 | Cancel mid-form | Fill some fields, click Cancel | Dialog closes, no conversion runs, no side effects | P3 | — | Not run |
| C-7 | Settings shortcut | From within the Converter dialog, open System Configuration | Config dialog opens on top; on close, Converter's Blender path/test state refreshes | P3 | — | Not run |

## Config

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| G-1 | Open dialog | Tools → System Configuration | Fields populate from persisted config | P1 | ✅ | **Pass** (Confirmed live — showed bare `blender`/`ffmpeg` defaults) |
| G-2 | Auto-detect | Click Auto-detect for each tool in an environment where it's actually installed | Field populates with a real path, test result shown | P2 | ✅ | Not run (no Blender/FFmpeg available in test environment this pass) |
| G-3 | Test invalid path | Type garbage into a path field, click Test | Failure result shown inline, doesn't crash the dialog | P2 | ✅ | Not run |
| G-4 | Save persists | Change a field, Save, reopen Config | New value is still there | P1 | ✅ | Not run |
| G-5 | Cancel discards | Change a field, Cancel, reopen Config | Old value is back | P2 | ✅ | Not run |

## Editor — generic components

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| E-1 | Large array rendering | Open a resource with a large array field (TRI's `props`, 1000 items) | Renders as a collapsed "Click to view items (N)" control, doesn't hang the page | P1 | ✅ | **Pass** (Confirmed live — text content observed, page remained responsive to `get_page_text`) |
| E-2 | Expand large array | Click "Click to view items" on a 1000-item array | Items render (paginated or all-at-once — Unknown which); UI stays responsive | P1 | ✅ | Not run |
| E-3 | Enum field | Locate and change an enum field's value | Dropdown/select shows valid enum choices only, value change registers as a pending change | P2 | ✅ | Not run |
| E-4 | Toggle Hidden Fields | View → Toggle Hidden Fields on a resource with `is_unknown` fields | Hidden/unknown fields show or hide accordingly | P2 | ✅ | Not run |
| E-5 | Unimplemented-UI fallback | Open/construct a resource whose block class isn't in `DATA_BLOCK_COMPONENTS_MAP` | Explicit "UI not implemented for …" message, not a blank pane or crash | P2 | — | Not run (didn't hit this case naturally) |
| E-6 | Serialize a sub-block | On any block with `schema.serialization` set, click Serialize | Save dialog opens seeded with a sensible filename hint; file(s) written match the block's data | P2 | ✅ | Not run |
| E-7 | Custom action with args | Trigger a custom action that declares arguments | Run Custom Action dialog opens, conditional (`visible_when`) fields show/hide correctly, submit runs the action | P2 | ✅ | Not run |
| E-8 | Custom action failure recovery | Trigger a custom action that will fail (e.g. invalid arg value if validation allows it through) | Snackbar shows the error, resource reloads from disk | P2 | ✅ | Not run |

## Bespoke viewers

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| V-1 | TRI map | Open a `.TRI` file | 3D terrain (checkerboard placeholder texture is normal/expected — no texture data embedded), minimap with track spline + start marker, "Current preview FAM" dropdown, view-mode icons (home/orbit/wireframe/globe) | P1 | ✅ | **Pass** (Confirmed live) |
| V-2 | Switch preview FAM | On a TRI viewer, change "Current preview FAM" dropdown | 3D view updates to reflect the newly selected FAM prefab set | P2 | ✅ | Not run |
| V-3 | Image viewer | Open a `.FSH` file | Image renders; palette info visible if applicable | P1 | ✅ | Not run this pass via GUI (verified only via headless parse in corpus test) |
| V-4 | Font viewer | Open a `.FFN` file | Glyphs render | P2 | ✅ | Not run via GUI |
| V-5 | Audio viewer | Open a `.BNK`/`.FSB` file | Playback control renders; Unknown whether autoplay/streaming works headlessly (audio playback needs a real audio device — likely untestable in a headless container) | P2 | — | Not run |
| V-6 | 3D geometry viewer | Open a `.CFM`/`.GEO`/`.CRP` file | obj-viewer renders the mesh, camera controls work (pointer-lock free-fly — see `APPLICATION_MAP.md` platform notes; pointer lock needs a real display, expect this to be hard to automate) | P2 | — | Not run |
| V-7 | Archive viewer | Open a generic (non-`Wwww`) archive-only file | Item list renders; add/edit item dialogs work | P2 | ✅ | Not run — no matching sample identified this pass |

## Negative / error paths

| ID | Area | Steps | Expected | Priority | Regression | Status |
|---|---|---|---|---|---|---|
| N-1 | Unsupported file | Open a `.txt`/random file | Inline error, not a crash (see F-7) | P0 | ✅ | Not run |
| N-2 | Empty converter input | Convert Files with Input pointed at an empty directory | Succeeds with 0 files processed, no crash | P2 | ✅ | Not run |
| N-3 | Cancel every dialog | Open each dialog (Converter, Config, New File, Run Custom Action) and cancel without making changes | No side effects, no console errors | P2 | — | Partial — Converter/Config Cancel not explicitly clicked this pass, only inferred from code |
| N-4 | Reopen already-open file | With a file open, use File → Open and pick the *same* file again | Reloads cleanly (`force_reload` flag exists in `open_file`'s signature) rather than duplicating state | P2 | ✅ | Not run |

## Notes for whoever runs this next

- Every "Not run" row above is a real gap, not a pass-by-omission — don't read absence of a
  status as "presumably fine".
- `TEST_ENVIRONMENT.md` explains the Docker/Xvfb/xdotool technique needed to drive native
  Open/Save/directory dialogs headlessly — several "Not run" rows above are blocked purely on time,
  not on missing capability.
- Golden-corpus coverage (S-3) is about the **parsing library**, not the GUI — it does not
  substitute for V-1..V-7 above. Keep both tracks going.
