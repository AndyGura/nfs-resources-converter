from math import floor
from typing import Dict

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
                'description': "Huh, that's a srange field. From my tests, if it is xxx0_0011, the "
                "polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only "
                'one polygon for entire TNFS with type == 2 in burnt sienna props. If '
                'ignore this polygon everything still looks great'
            },
        )
        mapping = (
            BitFlagsBlock(length=1, flag_names=[(0, 'two_sided'), (1, 'flip_normal'), (4, 'use_uv')]),
            {'description': 'Rendering properties of the polygon'},
        )
        texture_index = (IntegerBlock(length=1), {'description': "The index of item in ORIP's tex_ids block"})
        unk = (IntegerBlock(length=1), {'is_unknown': True})
        offset_3d = (
            IntegerBlock(length=4),
            {
                'description': "The index in vmap ORIP's table. This index "
                'represents first vertex of this polygon, so in order to determine all '
                'vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. '
                'Look at vmap description for more info'
            },
        )
        offset_2d = (
            IntegerBlock(length=4),
            {
                'description': 'The same as offset_3d, also points to vmap, but used '
                'for texture coordinates. Look at vmap description '
                'for more info'
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


class OripTextureName(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A settings of the texture. From what is known, contains name of bitmap (not always a correct UTF-8)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        type = (BytesBlock(length=8), {'is_unknown': True})
        file_name = (UTF8Block(length=4), {'description': 'Name of bitmap in SHPI block'})
        unknown = (BytesBlock(length=8), {'is_unknown': True})


class RenderOrderBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=8), {'description': "identifier ('NON-SORT', 'inside', 'surface', 'outside')"})
        unk0 = (IntegerBlock(length=4), {'description': "0x8 for 'NON-SORT' or 0x1 for the others"})
        polygons_amount = (
            IntegerBlock(length=4),
            {'description': 'Polygons amount (3DO). For TNFSSE sometimes too big value'},
        )
        polygon_sum = (
            IntegerBlock(length=4),
            {
                'description': "0 for 'NON-SORT'; block’s 10 size for 'inside'; equals block’s 10 size "
                "+ number of polygons from ‘inside’ = XXX for 'surface'; equals XXX + "
                "number of polygons from 'surface' for 'outside'; (Description for 3DO "
                'orip file, TNFSSE version has only 9 blocks!)'
            },
        )
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        unk2 = (IntegerBlock(length=4), {'is_unknown': True})


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
            NullTerminatedUTF8Block(length=8),
            {'description': 'Name of the entry (up to 7 characters). A few entries have a garbage name, like "\\x02"'},
        )
        offset = ArrayBlock(
            child=IntegerBlock(length=1),
            length=(lambda ctx: 8 - ctx.buffer.tell() + ctx.read_start_offset, '7 - len(name)'),
            programmatic_value=lambda ctx: [0] * (7 - len(ctx.data('name'))),
        )
        index = (IntegerBlock(length=4), {'description': 'Index of the vertex (`fx_polys`) or polygon (`labels`)'})


# TODO check additional info in http://3dodev.com/documentation/file_formats/games/nfs
class OripGeometry(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Geometry block for 3D model with few materials',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('ORIP'), length=4), {'description': 'Resource ID'})
        block_size = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
            {'description': 'Total ORIP block size in bytes'},
        )
        unk0 = (
            IntegerBlock(length=4, value_validator=Eq(0x02BC)),
            {
                'description': 'Looks like always 0x01F4 in 3DO version and 0x02BC in PC TNFSSE. ORIP type?',
                'is_unknown': True,
            },
        )
        unk1 = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})
        num_vrtx = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('vertices/data'))),
            {'description': 'Amount of vertices'},
        )
        unk2 = (BytesBlock(length=4), {'is_unknown': True})
        vrtx_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'vertices'),
            ),
            {'description': 'An offset to vertices'},
        )
        num_uvs = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('vertex_uvs'))),
            {'description': 'Amount of vertex UV-s (texture coordinates)'},
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
        identifier = (
            UTF8Block(length=12),
            {'description': "Some ID of geometry, don't know the purpose", 'is_unknown': True},
        )
        num_tex_ids = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('tex_ids'))),
            {'description': 'Amount of texture names'},
        )
        tex_ids_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: 112 + len(ctx.data('polygons')) * 12 + len(ctx.data('vertex_uvs')) * 8,
            ),
            {'description': 'An offset to texture names block. Always equals to `112 + num_polygons*12 + num_uvs*8`'},
        )
        num_tex_nmb = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('tex_nmb'))),
            {'description': 'Amount of texture numbers'},
        )
        tex_nmb_ptr = (IntegerBlock(length=4), {'description': 'An offset to texture numbers block'})
        num_ren_ord = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('render_order'))),
            {'description': 'Amount of items in render_order block'},
        )
        ren_ord_ptr = (
            IntegerBlock(
                length=4, programmatic_value=lambda ctx: ctx.data('tex_nmb_ptr') + len(ctx.data('tex_nmb')) * 20
            ),
            {'description': 'Offset of render_order block. Always equals to `tex_nmb_ptr + num_tex_nmb*20`'},
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
                programmatic_value=lambda ctx: (
                    ctx.data('tex_nmb_ptr') + len(ctx.data('tex_nmb')) * 20 + len(ctx.data('render_order')) * 28
                ),
            ),
            {
                'description': 'Offset of fx_polys block. Always equals to `tex_nmb_ptr + num_tex_nmb*20 + '
                'num_ren_ord*28`'
            },
        )
        num_lbl = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('labels'))),
            {'description': 'Amount of items in labels block'},
        )
        lbl_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: (
                    ctx.data('tex_nmb_ptr')
                    + len(ctx.data('tex_nmb')) * 20
                    + len(ctx.data('render_order')) * 28
                    + len(ctx.data('fx_polys')) * 12
                ),
            ),
            {
                'description': 'Offset of labels block. Always equals to `tex_nmb_ptr'
                ' + num_tex_nmb*20 + num_ren_ord*28 + num_fxp*12`'
            },
        )
        unknowns1 = (BytesBlock(length=12), {'is_unknown': True})
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
        unk_tex_ids = (
            Padding(to=(lambda ctx: ctx.data('tex_ids_ptr'), 'tex_ids_ptr')),
            {'description': 'Padding up to `tex_ids_ptr`, normally empty'},
        )
        tex_ids = (
            ArrayBlock(child=OripTextureName(), length=lambda ctx: ctx.data('num_tex_ids')),
            {'description': 'A table of texture references. Items are retrieved by index, located in polygon item'},
        )
        offset = (
            Padding(to=(lambda ctx: ctx.data('tex_nmb_ptr'), 'tex_nmb_ptr'), allow_negative_length=True),
            {
                'description': 'In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in'
                " case of DIABLO.CFM it's length is equal to -3, meaning that last 3 bytes from "
                'texture names block are reused by next block'
            },
        )
        tex_nmb = (
            ArrayBlock(
                child=ArrayBlock(child=IntegerBlock(length=1), length=20), length=lambda ctx: ctx.data('num_tex_nmb')
            ),
            {'is_unknown': True},
        )
        unk_ren_ord = (
            Padding(to=(lambda ctx: ctx.data('ren_ord_ptr'), 'ren_ord_ptr')),
            {'description': 'Padding up to `ren_ord_ptr`, normally empty'},
        )
        render_order = (
            ArrayBlock(child=RenderOrderBlock(), length=lambda ctx: ctx.data('num_ren_ord')),
            {'description': 'Render order. The exact mechanism how it works is unknown'},
        )
        unk_fxp = (
            Padding(to=(lambda ctx: ctx.data('fxp_ptr'), 'fxp_ptr')),
            {'description': 'Padding up to `fxp_ptr`, normally empty'},
        )
        fx_polys = (
            ArrayBlock(child=NamedIndex(), length=lambda ctx: ctx.data('num_fxp')),
            {
                'description': 'Named points of the model for visual effects, in high-poly car models (CFM). Despite '
                'the name, `index` is the index of an item of `vertices`, not of a polygon. Names (the case differs '
                'between cars: F512M, F512TR, TRAFFC and WARRIOR use lower case): `FL0`, `FL1`, `FR0`, `FR1`, '
                '`RL0`, `RL1`, `RR0`, `RR1` are the ground contact points of the wheels (front/rear, left/right), '
                '0 at the front edge of the wheel, 1 at the rear edge (the bottom corners of the wheel polygon '
                'labelled `lt_frnt`, `rt_rear`...); guess: sources of tyre smoke, dust and skid marks. `smok` is a '
                'point at the engine: on the hood of front-engined cars (DVIPER, CZR1, MRX7, TSUPRA), at the '
                'exhaust or the engine lid of the others; guess: source of engine smoke and fire of a wrecked car. '
                '`d` (only in the M*.CFM models) is a point near the bottom of the front left wheel, unknown '
                'purpose. DVIPER has one more entry with garbage name "\\x02" (the top of a wheel polygon). The '
                'gg-web-engine export writes every entry as a dummy "fx_<name>" at the vertex, with properties `fx` '
                '(the name) and `vertex` (the index), skipping entries with a non-printable name like "\\x02"'
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
                '`polygons`. Names: `lt_frnt`, `rt_frnt`, `lt_rear`, `rt_rear`: the outer side of the wheels '
                '(left/right, front/rear), mostly untextured (guess: the game draws the tyre textures `tyr*` there); '
                '`bkll` / `bklr`: left / right rear light (guess: lit when braking); `bott`: a horizontal quad over '
                'the whole underside of the body of the simple traffic car models (texture `bott`), purpose unknown. '
                'Guesses: `bacr` (P911) the centre part of the rear light bar; `mm` (LDIABLO; garbage name "\\x01" on '
                'the same polygon of LDIABL) a two-sided quad at the inner side of the front right wheel (texture '
                '`circ`); `W` (TRAFFC, WARRIOR) a triangle at the top rear left corner of the body (texture `abox`); '
                'COPMUST: `hll0` / `hlr0` headlights, `bkl0` / `bkr0` rear lights, `lfl0` / `lfr0` and `lrl0` / '
                '`lrr0` the front and rear left / right parts of the siren light bar on the roof, flashed by the game'
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
                'The unit is meter'
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
                'description': 'A LUT for both 3D and 2D vertices. Every item is an index of either item in '
                'vertices or vertex_uvs. When building 3D vertex, polygon defines offset_3d, '
                'a lookup to this table, and value from here is an index of item in vertices. '
                'When building UV-s, polygon defines offset_2d, a lookup to this table, and '
                'value from here is an index of item in vertex_uvs'
            },
        )

    def serializer_class(self):
        from serializers import OripGeometrySerializer

        return OripGeometrySerializer
