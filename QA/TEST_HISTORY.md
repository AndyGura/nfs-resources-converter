# Test History

Append-only. Add a new entry per pass; don't rewrite prior entries except to fix a factual error
(note the correction inline rather than silently editing away the original claim).

---

## 2026-09-06 — First QA pass (baseline)

**Commit**: `01c97f8` (branch `agent-testings`). **No prior `TEST_HISTORY.md` entry exists** — this
*is* the baseline, not a comparison against an earlier pass.

**Environment**: macOS (arm64) host; GUI exercised via the Docker/Xvfb/xdotool Linux dev-mode
recipe in `TEST_ENVIRONMENT.md`, driven with a real Chrome tab (`claude-in-chrome` MCP tools).
Neither Blender nor FFmpeg installed in the test environment.

### Scope
- Full repo read (README, `AI_AGENTS.md`, `CLAUDE.md`, both skills, frontend component tree, API
  endpoint surface, existing test suite layout) to build `APPLICATION_MAP.md`/`UI_MAP.md`.
- First-ever live GUI interaction with this app by an agent (no prior automated UI coverage
  existed to compare against).
- Golden-corpus (`test/golden_corpus/`) read+write round-trip, all 30 pre-existing files plus one
  newly added (`DVIPERDL.FMM`, copied in from `games/nfs1/SIMDATA/DASH/` this pass — see below).

### What was actually exercised live (see `TEST_PLAN.md` for pass/fail per scenario ID)
- App launch → landing page (S-1).
- Open File via the **real button + real native Tk dialog**, automated via `xdotool` rather than
  bypassed (F-1) — opened `test/golden_corpus/AL1.TRI`; confirmed the TRI 3D map viewer, its
  minimap, "Current preview FAM" dropdown, and a large (1000-item) generic array field all
  rendered correctly (S-2, V-1, E-1).
- Recent Files persistence across a full page reload (F-2).
- File → Close back to Landing Page (F-3), where Recent Files also renders on the landing page
  itself (not only in the File menu).
- Full app-menu sweep: File/Edit/View/Tools/About all opened and matched the expected structure.
- Converter dialog: opened, manual path typing into both required fields (not just Browse),
  Convert Files enable/disable logic (C-1, C-2) — **then found KI-1** when actually clicking
  Convert Files (C-3 fails in this environment/mode).
- Config dialog: opened, confirmed default field values are bare `blender`/`ffmpeg` command names
  in an environment with neither installed (G-1).
- About menu: confirmed structure and version label (`v0.0.26`) match code.

### Findings
- **KI-1** (Confirmed bug, P2): Convert Files throws server-side in Linux `--dev` mode — see
  `KNOWN_ISSUES.md` for full root-cause trace. Not yet checked against production/packaged builds.
- **KI-2** (Suspected bug): `environment.production` hardcoded `true` everywhere → dev-only debug
  menu never renders, Angular devtools globals unavailable even in dev.
- **KI-3** (Unclear): a tab that hosted a 3D/WebGL viewer stopped producing screenshots afterward,
  even off that content; JS execution/DOM introspection kept working. Worked around by opening a
  fresh tab; flagged as worth a real look at viewer teardown code.
- Golden-corpus round-trip: **31/31 pass** (read + write, no exceptions, no `error_class`) after
  adding `DVIPERDL.FMM`. 16/31 are byte-exact on re-serialization; the rest are QFS-family
  compressed formats, where a byte-exact mismatch is expected (not a bug) since the compressor
  isn't guaranteed to reproduce one specific encoding of the same decompressed content.
- Extended corpus coverage: copied `games/nfs1/SIMDATA/DASH/DVIPERDL.FMM` into
  `test/golden_corpus/` (small, 2896 bytes) after confirming it round-trips cleanly — it's a real
  in-scope TNFS SE format (`WwwwBlock`) that had zero prior coverage in the curated corpus. Also
  spot-checked `games/nfs1/FRONTEND/MOVIE/TITLE.TGV` (a `FfmpegSupportedVideo`, ~3.7MB) — parses
  fine too, but **not** added to the corpus (too large for a git-tracked fixture).
- Surveyed `games/` directory extension coverage vs. `test/golden_corpus/`: many extensions present
  in `games/` (`.INI`, `.CAN`, `.MAD`, `.SPL`, `.LOC`, `.LAY`, `.ADF`, `.SCN`, `.DES`, `.MAP`,
  `.BUN`, `.MUS`, `.LZC`, `.STF`, `.SSF`, `.LSP`, `.TGV`, `.SCC`, `.CLR`, `.ROB`, `.AIS`, `.RHO`,
  `.CAM`, `.QPS/QPL/QAS/QAL`, ...) have **no representative in the curated corpus** — most of these
  are plausibly later-title (NFS2/3/4) formats outside the current TNFS-SE focus rather than gaps
  in TNFS SE coverage specifically, but this was not individually verified per-extension. Left as
  a backlog item rather than chased exhaustively this pass — see "Not tested" below.

### Not tested (explicitly, not just omitted)
Everything in `TEST_PLAN.md` marked "Not run" — notably: Save/Reload-from-disk round trip (F-4,
F-5), New File dialog end-to-end (F-6), any negative/error-path scenario (N-1..N-4), every bespoke
viewer except TRI (V-3..V-7), custom actions and serialize/deserialize (E-6..E-8), Run Custom
Action dialog, Confirm/Error/Archive-item dialogs, `frontend`'s own `npm run test` Angular unit
suite (not run this pass — only the backend `unittest` corpus check and live GUI exploration were
performed), and macOS/Windows-native-only behaviors (pointer lock, Finder "Open With").

### Environment/tooling notes worth keeping
The Docker/Xvfb/xdotool recipe in `TEST_ENVIRONMENT.md` was built from scratch this pass (no prior
QA tooling existed) and confirmed working end-to-end, including driving the real native file-open
dialog rather than bypassing it. This is the reusable deliverable most likely to save the next
agent significant time — start there.

---

## 2026-09-06 — KI-1/KI-2 fix pass

**Commit**: fix applied on top of `1b8ac86` (branch `agent-testings`), not yet committed at time of
this entry.

**Environment**: same Docker/Xvfb/xdotool Linux dev-mode recipe as the baseline pass, rebuilt from
`TEST_ENVIRONMENT.md` (container from the earlier pass was gone; image layer cache made rebuild
fast). Neither Blender nor FFmpeg installed in the test environment.

### Scope
Fix KI-1 and KI-2 (from the baseline pass above), then re-verify both live rather than trusting the
code read.

### Changes made
- **KI-1**: `actions/gui_editor_linux.py`'s `dev_mode` branch now writes a synthetic
  `_eel_exposed.js` into `static_path` before `eel.init()`, with literal `eel.expose(null, '<name>')`
  calls for `open_arg_file`/`update_conversion_progress`/`on_append_changes` — satisfies Eel's
  static text scan without depending on a `frontend/dist/gui` build existing (which `ng serve` dev
  mode never produces on disk, so the original follow-up idea of copying a real `eel.*.js` chunk
  from there doesn't actually work in dev mode — confirmed this by reading `angular.json`'s
  `development` config, which file-replaces `api-delegate.service.ts` with a variant that inlines
  the `eel.expose()` calls directly into the main bundle rather than a separate lazy chunk).
  Production's branch (still copies the real `eel.*.js` chunk early) is untouched.
- **KI-2**: `frontend/src/environments/environment.ts` now sets `production: false`.
  `environment.prod.ts` unchanged.

### Verification (live, both confirmed fixed)
- `typeof window.ng` → `"object"` under `ng serve` (was `"undefined"`).
- Converter → Convert Files against `test/golden_corpus` (input) / a scratch temp dir (output):
  progress bar advanced live to "31 / 32 files processed"; backend log had no `AttributeError` for
  any of the three JS-exposed names. The one unconverted file landed in `skipped.txt` as expected
  (existing per-file errors unrelated to this fix: `ffmpeg` binary absent in the test container,
  one `.TRI` prop reference to a `.FAM` file not present in the pared-down golden corpus, and a few
  pre-existing `_enum_lookup`/`ValueError` tracebacks in `library/read_blocks/delegates.py` — none
  of these are new, all present in the corpus as documented in the baseline pass; not otherwise
  investigated this pass since out of scope for KI-1/KI-2).
- Opened `test/golden_corpus/AL1.TRI` via the real Open File button + native Tk dialog (not
  bypassed): toolbar now shows **"Changes (0)"** — the dev-only debug menu that KI-2 said could
  never render in any build.
- Full backend suite (`./.venv/bin/python -m unittest`, 234 tests) and frontend suite (`npm run
  test -- --watch=false --no-progress --browsers=ChromeHeadless`, 24 tests) both green after the
  change.

### Not verified (explicitly out of scope this pass)
- Production Linux build (`ng build` + `python run.py`, no `--dev`) and macOS/Windows dev mode —
  both untouched by this fix (only the Linux `dev_mode` branch changed), not independently
  re-checked end-to-end.
- KI-3 — untouched, not in scope this pass.

---

## 2026-10-10 — TNFS PBS / PDN car editors, checked against the tnfs-1995 engine

**Commit**: `d0dcdad` (branch `claude-1`). **Scope**: the `PlayerCarPhysicsBlockUiComponent` and
`CarAiAndCrashBodyBlockUiComponent` editors only, GUI-only edits on scratch copies of `games/tnfsse/SIMDATA`
`ANSX.PBS`, `TSUPRA.PBS`, `F512TR.PBS`, `ANSX.PDN`. Full report:
https://claude.ai/artifact/7UQmqmxtaK8MenZQcDqpEo.

### Findings
- Saving: 4/4 files byte-exact for the edited fields, derived fields and `checksum` recomputed, QFS3 (0x30FB) kept;
  the Win95 SE QFS3 decoder (ASM twin, `asm_runner`) reads all of them (Confirmed live).
- 24 edits driven in the tnfs-1995 engine (headless harness, see `TEST_ENVIRONMENT.md`): 17 as described, 7 show
  behaviour missing from field descriptions (TCS vs `throttle_on_ramp`, brake bias only ≤ 240, unreachable
  `top_speed`, upshift above the rev cap, `rpm_dec` both directions, PDN `speed_factor` vs catch-up glue).
- Editor issues → `KNOWN_ISSUES.md` KI-5.
- Undo / redo buttons, Reload from disk (in-app confirmation) and the `num_torques` ≤ 60 validator work
  (Confirmed live). No keyboard shortcut for undo.

### Not tested
Real game (DOSBox / Win95 SE), rally mode, PDN collision fields, `handling_factor`, 3DO `.BigSpecsFam`, the native
macOS window.

---

## 2026-10-15 — FFN font editor

**Commit**: `2425e32` (branch `claude-1`). **Scope**: `FontBlockUiComponent` (Chars / Kernings / Headers / Bitmap
tabs, Char Preview, Font Preview), save, undo, fnt + png export / import, File → New FFN. GUI driven in Chrome via the
no-Docker shortcut (`gui_editor_linux.run_gui_editor` on macOS, backend on 8001 because `pocket-ic` held 8000,
`proxy.conf.json` reverted afterwards), files opened by restarting the backend with the path. Scratch copies of
`games/` fonts only. Full report: https://claude.ai/artifact/FgTKuR5Zcp2SrTLwpkiZaw.

### Findings
- 70/70 game FFNs (NFS1–NFS6, versions 100–366) read and write byte-exact; export → import restores all glyph,
  kerning and header fields (8 fonts) (Confirmed headless).
- Char Preview move / resize / origin / advance drags, pan, wheel zoom, table edits, symbol column, add / remove
  glyph, kerning add / edit, undo, save all work (Confirmed live: MAIN18, SWISS36, BlairITC14b, Korean Gulim12 with
  20 577 glyphs, New.ffn). Import + Color Model 4Bit (alpha) + save gives a byte-exact SWISS36.
- Issues → `KNOWN_ISSUES.md` KI-6.

### Not tested
The native Serialize / Deserialize dialogs (import driven through `mainService.deserializeResource` from the console),
macOS native window, Toggle Hidden Fields on fonts, Bitmap tab pixel editing, in-game behaviour.

---

## 2026-10-15 — SHPI image editor (FSH / QFS / FAM / CFM)

**Commit**: `6b24f8b` (branch `main`). **Scope**: image viewer / editor (`ImageBlockUiComponent`, `ImageViewerComponent`),
palette editor, SHPI archive list (add / rename / delete / move, Convert all images to 8Bit), color model conversions,
mipmaps, hot spots, text, PNG and folder import, save, undo, File → New QFS, SHPIs nested in WWWW (FAM, CFM). GUI driven
in Chrome via the no-Docker shortcut (backend on 8001 because `pocket-ic` held 8000, `proxy.conf.json` reverted
afterwards), files opened by restarting the backend with the path; imports run through `mainService.deserializeResource`.
Scratch copies of `games/` files only. Full report: https://claude.ai/artifact/Eid5YRRc5x3a6QD9CSfkNP.

### Findings
- Round trip of all 2 481 game FSH / QFS / FAM / CFM (`NFS_GAMES_EXTENSIONS=.FSH,.QFS,.FAM,.CFM`, 3 min 37 s): 2 468
  read and write, 2 352 byte-exact, no regression against the committed stats (Confirmed headless).
- Headless survey (a scratch script, every SHPI of those files): 5 078 SHPIs, 63 478 images. PNG export → import keeps
  the pixels of every image; folder export → import keeps CFM SHPIs, not the others (KI-7).
- Palette edits (incl. the CFM 3D model), hot spot edits, color model changes, item add / delete, undo, save work
  (Confirmed live). Issues → `KNOWN_ISSUES.md` KI-7.

### Not tested
Native Open / Save / Serialize / Deserialize dialogs, an NFS6 DXT file in the GUI, the macOS native window,
in-game behaviour.


---

## 2026-10-16 — FFN font editor, re-check after PR #88 (image editor)

**Commit**: `0c60acf` (`main`). **Scope**: KI-6 items re-checked, plus the PR #88 image editor changes as they reach
the font's Bitmap tab. Same setup as 2026-10-15 (no-Docker shortcut, backend on 8001, `proxy.conf.json` reverted).
Scratch copies of `games/` fonts only. Full report: https://claude.ai/artifact/FgTKuR5Zcp2SrTLwpkiZaw.

### Findings
- Every KI-6 fix still holds (Confirmed live + saved files: MAIN18, SWISS36, HUDoutline12, both BlairITC14b, Editor,
  Korean Gulim12; 70/70 round-trip, export → import and add / remove glyph headless).
- New: KI-6 items 10 (4Bit (swapped) atlas flipped in memory by a write, corrupt file after a failed save + save) and
  11 (Bitmap tab opens at 10% zoom, regression from PR #88).
- PR #88 in the Bitmap tab works: grouped Color Model select, convert + undo, zoom kept on edits, background switch,
  PNG import over the atlas (keeps 4Bit), palette usage of an embedded palette, "Saved <file> (<n> bytes)".

### Not tested
Native file dialogs (imports through `mainService.deserializeResource`), Char Preview drags, macOS native window,
in-game behaviour.

### Fixes (same day, branch `fix/ffn-editor-pass2`)
KI-6 items 9–11 and the remaining lower-severity items fixed, one commit per finding (F11–F15 in the report).
Confirmed live: retried save after a failed one is byte-exact (backend: unit test + 70 FFNs packed twice), Bitmap tab
fits (753% for `Editor.ffn`), Font Preview boxes and lists missing glyphs (`SWISS36`: I X) and scrolls long lines,
advance drag edits `advance` (MAIN18) / `x_advance` (HUDoutline12), "Find glyph" 가 → row 9034 on page 91 of Korean
`Gulim12`, arrows / Shift+arrows nudge, kerning search steps through 35 pairs with V (BlairITC14b). Backend 476
tests and frontend 90 tests pass.
