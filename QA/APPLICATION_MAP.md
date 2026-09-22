# Application Map

*Status: Confirmed (code) throughout unless marked otherwise; the workflows marked "Confirmed
(live)" were actually exercised — see `TEST_HISTORY.md` 2026-09-06 run.*

## What this application does

NFS Resources Converter is a **3-in-1** tool built around one thing: a Python declaration, per
binary file format, of how to parse/serialize it (see repo-root `CLAUDE.md` for the
`DataBlock`/`DeclarativeCompoundBlock` framework). That single declaration drives three
user-facing surfaces:

1. **A parsing/conversion library** — turns proprietary EA Canada game resource files (mainly The
   Need For Speed SE / "TNFS", 1996 PC, plus some formats shared with later NFS titles) into common
   formats: images → PNG, fonts → FNT+PNG, 3D geometry/maps → OBJ/GLB/BLEND, audio → WAV, video →
   MP4, archives → directories, everything else → JSON/TXT. This also works in reverse for a subset
   of formats (edit → serialize back to the original binary layout).
2. **Auto-generated documentation** (`resources/*.md`) of every known format field — not covered
   further here; it's a build artifact, not a testable UI surface.
3. **A desktop GUI application** (Angular frontend + Python backend, bridged via `pywebview` on
   macOS/Windows or `Eel` on Linux) — open a resource file, view/edit it through a schema-driven
   editor, convert files in bulk, configure external tool paths. This is the primary subject of
   this QA directory.

## Primary users

Two audiences, both technical:
- **Modders / reverse-engineering hobbyists** who want to view, extract, or tweak NFS game assets.
- **The project maintainer**, feeding converted assets into a separate site
  ([The Need For Speed Web](https://tnfsw.guraklgames.com/)).

There is no non-technical end user; file paths, executable paths, and raw format internals are
exposed directly in the UI without hand-holding.

## Major functional areas

### 1. File lifecycle (open / new / close / save / reload)
Open an existing resource file, or create a blank one of a template format (FFN font, FSH or QFS
image archive). Editing is in-memory; nothing touches disk until **Save**. **Reload from disk**
discards in-memory edits. See `UI_MAP.md` → File menu / Landing page.

### 2. Resource editor (the core surface)
Once a file is open, its top-level `DataBlock` is rendered by a schema-driven Angular component
tree (`EditorComponent.DATA_BLOCK_COMPONENTS_MAP`, keyed by the block's Python class name via
`block_class_mro`). Two tiers exist:
- **Generic primitives** (number, string, enum, binary, array, compound, archive, delegate,
  trailing-optional, sub-byte-compound) — one Angular component type per `library/read_blocks`
  base class, reused across *every* format.
- **Bespoke rich viewers** for specific resource kinds — 2D image, palette, font, 3D geometry
  (ORIP/GEO/CRP), 3D maps with a minimap (TRI/TRK/FRD), audio (single clip / soundbank), Targa,
  archive (generic container + directory-like item list).

If a block's class isn't in that map, the editor shows an explicit **"UI not implemented for
\<class chain\>"** error instead of guessing — this is intentional, not a crash, and is the
correct behavior for a format with no rich/generic UI (should not occur for any currently
supported format; would occur for a newly-added format definition whose block type isn't yet
registered in the map).

Every block in the tree can independently: **Serialize** (export just that sub-tree to a common
format via a save dialog) and, where supported, **Deserialize** (re-import), plus any
format-specific **custom actions** (schema-declared operations with their own argument dialog —
e.g. extracting an embedded resource). Edits to any field are tracked centrally (see next).

### 3. Change tracking / Undo / Redo / Save
Every edit anywhere in the currently open resource is pushed through `ChangesService`
(`api/endpoints/changes_api.py` + `frontend/.../services/changes.service.ts`) as a linear list of
revisions, independent of which UI component made the edit. Undo/redo walk that list; **Save**
serializes the current in-memory state back to the original file's binary format and clears the
list. A dev-only "Changes (n)" menu is meant to show the raw change list for debugging — see
`KNOWN_ISSUES.md` for why it currently never renders.

### 4. Bulk converter (Tools → Converter to common formats)
Independent of the single-file editor: point it at an input file or directory and an output
directory, optionally tune per-format conversion settings (image mipmaps/palettes/positions, map
collision/skybox/props export, 3D geometry OBJ vs. BLEND vs. an external "gg-web-engine" export),
and it walks the input tree in a multiprocess pool, converting every recognized file and writing a
`skipped.txt` per directory for anything it couldn't convert. This is also available headless via
`./nfs-resources-converter convert <in> --out <out>` (see `run.py`).

### 5. System configuration (Tools → System Configuration)
Paths to the two optional external executables the converter shells out to: **Blender** (4+, for
`.blend`/glTF export and the "gg web engine" pipeline) and **FFmpeg** (audio/video). Each can be
auto-detected or manually tested. On first run only, the app auto-detects both in the background
and silently patches the config if found (`AppComponent.autoDetectExecutablesOnFirstRun`).
Everything 3D/audio/video-conversion-related in the Converter degrades to "unavailable" (checkbox
disabled) rather than failing at conversion time when Blender/FFmpeg aren't configured — **Confirmed
(live)**: verified in an environment with neither installed.

### 6. Custom actions & serialize/deserialize (cross-cutting, not a separate screen)
See functional area 2 — this is a capability every resource-tree node can expose, not a distinct
screen. Worth tracking as its own functional area because it's easy to under-test: it's schema
driven (defined per format in Python, e.g. `resources/eac/...`), so coverage differs per format and
isn't visible from the generic editor chrome alone.

## Data flow (GUI)

```
Angular (frontend/)  <--pywebview/Eel bridge-->  Python API (api/) --> library/ + resources/*.py
      |                                                                        |
      |  block.schema (JSON: block_class_mro, fields, custom_actions, ...)     |
      |<-----------------------------------------------------------------------
      |  block rendered to disk under a per-open-file temp dir, served over
      |  HTTP as /resources/<id>/... for large sub-assets (images, 3D meshes,
      |  audio) the Angular UI fetches directly rather than pulling through
      |  the RPC bridge — Confirmed (live): observed /resources/... GET
      |  requests for a TRI map's generated .obj terrain chunks.
```

Because of that split, don't assume "opening a file" is one atomic call: the RPC round-trip
returns schema+small data, and the rich 3D/image viewers then pull larger derived assets over
plain HTTP from a per-session temp directory the backend maintains.

## Platform differences that matter for behavior (not just packaging)

- **macOS / Windows**: GUI runs in a native web view (`pywebview`); Python↔JS bridge is
  `window.pywebview.api` plus a hand-written `eel.js`-compatible shim (`api/bridge.py`). Native
  OS file/save/directory dialogs.
- **Linux**: GUI runs on the real `Eel` library — either a dedicated Chromium app window
  (production) or, in `--dev`, no window at all (see `TEST_ENVIRONMENT.md`). File/save/directory
  dialogs fall back to **Tkinter** (`api/endpoints/file_dialog_api.py`) specifically because there's
  no native web-view dialog API to call.
- This difference is the root cause of a confirmed dev-mode-only bug — see `KNOWN_ISSUES.md`.

## Out of scope for this QA pass

- The parsing library's format-by-format correctness (hundreds of formats; covered by
  `test/resources/**`, `test/library/**`, and the golden-corpus/`games/` round-trip checks —
  see `TEST_ENVIRONMENT.md` and `KNOWN_ISSUES.md` for what those actually assert).
  This directory focuses on the **GUI application** built on top of that library.
- Windows/macOS-specific native-dialog and native-window behavior (pointer lock, "Open With",
  file associations) — read from code only, never exercised live in this pass. See
  `KNOWN_ISSUES.md` "Unknown" section.
