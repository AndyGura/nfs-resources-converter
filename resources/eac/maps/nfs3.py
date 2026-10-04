from typing import Dict

from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    BytesBlock,
    ArrayBlock,
    EnumByteBlock,
    DelegateBlock,
    LengthPrefixedArrayBlock,
    DecimalBlock,
    FixedPointBlock,
)
from library.read_blocks.misc.value_validators import Eq
from resources.eac.fields.misc import Point3D


class FrdPositionBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A group of consecutive high-res track polygons: a "row" of polygons across the '
            'road. A track block usually has 8 of them, together covering all polygons of '
            'the high-res track chunk',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        polygon = (
            IntegerBlock(length=2, is_signed=False),
            {
                'description': 'Index of the first polygon of this group in the high-res track polygon chunk '
                '(`polygons[4]` of the corresponding [FrdPolyBlock](#frdpolyblock))'
            },
        )
        num_polygons = (IntegerBlock(length=1, is_signed=False), {'description': 'Amount of polygons in this group'})
        unk = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        extra_neighbor1 = (
            IntegerBlock(length=2, is_signed=False),
            {'description': 'Extra neighbouring block index? 0xFFFF if none', 'is_unknown': True},
        )
        extra_neighbor2 = (
            IntegerBlock(length=2, is_signed=False),
            {'description': 'Extra neighbouring block index? 0xFFFF if none', 'is_unknown': True},
        )


class FrdBlockPolygonData(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Per-polygon data of the high-res track polygons: one record per polygon of '
            '`polygons[4]` chunk of the corresponding [FrdPolyBlock](#frdpolyblock)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        vroad_idx = (
            IntegerBlock(length=1, is_signed=False),
            {
                'description': 'Index of entry in `vroad` array of the block: orientation of the road surface '
                'at this polygon'
            },
        )
        flags = (
            IntegerBlock(length=1, is_signed=False),
            {'description': 'Polygon flags (road surface type, driveable etc.?)', 'is_unknown': True},
        )
        unk = (BytesBlock(length=6), {'is_unknown': True})


class FrdBlockVroadData(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Virtual road entry: orientation of the road surface, referenced by index from '
            '`polygons[].vroad_idx` of the block',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        normal = (
            Point3D(child=FixedPointBlock(length=2, fraction_bits=16, is_signed=True), normalized=True),
            {'description': 'A normal vector of the surface'},
        )
        forward = (
            Point3D(child=FixedPointBlock(length=2, fraction_bits=16, is_signed=True), normalized=True),
            {'description': 'A forward vector of the surface'},
        )


class FrdBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Track block: a segment of the track. Contains terrain vertices with shading, '
            'road orientation data and references to objects placed in this segment. '
            'Polygons of the block are stored separately, in the [FrdPolyBlock](#frdpolyblock) '
            'with the same index',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (
            Point3D(child=DecimalBlock(length=4)),
            {
                'description': 'Position of the block in the world: a point on the road at the block start. '
                'Positions of all blocks form the track path'
            },
        )
        bounds = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=4),
            {'description': 'Block bounding rectangle'},
        )
        num_vertices = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('vertices'))),
            {'description': 'Total amount of vertices'},
        )
        num_vertices_high = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of vertices used by high-res terrain polygons'},
        )
        num_vertices_low = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of vertices used by low-res terrain polygons'},
        )
        num_vertices_med = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of vertices used by medium-res terrain polygons'},
        )
        num_vertices_dup = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('vertices'))),
            {'description': 'Equals to `num_vertices`'},
        )
        num_vertices_obj = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of vertices used by per-block objects (polyobj)?', 'is_unknown': True},
        )
        vertices = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=lambda ctx: ctx.data('num_vertices')),
            {'description': 'Vertices. Coordinates are global (not relative to block position)'},
        )
        vertex_shading = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=lambda ctx: ctx.data('num_vertices')),
            {'description': 'Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex'},
        )
        neighbour_data = (
            ArrayBlock(child=IntegerBlock(length=2, is_signed=False), length=2 * 0x12C),
            {
                'description': '300 pairs of 16-bit values: (neighbouring block index, unknown). '
                'Unused pairs have index 0xFFFF'
            },
        )
        num_start_pos = (
            IntegerBlock(length=4, is_signed=False),
            {
                'description': 'Index of the first `positions` entry of this block among all blocks of the '
                'track (sum of `num_positions` of all previous blocks)'
            },
        )
        num_positions = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('positions'))),
            {'description': 'Amount of items in `positions`'},
        )
        num_polygons = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('polygons'))),
            {
                'description': 'Amount of items in `polygons`. Equals to the amount of high-res track '
                'polygons (`polygons[4]` chunk of the [FrdPolyBlock](#frdpolyblock))'
            },
        )
        num_vroad = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('vroad'))),
            {'description': 'Amount of items in `vroad`'},
        )
        num_xobj = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('xobj'))),
            {'description': 'Amount of items in `xobj`'},
        )
        num_polyobj = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('polyobj'))),
            {'description': 'Amount of items in `polyobj`'},
        )
        num_soundsrc = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('soundsrc'))),
            {'description': 'Amount of items in `soundsrc`'},
        )
        num_lightsrc = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('lightsrc'))),
            {'description': 'Amount of items in `lightsrc`'},
        )
        positions = (
            ArrayBlock(child=FrdPositionBlock(), length=lambda ctx: ctx.data('num_positions')),
            {'description': 'Groups of high-res track polygons ("rows" across the road)'},
        )
        polygons = (
            ArrayBlock(child=FrdBlockPolygonData(), length=lambda ctx: ctx.data('num_polygons')),
            {'description': 'Per-polygon data (road orientation reference + flags) for the high-res track polygons'},
        )
        vroad = (
            ArrayBlock(child=FrdBlockVroadData(), length=lambda ctx: ctx.data('num_vroad')),
            {'description': 'Virtual road: orientation vectors of the road surface, referenced from `polygons`'},
        )
        xobj = (
            ArrayBlock(child=BytesBlock(length=20), length=lambda ctx: ctx.data('num_xobj')),
            {
                'description': 'References to extra objects (XOBJ) placed in this block. Each 20-byte item: '
                'position (3 x 32-bit fixed point with 24 fraction bits), 16-bit unknown, 16-bit '
                'sequence number of the object among all extra objects of the track, 4 unknown bytes'
            },
        )
        polyobj = (
            ArrayBlock(child=BytesBlock(length=20), length=lambda ctx: ctx.data('num_polyobj')),
            {
                'description': 'References to per-block objects (POLYOBJ). Each 20-byte item: 16-bit unknown, '
                '8-bit type, 8-bit id, position (3 x 32-bit fixed point with 24 fraction bits), '
                '8-bit cross index, 3 unknown bytes'
            },
        )
        soundsrc = (
            ArrayBlock(child=BytesBlock(length=16), length=lambda ctx: ctx.data('num_soundsrc')),
            {
                'description': 'Sound sources. Each 16-byte item: position (3 x 32-bit fixed point with 24 '
                'fraction bits) + 32-bit sound type'
            },
        )
        lightsrc = (
            ArrayBlock(child=BytesBlock(length=16), length=lambda ctx: ctx.data('num_lightsrc')),
            {
                'description': 'Light sources. Each 16-byte item: position (3 x 32-bit fixed point with 24 '
                'fraction bits) + 32-bit light type'
            },
        )


class FrdPolygonRecord(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A single quad polygon of terrain or object'}

    class Fields(DeclarativeCompoundBlock.Fields):
        vertices = (
            ArrayBlock(child=IntegerBlock(length=2), length=4),
            {
                'description': 'Indexes of the 4 vertices in the vertex table of the enclosing track block '
                '(terrain polygons) or extra object (object polygons)'
            },
        )
        tex_id = (
            IntegerBlock(length=2),
            {
                'description': 'Index of entry in `texture_blocks` table of the track file, which defines the real '
                'texture index in the QFS archive and UV coordinates of polygon corners'
            },
        )
        tex_flags = (
            IntegerBlock(length=2),
            {
                'description': 'Texture flags. Zero for terrain polygons, non-zero only in the lanes chunk',
                'is_unknown': True,
            },
        )
        flags = (
            IntegerBlock(length=1),
            {'description': 'Usually 0, observed values 0x20, 0x30, 0x40', 'is_unknown': True},
        )
        unk = (IntegerBlock(length=1), {'description': 'Always 0xF9?', 'is_unknown': True})


class FrdPolygonsBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A chunk of terrain polygons of a track block'}

    class Fields(DeclarativeCompoundBlock.Fields):
        sz = (
            IntegerBlock(length=4),
            {'description': 'Amount of polygons in this chunk. 0 means the chunk is absent and no data follows'},
        )
        data = (
            DelegateBlock(
                possible_blocks=[
                    LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=FrdPolygonRecord()),
                    BytesBlock(length=0),
                ],
                choice_index=lambda ctx, **_: 0 if ctx.data('sz') != 0 else 1,
            ),
            {
                'description': 'Polygons. This data is presented only if sz != 0. The array length prefix '
                'duplicates `sz`'
            },
        )


class FrdPolyObjPolygonsBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Polygons of a single per-block object (POLYOBJ)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        type = (
            IntegerBlock(length=4, is_signed=False),
            {
                'description': 'Object type: 1 - polygons follow; 4 - the object is an extra object (XOBJ), its '
                'geometry is stored in the corresponding chunk of `extraobject_blocks` and nothing '
                'follows here'
            },
        )
        data = (
            DelegateBlock(
                possible_blocks=[
                    LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=FrdPolygonRecord()),
                    BytesBlock(length=0),
                ],
                choice_index=lambda ctx, **_: 0 if ctx.data('type') == 1 else 1,
            ),
            {'description': 'Polygons of the object. This data is presented only if type == 1'},
        )


class FrdPolyObjBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A chunk of per-block objects (POLYOBJ)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        sz = (
            IntegerBlock(length=4),
            {
                'description': 'Total amount of polygons of all objects in this chunk. 0 means the chunk is absent and '
                'no data follows'
            },
        )
        data = (
            DelegateBlock(
                possible_blocks=[
                    LengthPrefixedArrayBlock(child=FrdPolyObjPolygonsBlock(), length_block=IntegerBlock(length=4)),
                    BytesBlock(length=0),
                ],
                choice_index=lambda ctx, **_: 0 if ctx.data('sz') > 0 else 1,
            ),
            {
                'description': 'Objects. This data is presented only if sz > 0. The array length prefix is the '
                'amount of objects, including the XOBJ references (type == 4)'
            },
        )


class FrdPolyBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Polygons of a track block (the [FrdBlock](#frdblock) with the same index): 7 '
            'chunks of terrain polygons + 4 chunks of per-block objects',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        polygons = (
            ArrayBlock(child=FrdPolygonsBlock(), length=7),
            {
                'description': 'Terrain polygon chunks: 0 - low-res track, 1 - low-res misc (non-track), '
                '2 - medium-res track, 3 - medium-res misc, 4 - high-res track, 5 - high-res misc, '
                '6 - lanes (helper polygons, not rendered). Low/medium/high-res chunks are '
                'alternative levels of detail of the same terrain (roughly 1/4, 1/2 and full '
                'amount of polygons)'
            },
        )
        polyobj = (
            ArrayBlock(child=FrdPolyObjBlock(), length=4),
            {
                'description': '4 chunks of per-block objects. Extra objects (XOBJ) referenced from chunk N are '
                'stored in `extraobject_blocks[4 * block_index + N]` of the track file'
            },
        )


class ExtraObjectDataCrossType4(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Extra data of a static extra object (cross_type == 4)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        pt_ref = (
            Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True)),
            {'description': 'Reference point: position of the object in the world. Object vertices are relative to it'},
        )
        anim_memory = (IntegerBlock(length=4), {'is_unknown': True})


class AnimData(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Animation keyframe of an extra object'}

    class Fields(DeclarativeCompoundBlock.Fields):
        pt = (
            Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True)),
            {'description': 'Object position at this keyframe'},
        )
        od = (
            ArrayBlock(child=IntegerBlock(length=2), length=4),
            {
                'description': 'Object orientation at this keyframe, presumably a quaternion (x, y, z, w), where each '
                'component is 16-bit fixed point with 14 fraction bits (identity is [0, 0, 0, 16384])'
            },
        )


class ExtraObjectDataCrossType1(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Extra data of an animated extra object (cross_type == 3)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk = (BytesBlock(length=18), {'is_unknown': True})
        type = (IntegerBlock(length=1, value_validator=Eq(3)), {'description': 'Animation type, always 3'})
        objno = (IntegerBlock(length=1), {'description': 'Object number', 'is_unknown': True})
        num_animdata = (
            IntegerBlock(length=2, programmatic_value=lambda ctx: len(ctx.data('animdata'))),
            {'description': 'Amount of keyframes'},
        )
        anim_delay = (IntegerBlock(length=2), {'description': 'Delay between keyframes (animation speed)'})
        animdata = (
            ArrayBlock(child=AnimData(), length=lambda ctx: ctx.data('num_animdata')),
            {
                'description': 'Animation keyframes. Object vertices are relative to the position of the '
                'current keyframe'
            },
        )


class ExtraObjectBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Extra object (XOBJ): a standalone mesh placed on the track, e.g. a billboard, '
            'a building or an animated object',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        cross_type = (IntegerBlock(length=4), {'description': 'Object type: 4 - static object, 3 - animated object'})
        cross_no = (IntegerBlock(length=4), {'description': 'Object number', 'is_unknown': True})
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        data = (
            DelegateBlock(
                possible_blocks=[ExtraObjectDataCrossType4(), ExtraObjectDataCrossType1()],
                choice_index=lambda ctx, **_: 0 if ctx.data('cross_type') == 4 else 1,
            ),
            {'description': 'Type-specific data (position or animation), block class picked according to `cross_type`'},
        )
        num_vertices = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('vertices'))),
            {'description': 'Amount of vertices'},
        )
        vertices = (
            ArrayBlock(
                child=Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True)),
                length=lambda ctx: ctx.data('num_vertices'),
            ),
            {
                'description': 'Vertices, relative to the object position (reference point for static objects, '
                'current keyframe position for animated ones)'
            },
        )
        vertex_shading = (
            ArrayBlock(child=IntegerBlock(length=4), length=lambda ctx: ctx.data('num_vertices')),
            {'description': 'Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex'},
        )
        polygons = (
            LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=FrdPolygonRecord()),
            {'description': 'Polygons of the object. Vertex indexes point to `vertices` of this object'},
        )


class TextureBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Texture reference. Polygons refer to items of this table by `tex_id`, the item '
            'defines the actual texture in the QFS archive and UV coordinates of the polygon '
            'corners',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        width = (IntegerBlock(length=2, is_signed=False), {'description': 'Texture width'})
        height = (IntegerBlock(length=2, is_signed=False), {'description': 'Texture height'})
        unk0 = (
            IntegerBlock(length=4),
            {'description': 'Blending related, hometown covered bridges godrays', 'is_unknown': True},
        )
        corners = (
            ArrayBlock(child=DecimalBlock(length=4), length=8),
            {
                'description': 'UV coordinates of the 4 polygon corners (u0, v0, u1, v1, u2, v2, u3, v3), '
                'in the same order as polygon vertices'
            },
        )
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        is_lane = (
            EnumByteBlock(
                enum_names=[
                    (0, 'default'),
                    (1, 'lane'),
                ]
            ),
            {'description': '1 if not a real texture (lane), 0 usually', 'is_unknown': True},
        )
        texture_id = (
            IntegerBlock(length=2, is_signed=False),
            {'description': 'Index of the texture in the track QFS archive (<track>0.QFS)'},
        )


class FrdMap(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Main track file. The track is split into blocks (segments). Each block has its '
            'own vertex table ([FrdBlock](#frdblock)) and polygons at 3 levels of detail '
            '([FrdPolyBlock](#frdpolyblock)). Standalone objects (billboards, animated '
            'objects) are stored as extra objects. Polygon textures are referenced through '
            'the `texture_blocks` table, which points to images in <track>0.QFS',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk = (BytesBlock(length=28), {'description': 'Unknown header', 'is_unknown': True})
        num_blocks = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('blocks')) - 1),
            {'description': 'Number of blocks. Block arrays below have `num_blocks + 1` items'},
        )
        blocks = (
            ArrayBlock(child=FrdBlock(), length=lambda ctx: ctx.data('num_blocks') + 1),
            {'description': 'Track blocks: vertices, road data and object references of each track segment'},
        )
        polygon_blocks = (
            ArrayBlock(child=FrdPolyBlock(), length=lambda ctx: ctx.data('num_blocks') + 1),
            {'description': 'Polygons of the track blocks, same index as in `blocks`'},
        )
        extraobject_blocks = (
            ArrayBlock(
                child=LengthPrefixedArrayBlock(child=ExtraObjectBlock(), length_block=IntegerBlock(length=4)),
                length=lambda ctx: 4 * (ctx.data('num_blocks') + 1) + 1,
            ),
            {
                'description': 'Chunks of extra objects (XOBJ): 4 chunks per track block (matching '
                'the 4 `polyobj` chunks of the block), followed by one global chunk with '
                'objects not attached to any block. Each chunk is prefixed with the '
                'amount of objects in it'
            },
        )
        texture_blocks = (
            LengthPrefixedArrayBlock(child=TextureBlock(), length_block=IntegerBlock(length=4)),
            {
                'description': 'Texture references table, used by all polygons of the track. Texture '
                'images are in <track>0.QFS'
            },
        )

    def serializer_class(self):
        from serializers import FrdMapSerializer

        return FrdMapSerializer
