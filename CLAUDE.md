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
- Porting *game logic* (a decompressor, codec, checksum) from an executable's IDA/Ghidra
  disassembly, or verifying such a port → skill `asm-runner-porting`.

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
| `library/utils/asm_runner.py` | 32-bit x86 snippet interpreter (IDA syntax) used to execute and progressively port disassembled game routines; production code never uses it, the ASM-driven decompressor twins in `test/resources/eac/archives/test_compressed_block.py` do. |
| `resources/eac/` | EA Canada format definitions built from `read_blocks` primitives (bitmaps, archives, fonts, audio, geometries, maps, car specs, TNFS replays). Shared across many NFS titles. `compressions/` holds the pure-Python decompressors (RefPack, QFS2, QFS3, NFSU's JDLZ, NFSU2's HUFF = QFS3 behind a 16-byte header) behind `EacCompressedBlock`. |
| `resources/eac/maps/`, `resources/eac/geometries/` | Per-game specializations (`tnfs.py`, `nfs2.py`, `nfs3.py`, `nfs5.py`, ...). |
| `resources/common/` | Vendor-neutral formats reused as fallbacks (e.g. Targa image). |
| `resources/blackbox/` | Blackbox-studio (later NFS titles) formats, NFS Underground 1, 2 and Most Wanted: `chunks.py` (generic id+length chunk dispatch helpers), `geometries/` (car and world geometry packs), `bitmaps/` (texture packs, TPK), `maps/` (chunk bundles, scenery, streaming sections; `NfsuTrackBundle` is a race's `TRACKBnnnn.lzc` or an NFSU2/NFSMW location bundle `LxRA.BUN`), `archives.py` (JDLZ-compressed files). |
| `resources/eac/fields/` | Small reusable domain blocks: `Point2D`/`Point3D`/`RGBBlock`, angle/time fields. |
| `resources/*.md` | **Auto-generated** per-game docs (`generate_resource_doc.py`). Never hand-edit — edit the block definitions/descriptions and regenerate. |
| `serializers/` | Turn parsed block data into common output formats and back. One serializer class per resource kind, returned by a block's `serializer_class()`. |
| `api/` | Python↔JS bridge (pywebview/eel) exposing library + serializers to the GUI. |
| `frontend/` | Angular GUI. `.../editor/library/*.block-ui` = generic components, one per `read_blocks` base class. `.../editor/eac/*` and `.../editor/common/*` = bespoke rich viewers (image, 3D geometry, map, audio, font, hex/targa). |
| `actions/` | OS-integration entry points (convert all, open in GUI editor, uncompress) wired to file-manager context menus / installers. |
| `test/` | unittest suite mirroring `library/`/`resources/`. `test/golden_corpus/` + `test/test_gui_golden_corpus.sh` = manual smoke test that opens every sample file through `run.py`. |
| `docs/milestones.md` | AI-maintained roadmap of format coverage by game. |
| `QA/` | QA knowledge base for testing the GUI application: application/UI maps, test strategy/plan, regression procedure, known issues, environment setup (incl. how to get a browser-automatable instance of the desktop GUI), and test history. Start at `QA/CLAUDE_QA_INSTRUCTIONS.md`. |
| `generate_resource_doc.py` | Regenerates `resources/*.md` from block schemas. |

## Dev environment

- Python **3.14**, venv at `./.venv` (see `AI_AGENTS.md`). Always invoke `./.venv/bin/python`.
- Backend tests: `./.venv/bin/python -m unittest` (target one module with e.g.
  `-m unittest test.library.read_blocks.test_array`).
- Python formatting: `./.venv/bin/ruff format .` (Ruff, config in `pyproject.toml`; dev deps in
  `requirements-dev.txt`). Like prettier for the frontend, `.github/workflows/build-extras.yml` runs it
  on every PR/push to main and commits the result, so it's never a blocking check.
- Frontend: `cd frontend && npm install` once; `npm run start` for the dev server;
  CI-equivalent test run: `npm run test -- --watch=false --no-progress --browsers=ChromeHeadless`.
  Needs Node `^22.22.3 || ^24.15.0 || >=26` (`engines` in `frontend/package.json`); as root or in a
  sandbox, Karma's Chrome needs `--no-sandbox` (point `CHROME_BIN` at a wrapper script). Cloud-container
  setup and headless GUI screenshots: `QA/TEST_ENVIRONMENT.md`.
- `.github/workflows/build-extras.yml` runs on every PR and push to main: `ruff format`, prettier,
  `generate_resource_doc.py`, `generate_build_configs.py` and `npm run build`, then commits the result
  (incl. `frontend/dist`). Regenerating these by hand is only needed for a branch that gets no PR.
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
- Car mesh controllers (`*-car-mesh-controller.ts`) and track props controllers (`*track-props-controller.ts`) in
  `frontend/.../editor/eac/` are copied into the nfs-web game as they are (only import paths change): keep them free
  of GUI services, depending on three.js, gg-web-engine and rxjs only. nfs-web loads the converter's gg-web-engine
  export with "Add props to obj" off, so a track's props must reach it as dummies.
- Nothing repo-specific overrides standard slash commands (`/code-review`, `/simplify`, etc.).
- Real game files for broader validation live under the gitignored `games/<game>/` folders (e.g. every
  QFS3-compressed file across nfs1/nfs2/nfs2se/nfs3), beyond the few samples in `test/samples/`.
  `test/resources/test_games_directory.py` round-trips (read → write → compare) every one of them in
  `cpu_count() // 2` processes, writing `game_files_stats.txt`, `game_files_failures.txt` and
  `game_files_regressions.txt` (gitignored) next to it, then fails if any extension has fewer passed files than in
  the `game_files_stats.txt` committed at git HEAD (committing new stats accepts them as the baseline). Extensions
  without a single read file are left out of the stats. It takes more than 10 minutes, so it's opt-in:
  `NFS_GAMES_ROUNDTRIP=1`; `NFS_GAMES_DIR=test/samples` makes it a seconds-long smoke run without the regression
  check, `NFS_GAMES_EXTENSIONS=.FSH,.QFS` limits it to some extensions (both only print the reports, without
  overwriting the files).

## TNFS track export (SIMDATA/MISC/*.TRI)

- `TriMapSerializer` writes the road spline as the curve `road_path` of `map.meta` / `map.glb` (gg-web-engine export),
  with one array per point property, in point order: slope, slant, barrier / verge distances, lanes, AI / traffic speeds
  (per chunk of 4 points), `item_mode` (raw byte value), `left_shoulder_surface_type` / `right_shoulder_surface_type`
  and `left_fence` / `right_fence` (the nibbles of `shoulder_surface_type` / `fence_flag`, left = high nibble). nfs-web
  reads these keys and mirrors the track itself (left / right arrays swapped): keep them stable and unmirrored.

## TNFS sound banks (SIMDATA/SOUNDBNK/*.BNK)

- `items` / `children` are in file order, which is not always the index order of the 128-entry offset table
  `items_descr`: every collision bank with an entry 0x50 stores it before 0x3d–0x40. `SoundBank.item_indices(data)`
  gives each entry's table index; the serializer and the GUI's bank viewer name samples with it. Never pair the n-th
  non-zero table index with the n-th entry.
- Entries can share wave data (several indices of one wav point at the same bytes). `SoundBank.read` keeps in
  `children_offsets` only the bytes between the end of the wave data seen so far and the next entry's, and `write`
  reuses identical wave data. The `*SB*` collision banks and `OSUPMB3D` still don't round-trip byte-exact: entries
  there overlap only partly (one starts inside another and runs past it, or past the end of the file).
- Output: one folder per bank, `0x<index>.wav` (16-bit) + `0x<index>.meta.json` with `loop`, `loop_start_time_ms`,
  `loop_end_time_ms` and the bank entry's `bend_range_semitones`, `volume`, `pan`, `priority`, `random_range`,
  `unknown_0x16`. Car banks (`*SW.BNK`, `TRAFFC.BNK`, `TESTBANK.BNK` with 4 samples) name their samples `engine_on`,
  `engine_off`, `honk`, `gear` instead. nfs-web reads these file names and the `loop_*` keys: keep them stable.
- A sample without a loop has `repeat_loop_length` 0 (and start 0); the serializer's `start + (length - 1)` then gives
  `loop_end_time_ms` -0.0625 (-1 sample at 16 kHz). Standalone `.EAS` files mark it with loop start 0xFFFFFFFF.
- Collision bank variants `COLL_SW`, `COLLSWWT`, `COLLSWMT`, `COLLSW3D`, `COLSWWT3`, `COLSWMT3` hold byte-identical
  wavs at 0x21–0x3a (the `*3D`/`*3` ones add 0x31–0x3b odd). From 0x3d up each has a subset: 0x3f and 0x50 in all,
  0x3e in all but `*MT*`, 0x3d in `*MT*`, `COLL_SW` and `COLLSW3D` (two different wavs), 0x40 in the `*3D`/`*3` ones;
  otherwise one index is one wav in all of them. The `*SB*` variants share only some of them. Inside a `*SW*` bank several indices are one wav, one per mixer channel of the game:
  0x2d = 0x2a = 0x2b = 0x38 = 0x3a, 0x2e = 0x26 = 0x28, 0x27 = 0x34 = 0x36, 0x29 = 0x30 = 0x32.
- All banks of a race share one 128-entry sample id table, loaded in this order: car, opponents, `COLL*`, `NFS_FMMB`;
  a later bank replaces the ids it has. So an id means the same in every race bank (not in `FRONT_MW`).
- Sample roles, as the game uses them (tnfs-1995: DOS TNFS_DOS_FULL `sfx_00066056` / `sfx_00065eb1`, PSX, Win95 SE):
  car bank 3 horn (player channel 0xe), 0x20 gear click; collision bank 0x21 light hit / prop, 0x22 medium hit, 0x23
  fence hit, 0x24 heavy hit, 0x25 landing / bump, 0x27 body scrape loop, 0x29 wind loop, 0x2d tyre squeal loop, 0x2e
  gravel squeal loop, 0x3e waterfall loop (TRI `item_mode` 14 = waterfall to the left, 15 = to the right), 0x3f AI car
  horn (opponent banks: 0x41; DOS channel 4, pitch table 0x81aa9); Win95 SE only: 0x3d left waterfall loop and 0x50
  cave drips in a tunnel, each on one track; `NFS_FMMB` 0x61 radar detector beep, 0x62 police siren loop, 0x64 police
  siren loop in a tunnel (played along with 0x62 while the player is in a tunnel). No caller found for `NFS_FMMB`
  0x69 / 0x6a. The GUI's bank viewer labels them.
- Entry fields (`SoundBankHeaderEntry`): 0x00 `voice_mask` (DOS voice allocator `sfx_voice_alloc` 0x96760), 0x0c
  `random_range` and 0x10 `pitch_offset` in cents (voice start, DOS 0x96d22: offset = pitch_offset +- random up to
  random_range), 0x17 `bend_range_semitones` (cents = (pitch - 64) * bend * 100 / 64 + offset, rate = base *
  2^(cents/1200), DOS 0xa6fbd), 0x19 `volume` (+- random 0x1a; final = master * volume * channel volume / 127^2), 0x1b
  `driver`, 0x1c `flags` (bit 0: stereo pair, the next sample is the other channel). 0x16 (`unk4`, meta
  `unknown_0x16`) is read by no binary.
- PSX TNFS has its own sound patch format, which the converter does not read: 0x08 base pitch, 0x0e ushort random
  range in cents (max 1200), 0x13 bend range, 0x17 reverb flag (voices with it get the SPU reverb in tunnels).

## EA sound banks of NFS2-NFS6 (BNKl)

- `EaSoundBank` (`resources/eac/archives`, magic `BNKl`, versions 2/4/5) holds a slot table of `EaSoundPatch` "PT"
  headers (tag list, `resources/eac/audios.py`) and the wave data. The loader picks it by magic before the TNFS `.BNK`
  rule; it is also a BIGF item (NFS3 `car.viv` `car.bnk`, `ocar.bnk`, `ocard.bnk`, `scar.bnk`; NFS4 `careng.bnk`...).
  Patch tags are written back in place, so a tag value can change but not its length; wave data is not editable.
- A patch can have several layers (tag 0xFE between them), each with its own settings and wave data: NFS3 player
  engines layer a stereo sample with a short mono loop.
- Codecs: 16-bit PCM, EA-XA v1 (`codec` 7) and v2, signed 8-bit PCM (`library/utils/audio_ea_xa_codec.py`; the EA-XA
  decoder matches the 8-bit PCM copies NFS5 keeps of the same samples). EA MicroTalk (`codec` 9, NFS3/NFS4 speech) is
  not decoded: those layers go to the bank's `skipped.txt`.
- Output: one folder per bank, `0x<index>.wav` + `0x<index>.meta.json` (`0x<index>_layer_<n>` for the next layers)
  with `loop`, `loop_start_time_ms`, `loop_end_time_ms` and the layer's named tags (`volume`, `pan`, `priority`,
  `bend_range_semitones`, `random_detune_range`...). Default sampling rate is 22050.
- Car banks: 0 and 1 engine loops, 2 gear shift (one-shot, random detune 200-250), 3 horn (loop). Opponent banks
  have the engine and the horn only: NFS2 `O<car>.BNK` in 0 and 1 (2-slot table), NFS3 `ocar.bnk` / NFS4
  `ocareng.bnk` in 0 and 3. `GEN.BNK` (NFS2 SE, NFS3) seems to keep TNFS collision bank indices: hits
  0x1d-0x25 (one-shots with random detune 250-300), loops 0x28 (scrape?), 0x29 (wind?), 0x2a-0x2d (tyre squeal?),
  0x2e (gravel?). Picked by signal analysis, not confirmed by game code or by ear.
