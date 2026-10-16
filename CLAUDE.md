# TailsLab

TailsLab (formerly NFS Resources Converter) is a parser/converter library + GUI app for binary resource files from
EA's **Need For Speed** series (games 1–9, TNFS to NFS Most Wanted). The deepest coverage is **The Need For Speed SE**
(1996, PC / "TNFS"); many EA Canada formats (FSH images, FFN fonts, ...) are shared across later titles too. The repo,
Python packages, settings / log file names, `~/.nfs-resources-converter` cache, Windows ProgIDs / installer `AppId` and
the `NFS_RESOURCES_CONVERTER_*` env vars keep the old name (renaming them would lose users' settings or duplicate
installs). Output feeds
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
| `library/lazy.py` | Lazy parts: `LazyDict` archive entries / bundle chunks parsed on first access, untouched ones written back as original bytes; file and memory sources. `require_file` is lazy by default (`lazy_loading` setting). The GUI receives unloaded parts as `__lazy__` markers and fetches them with `load_lazy_part` when shown. |
| `library/loader.py` | File-type auto-detection (`probe_block_class`) by extension/magic bytes; top-level `require_file`/`require_resource` with an in-process file cache bounded by the `file_cache_size` setting (least recently required files dropped, `pin_file` keeps the GUI's open file). |
| `library/changes_service.py` | Tracks unsaved GUI edits against the loaded data tree. |
| `library/utils/asm_runner.py` | 32-bit x86 snippet interpreter (IDA syntax) used to execute and progressively port disassembled game routines; production code never uses it, the ASM-driven decompressor twins in `test/resources/eac/archives/test_compressed_block.py` do. |
| `resources/eac/` | EA Canada format definitions built from `read_blocks` primitives (bitmaps, archives, fonts, audio, geometries, maps, car specs, TNFS replays). Shared across many NFS titles. `compressions/` holds the pure-Python decompressors and compressors (RefPack, QFS2, QFS3, NFSU's JDLZ, NFSU2's HUFF = QFS3 behind a 16-byte header) behind `EacCompressedBlock`, which writes a resource back with the algorithm it was read with (`compression_flags` in its data, new data gets RefPack). Formats, game addresses and compressor notes: `resources/eac_compressions.md`. Compressor output is checked with the games' ASM decoders in `test_compressed_block.py`. |
| `resources/eac/maps/`, `resources/eac/geometries/` | Per-game specializations (`tnfs.py`, `nfs2.py`, `nfs3.py`, `nfs5.py`, ...). |
| `resources/common/` | Vendor-neutral formats reused as fallbacks (e.g. Targa image). |
| `resources/blackbox/` | Blackbox-studio (later NFS titles) formats, NFS Underground 1, 2 and Most Wanted: `chunks.py` (generic id+length chunk dispatch helpers), `geometries/` (car and world geometry packs), `bitmaps/` (texture packs, TPK), `maps/` (chunk bundles, scenery, streaming sections; `NfsuTrackBundle` is a race's `TRACKBnnnn.lzc` or an NFSU2/NFSMW location bundle `LxRA.BUN`), `archives.py` (JDLZ-compressed files). |
| `resources/eac/fields/` | Small reusable domain blocks: `Point2D`/`Point3D`/`RGBBlock`, angle/time fields. |
| `resources/*.md` | **Auto-generated** per-game docs (`generate_resource_doc.py`). Never hand-edit — edit the block definitions/descriptions and regenerate. |
| `serializers/` | Turn parsed block data into common output formats and back. One serializer class per resource kind, returned by a block's `serializer_class()`. |
| `api/` | Python↔JS bridge (pywebview/eel) exposing library + serializers to the GUI. |
| `frontend/` | Angular GUI. `.../editor/library/*.block-ui` = generic components, one per `read_blocks` base class. `.../editor/eac/*` and `.../editor/common/*` = bespoke rich viewers (image, 3D geometry, map, audio, font, hex/targa, TNFS car specs) and widgets they share (`curve-editor` = editable SVG charts, `stat-tiles`). |
| `actions/` | OS-integration entry points (convert all, open in GUI editor, uncompress) wired to file-manager context menus / installers. |
| `test/` | unittest suite mirroring `library/`/`resources/`. `test/golden_corpus/` + `test/test_gui_golden_corpus.sh` = manual smoke test that opens every sample file through `run.py`. |
| `icons/` | App icon source (`tailslab.png`) and the per-platform icons made from it by `icons/generate_icons.py` (also writes the GUI's favicon and `assets/logo.png`). |
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
- GUI log: `~/nfs-resources-converter-logs.log` (`config.LOG_FILE_PATH`), Python logging and stdout/stderr. Every
  save logs "Saved <path> (<n> bytes)"; `save_file` checks the size on disk and returns it, the GUI shows it.
  `frontend/src/assets/js-error-logger.js` (loaded by `index.html` before the Angular bundle) sends uncaught JS
  errors, scripts that fail to load and `console.error` to it through the `log_frontend_message` endpoint, every line
  prefixed `[JS]`. On Windows the GUI needs the Edge WebView2 Runtime: without it pywebview falls back to MSHTML (IE11,
  white window), so `gui_editor_windows.py` shows a message box and exits instead; the installer installs the runtime.
  `gui_editor_windows.py` also maps `.js` / `.mjs` / `.css` to their standard types in `mimetypes`, which takes them from
  the Windows registry (`.js` is often `text/plain` there, and the web view refuses module scripts with it).
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
- Conversion settings presets (`config.py`): "No preset" is the `[Conversion]` section, a user-defined preset is a
  `[Conversion: <name>]` section with the conversion settings and input / output paths (everything but
  `selected_preset`, see `CONVERSION_NON_PRESET_KEYS`); a setting missing in a preset takes the built-in default.
  `run.py convert --preset "<name>"` (input and `--out` default to the preset's paths) and the GUI converter's preset
  select use them; a new conversion setting goes into `ConfigManager._get_defaults()` and the converter's form.
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
- Unit tests never read `games/`: it is gitignored and empty in CI, so such a test is skipped there or breaks.
  `test_games_directory.py` is the only exception. A test that needs a real file uses a copy committed to
  `test/samples/` (keep it small); `games/` is for probe scripts and the opt-in round-trip only.

## TNFS track export (SIMDATA/MISC/*.TRI)

- `TriMapSerializer` writes the road spline as the curve `road_path` of `map.meta` / `map.glb` (gg-web-engine export),
  with one array per point property, in point order: slope, slant, barrier / verge distances, lanes, AI / traffic speeds
  (per chunk of 4 points), `item_mode` (raw byte value), `left_shoulder_surface_type` / `right_shoulder_surface_type`
  and `left_fence` / `right_fence` (the nibbles of `shoulder_surface_type` / `fence_flag`, left = high nibble). nfs-web
  reads these keys and mirrors the track itself (left / right arrays swapped): keep them stable and unmirrored.
- Fences follow the game's `tnfs_render_track_fence` (SE 0x44a2b4, DOS 0x69719, PSX 0x80046484; `TerrainChunk.build_fence`):
  only the chunk's `fence` byte decides them (`fence_flag` of the spline points is collision only). One vertical quad per
  node, 2 m or 0.9 m (`is_low`) high, standing on the terrain vertex picked by the `item_mode` of the chunk's first node
  (`TerrainChunk._fence_columns`: right A2; left A7, or A8 for 1 and 14..18, lane split / merge mixed; tunnels 7, 9, 12,
  13 none). The vertex comes from the rows the terrain polygons use (`_terrain_rows`), so it stays on the rendered
  edge across the lane split / merge vertex shuffling. Texture id `texture_id` + 32; closed tracks use `ga00` / `ga10`
  / `ga20` for the ids of `fence_texture_id` // 3. The name gets the on-disk case of the FAM bitmap (S3 is case
  sensitive; `GA00` in TR3-TR5, `ga00` elsewhere), and a chunk whose texture the FAM lacks gets no fence, as in SE
  (TR4's 109 chunks with texture `18B0`). UV: half a texture width per node, like the terrain along the road.
- Z-buffer workaround (the game paints the fence over its row's terrain): where the terrain rises (nearly) vertically
  outwards from the fence vertex (within `FENCE_WALL_MAX_ANGLE`), the fence bottom moves `FENCE_WALL_SHIFT` towards
  the road along the terrain edge, or the wall and the fence z-fight (TR7, TR4). Mesh names are
  `terrain_chunk_{i}_{left|right}fence_{texture}`: nfs-web picks the material from the text after the last `_`.
- Props are dummies `proxy_<n>` (`_prop_json`) with properties `is_prop`, `type`, `road_index`, `object_index` (index
  in the TRI `props` array, the game's road object index for `get_sign_status`) and `object_rotation` (raw 8-bit
  `rotation` byte; a knocked-down bitmap sign falls the other way when > 64), plus the model / texture keys of the
  prop type. nfs-web reads them: keep them stable.

## TNFS horizon (SIMDATA/*TRACKFM/*.FAM, bitmap `horz`)

- `ShpiArchiveSerializer` writes `spherical.png` (2048x1024 equirectangular, eye level in the middle, heading 0 at the
  centre) with `library/utils/nfs1_panorama_to_spherical.py`, which places `horz` as Win95 SE draws it: ring type 0
  scrolls it (1280 texels per turn, 2 px rows at 640x480, row `pivot_y` on the horizon line), ring type 1 draws a ring
  of 180 degrees per bitmap (mirrored second half with the mirror flag), texel rows 1..H-2 over
  `ring_y_offset +- ring_height` px. Screen px become angles with the focal length of the 96 degrees chase cameras
  (320 / tan(48 deg)). Settings: `MISC/<track>INFO` for `_T01` FAMs, the executable's table (`SE_HORIZON_SETTINGS`)
  otherwise. nfs-web makes cube map faces of `spherical.png`.

## SHPI images (`EacImage`, `resources/eac/bitmaps.py`, all games up to NFS6)

- Bytes 1..3 of an image (`next_offset`), and of every block attached to it, link to the next attached block (0 in the
  last): palette (0x22/0x24/0x29/0x2A/0x2D), hot spots (0x7C, `ShpiHotSpots`), text (0x6F), NFS6 0x69 / 0x70 (unparsed,
  kept as raw bytes). Never a block size. The parser follows the links (`chained_block_criteria`), `write` relinks the
  parsed blocks (`_link_chained_blocks`); the `next_offset` fields are programmatic only for the GUI to show them
  read-only. NFS6 0x69 / 0x70 blocks stay in the entry's `post_offset_payload`: an image linking to one without a
  parsed block first has `pad` (empty when the block follows the pixels), and `write` points `next_offset` past the
  pixels + `pad`, so the link survives a size change. TNFS has negative offsets (to `!PAL`) and garbage in some CFM /
  FAM textures without attached blocks: no `pad`, written as read.
- Mipmaps exist only in NFS5: the 4 high bits of `position.y` hold the level count (always the full chain), each level
  is padded with zeros to 16 bytes. `write` sets the count from `mipmaps`.
- Hot spots: TNFS reads them only in the dashboard loader (`dash`, `tach`, `sped`, `gate` of `DASH/*DH|DL.FSH`, it hangs
  without them); point + `pivot` is the pixel of the bitmap. The GUI's image editor draws them over the image
  (`ImageViewerComponent.overlays`, toggled in its viewport toolbar).
- PNG import over an image (`ImageSerializer.deserialize` with the image's id) replaces its pixels only: format,
  position, pivot, hot spots, text and palettes stay, 8Bit pixels take the index of their color in the palette the
  image is exported with (the same index where unchanged, else the first exact, else the nearest; a CFM's 250..254 by
  exact color only), mipmaps are made again when the pixels change. Re-importing its own export keeps every game file
  byte-exact. New images come in as 32-bit: `ImageSerializer.new_image_data`, used by SHPI folder import and by the
  archive list's "Import from disk" (`SerializationAPI.new_images_from_files`, several files, one undoable change).
- SHPI folder import (`ShpiArchiveSerializer.deserialize`, not CFM: those go through `car_colors.json`) merges into the
  loaded SHPI: files match items by the names the export gives them (`export_file_names`: escaped name, `0`, `1`...
  appended to a name taken ignoring case, as Windows / macOS file systems would merge them). A matching image replaces
  the pixels as above, a `.pal.txt` the palette, another image file is a new 32-bit item at the end; items without a
  file stay, other files (`skipped.txt`, `.bin`, `spherical.png`, `_mm_n` levels) are ignored. Exporting every game
  SHPI and importing the folder back keeps every file byte-exact. `deserialize_resource` returns the importer's
  `deserialize_report`, shown in a snackbar.
- SHPI "Convert all images to 8Bit" (`ShpiBlock.action_convert_to_8bit`): the images as they look (`to_image`)
  quantized onto one palette, which replaces the palette the images use (`_get_palette_from_shpi`, by the names of
  `SHPI_PALETTE_NAMES` in order: some TNFS FAM horizons have both `!PAL` and `!pal`) in place, or is added at the end
  (NFS2 tracks pick textures by index); images drop their own palettes, mipmaps are made again, other items stay.
  Refused for CFM textures (lights at 250..254) and for 8Bit images without a palette in the file (NFS2 PAUSE).
- Changes the backend makes (imports, custom actions) reach the GUI diffed: entries added to an archive as
  `array_insert`, the rest as `set`; the GUI skips changes inside lazy parts it has not loaded (they come from the
  backend, with the change, when shown), except values an unloaded part already shows (an archive entry's alias).

## TNFS car models (SIMDATA/CARFAMS/*.CFM)

- `OripGeometrySerializer` splits meshes by texture and by ORIP `labels` (polygon indices): mesh names
  `lbl__<label>__<texture>` (`lbl__lt_frnt`, `lbl__bkll__rsid`...), nfs-web reads them. Labels and `fx_polys` with a
  garbage name (DVIPER bytes 80 02, LDIABL e0 01) are left out (`is_orip_name`): `NamedIndex` reads names with
  bytes which are not UTF-8 kept as U+DC80..U+DCFF (`NullTerminatedUTF8Block(errors='surrogateescape')`), so the
  file writes back byte-exact but such a name cannot go to a UTF-8 text file. A `NamedIndex` is always 12 bytes
  (`estimate_packed_size`), whatever the stored padding, so ORIP `block_size` stays right after a rename. ORIP `fx_polys` are vertex
  indices (wheel ground points `FL0`..`RR1` / `fl0`..`rr1`, engine point `smok`, `d`): they go to the meta as dummies
  `fx_<name>` with properties `fx` and `vertex` (`orip_fx_dummies`), at the vertex in mesh space. Field descriptions in
  `resources/eac/geometries/tnfs.py` list what each name marks and which fields the game code reads.
- A mesh holds polygons of one ORIP partition (`inside` / `surface` / `outside`, the game's draw order) only
  (`orip_sub_mesh_names`): when a label + texture group spans several, the partition with most of its polygons keeps
  the name, the others get `__<partition>` (`rsid__inside`; `__none` for polygons in no drawn partition, e.g. only in
  `NON-SORT`). The partition goes to the node extras (`{"partition": "inside"}`, three.js `userData`) through
  `Scene.object_properties`.
- The morphs `left_tur` / `right_tu` (front wheel steering) become glTF morph targets `left_turn` / `right_turn`
  (`mesh.extras.targetNames`, weights 0) of the meshes with moved vertices (`SubMesh.morph_targets`, deltas in mesh
  space). The gg-web-engine Blender exporter writes no morph targets, so `export_scenes` adds them to the written GLB
  (`serializers/common/three_d/glb_morph_targets.py`, glTF vertices matched to sub-mesh vertices by position). The
  delta vectors are the ORIP vertices after `num_shape_vrtx`, which no polygon uses, so they never become geometry.
- Textures use `!PAL` of their SHPI. `!xxx` beside it is the car's slice of the shared 8-bit VGA palette (Win95 SE
  `gfx_car_palettes_setup` 0x4572e0: first 23 colours to entries 0x30 / 0x48 for player / opponent, 8 for traffic), never
  a texture palette; junk in the `M*.CFM` models (single race / tournament opponents, `CARFAMS/CARPAL.FSH` instead), and
  often typed 0x7B (an 8-bit "bitmap" 256x1 / 256x3). `ShpiArchiveSerializer` writes no file for it.
- `car_colors.json` (`serializers/misc/tnfs_car_colors.py`, next to the PNGs of each CFM textures SHPI) lists PNG colours
  the game draws otherwise, with the textures having them, with the same keys for every car (the game, not the file,
  makes a car the cop, so a modded model can be either): `tail_lights` (index 254: `texture_color`, `off` / `on` from the
  executable's per-model tables, the common ones for an unknown model), `light_bar` (250..253: `texture_colors`, the
  cop's `siren_colors` / `siren_colors_swapped`, `swap_interval_ms`; black on other cars), `palette_slice` (the first 24
  `!xxx` colours, when it holds colours). CFM textures are exported with `car_texture_palette`: a colour of 250..254
  shared with another palette entry is moved to the nearest free one (deterministic; no shipped file has one), so
  recolouring a PNG colour hits those pixels only. `ShpiArchiveSerializer.deserialize` of a CFM SHPI
  (`deserialize_tnfs_car_textures`) builds what the game needs from the PNGs + `car_colors.json`: 8-bit textures on one
  256-colour `!PAL` (0x24, `unk1` 3 = shape height), 0..249 the PNG colours (exact up to 250, else median cut without
  dithering, deterministic), 250..254 the JSON's marker colours (pixels of exactly them), 255 alpha 0, `!xxx` (0x22)
  from `palette_slice` or black (always in the high-poly SHPI: the loader looks it up), directory `WRAP`; textures by
  name. Exported PNGs + JSON re-import to the same PNGs + JSON (all shipped CFMs). `TnfsCarMeshController` (`tailLightsOn`, `lightBar` 'black' / 'siren'
  / 'texture', `sirenActive` + `updateLights`) recolours the PNGs with it, also in models without the wheel labels
  (COPMUST, low-poly: `hasWheels` false, no tyres / steering); the GUI shows the light controls for every CFM model.
  nfs-web reads these keys: keep them stable.
- OBJ + MTL import (`OripGeometrySerializer.deserialize`, `serializers/misc/orip_import.py`, CFM cars and FAM props
  alike; OBJ reader `serializers/common/three_d/obj_reader.py`) is the inverse of the export: OBJ axes are ORIP with y
  and z swapped (Blender: export with forward Y, up Z, as the converter imports it), quads are found again in the
  export's triangle pairs (the pair order tells `flip_normal`), two-sided polygons in a polygon followed by its
  reverse, corner UVs mean no `use_uv`. Labels and partitions come from the mesh names (`__<partition>` suffix,
  extras `objects`, else the current mesh of that name), textures from MTL material names (FSH bitmap names, 4 bytes
  at most) or `map_Kd` file names. What an OBJ cannot hold comes from the ORIP being replaced: material fields and
  polygon type bits of the same texture, lookup-only materials (`tire1`..`tire4`, `pal`), non-wheel `fx_polys`
  positions, morphs whose vertices are all still there. Wheel `fx_polys` are the bottom corners of the wheel quads,
  missing steering morphs are rotations by 30 degrees of the front wheel quad and its `circ` quad. UVs are scaled to
  texels with the size of the `map_Kd` / `assets/<name>.png` image. Those textures go to the SHPI next to the ORIP when
  they differ from its own export (`_import_textures`: the SHPI's export with the folder's `assets` files and the
  `map_Kd` images over it, imported with the SHPI folder import, so a CFM's SHPI is made again); the serializer leaves
  it in `deserialize_related`, which `deserialize_resource` applies in the same change bundle. The export of every ORIP of `test/samples/TSUPRA.CFM`
  imports back to the same polygons, fx points and morphs (`test/serializers/test_orip_import.py`).

## TNFS car specs (SIMDATA/CARSPECS/*.PBS, SIMDATA/CARFAMS/*.PDN)

- `resources/eac/car_specs.py`, field meanings and readers verified against the DOS, Win95 SE and PSX code
  (tnfs-1995). Value formats follow the game: 16.16 fixed point, 8.8 for `thrust_scale` / `force_to_accel` /
  `unknown_0x320*` / `gear_efficiency`, plain ints for 24-bit angles (`slip_cutoff`, `auto_steer`, PDN
  `handling_factor`; 0x1000000 = full turn; `slip_cutoff` and `handling_factor` are `IntegerAngleBlock`s, so the GUI
  shows them in degrees / radians while the data stays the int), raw u8 grip tables (grip = value / 128). Derived fields (`mass`, inverses,
  `brake_bias_r`, `force_to_accel`) and the PBS `checksum` are programmatic (all 9 PBS and 22 PDN round-trip byte-exact).
- nfs-web (`classic-world/utils/load-pbs.ts`) reads `*.PBS.json` keys: body_len, body_width, brake_bias_f,
  max_brake_force_1, drag, drive_bias, final_drive, force_to_accel, friction_f, friction_r, gear_ratios,
  incar_camera_height, lat_acc_cutoff, mass, max_rpm, min_rpm, mps_to_rpm, num_torques, rpm_acc, rpm_dec, torques,
  upshifts, wheel_base, wheel_track. Renaming one or changing its value format breaks it: tell the nfs-web side.
- GUI: `PlayerCarPhysicsBlockUiComponent` / `CarAiAndCrashBodyBlockUiComponent` (`frontend/.../editor/eac/`)
  edit them on charts (torque / power, gearing, grip tables, pedal ramps, brake caps; PDN AI acceleration, top speed
  markers, corner slowdown). Their derived curves follow the formulas in the field descriptions: keep the two in sync.
  Programmatic fields (`mass`, inverses, `force_to_accel`, checksum) are recomputed on save only, so the charts compute
  from the source fields.
- TNFS 3DO `DriveData/CarData/*.BigSpecsFam` (`Tnfs3doCarPhysics`, doc `resources/TNFS_3DO.md`): a big-endian wwww
  archive of 3 fixed items, the PBS physics fields without `max_brake_force_2` / `gear_efficiency` / checksum, then
  the front and rear grip tables. The block subclasses `PlayerCarPhysics` and builds its `Fields` from the PBS ones
  (big-endian copies, `_TNFS_3DO_REPLACED_FIELDS` for the slots with another meaning on 3DO: `max_brake_force` in m/s²,
  `front_grip_mult` / `rear_grip_mult` and inverses, `burnout_div`); `_TNFS_3DO_DESCRIPTIONS` has a description for
  every field, from the 3DO `LaunchMe` code (tnfs-1995 Ghidra). The PBS editor renders it through the
  `block_class_mro` fallback and switches on `is3do` (no gear efficiency column, one brake cap).

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
  gravel squeal loop, 0x3e waterfall loop (TRI `item_mode` 14 = waterfall to the left, 15 = to the right), 0x3f traffic
  horn loop (DOS channel 4, pitch value `table[index] * doppler >> 8`, table at DOS 0x81aa9, index = the traffic car's
  PDN `gear_count`); opponent banks `O*MB.BNK` / `TRAFFCO.BNK` 0x41 the opponent car's horn loop (racers: car slot 1,
  pitch index 1, channel 4, DOS `tnfs_sfx_horn_other` 0x82cd4); Win95 SE only: 0x3d left waterfall loop and 0x50
  cave drips in a tunnel, each on one track; `NFS_FMMB` 0x61 radar detector beep, 0x62 police siren loop, 0x64 police
  siren loop in a tunnel (played along with 0x62 while the player is in a tunnel). `NFS_FMMB` 0x69 / 0x6a are one-shots
  (0.19 s, 0.65 s, voice mask bit 8, priority 0x64) that no code in DOS or SE plays. The GUI's bank viewer labels them.
- Entry fields (`SoundBankHeaderEntry`): 0x00 `voice_mask` (DOS voice allocator `sfx_voice_alloc` 0x96760), 0x04
  `eacs_header_offset` (a pointer after load), 0x08 `play_time_limit` in driver ticks (voice+4 = value - 1, the driver
  tick DOS 0xaada7 / SE 0x4a4ac0 stops the voice below 0; 0 = no limit, in every shipped entry), 0x0c
  `random_range` and 0x10 `pitch_offset` in cents (voice start, DOS 0x96d22: offset = pitch_offset +- random up to
  random_range), 0x17 `bend_range_semitones` (cents = (pitch - 64) * bend * 100 / 64 + offset, rate = base *
  2^(cents/1200), DOS 0xa6fbd), 0x19 `volume` (+- random 0x1a; final = master * volume * channel volume / 127^2), 0x1b
  `driver` (written by the demo's bank loader 0x79a62 at run time: non-zero 0x1b and later bytes in shipped banks are
  leftovers), 0x1c `flags` (bit 0: stereo pair, the next sample is the other channel). 0x15 (`unk3`, 0x80 everywhere)
  is copied to voice+0x14 by DOS and the demo and never read; 0x16 (`unk4`, meta `unknown_0x16`) is read by no binary
  (DOS, demo, SE), probably an authoring transpose.
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
