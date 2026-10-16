from math import floor
from typing import Dict

from library.context import WriteContext
from library.exceptions import DataIntegrityException
from library.read_blocks import (
    DeclarativeCompoundBlock,
    UTF8Block,
    IntegerBlock,
    ArrayBlock,
    BytesBlock,
    DelegateBlock,
    BitFlagsBlock,
    FixedPointBlock,
    Padding,
)
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.fields.misc import Point3D

# "Verified" in the descriptions below: read in the game code (TNFS DOS, PSX and Win95 SE executables, tnfs-1995
# Ghidra projects; DOS `gfx_oriload` 0xa1148, `gfx_orilocatemorph` 0xa14d0, `gfx_oriapplymorph` 0xa16a4,
# `gfx_ori_init_material_colours` 0xa0f98, `gfx_ori_sort_polys` 0xa1a00, `gfx_draw_car_model` 0x74766) or checked
# against every ORIP of the game files (CFM car models, FAM track props)


class OripPolygon(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A geometry polygon',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_type = (
            IntegerBlock(length=1),
            {
                'description': 'Polygon type (verified). Bits 0-2: number of vertices (3 triangle, 4 quad, 2 a line: '
                'the only ones in the game files are in the TR6 mine prop, the converter skips them). Bit 0x08: '
                'colour-keyed, texel 0xFF is transparent (else opaque). Bit 0x80: textured (else filled with the '
                "flat colour of the material). Bits 3-6 together pick the game's rasterizer. Values in the files: "
                '0x84 / 0x83 textured opaque quad / triangle, 0x8C / 0x8B textured colour-keyed quad / triangle, '
                '0x04 flat colour quad, 0x02 line'
            },
        )
        mapping = (
            BitFlagsBlock(
                length=1,
                flag_names=[
                    (0, 'two_sided'),
                    (1, 'flip_normal'),
                    (2, 'not_in_draw_list'),
                    (3, 'chain'),
                    (4, 'use_uv'),
                    (5, 'alt_rasterizer'),
                ],
            ),
            {
                'description': 'Polygon flags (verified): 0x01 `two_sided`, no backface culling; 0x02 '
                '`flip_normal`, reversed winding; 0x04 `not_in_draw_list`: not culled and left out of the default '
                'draw list (drawn only through a chain); 0x08 `chain`: after drawing this polygon the game draws '
                'the polygon whose index follows the vertex indices in `vmap` (vmap[offset_3d + vertex count]), '
                'only in the CY1 tunnel prop; 0x10 `use_uv`: has texture coordinates (without it `offset_2d` is '
                'garbage and the texture is mapped to the corners of the quad); 0x20 `alt_rasterizer`: another '
                'rasterizer, only in two polygons of the AL1 trestle prop'
            },
        )
        material_index = (
            IntegerBlock(length=1),
            {'description': "Index of the polygon's material in `materials` (verified)"},
        )
        unk = (
            IntegerBlock(length=1),
            {
                'description': 'Masked off and never read by the draw code (verified). Values 0, 1, 2, 4',
                'is_unknown': True,
            },
        )
        offset_3d = (
            IntegerBlock(length=4),
            {
                'description': 'Index in `vmap` of the first vertex index of this polygon: the polygon has as '
                'many vertices as bits 0-2 of `polygon_type` tell, their indices in `vertices` are the vmap items '
                'from this one on'
            },
        )
        offset_2d = (
            IntegerBlock(length=4),
            {
                'description': 'The same as offset_3d for texture coordinates: index in `vmap` of the index '
                'in `vertex_uvs` of the first vertex. Garbage when `use_uv` is off'
            },
        )


class OripVertexUV(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Texture coordinates for vertex, where each coordinate is: '
            + IntegerBlock(length=4).schema['block_description']
            + '. The unit is a pixels amount of assigned texture. So it should be changed when selecting '
            'texture with different size',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        u = IntegerBlock(length=4, is_signed=True)
        v = IntegerBlock(length=4, is_signed=True)


class OripMaterial(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A material: FSH bitmap and flat colour of the polygons that use it',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (
            BytesBlock(length=8),
            {
                'description': 'Material name, 8 bytes, NUL-padded when shorter, empty in most materials. The game '
                'looks materials up by name (verified): `frntires` and `rertires` (the front and rear wheel quads, '
                'which get the animated tyre textures `tyr1`..`tyr4`), `tire1`..`tire4`. Other names in the files, '
                'never looked up: `pal`, `rtir1`..`rtir4` / `rty1`..`rty4` (Warrior rear tyres, never shown), '
                'traffic car part names (`side`, `front`, `rear`, `tires`...) and a few garbage values'
            },
        )
        file_name = (
            UTF8Block(length=4),
            {'description': 'Name of the bitmap in the FSH archive next to this ORIP (verified)'},
        )
        color = (
            IntegerBlock(length=3),
            {
                'description': 'Flat colour 0xRRGGBB (the game reads the 4 bytes as 0x00RRGGBB, little-endian), '
                'matched to the nearest palette entry; untextured polygons are filled with it (verified)'
            },
        )
        unknown_0x0f = (
            IntegerBlock(length=1),
            {
                'description': 'High byte of the colour, never read by the game (verified). 0, 0x80, 0x81 or 0x82 in '
                'the files',
                'is_unknown': True,
            },
        )
        unknown_0x10 = (
            IntegerBlock(length=4),
            {'description': 'Never read by the game (verified)', 'is_unknown': True},
        )


class OripMorph(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A morph (verified): vertices moved by delta vectors times a weight, '
            '`vertex = base + round(delta * weight / 0x10000)` per component (weight in 16.16 fixed point, linear)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (
            UTF8Block(length=8),
            {
                'description': 'Morph name, 8 bytes without NUL: the game compares 8 characters of the names it '
                'looks up, `left_turn` and `right_turn`, so the files hold `left_tur` and `right_tu`'
            },
        )
        num_vertices = (IntegerBlock(length=4), {'description': 'Number of moved vertices'})
        vmap_offset = (
            IntegerBlock(length=4),
            {'description': 'Index in `vmap` where the indices (in `vertices`) of the moved vertices start'},
        )
        first_delta = (
            IntegerBlock(length=4),
            {
                'description': 'Index in `vertices` of the delta vector of the first moved vertex, the deltas of '
                'the others follow it in the order of the vertex indices in vmap. They have the format of vertices '
                'and are stored after the `num_shape_vrtx` shape vertices'
            },
        )


class OripPartition(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A partition: a named list of polygons, depth-sorted and drawn as a whole. The game '
            'draws a car as its `inside`, then `surface`, then `outside` partition (verified), each sorted on its '
            'own and painted completely over the previous one: `inside` (the inner tyre faces `circ`, the tyre '
            "bottoms `shad`, the Warrior's `bott` and `tire`, some body parts) is always under the body, "
            '`outside` (the 4 wheel quads in every full car model) always over it',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (
            UTF8Block(length=8),
            {
                'description': 'Partition name. Every ORIP has `NON-SORT`, car models also `inside` and '
                '`surface`, full car models and the M*.CFM models `outside`, COPMUST `badge`. The game looks up '
                '`inside`, `surface`, `outside` and `convex` (never present); `NON-SORT` and `badge` are never drawn '
                'by the car code (verified)'
            },
        )
        unknown_0x08 = (
            IntegerBlock(length=4),
            {
                'description': 'Never read by the game (verified). 0, or a large value equal in all partitions of '
                "the model; in traffic and M*.CFM models `inside`'s is the others' + 1",
                'is_unknown': True,
            },
        )
        unknown_0x0c = (
            IntegerBlock(length=4, is_signed=True),
            {
                'description': 'Never read by the game (verified). In the full car models 1 for `inside`, 0 for '
                '`surface`, -1 for `outside`; 0 in the other models (PICKUP: -1 for `surface`)',
                'is_unknown': True,
            },
        )
        polygons_start = (
            IntegerBlock(length=4),
            {'description': 'Index in `vmap` where the indices (in `polygons`) of the polygons of the partition start'},
        )
        num_polygons = (IntegerBlock(length=4), {'description': 'Number of polygons in the partition'})
        unknown_0x18 = (
            IntegerBlock(length=4),
            {'description': 'Never read by the game (verified), always 0', 'is_unknown': True},
        )


class NamedIndex(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': '12-bytes record, first 8 bytes is null-terminated UTF-8 string, last'
            ' 4 bytes is an unsigned integer (little-endian). Used by ORIP `fx_polys` (index is a vertex index) and '
            '`labels` (index is a polygon index)',
            'inline_description': True,
        }

    @property
    def size_doc_str(self):
        return '12'

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (
            NullTerminatedUTF8Block(length=8, errors='surrogateescape'),
            {
                'description': 'Name of the entry (up to 7 bytes). A few entries have a garbage name, like the bytes '
                '80 02 of a DVIPER `fx_polys` entry (kept as is: a byte which is not UTF-8 is read as U+DC80..U+DCFF)'
            },
        )
        offset = ArrayBlock(
            child=IntegerBlock(length=1),
            length=(lambda ctx: 8 - ctx.buffer.tell() + ctx.read_start_offset, '7 - len(name)'),
            programmatic_value=lambda ctx: [0] * (7 - len(NamedIndex.name_bytes(ctx.data('name')))),
        )
        index = (IntegerBlock(length=4), {'description': 'Index of the vertex (`fx_polys`) or polygon (`labels`)'})

    @staticmethod
    def name_bytes(name: str) -> bytes:
        return name.encode('utf-8', errors='surrogateescape')

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        # always 12: `offset` is written from the name, whatever it was read with (ORIP `block_size` counts on it)
        return 12

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        if len(self.name_bytes(data['name'])) > 7:
            raise DataIntegrityException(
                f'Name "{data["name"]}" is longer than 7 bytes, the most a {name or "named index"} entry can hold',
                ctx=ctx,
            )
        return super().write(data, ctx, name)


# TODO check additional info in http://3dodev.com/documentation/file_formats/games/nfs
class OripGeometry(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Geometry block for 3D model with few materials: TNFS car models (CFM) and track '
            'props (FAM). Exported to OBJ + MTL, and imported from them: the polygons, labels and partitions of the OBJ '
            'replace the geometry, the rest (material names and colours, morphs, fx points) follows the replaced '
            'model and the wheel quads',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('ORIP'), length=4), {'description': 'Resource ID'})
        block_size = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
            {'description': 'Total ORIP block size in bytes'},
        )
        version = (
            IntegerBlock(length=4, value_validator=Eq(0x02BC)),
            {
                'description': 'Format version (verified): 700 (0x2BC) on PC, the game warns about any other value. '
                'The PSX version expects 800, the 3DO version reportedly has 500 (0x1F4)'
            },
        )
        instance_counter = (
            IntegerBlock(length=4, value_validator=Eq(0)),
            {
                'description': 'Number of instances of the model: zeroed by the game at load and incremented per '
                'instance at run time (verified). Always 0 in the files'
            },
        )
        num_vrtx = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('vertices/data'))),
            {'description': 'Number of items in `vertices`: the shape vertices and the morph delta vectors'},
        )
        num_shape_vrtx = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: (
                    len(ctx.data('vertices/data')) - sum(m['num_vertices'] for m in ctx.data('morphs'))
                ),
            ),
            {
                'description': 'Number of shape vertices: `vertices` without the morph delta vectors (`num_vrtx` - '
                'the vertices of all morphs). The game takes the bounding box of a car from these (verified)'
            },
        )
        vrtx_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'vertices'),
            ),
            {'description': 'An offset to vertices'},
        )
        num_uvs = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('vertex_uvs'))),
            {'description': 'Amount of vertex UV-s (texture coordinates). Not read by the game (verified)'},
        )
        uvs_ptr = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: 112 + len(ctx.data('polygons')) * 12),
            {'description': 'An offset to vertex_uvs. Always equals to `112 + num_polygons*12`'},
        )
        num_polygons = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('polygons'))),
            {'description': 'Amount of polygons'},
        )
        polygons_ptr = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(112)),
            {'description': 'An offset to polygons block'},
        )
        name = (
            UTF8Block(length=12),
            {'description': 'Model name, like "_SUPRA" or "_TRESTLE". Never read by the game (verified)'},
        )
        num_materials = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('materials'))),
            {'description': 'Amount of materials'},
        )
        materials_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: 112 + len(ctx.data('polygons')) * 12 + len(ctx.data('vertex_uvs')) * 8,
            ),
            {'description': 'An offset to materials. Always equals to `112 + num_polygons*12 + num_uvs*8`'},
        )
        num_morphs = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('morphs'))),
            {'description': 'Amount of morphs'},
        )
        morphs_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'morphs'),
            ),
            {
                'description': 'An offset to morphs. Equals to `materials_ptr + num_materials*20`, except in the '
                'far model of LDIABLO.CFM (see `unk_morphs`)'
            },
        )
        num_partitions = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('partitions'))),
            {'description': 'Amount of partitions'},
        )
        partitions_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'partitions'),
            ),
            {'description': 'An offset to partitions. Always equals to `morphs_ptr + num_morphs*20`'},
        )
        vmap_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'vmap'),
            ),
            {'description': 'Offset of polygon_vertex_map block'},
        )
        num_fxp = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('fx_polys'))),
            {'description': 'Amount of items in fx_polys block'},
        )
        fxp_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'fx_polys'),
            ),
            {'description': 'Offset of fx_polys block. Always equals to `partitions_ptr + num_partitions*28`'},
        )
        num_lbl = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('labels'))),
            {'description': 'Amount of items in labels block'},
        )
        lbl_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'labels'),
            ),
            {'description': 'Offset of labels block. Always equals to `fxp_ptr + num_fxp*12`'},
        )
        num_jld = (
            IntegerBlock(length=4),
            {
                'description': 'Number of JLD items (verified: when not 0, the game allocates num_jld * 0x24 bytes of '
                'inverse matrices at `jld_runtime_ptr`, "InitJLD"). What JLD is is unknown. 0 in every file',
            },
        )
        jld_ptr = (
            IntegerBlock(length=4),
            {'description': 'Offset of the JLD items. 112 (the end of the header) in every file, where there are none'},
        )
        jld_runtime_ptr = (
            IntegerBlock(length=4),
            {'description': 'Run time pointer to the JLD inverse matrices (verified), 0 in the files'},
        )
        polygons = (
            ArrayBlock(child=OripPolygon(), length=lambda ctx: ctx.data('num_polygons')),
            {
                'description': 'A block with polygons of the geometry. Probably should be a start point when '
                'building model from this file'
            },
        )
        unk_uvs = (
            Padding(to=(lambda ctx: ctx.data('uvs_ptr'), 'uvs_ptr')),
            {'description': 'Padding up to `uvs_ptr`, normally empty'},
        )
        vertex_uvs = (
            ArrayBlock(child=OripVertexUV(), length=lambda ctx: ctx.data('num_uvs')),
            {'description': 'A table of texture coordinates. Items are retrieved by index, located in vmap'},
        )
        unk_materials = (
            Padding(to=(lambda ctx: ctx.data('materials_ptr'), 'materials_ptr')),
            {'description': 'Padding up to `materials_ptr`, normally empty'},
        )
        materials = (
            ArrayBlock(child=OripMaterial(), length=lambda ctx: ctx.data('num_materials')),
            {'description': 'A table of materials. Items are retrieved by index, located in polygon item'},
        )
        unk_morphs = (
            Padding(to=(lambda ctx: ctx.data('morphs_ptr'), 'morphs_ptr'), allow_negative_length=True),
            {
                'description': 'Padding up to `morphs_ptr`, empty in every file but one: in the far model of '
                'LDIABLO.CFM (no morphs) its length is -3, the morph and partition tables start 3 bytes before the '
                'end of the materials, so the last 3 bytes of the materials are the start of the first partition '
                'name. Written back as 0 bytes, so that model is not written byte-exact'
            },
        )
        morphs = (
            ArrayBlock(child=OripMorph(), length=lambda ctx: ctx.data('num_morphs')),
            {
                'description': 'Morphs (verified). Only full car models have them: `left_turn` and `right_turn`, '
                'each moving the 4 vertices of its front wheel quad (labels `lt_frnt` / `rt_frnt`) and the 4 of '
                "that wheel's inner `circ` quad (TRAFFC, WARRIOR, WARIOR: the wheel quad only), no body vertex. "
                'Both turn their wheel left at a positive weight. The game applies the weight '
                '-steer_angle / 0x200000 (weight 1.0 is about 30 degrees of wheel turn), `left_turn` only when the '
                "camera sees the car's left side, `right_turn` only the right side. The gg-web-engine export writes "
                'them as glTF morph targets `left_turn` / `right_turn` of the meshes with moved vertices'
            },
        )
        unk_partitions = (
            Padding(to=(lambda ctx: ctx.data('partitions_ptr'), 'partitions_ptr')),
            {'description': 'Padding up to `partitions_ptr`, normally empty'},
        )
        partitions = (
            ArrayBlock(child=OripPartition(), length=lambda ctx: ctx.data('num_partitions')),
            {
                'description': 'Partitions, the draw order of the polygons (verified). The gg-web-engine export '
                'writes the partition of each mesh (`inside`, `surface` or `outside`) to its node extras '
                '(`partition`)'
            },
        )
        unk_fxp = (
            Padding(to=(lambda ctx: ctx.data('fxp_ptr'), 'fxp_ptr')),
            {'description': 'Padding up to `fxp_ptr`, normally empty'},
        )
        fx_polys = (
            ArrayBlock(child=NamedIndex(), length=lambda ctx: ctx.data('num_fxp')),
            {
                'description': 'Named points of the model for visual effects, in high-poly car models (CFM). Despite '
                'the name, `index` is the index of an item of `vertices`, not of a polygon. The game looks up `smok` '
                'and `fl0`, `fl1`, `fr0`, `fr1`, `rl0`, `rl1`, `rr0`, `rr1`, ignoring case (verified; F512M, F512TR, '
                'TRAFFC and WARRIOR use lower case, the other cars upper case). `FL0`..`RR1` are the ground contact '
                'points of the wheels (front/rear, left/right), 0 at the front edge of the wheel, 1 at the rear '
                'edge (the bottom corners of the wheel polygon labelled `lt_frnt`, `rt_rear`...); guess: sources of '
                'tyre smoke, dust and skid marks. `smok` is a point at the engine: on the hood of front-engined '
                'cars (DVIPER, CZR1, MRX7, TSUPRA), at the exhaust or the engine lid of the others; guess: source '
                'of engine smoke and fire of a wrecked car. Never looked up: `d` (only in the M*.CFM models, a point '
                'near the bottom of the front left wheel) and the garbage name (bytes 80 02) of one more DVIPER entry '
                '(the top of a wheel polygon). The gg-web-engine export writes every entry as a dummy "fx_<name>" at '
                'the vertex, with properties `fx` (the name) and `vertex` (the index), skipping entries with a name '
                'which is not printable ASCII'
            },
        )
        unk_lbl = (
            Padding(to=(lambda ctx: ctx.data('lbl_ptr'), 'lbl_ptr')),
            {'description': 'Padding up to `lbl_ptr`, normally empty'},
        )
        labels = (
            ArrayBlock(child=NamedIndex(), length=lambda ctx: ctx.data('num_lbl')),
            {
                'description': 'Named polygons of high-poly car models (CFM), `index` is the index of an item of '
                '`polygons`. The game looks up `lt_frnt`, `rt_frnt`, `lt_rear`, `rt_rear` only (verified): the '
                'outer side of the wheels (left/right, front/rear), quads of the `outside` partition with the '
                'materials `frntires` / `rertires`, which get the animated tyre textures. Never looked up: '
                '`bkll` / `bklr` (left / right rear light), `bott` (a horizontal quad over the whole underside of '
                'the body of the simple traffic car models, texture `bott`), `bacr` (P911, the centre part of the '
                'rear light bar), `mm` (LDIABLO; garbage name, bytes e0 01, on the same polygon of LDIABL, left out of the exported mesh '
                'names: a two-sided quad at the inner side of the front right wheel, texture `circ`), `W` (TRAFFC, WARRIOR: a triangle '
                'at the top rear left corner of the body, texture `abox`) and the COPMUST lights `hll0` / `hlr0` '
                '(headlights), `bkl0` / `bkr0` (rear lights), `lfl0` / `lfr0` and `lrl0` / `lrr0` (front and rear '
                'left / right parts of the siren light bar on the roof). Brake and siren lights are palette '
                'animations in the game, not label lookups (verified): the brake light is one palette entry, lit '
                'when the brake is at 11 or more; the siren swaps the 4 palette entries from 0xFA every 16 clock '
                'units. Parts known by their texture: `circ`, four two-sided colour-keyed quads at the inner side '
                'of the tyres (`inside` partition); `shad`, two vertical two-sided colour-keyed quads across the car '
                'at each axle (from the ground up to 0.24 m, 4x1 texture, no UVs), not the shadow of the car (the '
                'game draws that as a separate flat quad on the road); guess: the tyre bottoms seen from the front '
                'and the rear'
            },
        )
        unk_vrtx = (
            Padding(to=(lambda ctx: ctx.data('vrtx_ptr'), 'vrtx_ptr')),
            {'description': 'Padding up to `vrtx_ptr`, normally empty'},
        )
        vertices = (
            DelegateBlock(
                choice_index=lambda ctx, **_: 0 if ctx.buffer.name.endswith('.CFM') else 1,
                possible_blocks=[
                    ArrayBlock(
                        child=Point3D(child=FixedPointBlock(length=4, fraction_bits=7, is_signed=True)),
                        length=lambda ctx: ctx.data('num_vrtx'),
                    ),
                    ArrayBlock(
                        child=Point3D(child=FixedPointBlock(length=4, fraction_bits=4, is_signed=True)),
                        length=lambda ctx: ctx.data('num_vrtx'),
                    ),
                ],
            ),
            {
                'description': 'A table of mesh vertices 3D coordinates. For cars uses 32:7 points, else 32:4. '
                'The unit is meter. The first `num_shape_vrtx` items are the vertices of the model, the others are '
                'the delta vectors of the morphs'
            },
        )
        unk_vmap = (
            Padding(to=(lambda ctx: ctx.data('vmap_ptr'), 'vmap_ptr')),
            {'description': 'Padding up to `vmap_ptr`, normally empty'},
        )
        vmap = (
            ArrayBlock(
                child=IntegerBlock(length=4),
                length=(
                    lambda ctx: floor((ctx.data('block_size') + ctx.read_start_offset - ctx.buffer.tell()) / 4),
                    '?',
                ),
            ),
            {
                'description': 'A table of indices the other blocks point into: the vertex indices (in `vertices`) '
                'and texture coordinate indices (in `vertex_uvs`) of the polygons (`offset_3d`, `offset_2d`), the '
                'indices of chained polygons, the moved vertices of the morphs and the polygon lists of the '
                'partitions'
            },
        )

    def serializer_class(self):
        from serializers import OripGeometrySerializer

        return OripGeometrySerializer
