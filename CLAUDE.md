# NFS Resources Converter

A parser/converter library + GUI app for binary resource files from EA's **Need For Speed** series
(games 1–6). Current focus is **The Need For Speed SE** (1996, PC / "TNFS"), though many EA Canada
formats (FSH images, FFN fonts, ...) are shared across later titles too. Output feeds
[The Need For Speed Web](https://tnfsw.guraklgames.com/).

It's a "3-in-1" project — a single Python format definition simultaneously provides:
1. **Conversion** of game resources to common formats (obj/blend/glb, wav, png, mp4, fnt+png, json, txt)
2. **Documentation** — `resources/*.md` is auto-generated from the same format definitions
3. A **GUI editor** (Angular + pywebview/eel) to browse/edit/convert resource files

## Read this next

- Extending the *framework itself* (new generic `DataBlock` subclass, new generic Angular UI
  component, new base serializer behavior) → skill `read-block-framework`.
- Adding support for a *new game file format*, or new/unknown fields to an existing one, by
  composing existing blocks → skill `nfs-resource-formats` (has a cheat-sheet of every existing
  building block).

## The core idea

Every supported file format is described **once**, in Python, as a tree of `DataBlock` subclasses
(mostly `DeclarativeCompoundBlock` with a nested `Fields` class — see e.g. `resources/eac/bitmaps.py`).
That single declaration drives, with no separate work:

- binary parsing (`read`) and serialization back to bytes (`write`)
- conversion to/from common formats, via the block's `serializer_class()`
- the GUI editor: `block.schema` (incl. `block_class_mro`, a `__`-joined class-name chain) picks
  which Angular component renders the field
- the Markdown reference docs in `resources/*.md`, generated from the same `schema`/`description` text

So writing a good field `description` and picking the right existing block type usually gets you
docs and a working GUI editor for free.

## Repo map

| Path | What lives there |
|---|---|
| `library/read_blocks/` | Generic, reusable binary-parsing primitives — the framework. |
| `library/context.py` | `ReadContext`/`WriteContext`/`DocumentationContext` passed through the block tree while reading/writing/documenting. |
| `library/loader.py` | File-type auto-detection (`probe_block_class`) by extension/magic bytes; top-level `require_file`/`require_resource` with an in-process file cache. |
| `library/changes_service.py` | Tracks unsaved GUI edits against the loaded data tree. |
| `resources/eac/` | EA Canada format definitions built from `read_blocks` primitives (bitmaps, archives, fonts, audio, geometries, maps, car specs, compressions). Shared across many NFS titles. |
| `resources/eac/maps/`, `resources/eac/geometries/` | Per-game specializations (`tnfs.py`, `nfs2.py`, `nfs3.py`, `nfs5.py`, ...). |
| `resources/common/` | Vendor-neutral formats reused as fallbacks (e.g. Targa image). |
| `resources/blackbox/` | Blackbox-studio (later NFS titles) formats — thin/early. |
| `resources/eac/fields/` | Small reusable domain blocks: `Point2D`/`Point3D`/`RGBBlock`, angle/time fields. |
| `resources/*.md` | **Auto-generated** per-game docs (`generate_resource_doc.py`). Never hand-edit — edit the block definitions/descriptions and regenerate. |
| `serializers/` | Turn parsed block data into common output formats and back. One serializer class per resource kind, returned by a block's `serializer_class()`. |
| `api/` | Python↔JS bridge (pywebview/eel) exposing library + serializers to the GUI. |
| `frontend/` | Angular GUI. `.../editor/library/*.block-ui` = generic components, one per `read_blocks` base class. `.../editor/eac/*` and `.../editor/common/*` = bespoke rich viewers (image, 3D geometry, map, audio, font, hex/targa). |
| `actions/` | OS-integration entry points (convert all, open in GUI editor, uncompress) wired to file-manager context menus / installers. |
| `test/` | unittest suite mirroring `library/`/`resources/`. `test/golden_corpus/` + `test/test_gui_golden_corpus.sh` = manual smoke test that opens every sample file through `run.py`. |
| `docs/milestones.md` | AI-maintained roadmap of format coverage by game. |
| `generate_resource_doc.py` | Regenerates `resources/*.md` from block schemas. |

## Dev environment

- Python **3.14**, venv at `./.venv` (see `AI_AGENTS.md`). Always invoke `./.venv/bin/python`.
- Backend tests: `./.venv/bin/python -m unittest` (target one module with e.g.
  `-m unittest test.library.read_blocks.test_array`).
- Frontend: `cd frontend && npm install` once; `npm run start` for the dev server;
  CI-equivalent test run: `npm run test -- --watch=false --no-progress --browsers=ChromeHeadless`.
- Run the app: `python run.py [path/to/file]`; `python run.py --dev` for the hot-reload GUI
  (see `README.md` "Debugging the Angular frontend" for the full dev-server dance, incl. Linux
  differences).
- `ffmpeg` and Blender 4+ are required for audio/video/3D conversions.
- CI (`.github/workflows/pull_request_build.yml`) runs exactly the two test commands above —
  keep both green before considering a change done.

## Keep this file and the skills current

This file and the two skills (`read-block-framework`, `nfs-resource-formats`) are meant to track
the codebase as it actually is right now. If, while working, you find a statement here that's
wrong, incomplete, or no longer matches the code — or you add something (a block type, a
convention, a directory) that future sessions would benefit from knowing about — update the
relevant file as part of your change, don't just note it in conversation.

When you do:
- Describe **only the current state**, as if it had always been this way. Don't write change-log
  style prose ("used to be X, now Y", "X was migrated/removed/renamed", "previously..."). If
  something is gone, delete its mention instead of noting its absence.
- Keep entries dry and reference-like (what exists, where, what it's for), matching the style
  already used here — not narration of how it got that way.
- Prefer editing the smallest section that's actually stale over rewriting the whole file.

## Conventions worth knowing

- `library/loader.py`'s `_find_block_class` imports resource modules **locally, inside each branch**
  on purpose (one process is spawned per file conversion, so this avoids loading every parser every
  time). Follow that pattern there rather than importing at module top level.
- Field extras dict (third tuple element in `Fields`) keys: `description`, `is_unknown`,
  `custom_offset`, `usage` (comma-separated subset of `ui`/`io`/`doc`, default = everywhere).
- Nothing repo-specific overrides standard slash commands (`/code-review`, `/simplify`, etc.).
