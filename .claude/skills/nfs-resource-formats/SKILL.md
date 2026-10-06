---
name: nfs-resource-formats
description: Use when adding support for a new NFS game file format, or new/unknown fields to an existing one, by composing existing library/read_blocks primitives into resources/*.py block definitions — plus wiring file-type detection, serializers, docs and tests for it. Includes a cheat-sheet of every existing reusable block, so check here before inventing a new primitive. NOT for extending the parsing framework itself — use read-block-framework for that.
---

# NFS resource format development

> Keep this file in sync with the codebase: if something here is wrong, stale, or missing (a block
> that no longer matches its description, a new reusable block worth adding to the cheat-sheet,
> a directory that moved), fix it as part of your change. Describe only the current state, dry and
> reference-like — never change-log prose ("used to be X", "was migrated", "no longer exists"). If
> something's gone, remove its mention instead of noting its removal.

Adding or fixing a file format here almost always means **composing existing blocks**, not writing
new parsing primitives. Skim the cheat-sheet below before reaching for `read-block-framework`.

## Where things live

| Path | Contents |
|---|---|
| `resources/eac/` | EA Canada formats shared across many NFS titles: `bitmaps.py` (EacImage/EacPalette), `archives/` (SHPI/WWWW/BIGF/SoundBank/compressed), `fonts.py`, `audios.py`, `videos.py`, `geometries/`, `maps/`, `car_specs.py`, `configs.py`, `misc.py`, `compressions/` (RefPack, QFS2, QFS3, JDLZ decompressors; porting new ones from disassembly → skill `asm-runner-porting`). |
| `resources/eac/maps/{tnfs,nfs2,nfs3,nfs6,nfs_common}.py`, `resources/eac/geometries/{tnfs,nfs2,nfs3,nfs4,nfs5,nfs6}.py` | Per-game specializations of a shared concept. |
| `resources/common/bitmaps/targa_image.py` | Vendor-neutral TGA, used as an `AutoDetectBlock` fallback. |
| `resources/blackbox/` | Blackbox-studio (NFS Underground) chunk bundles: every file is a tree of u32 id + u32 length chunks (bit 0x80000000 = container), payloads padded with 0x11 bytes to 16-byte (vertices, textures: 128-byte) absolute file offsets. `chunks.py` has `chunk_delegate`/`nfsu_sub_chunks_field` to dispatch sub-chunks by id (unknown ids fall back to raw bytes); `maps/nfsu.py` `walk_nfsu_chunk_ids` is what the loader uses to recognise a bundle. Geometry packs (`geometries/nfsu.py`), texture packs (`bitmaps/nfsu.py`), scenery and streaming sections (`maps/nfsu.py`). |
| `resources/eac/fields/misc.py`, `resources/eac/fields/numbers.py` | Small reusable domain blocks: `Point2D`/`Point3D`/`RGBBlock`, `Nfs1Angle8`/`Nfs1Angle14`, `Nfs1TimeField`. Check here before writing a new one. |

## Cheat-sheet: existing blocks (import from `library.read_blocks` unless noted)

**Leaves**
- `IntegerBlock(length, is_signed=False, byte_order='little')` — fixed-width int.
- `FixedPointBlock(length, fraction_bits, ...)` — int with N fractional bits, read/written as float.
- `DecimalBlock(length ∈ {4,8}, byte_order)` — IEEE float/double.
- `EnumByteBlock(enum_names=[(int, str), ...], raise_error_on_unknown=False)` — 1-byte enum, unknown
  values pass through as their stringified number unless `raise_error_on_unknown`.
- `UTF8Block(length)` / `NullTerminatedUTF8Block(length)` / `LengthPrefixedUtf8Block(length_block)`
  (`library.read_blocks.strings`) — fixed/null-terminated/length-prefixed text.
- `BytesBlock(length, allow_negative_length=False)` — raw bytes; `length` may be an int, a
  `lambda ctx: ...`, or `(lambda ctx: ..., "doc string")` to control what `size_doc_str` shows.
  `Padding(to, is_global=False)` — `BytesBlock` subclass that pads up to an absolute/local offset.

**Containers**
- `CompoundBlock(fields=[(name, block, extras), ...])` / `DeclarativeCompoundBlock` (fields declared
  as a nested `Fields` class — the pattern almost everything uses, see below).
- `ArrayBlock(child, length)` — `length` int or `lambda ctx: ...`.
  `LengthPrefixedArrayBlock(length_block, child)` — length read from a leading field.
  `SubByteArrayBlock(length, bits_per_value, value_deserialize_func=None, value_serialize_func=None)`
  — packed sub-byte values (e.g. 4-bit-per-pixel bitmaps).
- `SubByteCompoundBlock(schema=[(bits, alias, type, details, description), ...])` — bitfields packed
  into an integer; `type` is `'boolean' | 'number' | 'enum'`. `BitFlagsBlock(flag_names=[(bit, name), ...], length)`
  — convenience subclass, one boolean per bit.
- `OptionalBlock(child, criteria, default_value=None)` — reads `child` only if
  `criteria(ctx)` is true (or `(criteria, "doc label")`), else `default_value` (defaults to
  `child.new_data()`). For presence gated by data available identically on read and write (a
  version field, a flag, a pointer being non-zero) - see `GlyphDefinition`/`FfnFont` in
  `resources/eac/fonts.py`.
  `TrailingOptionalBlock(child, criteria=None)` (`library.read_blocks.optional`) — same idea for
  presence only observable while reading: leftover space at the end of a structure/file (default
  criteria: `ctx.read_bytes_remaining > 0`), or a custom `criteria(ctx)` that peeks at upcoming
  bytes (`ctx.buffer.read(n)` then `ctx.buffer.seek(-n, SEEK_CUR)` to undo the peek) and checks
  whether they look like the expected format - the way to parse a sequence of same-shaped,
  independently-optional trailing chunks in a known order (stack one `TrailingOptionalBlock` per
  chunk, each sniffing its own signature), e.g. a bitmap's optional mipmaps/palette chunks.
  Absence reads back as `None` rather than a fabricated `child.new_data()`, and writing skips the
  field whenever the value is `None` - presence lives in the value itself since, unlike
  `OptionalBlock`, the criteria can't be recomputed while writing. Renders as its own GUI
  component (a presence checkbox wrapping the child's editor), not the child's, since `None` has
  to be toggleable by hand.
- `DelegateBlock(possible_blocks, choice_index)` — reads one of several block types, storing
  `{'choice_index', 'data'}`. `AutoDetectBlock(possible_blocks)` — auto-detect via
  `library.probe_block_class` (used e.g. inside `ShpiBlock` item slots).
  `EnumLookupDelegateBlock(enum_field, blocks)` — picks by looking up a sibling enum field's value.
- `ArchiveBlock` (`library.read_blocks.archives`) — base for name/offset-indexed archives; see the
  ShpiBlock walkthrough below.

**Value validators** (`library.read_blocks.misc.value_validators`): `Eq(value)`,
`Or([values])` — pass as `value_validator=` to any leaf block to assert/document a fixed or
enumerated value (e.g. a magic-number field).

**Domain helpers** (`resources.eac.fields`): `Point2D(child, normalized=False)`,
`Point3D(child, normalized=False)`, `Quaternion(child)` (x, y, z, w; NFS2/NFS3 animation keyframes use 2.14 fixed
point), `RGBBlock()`, `Nfs1Angle8()`/`Nfs1Angle14()` (8/14-bit angle → radians float), `Nfs1TimeField()` (ticks →
seconds float). `normalized=True` rescales the vector to unit length on write, which breaks a byte-exact round trip
of stored vectors that are slightly off unit length or zero; leave it off for data read from game files.

## If no existing block fits: ask before adding a generic one

If the cheat-sheet above has nothing that fits and you conclude the field needs a genuinely new
`DataBlock` subclass in `library/read_blocks` (not just a one-off block local to this format's
`resources/*.py` file), that's a `read-block-framework` change with project-wide reach — don't make
that call unilaterally. Stop and ask the user first, via `AskUserQuestion`, with concrete detail:

- **The field/pattern itself**: byte layout, size (fixed or how computed), and a couple of concrete
  example values from the file(s) you're parsing.
- **The proposed block**: class name, constructor parameters, and what `read`/`write` would do —
  spelled out precisely enough that the user could implement it from your description alone.
- **Why it's generic**, not a one-off: point to the actual other places (which formats/games,
  which existing fields) that share this exact shape today, or the concrete external reason you
  expect it to recur (e.g. it's a known EA-wide convention, not specific to this file). "I think it
  might be useful elsewhere" is not sufficient justification by itself — cite real occurrences.
- Offer the alternative plainly: a block scoped to just this format's file (e.g. a small
  `CompoundBlock`/subclass next to the rest of that format's definitions, or a helper alongside
  `resources/eac/fields/`) instead of a `library/read_blocks` addition.

Only proceed to actually add the generic block (following `read-block-framework`) after the user
picks that option.

## The declarative pattern

```python
class SomeThing(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        magic = (UTF8Block(length=4, value_validator=Eq('ABCD')), {'description': 'Magic header'})
        count = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('items'))),
                  {'usage': 'io,doc', 'description': 'Number of items'})
        items = (ArrayBlock(child=IntegerBlock(length=2), length=lambda ctx: ctx.data('count')),
                  {'description': 'The items'})
```

- Extras dict keys: `description`, `is_unknown` (mark purpose not understood — still shows up in
  docs, flagged), `custom_offset` (docs only, for non-sequential layouts), `usage` — comma-separated
  subset of `ui`/`io`/`doc` (default = everywhere; e.g. `'io,doc'` hides a redundant length field
  from the editable GUI while keeping it in docs and round-trip I/O).
- `programmatic_value=lambda ctx: ...` — field is still *read* normally, but on `write` its value is
  recomputed from the rest of the tree instead of trusting stored data (use for lengths/counts that
  must stay consistent after edits).
- Length/condition lambdas can reach any already-parsed sibling/ancestor via `ctx.data('path')` /
  `ctx.data('../parent_field')` — see `read-block-framework`'s context section; keep them
  documentation-safe (pure arithmetic/comparisons).

### Post-processing raw bytes into a nicer shape

When the on-disk representation is awkward (e.g. packed color bitness, indexed rows), override
`read`/`write` around `super()`: call `super().read(...)`, transform `data[...]` in place
(`_native_to_internal`), return it; in `write`, **`deepcopy(data)` first** (the same dict backs the
GUI's live/unsaved-edits state — mutating it directly corrupts that), transform the copy
(`_internal_to_native`), then `super().write(copied, ...)`. See `EacImage`/`EacPalette` in
`resources/eac/bitmaps.py` for the full pattern, including per-color-format conversion tables.

If a field's native bytes are actually a *concatenation of several same-format chunks of differing
size* (e.g. `EacImage.mipmaps`: w/2×h/2, w/4×h/4, ..., 1×1 bitmaps back to back), don't feed the
whole blob through the single-instance converter with the base dimensions — slice it per chunk and
convert each with its own dimensions (`EacImage._mipmaps_native_to_internal`/
`_mipmaps_internal_to_native`). Reusing the base dimensions happens to work for formats whose
conversion is elementwise/shape-independent, but silently corrupts sub-byte-packed formats (4-bit)
whose decoding depends on row width.

### Custom GUI actions

Add a `custom_actions` list to the block's `schema` (method name, title, description, `is_pure`,
`args` — each arg has `id`/`title`/`type` where `type` ∈ `'string' | 'number' | 'bool' | 'enum_string'
(+ 'choices') | 'file_output'`, optional `default`). Implement `action_<method>(self, read_data,
**kwargs)` mutating `read_data` in place. See `convert_to_4bit`/`convert_to_8bit`/`convert_to_rgba`
on `EacImage`, `invert_colors`/`convert_format` on `EacPalette`. An arg can declare
`'visible_when': {'arg': '<other id>', 'value': <value>}` to only show/require it in the run-action
dialog while that sibling arg currently holds `value` (e.g. `convert_to_8bit`'s `palette_type` only
matters when `channel == 'generate embedded palette'`) — the dialog handles the rest generically.

A block whose *format* changes on write (an enum `resource_id`-like field picking how a payload is
encoded) typically has other fields whose shape or presence depends on that same format - a
same-shaped secondary chunk (`EacImage.mipmaps`, encoded the same way as `bitmap`) and/or trailing
fields only ever populated for one format (`EacImage.embedded_palette*`, 8Bit-only). A conversion
action must keep *all* of them in sync, not just the primary field: convert the secondary chunk
through the identical transform, and null out now-inapplicable trailing fields - their write-time
presence check may only look at "is it set", not at the new format, so stale data gets written
anyway and misaligns everything read after it. `EacImage.action_convert_to_8bit`/`_to_4bit`/`_to_rgba`
share `_clear_8bit_palette_fields` for the latter.

`resources.eac.utils.quantize_images_to_8bit`/`build_8bit_palette` quantize one or more RGBA
`PIL.Image`s onto one shared palette (reserving a genuinely-transparent entry for alpha-0 pixels)
and build the resulting `EacPalette` - reuse them for any new from-RGBA-to-8Bit action instead of
re-deriving a quantizer; `ShpiBlock.action_convert_to_8bit` and `EacImage.action_convert_to_8bit`
both do.

### Archives (name/offset-indexed containers)

`ArchiveBlock` (base class) already handles the item/pre-offset-payload/post-offset-payload/alias
plumbing. To build one (see `ShpiBlock` in `resources/eac/archives/shpi_block.py` as the reference):
1. Pass `item_block=` (typically an `AutoDetectBlock` of the possible item types) to `super().__init__()`.
2. Declare your own header fields normally (magic, length, item count, offset table, ...), marking
   the raw offset-table/data-bytes fields `usage: 'io,doc'` (hidden from the edit UI).
3. Add `children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})` to `Fields` — this is the
   GUI-facing reconstructed item list.
4. Override `read()` to build `children` from the offset table (walk offsets, read each item via
   `self.item_block.unpack(...)`, capture inter-item bytes as `pre_offset_payload`/`post_offset_payload`).
5. Override `write()` to flatten `children` back into the offset table + raw data bytes.
6. Override `estimate_packed_size()` (sum header + per-child sizes).

## Registering a brand-new top-level file format

1. **Detect it**: add a branch to `_find_block_class` in `library/loader.py`, matching on file
   extension (`file_path.endswith/upper().endswith`) and/or magic bytes (`header_str`/`resource_id`
   from the first bytes). Import the block class **locally inside the branch** (perf convention —
   see root `CLAUDE.md`).
2. **Define it** under `resources/<vendor>/...py` using the blocks above. Give the top-level block
   class a name that's unique **across every game's module**, not just within its own file - the
   GUI picks a viewer component by walking `schema['block_class_mro']`, which is built from the
   Python class's own `__name__` (`DataBlock.schema`, `library/read_blocks/basic.py`), with no
   awareness of which module it came from. A same-named class in another game's module (e.g. two
   different `class FrdMap(...)` for two different track formats, one per game) collides silently:
   whichever viewer is registered for that name in `DATA_BLOCK_COMPONENTS_MAP` renders for *both*
   formats, even though their `schema`/field shapes differ - no error, just a viewer fed data it
   doesn't expect. Prefix per-game top-level classes that share a concept name with another game
   (`Nfs4FrdMap`, not `FrdMap`, alongside NFS3's `FrdMap`) and verify with
   `SomeBlock().schema['block_class_mro']` that it doesn't match an existing one before wiring up
   a bespoke viewer for it.
3. **Serialize it**: add a serializer class (subclass `BaseFileSerializer` from
   `serializers/base.py`) under `serializers/<area>.py`, implement `serialize()` (and
   `deserialize()`/`ui_serialization()` if it should round-trip from the GUI convert panel), return
   it from the block's `serializer_class()`, and import the new serializer class in
   `serializers/__init__.py`.
   For 3D formats, give each `SubMesh` a `texture_id`, list those ids in `Scene.mtl_texture_names`
   and set `Scene.mtl_texture_path_func`; the exported `.mtl` then carries the textures to every
   consumer (GUI OBJ preview, Blender, glb). `Scene.mtl_texture_alpha_modes` (texture name ->
   `'blend'` for translucent textures, `'cutout'` for alpha masks; `texture_alpha_mode(image)` in
   `serializers/geometries.py` picks one from pixels) is written as an `alpha_mode` MTL statement,
   which tells the GUI preview whether to blend the material; without it the preview blends
   every textured material. `ImageSerializer().to_image(data, block, id)` returns a
   PIL image of any `EacImage` (palette resolved from `id`), e.g. to compose texture atlases (see
   `compose_texture_page` in `serializers/geometries.py` for NFS5 CRP texture pages). A texture
   file that sits next to the model (track `.fsh`, car `.tpg`) is loaded with
   `require_resource(path_to_name(<sibling path>))`; unwrap `EacCompressedBlock` by re-requiring
   `join_id(id, 'data')`. NFS5 car atlases overlap alternative image variants (roof, decals, ...):
   `crp_car_is_image_used` keeps those of the car's default `.tpg` `[styleN]`. CRP alpha is not
   transparency except for `CarWheel`/`CarWindow` materials, so other pages are written opaque
   (`page_<n>.png` vs `page_<n>_alpha.png`). Meshes without a texture still need a material
   (`untextured`), otherwise OBJ readers carry over the previous `usemtl`.
   NFS3 `car.fce` (`Fce3Geometry`) textures are the TGA siblings in the same BIGF archive (`car.viv`) or folder
   (`_find_fce_siblings`), written opaque plus `<name>_paint_mask.png` (TGA alpha < 255 marks paintable pixels,
   used by the GUI color pickers); part roles come from part index (`fce_part_lod_prefix`). NFS4 `car.fce`
   (`Fce4Geometry`, version `0x00101014`/`0x00101015` in the first 4 bytes, which is how the `.FCE` loader branch tells
   it from FCE3) goes through `Fce4GeometrySerializer`, a subclass that takes part roles from part names
   (`fce4_part_lod_prefix`), exports a `<mesh>_damaged` copy of every mesh from `damaged_vertices`, reads texture V
   top-down (FCE3: bottom-up) and keeps TGA alpha 0 as transparency. Texture page N of `<name>.fce` is
   `<name>0N.tga` (NFS4 upgrade models `car1.fce`..`car3.fce` use `car100.tga`..`car300.tga`, `dash.fce` uses
   `dash00.tga`), falling back to all sibling TGAs in alphabetical order. Both versions
   share the GUI viewer `eac/fce-geometry.block-ui` (`FceCarMeshController`), which picks FCE3/FCE4 behavior (wheels,
   paint colors by texture alpha, light dummies, damage filter) from `block_class_mro`.
   NFS6 track geometry (`compNN.o`, `levelG.o`, `trackg.o`, `skyg.o`) is an EAGL MIPS ELF object (`EaglModel` in
   `resources/eac/geometries/nfs6.py`, detected by the `\x7fELF` magic): the block keeps the raw sections, and
   `read_eagl_meshes` walks `__RenderMethod` symbols and `.data` relocations to vertex/index buffers (format notes in
   that file's header comment). Textures are FSH aliases looked up by `find_eagl_texture_archive` (same BIGF, sibling
   file, then `persist.viv`); FSH images there are DXT1/DXT3/DXT5 (`library/utils/dxt.py`, which caches decoded
   pixels so unchanged images write back byte-exact).
   Mesh names `<name>_ai<frame>` mark morph animation frames: the GUI `obj-viewer` collapses them
   into one list entry with a play button via `visibilityGroupFunction`/`animationFrameFunction`.
   Track props: with `maps__add_props_to_obj` a track serializer bakes props into the terrain meshes; without it
   (the GUI track viewer, and nfs-web, which loads the gg-web-engine export) every prop is a dummy of its terrain
   chunk scene (`_extra.json` / `.meta`; position relative to the chunk, `properties.is_prop`, `type`,
   `model_ref_id`) and the props controllers of the frontend spawn them (see the track viewer section below).
   TNFS (`TriMapSerializer`) dummies reference FAM props (`model`, `bitmap`, `two_sided_bitmap`). NFS2
   (`TrkMapSerializer`), NFS3 (`FrdMapSerializer`) and NFS4 (`Nfs4FrdMapSerializer`) share
   `EacTrackSerializer._export_track`: terrain chunks plus `TrackProp`s (model id, keyframes of position +
   quaternion in game coordinates, optional animation delay). Baked props are meshes `prop_<n>__<texture>`; a dummy
   has `quaternion` [w, x, y, z] and `type: "model"`. Every model is exported once (identical ones deduplicated,
   `_deduplicate_models`) to its own folder `props/<model id>/` with the converter's single-model names
   (`geometry.obj` + `material.mtl`, gg-web-engine `body.glb` + `.meta` without materials: the game assigns track
   textures by mesh name), all in one `export_scenes` call through `Scene.directory`. An animated prop carries
   `properties.animation`, a JSON string `{"delay", "frame_duration", "frames": [{"position", "quaternion"}]}` in
   the same coordinates as the dummy (`frame_duration` in seconds, assuming 64 delay units per second); baked
   animated meshes get it through `Scene.object_properties` (custom properties of the imported Blender objects).
   Prop sources: TRK block `props_7`/`props_18` + `prop_descriptions`, COL file `props_7` + `prop_descriptions`
   (NFS2, NFS3), NFS3 and NFS4 extra objects (XOBJ; NFS4 special objects are rotated by their transform matrix, as
   row vectors). NFS3 terrain is the high-res chunks (`FRD_TERRAIN_POLYGON_CHUNKS`) plus the block's POLYOBJ
   objects; the low/medium-res chunks are LODs of it. NFS5 (CRP) and NFS6 tracks have no prop dummies yet: NFS5
   bakes every article into the chunks, NFS6 routes don't include `levelG.o` props (`level.dat` is not parsed).
4. **OS integration** (optional): add the extension to `file_associations.py` if it should get a
   file-manager association/icon in the installers.
5. **Docs**: add/extend an entry in `generate_resource_doc.py`'s `EXPORT_RESOURCES[<game>]`
   — a one-line `file_list` entry using `render_type(SomeBlock())`, and add relevant block instances
   to the right category under `['blocks']`. Then run `python generate_resource_doc.py` to
   regenerate `resources/<GAME>.md`. **Never hand-edit the generated `.md` files.**
6. **Test it**: `test/resources/eac/test_<area>.py` — build minimal bytes with `BytesIO`,
   `block.unpack(ReadContext(buf))`, assert fields, then assert `block.pack(data)` round-trips (see
   `test/resources/eac/test_bitmaps.py`). For a full read/write round-trip of a *top-level* block,
   use `block.unpack_from_bytes(data)` rather than building a bare `ReadContext` and calling
   `.read()`/`.unpack()` directly — the latter skips `read_bytes_amount` propagation, so anything
   gated on `ctx.read_bytes_remaining` (e.g. `TrailingOptionalBlock`'s default criteria) silently
   reads as absent. When a conversion is genuinely lossy (e.g. any format down to 4Bit, which only
   keeps 4 bits per channel), don't assert the round-tripped value equals the pre-write one -
   assert it's stable after one write/read cycle instead (`twice = unpack(pack(once))`). Backend
   suite: `./.venv/bin/python -m unittest`.
7. **Smoke test** (optional but valuable for archive/container formats): drop a small real sample
   into `test/golden_corpus/` and run `test/test_gui_golden_corpus.sh`, which opens every corpus
   file through `run.py` — a cheap way to catch crashes across the whole known file zoo.

## Working out an undocumented format

- Check for a standard container before reading hex: `file <sample>` and the first bytes. NFS6 `.o` is a
  plain ELF object, so a short `struct` parser of its symbol table and relocations named every
  structure and turned every pointer into a known target; guessing offsets would have taken far longer.
- Write throwaway probe scripts (in the scratchpad) that run over every file of that kind in
  `games/<game>/` or the samples, and print value ranges and counts per field rather than dumping
  one file. Field descriptions like "always 44.703" or "values from 35 to 60" come from that.
- Where a command stream and a metadata table both give a count, trust the metadata: draw commands
  pad index counts (NFS6 rounds up to even), which adds a garbage triangle at the end of a strip.
- Triangle strips: flip the winding of every odd triangle and skip degenerate ones.
- Look at geometry early. Export one model to OBJ, open it in the GUI and take a screenshot
  (`QA/TEST_ENVIRONMENT.md`); a wrong axis, winding or UV-set-to-texture mapping is obvious in a
  picture and invisible in numbers.
- Round-trip every real sample (`blk.pack(data) == original bytes`). When one differs, check
  whether it also differs on the base branch before suspecting your change, and record a real
  game quirk in `QA/KNOWN_ISSUES.md`.
- Lossy codecs (DXT): keep a cache from decoded pixels to the original bytes so an image the user
  didn't touch is written back unchanged.
- Changing a block shared by every game (an `EacImage` enum value, `BigfBlock.possible_blocks`)
  rewrites every game's `resources/*.md` when regenerated; that diff is expected.

## GUI: usually nothing to build

The generic components (compound/array/number/string/enum/delegate/binary/sub-byte-compound/archive)
render any new block automatically from its `schema` — this covers the large majority of new
fields and even whole new formats built from existing primitives. Only add a bespoke
`*.block-ui` component (under `frontend/.../editor/eac/` or `.../editor/common/`, e.g. for an
image/3D-model/map/audio preview) when a rich visualization genuinely earns its keep — and note
that registering one (`editor.module.ts` + `editor.component.ts`'s `DATA_BLOCK_COMPONENTS_MAP`) is
the same mechanism whether generic or custom; see skill `read-block-framework` for the how-to.

### Reusing an existing 3D map/terrain viewer for a new per-game format

TNFS (`TriMap`), NFS2 (`TrkMap`), NFS3 (`FrdMap`), NFS4 (`Nfs4FrdMap`), NFS6 (`Nfs6AiPaths`) and NFSU (`NfsuTrackBundle`) tracks all render through
one component, `TrackMapBlockUiComponent` in `frontend/.../editor/eac/track-map.block-ui/`, registered
for each block class in `DATA_BLOCK_COMPONENTS_MAP`. Its world entity `TrackMapWorldEntity`
(`track-map-world.entity.ts`) is generic chunk-graph-of-OBJs-plus-texture-archive machinery.
Per-game differences live in a `TrackMapAdapter` (`track-map-adapters.ts`): chunk positions, the road
spline used by the minimap and "Spline item" fly-to (with orientation), whether the track is closed,
texture archive kind (QFS/FAM), glob patterns for finding it, serializer settings for it, skybox,
terrain texture wrapping, the props controller (`propsController`), and optional panels
showing the selected spline point's data. For another game's chunked track, add an adapter and a
`TRACK_MAP_ADAPTERS` entry keyed by the block class name, and map that class to
`TrackMapBlockUiComponent`; don't fork the component.

Props are spawned by props controllers, which are copied into nfs-web as they are (like the car mesh controllers),
so they depend only on three.js, gg-web-engine and rxjs (plus `setupNfs1Texture`): `TrackPropsController`
(`track-props-controller.ts`; NFS2-NFS4 models from `props/<model>/`, keyframe animation) and
`TnfsTrackPropsController` (`tnfs-track-props-controller.ts`; FAM models and bitmaps with frame animation, mirrored
tracks). They take dummies in gg-web-engine meta format (`GgDummy`) and a `TrackPropsAssets` (model by folder,
texture, terrain material by texture name), which `TrackMapWorldEntity` implements with OBJ/MTL files and nfs-web
with its gg-web-engine loader; the viewer reads a chunk's dummies from its `_extra.json`.

`chunkPositions` and the texture archive settings are optional. Without `chunkPositions` the
component reads chunk pivots from the `terrain_chunks.json` the serializer writes next to the chunk
OBJs; with `bundledTextures` the serializer writes the textures itself (`<chunks dir>/textures/`)
and there is no texture picker. NFS6 uses both: a route is `levelNN/aipaths.dat`, its serializer
(`Nfs6AiPathsSerializer`) exports the compartments listed in `drvpath.ini` with their textures, and
`nfs6-route.ts` derives the spline as the longest chain of the AI path graph.

Chunks are loaded around the camera along a graph: by default a chain in chunk order (a road), up to
`loadDepth` (40) hops. A city sets `chunkGraph: proximityChunkGraph` (k nearest chunks, clusters joined)
and a small `loadDepth`. Without `splinePoints`/`chunkPositions` the spline is the chunk positions from
`terrain_chunks.json`; `minimapPointsOnly` draws them as dots. NFSU uses all of these: a race bundle
`TRACKBnnnn.lzc` lists the streamed sections, and `NfsuTrackBundleSerializer` reads every section's
scenery from the `STREAM*.BUN` next to it (`find_nfsu_stream_file`) and writes one chunk per scenery,
in game coordinates (Z up), with its textures.

When the block data that reaches the GUI doesn't carry the layout (NFS5 `CrpGeometry` tracks: the
mesh parts are `io,doc`-only), the adapter implements `loadLayout(serializedPaths)` instead: the
serializer, called with `maps__save_as_chunked`, writes the chunks plus a `track_layout.json` (chunk
positions, road headings, loop flag), and the viewer reads it after serializing. `CrpGeometry` is
shared by cars and tracks, so `CrpGeometryBlockUiComponent` embeds `app-track-map-block-ui` for
"karT" data instead of being re-registered. NFS5 chunking (`CrpGeometrySerializer._serialize_track_chunks`)
relies on article names `<RD|CNK|OBJ><road piece number><L|C|R> (<section> ...)`: one chunk per "RD"
piece of the section with the most of them, other sections and unnamed articles go to the nearest chunk.

The texture picker lists every file matching the adapter's `textureArchivePatterns`, found by the
backend's `find_files` endpoint (`find_files_case_insensitive` in `library/utils/file_utils.py`:
wildcards in the file name only, letter case ignored, since game files ship as "tr0.qfs",
"TRN0.qFS" etc.). The first match is loaded; "Browse..." opens a native file dialog for anything else.

In `TrackMapBlockUiComponent.onTextureArchiveSelected`, the `serializeResource(path)` call is needed
even when the adapter has no skybox and nothing reads its return value. The call has a load-bearing
**side effect**: it's what makes the backend actually write the archive's texture PNGs (and, for
FAM, props) to disk (under `resources/<path>/`, which the dev-server proxy and production static
server both serve), which `TrackMapWorldEntity.getTerrainMaterial` then loads by predicting that same
path from the string alone - it never receives the call's return value. Drop the call and every
terrain material silently falls back to the checkerboard placeholder texture with no error anywhere;
the only symptom is a `console.warn('Problem with loading terrain material ...')` per texture, easy
to miss unless you're watching the dev-server log (`read_console_messages`) while checking the live
preview, not just the build/compile step.

Don't assume the texture archive's path can always be derived purely from the track file's own
name, either. NFS4 has a reverse-direction track ("Trn.FRD") that doesn't always ship its own
archive; its polygons reference the forward track's ("Tr.FRD") "Tr0.QFS" instead (see
`_require_nfs4_texture_archive` in `serializers/maps.py`, which the FRD serializer uses to resolve
texture names, and the matching `NFS4_TRACK_ADAPTER.textureArchivePatterns`). Both try the derived
path first and fall back to the forward track's archive; both look files up ignoring letter case.

### Overriding a few fields inside an existing bespoke viewer

A bespoke `*.block-ui` component doesn't have to render every field generically: exclude specific
ones from `<app-compound-block-ui>`'s generic list via its `[fieldBlacklist]` input, then render
custom interaction for them directly in the parent component/template instead. To gate visibility
the same way `is_unknown` fields are (hidden unless the user toggles "show hidden fields"), check
`mainService.hideHiddenFields$` yourself. See `ImageBlockUiComponent`
(`frontend/src/app/components/editor/eac/image.block-ui/`), which replaces its `mipmaps` field with
a plain checkbox (unchecking just clears the field generically; checking runs a custom GUI action -
see "Custom GUI actions" above - to have the backend compute it) and presents three fixed `TrailingOptionalBlock`
fields (`embedded_palette_2/3/4`) as a single max-3-length pseudo-array.

When one user interaction should change several *discrete, independently-addressed* fields as one
undo step (e.g. reordering across those three fixed fields), don't call `onValueSet`/
`emitNewChange` once per field - each call is its own undo entry. Build a `ChangeEntry[]` of `'set'`
ops (each with its own `id` from `joinId`) and emit them together as
`emitNewChange({op: 'bundle', changes})` (see `font.block-ui.component.ts` for another example, and
`ImageBlockUiComponent`'s `applyEmbeddedPaletteSlots`). To programmatically flip a
`TrailingOptionalBlock` field from absent to present outside its own checkbox component, fetch
`child.new_data()` via `mainService.getTrailingOptionalFieldData(fieldId)` rather than fabricating
a value.

## Roadmap awareness

`docs/milestones.md` tracks coverage game-by-game; current priority is TNFS SE (1996 PC). Check it
before deciding what to prioritize next.
