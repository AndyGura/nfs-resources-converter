# Known Issues

Classification used below: **Confirmed bug**, **Suspected bug**, **Expected behavior**, or
**Unclear / needs product decision**. Don't reclassify a "Suspected" to "Expected" without actual
evidence of intent — leave it Suspected/Unclear instead.

---

## KI-1 — Convert Files fails in Linux `--dev` mode: `AttributeError: module 'eel' has no attribute 'update_conversion_progress'`

**Status**: **Fixed** (2026-09-06). `actions/gui_editor_linux.py`'s `dev_mode` branch now writes a
synthetic `_eel_exposed.js` file into `static_path` before `eel.init()`, containing literal
`eel.expose(null, '<name>')` calls for all three JS-exposed names (`open_arg_file`,
`update_conversion_progress`, `on_append_changes`) — this satisfies Eel's static text scan (see
Root cause below) without depending on a `frontend/dist/gui` build existing, which dev mode
doesn't require. Production's original early-copy-of-`eel.*.js` approach is unchanged.
**Verified live** (Docker + Linux `--dev`, per `TEST_ENVIRONMENT.md`): Converter's Convert Files
against `test/golden_corpus` now shows a live-updating progress bar ("31 / 32 files processed")
with no `AttributeError` anywhere in the backend log — see `TEST_PLAN.md` C-3/C-4.

<details>
<summary>Original report</summary>

**Severity** (at time of filing): **P2** (breaks a documented contributor workflow; does not
obviously reach packaged/production builds — not yet verified against one, see Follow-up).

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

</details>

**Remaining open follow-up** (not done as part of the fix): production-Linux and macOS/Windows
dev-mode were not independently re-verified — the fix only touches the `dev_mode` branch, so
production's already-working path is untouched, but a real end-to-end check on those other
targets is still outstanding.

---

## KI-2 — `environment.production` is hardcoded `true` in both Angular environment files; no dev-mode override exists

**Status**: **Fixed** (2026-09-06). `frontend/src/environments/environment.ts` (used as-is by the
**development** build configuration; only the **production** configuration's `fileReplacements`
swaps in `environment.prod.ts`) now sets `production: false`. `environment.prod.ts` is unchanged
(`production: true`).

**Verified live** (Docker + Linux `--dev`, per `TEST_ENVIRONMENT.md`):
- `typeof window.ng` is now `"object"` under `ng serve` (was `"undefined"` before the fix).
- With a file open (`test/golden_corpus/AL1.TRI`), the toolbar now renders **"Changes (0)"** —
  `AppComponent`'s dev-only staged-changes debug menu, previously dead in every build — see
  `UI_MAP.md`.

<details>
<summary>Original report</summary>

**Status** (at time of filing): Suspected bug (behavior was very likely unintentional, but no
direct evidence of intent either way).

**Observation**: `frontend/src/environments/environment.ts` contained `production: true`, same as
`environment.prod.ts`, with no `environment.development.ts` or equivalent providing `production:
false` for the dev build. Consequence, Confirmed (live): `window.ng` (Angular's dev-mode debug
global, `ng.getComponent()` etc.) was unavailable even under `ng serve`, consistent with the app
always running as if in production mode regardless of build configuration.

**Impact on the product itself**: `AppComponent`'s dev-only **"Changes (n)"** staged-changes debug
menu (`@if (!isProduction)` in `app.component.html`) could never render, in *any* build — see
`UI_MAP.md`. Whatever this menu was meant to help debug had no UI path to it at all.

**Impact on testing**: Angular DevTools-style console introspection (`window.ng.getComponent(...)`)
was unavailable for driving the app from a browser console; the app's own exposed `eel.*` RPCs or
real UI interaction were the workaround (see `TEST_ENVIRONMENT.md`) — `window.ng` now works too,
so this workaround is no longer required, though it remains valid.

</details>

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

## KI-4 — NFS Underground: opening a race bundle is slow, opening the city stream directly is slower

Opening `TRACKS/TRACKBnnnn.lzc` exports the whole city (all streamed sections of `STREAML1RA.BUN`, about
420 chunks and 1,300 textures) before the viewer shows anything: about 75 s and 2.3 GB of memory on a
cloud container, every time (the export is not cached). Opening `STREAML1RA.BUN` itself (92 MB) parses it
as one generic chunk bundle for the data tree: about 60 s and 3 GB, and there is no 3D view for it.
22 texture hashes used by the city are not in the track's texture packs (probably `GLOBAL/*.BIN`); those
materials show the placeholder texture.

NFSU2 Bayview (`TRACKS/L4RA.BUN` + `STREAML4RA.BUN`, 392 sections) is the same: about 95 s per open. 15 texture
hashes (race barriers, light glows, billboards, sky dome) and 46 animated `ANM_*` meshes (doors, planes,
spotlights) are not found, so about 5% of the city is untextured or missing, and there is no sky.

NFSU2 cars: the body paint (`<CAR>_SKIN1`), windows (`WINDOW_*`) and decal slots (`DUMMY_DECAL*`) are not in any
texture pack (the game makes them at run time), so those parts are untextured. NFSU2 mesh names are truncated
to 27 characters, so the LOD letter can be cut off and such meshes land in the default LOD group.

NFSMW Rockport (`TRACKS/L2RA.BUN` + `STREAML2RA.BUN`, 720 sections, 949 exported chunks, 1,623 textures) takes
about 240 s and 1.9 GB of memory per open. NFSMW cars: the body paint (`<CAR>_SKIN1`) and decal slots are made at
run time, so the body is untextured; headlights, brake lights, windows and the driver map to the car's own
`_OFF`/`WINDOW_FRONT`/`DRIVER_CUTOUT` textures. Wheel positions are not in the car's `GEOMETRY.BIN` (its position
markers are exhaust and light points), so all four wheels sit at the origin.

---

## KI-5 — TNFS car spec editors (PBS / PDN) accept edits that silently break the car

**Status**: Open (found 2026-10-10). **Classification**: Confirmed bug (items 1, 4), Unclear / needs product
decision (items 2, 3). Full report with repro steps and engine measurements:
https://claude.ai/artifact/7UQmqmxtaK8MenZQcDqpEo (private to the repo owner).

1. Letters typed into a numeric field become 0 and are recorded as a change (TSUPRA `drop_rpm_dec` "abc" → 0).
   Confirmed live.
2. No warning when an automatic `upshifts` entry is ≥ `max_rpm` × 255/256: dragging F512TR's redline to 6000
   (upshifts 7140) leaves the gearbox stuck in 1st in the tnfs-1995 engine (top speed 20 m/s). Confirmed live
   (GUI) + engine.
3. The Top speed tile shows the `top_speed` field, not the reachable speed (stock F512TR: 324 km/h shown, 309 km/h
   reached in 5th at the rev cap). Confirmed live + engine.
4. Raising `num_torques` exposes leftover entries (TSUPRA 51–59 ≈ 4×10⁹ N·m) and rescales the torque chart so the
   real curve flattens. Confirmed live.

Lower-severity items in the same report: brake pedal chart uses float ×1.25 (game: `ramp + ramp/4`), steering-rate
chart ignores the `steer_ramp_div` / `steer_ramp_mult` shifts, `drive_bias` slider thumb doesn't move after a drag,
mixed decimal formatting, Changes list prints arrays as "[object Object]".

---

## KI-6 — FFN font editor: kerning index goes stale, preview ignores font metrics, import makes the atlas 32-bit

**Status**: Open (found 2026-10-15; items 1–8 and two lower-severity ones fixed 2026-10-15). **Classification**: Confirmed bug (items 1–5, 7, 8), Suspected bug (9), Unclear /
needs product decision (6). Full report with repro steps and proposed UX changes:
https://claude.ai/artifact/FgTKuR5Zcp2SrTLwpkiZaw (private to the repo owner).

1. 16-byte NFS6 fonts: `kern_index` (first kerning row whose `right` is the glyph, 62/62 in every shipped 16-byte
   font) is a plain field, not recalculated. Deleting one kerning in `BlairITC14b` and saving left 61/62 glyphs off by
   one; Add Item appends a pair at the end, breaking the sort by right glyph. Confirmed live + saved file; in-game
   effect Inferred. **Fixed**: `kern_index` is programmatic (0 for a glyph without pairs, as in all shipped fonts), the
   writer sorts the pairs of a version > 309 font by right glyph, and the editor keeps them sorted (a changed right
   glyph moves the pair to its place). Confirmed live + saved file.
2. Font Preview reads `line_height` / `base`, which the format doesn't have: always 32 px / 25.6 px, so ascent /
   descent edits do nothing and tall fonts (NFS2 `SWISS36`) overlap. Confirmed live. **Fixed**: line height is
   `ascent + descent`, a glyph's top is the line top + `y_offset` (NFS6 capitals end at `ascent`, descenders at
   `ascent + descent`; fonts with `descent` 0 keep the line height in `ascent`). Confirmed live on `HUDoutline12`.
3. fnt + png import (`ImageSerializer.deserialize`) always makes the atlas 32-bit RGBA: file 5–7× bigger, NFS6
   palette lost. Color Model → 4Bit (alpha) afterwards is byte-exact for v100 / v101 fonts, not for NFS6. Confirmed live.
   **Fixed**: the import keeps the format of the atlas it replaces (4Bit from the alpha channel, 8Bit by the colors
   of the current palette) and its embedded palette. Export → import → save is byte-exact for all 70 game FFNs; the
   `dropshadow` flag, exported as True / False and read back as 0, now survives too. Confirmed live on `HUDoutline12`.
4. The symbol column bypasses range checks: kerning right symbol "Ж" (1046) goes into a 1-byte field and Save fails
   with `OverflowError('int too big to convert')` (file left intact). Number cells clamp silently (300 → 255).
   Confirmed live. **Fixed**: an out-of-range symbol is refused with a message ("Right glyph code must be 0..255:
   "Ж" is 1046"); number cells show their range on hover and say when they clamp; an import with a kerning `second`
   above 255 fails with a message naming it; a save error names the field and its range
   (`IntegerOutOfRangeException`, still an `OverflowError`).
5. Up / down / delete row buttons appear on hover over the `#` cell: clicking a row number to select it moved the
   glyph. Confirmed live. **Fixed**: the buttons are in a last column (sticky at the right edge, shown on row hover /
   focus) in every data table, and a click on `#` selects the row.
6. Glyphs can be reordered and given duplicate codes with no warning; all 70 game FFNs are sorted by code without
   duplicates. Whether the games need the order is Unknown. **Fixed (order)**: no move buttons, a changed code moves the
   glyph to its sorted place (one undo step) and selects it there, Add Item gives the code after the last glyph.
   A code already used by another glyph is refused with a message (the cell gets its value back). Data opened unsorted
   or with duplicate codes (imports) gets a notice above the table with "Sort now" (one undo step); the writer sorts
   glyphs by code (all versions) and kernings by right glyph (version > 309) on save anyway.
7. `num_kern` is editable in the glyph table but recalculated on save (typed 5, saved 8). Confirmed live. **Fixed**:
   `num_kern` / `kern_index` columns show only with hidden fields, read-only, with the values the save will write.
8. Import without the converter's `#custom` line (plain BMFont) and File → New give `version` 0 (no game font is
   below 100): the `version = 100` fallback in `serializers/fonts.py` sits inside the skipped `try`. Confirmed headless.
   **Fixed**: a new font has version 100 (the TNFS - NFS4 layout); a `.fnt` without `#custom` keeps the header,
   layout and bitmap format of the font it replaces, and its `xadvance` goes to `x_advance` for 16-byte glyphs
   (`advance` is 0 in all of them in the game files; the export now writes `x_advance` as `xadvance`). Importing
   each of the 70 game FFNs from its export without `#custom` is byte-exact.
9. Char Preview draws `advance` a second time as a magenta vertical line for 12-byte fonts (`x_advance` is `null`,
   passes `!== undefined`). Confirmed live.

Lower-severity items in the same report: adding / removing glyphs in v100 / v101 fonts leaves the bitmap at an
unaligned offset (**fixed**: `padding_2` is recomputed on save, see its description; add / remove checked on all 70
game FFNs), import needs both files multi-selected (**fixed**: the `.fnt` alone is enough, the PNG comes from its
`page` line; errors name what to pick), missing glyphs vanish from the preview, long preview lines are
clipped, coarse 1.8× wheel zoom with no Fit button, no glyph search, prev / next only paginator.

---

## KI-7 — SHPI image editor (FSH / QFS / FAM / CFM): imports drop data, some saves break models or images

**Status**: Fixed (found 2026-10-15; items 1–6 and every lower-severity item fixed 2026-10-15/16, item 7 mitigated: not reproduced, saves now verified and logged). **Classification**: Confirmed bug (1–6), Unclear (7). Full report with repro
steps, numbers and proposed UX changes: https://claude.ai/artifact/Eid5YRRc5x3a6QD9CSfkNP (private to the repo owner).

1. PNG import over an image (`ImageSerializer.deserialize` → `block.new_data()`, whole block replaced) keeps the
   pixels but makes the image 32-bit and drops position, pivot, hot spots, embedded palette, text and mipmaps.
   TNFS `LDIABLDH.FSH` `sped` lost its 18 hot spots (the game hangs without them). Over all game images 41 402 /
   63 478 lose a field. Confirmed live + headless. **Fixed**: the import replaces the pixels only and keeps the format
   (8Bit mapped to the image's palette, unchanged pixels keep their index, CFM 250..254 by exact color only; mipmaps
   made again when the pixels change). Re-importing every image's own export keeps all game files byte-exact that
   were before. New 32-bit images come from the archive list's "Import from disk" (several files at once).
   Confirmed live (`sped`: 8Bit, 18 hot spots, position and palette kept) + headless.
2. SHPI folder import (`ShpiArchiveSerializer.deserialize`, non-CFM) reads every file of the folder as an image in
   `os.listdir` order, names it by its first 4 characters, drops palettes, makes everything 32-bit: of 5 067 game
   SHPIs, 2 213 come back reordered, 2 991 lose palettes, 199 gain images (`spherical.png` → `sphe`), 11 fail on
   exported `.bin` items; 1.35 GB → 4.19 GB. CFM SHPIs (car_colors.json path) are fine. Confirmed headless.
   **Fixed**: the import merges into the loaded SHPI by the export's file names (item 1's pixel replacement), adds
   other images at the end as 32-bit, keeps items without a file and ignores other files; a snackbar says what it
   did. The export's duplicate-name suffix now ignores case: names differing in case only (NFS5 `AUDI` / `audi`)
   overwrote each other on macOS / Windows. Export → import keeps all 63 014 images of 5 000 SHPIs and every
   byte-exact file byte-exact. Changes inside parts the GUI has not loaded no longer abort the GUI's update
   (`TypeError ... reading 'data'`). Confirmed live (AL1_001.FAM horizon) + headless.
3. Saving 6 TNFS CFM (DVIPER, F512M, F512TR, LDIABL, LDIABLO, MP911T) and 14 FAM (TR1, CY3, TR5, TR8_R01) writes the
   ORIP `block_size` one byte short (`estimate_packed_size`), so the model re-opens as raw bytes, also after a
   texture-only edit. Confirmed live (DVIPER) + headless. In-game effect Unknown. **Fixed**: the garbage `fx_polys` /
   `labels` names of these models have a byte which is not UTF-8 (DVIPER 80 02), dropped on read, while the padding
   after the name kept its read length: the size estimate came out a byte short per name. Names keep those bytes
   now, and a `NamedIndex` is sized 12 bytes whatever its padding (a renamed label had the same problem; a name over
   7 bytes is refused on save). CY3_M01.FAM also had an empty WWWW entry (offset 0) written with the next entry's
   offset, which then read as a copy of it: written as 0 again. All 20 files re-read the same after a save; 15 are
   byte-exact, F512M / F512TR / MP911T differ in their SHPI layout / DOS palette high bits only, LDIABLO's far model
   is written 3 bytes longer (`unk_morphs`). Confirmed live (DVIPER saved after a palette edit: 3 bytes differ, model
   opens) + headless.
4. SHPI action "Convert all images to 8Bit" writes indices for a new `!pal` but keeps each image's embedded palette
   (which wins), so all 37 images of `LDIABLDH.FSH` render garbled; it also deletes non-image items. Confirmed live +
   headless. **Fixed**: images drop their own palettes, mipmaps are made again, the other items stay, the palette
   replaces the one the images use (by name: some TNFS FAM horizons have both `!PAL` and `!pal`) in place or goes at
   the end (inserting at the front shifted item indices); pixels come from `ImageSerializer.to_image` (the PNG export read duplicate names twice). Refused for CFM
   textures and for 8Bit images whose palette is not in the file (NFS2 PAUSE). Also fixed: an NFS6 image linking
   to a raw 0x69 / 0x70 block lost the link when its pixels changed size. Partial alpha (glow textures) still
   becomes opaque: the quantizer keeps one transparent entry only. Confirmed live (LDIABLDH) + headless (all game
   SHPIs).
5. Non-ASCII text in a ShpiText (or a 4-char item name) corrupts the image on save: `UTF8Block` sizes in characters,
   writes UTF-8 bytes, and its reader compares characters to bytes. Confirmed live (NFS5 `iconsRace.fsh`, "ü").
   **Fixed**: `UTF8Block` reads, sizes and pads in bytes; a value longer than a fixed-size field is refused on save
   (`DataIntegrityException` naming the field) and in the GUI's text input ("name holds 4 bytes: "Grün" is 5").
6. Color Model → DXT1/3/5 fails with `ValueError('cannot reshape array …')` on any image with mipmaps (all 3 139 are
   NFS5). Confirmed live (`skidpad.fsh`). **Fixed**: mipmaps convert level by level (DXT encodes 4x4 blocks of each
   level); DXT1/3/5 with mipmaps re-read identically (skidpad.fsh, unit test).
7. Once, Save cleared the change count without writing the file (after a DXT1 conversion and closing the Changes
   menu with Escape); 4 later saves wrote. Not reproduced. **Mitigated** (2026-10-16): no code path was found that
   clears the changes without writing (`ChangesService.on_file_saved` runs after the write). Saves are now
   verifiable: the file is flushed to disk, its size is checked before the changes count as saved (else the save
   fails with a message), every save is logged ("Saved <path> (<n> bytes)") and the GUI shows "Saved LDIABLDH.FSH
   (1 191 271 bytes)". Confirmed live. If it happens again, the log tells whether the backend saved.

Lower-severity items in the same report: Color Model offers every model with no hint for the file's game (DXT1 on a
TNFS 105×101 image, Mipmaps on a TNFS texture rewrites `position.y` 54 → 28726, new items default to 4Bit 1×1);
alias silently cut to 4 characters, unnamed items saved with an empty name, sidebar label stale after rename; the
viewer resets zoom to Fit on every edit and Fit exceeds the 1500 % limit; hot spots not draggable, `pivot` hidden;
palette edits one swatch per change, special TNFS car entries unmarked; Changes list shows colors in decimal and
bundles as "(unknown operation)"; WWWW levels titled by class name with numeric items; QFS compression not shown;
1×1 mip level of non-square images not offered; TNFS SE frontend FSH / QFS re-laid out on save (baseline).

Fixed since (2026-10-16, report ids):
- S7 format choices: the Color Model select is grouped (palette / direct color / compressed) and marks the models
  the other images of the SHPI use (`archive_image_stats`); a model none of them uses, and mipmaps when none has them
  (with the new `position.y`), ask first. New images are 32-bit (new FFN atlases stay 4Bit). The conversion dialog
  is "Convert color model" (DXT included) and explains Output colors. Confirmed live (LDIABLDH, AL1_001.FAM).
- S8 item names: a new entry gets a free name (`new0`...); the edit dialog shows the name first (raw
  `post_offset_payload` with hidden fields only); fixed-size text inputs show their size in bytes and refuse a longer
  value; the sidebar label follows a rename at once. Confirmed live (AL1_001.FAM horizon).
- S9 viewer: an edit re-renders the image keeping zoom and scroll when its size stays (no blank flash); Fit stays
  within 10..1500 %; a viewport toolbar button cycles the background checkerboard / black / white (remembered).
  Confirmed live (LDIABLDH `sped`: 966 % kept across a hot spot edit; `sstr` fits at 1500 %).
- S10 hot spots: markers can be dragged (one undoable change for x and y, relative to `pivot`); `pivot` is no longer
  `is_unknown` (verified for dashboards and horizons), so it shows without hidden fields; the TNFS FAM `horz` bitmap
  shows its horizon row (`pivot.y`) as an overlay line. Confirmed live (LDIABLDH `gate`, AL1_001.FAM `horz`).
- S11 palette: colors the images of the palette do not use are faded (`palette_usage`); TNFS car entries 250..255
  are outlined and named in the tooltip; Shift+click selects a range, Cmd/Ctrl+click toggles one (Ctrl+click is the
  context menu on macOS), "Set color" and "Shift hue" change the selection as one undoable change; the Changes list
  prints palette colors in hex and bundles as their first changes "and N more". Confirmed live (JEEP.CFM `!PAL`:
  50 colors hue-shifted in one change, undone).
- S12 navigation: archive headers read "SHPI images" / "WWWW archive" / "BIGF archive" (block description on hover);
  TNFS FAM / CFM levels are named as the export names them ("0 · background", "1 · high-poly textures"...);
  unloaded entries show the icon of their kind, guessed from their first bytes (`Slot.hint`, `__kind__` next to
  `__lazy__`), faded; duplicate names get their index; a compressed file's archive shows its algorithm (RefPack /
  QFS2 / QFS3); the archive and block-action icon buttons have accessible names. The one selection jump after a save
  was not reproduced (see item 7). Confirmed live (AL1_001.FAM, OZREC.QFS, iconsRace.fsh).
- S13 mip levels: the PNG export (and so the viewer's M0..Mn buttons) goes down to 1x1 for non-square images too
  (`mipmap_level_dims`; it stopped when the shorter side reached 1). Confirmed by unit test (4x8: 2x4, 1x2, 1x1).
- S14 SHPI layout: the reader keeps the order the item data is stored in (`heap_order`; TNFS SE menus store `!pal`
  last, MASKHI / F512M differently again) and the writer follows it while it covers every item. 98 of the 100 FSH /
  QFS / CFM files of the TNFS SE failure list now save byte-exact; LDIABLO (ORIP overlap, item 3) and MP911T (high
  bits of a DOS palette the game ignores, dropped on read) still differ. Confirmed headless.
- S15 Convert all images to 8Bit: palette type "same as the current palette" by default (32-bit when the SHPI has
  none and an image has partial alpha); a 32-bit palette keeps partial alpha (RGBA quantization); TNFS car textures
  (CFM) convert with their colors on 0..249, the light bar / tail light pixels on 250..254, transparent on 255,
  `!xxx` left alone (it was refused). Confirmed headless (AQUA.QFS glows: alpha error 0.97; JEEP / DVIPER textures
  unchanged on screen, light entries kept) + live (JEEP dialog default, car unchanged). The first click on Run after
  closing a select in the dialog is taken by the select's overlay (Angular Material), left as it is.

---

## Unknown / not yet investigated (flagged, not silently assumed fine)

- Compressed formats (QFS-family, JDLZ) are written back as their original compressed bytes while the
  decompressed bytes are unchanged (`CompressedData` in `resources/eac/archives/compressed_block.py`), so they
  round-trip byte-exact when the inner format does. After an edit they are recompressed with QFS2 (JDLZ for
  `.lzc`), which doesn't reproduce the original byte stream and can be bigger (alps.fsh: 9.0 MB to 18.7 MB).
- NFS6 BIGF archives store header `length` as header size plus item lengths, without the padding between items
  (car.viv, skin.viv); `BigfBlock` keeps that convention when the read value matches it, so they round-trip
  byte-exact. `persist.viv` (described earlier as "file size minus 14") was not re-checked.
- NFS6 track geometry is probably exported mirrored: car models show that EAGL space is right-handed (license plate
  text reads correctly only with a rotation), while `EaglModelSerializer` (non-car) and the NFS6 route serializer
  swap Y and Z, which is a mirror. **Unverified** on a track (no NFS6 track sample in the repo).
- NFS3 COL props (track-wide `prop_descriptions`/`props_7` of `TRnn.COL`, e.g. an airliner and a 55 m column in
  TR00.COL) have texture numbers that don't match the track's `TRnn0.QFS` (nor the FRD `texture_blocks`): they get
  wrong textures, so the GUI hides them unless hidden fields are shown (`is_unknown` dummy property). **Unclear**
  which archive textures them, or whether the game shows them at all.
- NFS2-NFS4 animated props: the unit of `anim_delay` is not confirmed; the converter writes `frame_duration`
  assuming 64 units per second. NFS4 animated extra objects are read like NFS3 ones (16.16 positions, 2.14
  quaternions), not verified on a file that has them (GT1.FRD has none). The NFS3
  lane markings (FRD polygon chunk 6, `is_lane` texture blocks) are not rendered: their textures are not in the
  track QFS.
- NFS Underground city handedness: chunks keep game coordinates (Z up), the same as the NFSU car viewer.
  Whether that mirrors the city compared to the game (look at text on signs) is not verified.
- macOS-specific native behaviors (pointer lock for 3D free-fly camera, Finder "Open With" /
  file-association open events, the pointer-lock "funk beep" suppression) — read from code
  (`actions/gui_editor_macos.py`), never exercised live this pass (this pass ran entirely inside a
  Linux container).
- File → Close with unsaved changes: does it warn, or silently discard? Not verified — see
  `TEST_PLAN.md` F-9.
- Archive viewer (generic, non-`Wwww` container) and its add/edit-item dialogs: no sample file
  identified this pass that renders it — coverage is currently zero, live or otherwise.
