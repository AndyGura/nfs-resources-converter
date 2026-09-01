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
| `resources/eac/` | EA Canada formats shared across many NFS titles: `bitmaps.py` (EacImage/EacPalette), `archives/` (SHPI/WWWW/BIGF/SoundBank/compressed), `fonts.py`, `audios.py`, `videos.py`, `geometries/`, `maps/`, `car_specs.py`, `configs.py`, `misc.py`, `compressions/` (QFS/RefPack). |
| `resources/eac/maps/{tnfs,nfs2,nfs3,nfs_common}.py`, `resources/eac/geometries/{tnfs,nfs2,nfs5}.py` | Per-game specializations of a shared concept. |
| `resources/common/bitmaps/targa_image.py` | Vendor-neutral TGA, used as an `AutoDetectBlock` fallback. |
| `resources/blackbox/geometries/` | Blackbox-studio (later titles) formats — thin, early. |
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
`Point3D(child, normalized=False)`, `RGBBlock()`, `Nfs1Angle8()`/`Nfs1Angle14()` (8/14-bit angle →
radians float), `Nfs1TimeField()` (ticks → seconds float).

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

### Custom GUI actions

Add a `custom_actions` list to the block's `schema` (method name, title, description, `is_pure`,
`args` — each arg has `id`/`title`/`type` where `type` ∈ `'string' | 'number' | 'bool' | 'enum_string'
(+ 'choices') | 'file_output'`, optional `default`). Implement `action_<method>(self, read_data,
**kwargs)` mutating `read_data` in place. See `convert_to_4bit`/`convert_to_8bit`/`convert_to_rgba`
on `EacImage`, `invert_colors`/`convert_format` on `EacPalette`.

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
2. **Define it** under `resources/<vendor>/...py` using the blocks above.
3. **Serialize it**: add a serializer class (subclass `BaseFileSerializer` from
   `serializers/base.py`) under `serializers/<area>.py`, implement `serialize()` (and
   `deserialize()`/`ui_serialization()` if it should round-trip from the GUI convert panel), return
   it from the block's `serializer_class()`, and import the new serializer class in
   `serializers/__init__.py`.
4. **OS integration** (optional): add the extension to `file_associations.py` if it should get a
   file-manager association/icon in the installers.
5. **Docs**: add/extend an entry in `generate_resource_doc.py`'s `EXPORT_RESOURCES[<game>]`
   — a one-line `file_list` entry using `render_type(SomeBlock())`, and add relevant block instances
   to the right category under `['blocks']`. Then run `python generate_resource_doc.py` to
   regenerate `resources/<GAME>.md`. **Never hand-edit the generated `.md` files.**
6. **Test it**: `test/resources/eac/test_<area>.py` — build minimal bytes with `BytesIO`,
   `block.unpack(ReadContext(buf))`, assert fields, then assert `block.pack(data)` round-trips (see
   `test/resources/eac/test_bitmaps.py`). Backend suite: `./.venv/bin/python -m unittest`.
7. **Smoke test** (optional but valuable for archive/container formats): drop a small real sample
   into `test/golden_corpus/` and run `test/test_gui_golden_corpus.sh`, which opens every corpus
   file through `run.py` — a cheap way to catch crashes across the whole known file zoo.

## GUI: usually nothing to build

The generic components (compound/array/number/string/enum/delegate/binary/sub-byte-compound/archive)
render any new block automatically from its `schema` — this covers the large majority of new
fields and even whole new formats built from existing primitives. Only add a bespoke
`*.block-ui` component (under `frontend/.../editor/eac/` or `.../editor/common/`, e.g. for an
image/3D-model/map/audio preview) when a rich visualization genuinely earns its keep — and note
that registering one (`editor.module.ts` + `editor.component.ts`'s `DATA_BLOCK_COMPONENTS_MAP`) is
the same mechanism whether generic or custom; see skill `read-block-framework` for the how-to.

## Roadmap awareness

`docs/milestones.md` tracks coverage game-by-game; current priority is TNFS SE (1996 PC). Check it
before deciding what to prioritize next.
