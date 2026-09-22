# UI Map

Tags: **Confirmed (live)** = actually clicked/observed in a running instance (2026-09-06 pass,
see `TEST_HISTORY.md`); **Confirmed (code)** = read off the Angular template/component, not
exercised; **Unknown** = genuinely unverified either way.

Source of truth for the menu bar: `frontend/src/app/app.component.html`. For the editor's
per-block-type components: `EditorComponent.DATA_BLOCK_COMPONENTS_MAP` in
`editor.component.ts`.

## Global chrome

A top `mat-toolbar` is always present. Its content depends on whether a resource is open
(`mainService.api.openedResourcePath$`):

- **No file open** → toolbar shows just the app menu (below) + app name, and the body is the
  **Landing Page**.
- **File open** → toolbar additionally shows, right-aligned: a dev-only **"Changes (n)"** menu,
  **Undo**, **Redo**, **Save** icon buttons; body is the **Resource Editor**.

### App menu (always visible) — Confirmed (live)

| Menu | Item | Action | Enabled when |
|---|---|---|---|
| File | New... | Opens **New File dialog** | always |
| File | Open | Opens native/Tk **Open File** dialog, then loads the file | always |
| File | Recent Files ▸ | Submenu listing recently opened paths (basename only); click reopens | has ≥1 recent file |
| File | Close | Closes the current resource, returns to Landing Page | a file is open |
| File | Save | Serializes in-memory state back to the original file | a file is open **and** there are unsaved changes **and** not already saving |
| File | Reload from disk | Re-reads the currently open file, discarding in-memory edits | a file is open |
| Edit | Undo | Steps the change list back one revision | an undo step is available |
| Edit | Redo | Steps forward one revision | a redo step is available |
| View | Toggle Hidden Fields | Shows/hides fields marked `is_unknown` in the schema | always |
| Tools | Converter to common formats | Opens **Converter dialog** | always |
| Tools | System Configuration | Opens **Config dialog** | always |
| About | Home Page / File specs / Support me | Opens external URL in system browser | always |
| About | Report a bug / Request a feature | Opens external issue-tracker URL | always |
| About | *(footer)* vN.N.N | Static version label, not a control | — |

Same File/Edit/Tools items are reachable from the toolbar icon buttons when a file is open (Undo,
Redo, Save icons) — these mirror the menu items 1:1, same enablement rules. **Confirmed (live)**.

### "Changes (n)" debug menu — Confirmed (live)

Guarded by `@if (!isProduction)` in the template. `environment.ts` (the file used by the
"development" Angular build config; the "production" config's `fileReplacements` swaps in
`environment.prod.ts` instead) sets `production: false`, so this menu renders under `ng serve` dev
mode — confirmed live: opening `test/golden_corpus/AL1.TRI` showed **"Changes (0)"** in the
toolbar (see `KNOWN_ISSUES.md` KI-2, Fixed). It does not render in production builds
(`environment.prod.ts` keeps `production: true`). If you need the raw change list outside dev
mode, read `ChangesService` state directly instead (e.g. via `api.getChanges()`/`getRevisions()`
RPCs).

## Landing Page (`app-landing-page`) — Confirmed (live)

Shown when no file is open. Contents:
- Title + one-line description.
- **New File** button (pink) → New File dialog.
- **Open File** button (blue) → native Open dialog → loads file.
- **Recent Files** list (only rendered once there is ≥1 entry): each row shows the file's
  basename, is clickable to reopen it, and has a trailing "open containing folder" icon button
  that opens the file's parent directory in the OS file manager
  (`openFileWithSystemApp`). **Confirmed (live)**: after opening `AL1.TRI` once, it appeared here
  and stayed across a full page reload (recent-files list is persisted backend-side, not just
  in-memory).
- A first-run-only snackbar: *"First time run: looking for Blender and FFmpeg…"* followed by a
  result snackbar (*"Blender: \<path\> — FFmpeg not found"* etc.) with a **Settings** action that
  opens the Config dialog. **Confirmed (live)** in an environment with neither tool installed:
  final snackbar read *"Blender not found — FFmpeg not found"*.

## Resource Editor (`app-editor`, shown when a file is open)

Renders the open file's root `DataBlock` via whichever component
`DATA_BLOCK_COMPONENTS_MAP[block_class_mro]` resolves to. Every node in the tree, generic or
bespoke, additionally gets a **block-actions** toolbar (`app-block-actions`) wherever the schema
allows it:
- **Serialize** → save-file dialog → exports that sub-tree alone to its common format.
- **Deserialize** (where schema allows) → re-imports from a common-format file back into the tree.
- Any schema-declared **custom actions** (format-specific; e.g. an "extract embedded X" button) →
  if the action takes arguments, opens the **Run Custom Action dialog**; if all args are already
  known (`formPatch` covers every arg), runs immediately instead. On failure, shows a snackbar and
  **reloads the resource from disk**, discarding whatever the action partially changed —
  Confirmed (code), not exercised live.

### Generic (schema-driven) field components
One Angular component per `read_blocks` base class, reused by every format that doesn't need a
bespoke viewer: integer/decimal, string, enum, raw bytes, array, compound (nested object — this is
what most "generic" resources render as, recursively), sub-byte-compound, delegate (polymorphic
"actual type chosen at parse time"), trailing-optional, archive (generic named-item container).
**Confirmed (live)**: the TRI map viewer's data panel below the 3D view is built entirely from
these — nested compound blocks with numeric/enum leaf fields, an array-of-compound "AI info"
block, an array field with per-item "Click to view items (N)" expanders for large arrays
(1000-item `props` array observed).

### Bespoke rich viewers (`editor/eac/*`, `editor/common/*`)
| Viewer | For block class(es) | Notable controls |
|---|---|---|
| Image | `EacImage` | — |
| Palette | `EacPalette` | — |
| Font | `FfnFont` | — |
| Targa image | `TargaImage` | — |
| ORIP geometry | `OripGeometry` | embeds an **obj-viewer** (3D, WebGL) |
| GEO geometry | `GeoGeometry` | embeds obj-viewer |
| CRP geometry | `CrpGeometry` | embeds obj-viewer |
| TRI map | `TriMap` | 3D terrain view (WebGL) + **minimap** (2D spline path) + "Current preview FAM" dropdown (a TRI can reference multiple `.FAM` prefab sets) + view-mode icon toolbar (home/orbit/wireframe/globe icons observed) + full generic-field data panel below (see above) |
| TRK map | `TrkMap` | same family as TRI, NFS2-specific |
| FRD map | `FrdMap` | same family, NFS3-specific |
| EACS audio | `EacsAudioFile` | single audio clip playback, presumably |
| Soundbank | `SoundBank` | multi-clip container |
| Archive | `ArchiveBlock` (generic, non-`Wwww`) | directory-like item list; has its own item-type/edit dialogs (`archive-delegate-item-type.dialog`, `archive-item-edit.dialog`) — **Unknown**: not exercised live |

**Unimplemented-UI fallback**: if a block's `block_class_mro` chain matches nothing in the map, the
editor shows the error *"UI not implemented for A → B → C"* instead of the resource. Confirmed
(code) only; did not encounter live (all files opened during this pass had a working viewer).

## Converter dialog (`app-converter`, Tools → Converter to common formats) — Confirmed (live)

Modal, `disableClose: true` (only closable via its own Cancel/close, not backdrop click — matches
observed behavior). Fields:
- **Input Directory/File*** (required, text input + Browse → directory/file picker). Accepts
  manual typing, not just Browse — Confirmed (live).
- **Output Directory*** (required, same). Confirmed (live).
- **Conversion Settings** (collapsible `mat-expansion-panel`, "Customize conversion settings")
  containing: `multiprocess_processes_count`, and per-domain checkboxes — Images (save positions /
  palettes / mipmaps / embedded palette / texts), Maps (save as chunked / invisible-wall collisions
  / terrain collisions / spherical skybox texture / add props to obj), Geometry (save OBJ / save
  BLEND / export to gg-web-engine). Not expanded/inspected field-by-field this pass — Unknown
  defaults beyond what `converter.component.ts`'s form group shows in code (`maps__save_spherical_skybox_texture`
  and `geometry__save_obj`/`geometry__save_blend` default **on**; everything else defaults **off**).
- On load, **Blender is tested automatically** (`testBlenderExecutable`); if it's not working,
  `save_blend` and `export_to_gg_web_engine` are programmatically **disabled** (not just
  unchecked) — Confirmed (code); the disabling itself wasn't visually verified this pass (form was
  filled and submitted without expanding the settings panel).
- **Convert Files** button: disabled until both required paths are filled; on click, calls
  `convert_files` and shows a progress bar (`api.conversionProgress$`) while `isConverting`.
  Confirmed (code) for the button-enable logic; **the actual convert action currently throws
  server-side in the dev-mode environment this was tested in** — see `KNOWN_ISSUES.md` for the
  confirmed bug and its scope. On success (per code, not observed working end-to-end this pass):
  snackbar "Conversion completed successfully!" with an "Open Directory" action, and the output
  directory auto-opens in the OS file manager.
- **Cancel** closes the dialog with no side effects.
- Static "About Conversion" help text below the form, always visible.
- A **⚙ (settings)** shortcut inside the dialog reopens the **Config dialog** on top of it
  (`openConfigDialog`) — Confirmed (code), not clicked this pass.

## Config dialog (`app-config`, Tools → System Configuration) — Confirmed (live)

Modal. Fields: **Blender Executable Path** (text + Auto-detect + Test), **FFmpeg Executable Path**
(same), **Capture Blender Log** checkbox. Auto-detect fills the field from a backend probe and
shows a result message; Test runs the currently-typed path and shows success/failure inline.
**Save** persists via `patchGeneralConfig` and closes; **Cancel** discards. Confirmed (live):
default field values were the bare command names `blender` / `ffmpeg` (PATH-relative, no absolute
path) in an environment where neither is installed.

## New File dialog (`app-new-file.dialog`, File → New...) — Confirmed (code)

Lets the user pick a template format to start a blank file from: **FFN font**, **FSH image
archive**, **QFS image archive** (radio-style list with format icons, one preselected: `ffn`).
Confirming opens a save-file dialog seeded with `Untitled.<ext>`, then calls `createNewFile`.
Cancelling returns nothing. Not exercised live this pass (would need to drive both this dialog and
a subsequent native save dialog back-to-back).

## Run Custom Action dialog (`app-run-custom-action.dialog`) — Confirmed (code), not exercised live

Dynamically built reactive form, one control per `CustomActionArgument` the invoked action
declares. Arg types: `number` (numeric-pattern validated), `string`, `bool` (checkbox, default
`false`), `enum_string` (choices list), `file_output` (text field + a "browse" button that opens a
save dialog, pre-seeded with a filename hint derived from the resource's id path). Supports
**conditional fields** via `visible_when: {arg, value}` — a hidden conditional field is excluded
from validation entirely while hidden, so the form can be valid even with a "required" field not
yet visible. Submit closes with the merged arg values; Cancel returns nothing to the caller
(`CustomActionService.runCustomAction` treats a falsy dialog result as "user cancelled" and does
not call the backend).

## Other dialogs — Confirmed (code), not exercised live

- **Confirm dialog** (`confirm.dialog`) — generic yes/no, used wherever the app needs a
  confirmation (exact trigger sites not enumerated this pass — grep `dialog.open(ConfirmDialogComponent` for callers before assuming one exists for a given action).
- **Error dialog** (`error.dialog`) — generic error surface; distinct from the inline
  "resourceError" state the editor shows for a file that failed to parse (that's rendered inline in
  the editor pane, not as a dialog — Confirmed (code) from `EditorComponent.resourceError`).
- **Archive item dialogs** (`archive-delegate-item-type.dialog`, `archive-item-edit.dialog`) —
  used by the generic Archive viewer when adding/editing an item whose concrete type must be
  chosen or whose fields must be edited outside the main tree. Unknown trigger flow; not reached
  this pass (no plain `ArchiveBlock` file was opened — only the `Wwww`-flavoured archives seen
  render via the bespoke geometry/map/image viewers of their contents instead of the generic
  archive item list).

## Known interaction quirks worth remembering when testing

- **Menu items must be clicked by re-querying position/ref right before the click** — a coordinate
  captured from an earlier screenshot can be a few pixels stale once Angular Material re-measures
  a menu (observed a mis-click landing on the still-open parent menu instead of its item).
  Prefer `find` + click-by-ref, or click immediately after the screenshot that shows the target.
- **A resource with an active WebGL viewer (any 3D map/geometry) can wedge the browser tab's
  screenshot capture** even after navigating away within the same tab — see
  `KNOWN_ISSUES.md`. Textual introspection (`get_page_text`, `read_page`, `find`,
  `javascript_tool`) kept working throughout; only `computer` screenshot capture hung. Open a
  fresh tab rather than fighting a wedged one.
