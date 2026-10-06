from typing import Dict

from library.read_blocks import (
    DeclarativeCompoundBlock,
    CompoundBlock,
    IntegerBlock,
    BytesBlock,
    ArrayBlock,
    DecimalBlock,
    FixedPointBlock,
    OptionalBlock,
)
from resources.eac.fields.misc import Point3D, Quaternion

# NFS4 (High Stakes) uses the same overall "TRK" family of formats as NFS3, but the file layout
# differs in several places: virtual road (vroad) data moved from per-block to a single global
# array referenced by index, block headers are stored in one contiguous array followed by a
# separate contiguous array of block bodies (rather than being interleaved per block like NFS3),
# and each block's own polygon/extra-object chunks are sized from counts already read as part of
# its header instead of being self-length-prefixed. See `library/loader.py`'s `.FRD` detection
# branch for how NFS3 vs NFS4 files (same extension) are told apart.


def _ancestor(ctx, levels: int):
    # Guards against the standalone, parent-less `DocumentationContext()` used when rendering a
    # criteria/length lambda's string representation for the auto-generated docs (see
    # `OptionalBlock.schema`/`ArrayBlock.length_doc_str`) - real read/write contexts always have
    # enough real parents for the `levels` this module calls with.
    for _ in range(levels):
        if ctx is None or ctx.parent is None:
            return ctx
        ctx = ctx.parent
    return ctx


def _block_header_field(*path: str):
    # For use inside Nfs4TrkBlock.Fields: looks up a field of the corresponding entry (same
    # array index) of the top-level `blocks_headers` array, 2 context levels above this block
    # (Nfs4TrkBlock's own context -> the `blocks` array context -> FrdMap's own context).
    suffix = '/'.join(path)
    return lambda ctx: _ancestor(ctx, 2).data(f'blocks_headers/{ctx.name}/{suffix}')


def _block_header_chunk_count(chunk_index: int):
    # For use as the `length` of a Nfs4XObjChunk nested directly inside Nfs4TrkBlock.Fields:
    # looks up `object_chunk_counts[chunk_index].num` of the enclosing block's header. 3 levels
    # above the chunk's own context: Nfs4XObjChunk's context -> Nfs4TrkBlock's own context (whose
    # name is the block index) -> the `blocks` array context -> FrdMap's own context.
    return lambda ctx: _ancestor(ctx, 3).data(f'blocks_headers/{ctx.parent.name}/object_chunk_counts/{chunk_index}/num')


def _object_header_field(*path: str):
    # For use inside Nfs4ExtraObject.Fields: looks up a field of the corresponding entry (same
    # array index) of the enclosing Nfs4XObjChunk's own `object_headers` array, 2 context levels
    # above this object (Nfs4ExtraObject's own context -> the `objects` array context ->
    # Nfs4XObjChunk's own context).
    suffix = '/'.join(path)
    return lambda ctx: _ancestor(ctx, 2).data(f'object_headers/{ctx.name}/{suffix}')


class Nfs4VRoadBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Virtual road entry: a point on the road centre line with orientation vectors '
            'of the road surface and distances to the road edges. Referenced by index from '
            'polygons of track blocks',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        ref_point = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'A point on the track surface this virtual road entry describes'},
        )
        normal = (Point3D(child=DecimalBlock(length=4)), {'description': 'A normal vector of the road surface'})
        forward = (Point3D(child=DecimalBlock(length=4)), {'description': 'A forward vector, along the road direction'})
        right = (Point3D(child=DecimalBlock(length=4)), {'description': 'A right vector, across the road'})
        left_wall = (DecimalBlock(length=4), {'description': 'Distance to the left wall/edge'})
        right_wall = (DecimalBlock(length=4), {'description': 'Distance to the right wall/edge'})
        unk0 = (ArrayBlock(child=DecimalBlock(length=4), length=2), {'is_unknown': True})
        unk1 = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=5), {'is_unknown': True})


class Nfs4BlockCount(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Amount of items in some array of the track block, paired with an unknown value',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        num = (IntegerBlock(length=4, is_signed=False), {'description': 'Amount of items'})
        unk = (IntegerBlock(length=4), {'is_unknown': True})


class Nfs4NeighbourData(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Reference to a neighbouring track block'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block = (IntegerBlock(length=2, is_signed=True), {'description': 'Neighbouring block index, or -1'})
        unk = (IntegerBlock(length=2, is_signed=True), {'is_unknown': True})


class Nfs4TrkBlockHeader(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Metadata of a track block (segment of the track): position, bounds, neighbours '
            'and the counts which define sizes of all arrays in the [Nfs4TrkBlock]'
            '(#nfs4trkblock) with the same index',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_chunk_sizes = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=11),
            {'description': 'Amount of polygons in each of the 11 polygon chunks (see Nfs4TrkBlock) of this block'},
        )
        polygon_chunk_sizes_dup = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=11),
            {'is_unknown': True},
        )
        num_vertices = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Total amount of vertices stored for this block'},
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
        num_vertices_dup = (IntegerBlock(length=4, is_signed=False), {'description': 'Equals to `num_vertices`'})
        num_vertices_obj = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of vertices used by per-block objects?', 'is_unknown': True},
        )
        unk0 = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=2), {'is_unknown': True})
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
        neighbour_data = (
            ArrayBlock(child=Nfs4NeighbourData(), length=300),
            {'description': 'Neighbouring blocks. Unused items have block index -1'},
        )
        object_chunk_counts = (
            ArrayBlock(child=Nfs4BlockCount(), length=4),
            {
                'description': 'Amount of extra objects in each of the 4 per-block '
                'extra object chunks (see Nfs4TrkBlock)'
            },
        )
        num_polygons = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of items in `polygon_vroad_data`'},
        )
        bounds_min = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Minimum corner of the axis-aligned bounding box of the block'},
        )
        bounds_max = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Maximum corner of the axis-aligned bounding box of the block'},
        )
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        num_positions = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of position entries (groups of road polygons), usually 8', 'is_unknown': True},
        )
        num_xobj = (Nfs4BlockCount(), {'description': 'Amount of items in `xobj`'})
        num_polyobj = (Nfs4BlockCount(), {'description': 'Amount of items in `xobj2`'})
        num_soundsrc = (Nfs4BlockCount(), {'description': 'Amount of items in `soundsrc`'})
        num_lightsrc = (Nfs4BlockCount(), {'description': 'Amount of items in `lightsrc`'})
        neighbors = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=8), {'is_unknown': True})


class Nfs4PolygonVroadData(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Per-polygon road data of a track block: reference to the global virtual road '
            'entry plus orientation vectors of the surface at this polygon',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        hs_minmax = (ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=4), {'is_unknown': True})
        flags = (ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=5), {'is_unknown': True})
        unk = (IntegerBlock(length=1), {'is_unknown': True})
        vroad_idx = (
            IntegerBlock(length=2, is_signed=False),
            {'description': 'Index of the corresponding entry in the top-level `vroad` array'},
        )
        normal = (
            Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True),
            {'description': 'A normal vector of the surface'},
        )
        forward = (
            Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True),
            {'description': 'A forward vector of the surface'},
        )


class Nfs4RefExtraObject(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Reference to an extra object (XOBJ) placed in the track block'}

    class Fields(DeclarativeCompoundBlock.Fields):
        pt = (
            Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
            {'description': 'Position of the object'},
        )
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        global_index = (
            IntegerBlock(length=2, is_signed=False),
            {'description': 'Sequence number of this object among all extra objects of the track'},
        )
        unk1 = (BytesBlock(length=3), {'is_unknown': True})
        collision = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})


class Nfs4RefExtraObject2(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Reference to a per-block object (POLYOBJ) placed in the track block',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        type = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        id = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        pt = (
            Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True)),
            {'description': 'Position of the object'},
        )
        crossindex = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        unk1 = (BytesBlock(length=3), {'is_unknown': True})


class Nfs4XObjHeader(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Header of an extra object: type, position and the counts which define the '
            'sizes of the corresponding [Nfs4ExtraObject](#nfs4extraobject) arrays',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        type = (
            IntegerBlock(length=4, is_signed=False),
            {
                'description': 'Object type. One of: 2, 4 (normal static object), 3 (animated object, has '
                '`anim_data`), 6 (special/physics prop, has `special_data`). Objects of type 6 '
                'are placed in global chunks of the track file, not in track blocks'
            },
        )
        index = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        pt = (Point3D(child=DecimalBlock(length=4)), {'description': 'Object position'})
        size = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        num_vertices = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of vertices of the corresponding entry in `objects`'},
        )
        unk2 = (ArrayBlock(child=IntegerBlock(length=4), length=2), {'is_unknown': True})
        num_polygons = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Amount of polygons of the corresponding entry in `objects`'},
        )
        unk3 = (IntegerBlock(length=4), {'is_unknown': True})


class Nfs4AnimKeyframe(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Animation keyframe of an extra object'}

    class Fields(DeclarativeCompoundBlock.Fields):
        pt = (
            Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
            {'description': 'Object position at this keyframe'},
        )
        orientation = (
            Quaternion(child=FixedPointBlock(length=2, fraction_bits=14, is_signed=True)),
            {
                'description': 'Object orientation at this keyframe. Presumably the same as in NFS3: object vertices '
                "are rotated by it (v' = q v q^-1), then moved to `pt`"
            },
        )


class Nfs4AnimExtra(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Animation of an extra object: a sequence of keyframes'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        anim_type = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        anim_id = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        num_keyframes = (
            IntegerBlock(length=2, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('keyframes'))),
            {'usage': 'io,doc', 'description': 'Amount of keyframes'},
        )
        delay = (IntegerBlock(length=2, is_signed=False), {'description': 'Animation delay/period'})
        keyframes = (
            ArrayBlock(child=Nfs4AnimKeyframe(), length=lambda ctx: ctx.data('num_keyframes')),
            {'description': 'Animation keyframes'},
        )


class Nfs4SpecialExtra(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Physics properties of a special extra object (movable prop, e.g. a barrel or a cone)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        location = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Position of the object. Equals to `pt` of the object header'},
        )
        mass = (DecimalBlock(length=4), {'description': 'Mass of the object'})
        transform = (
            ArrayBlock(child=DecimalBlock(length=4), length=9),
            {
                'description': "3x3 rotation matrix of the object. Rotates its vertices as row vectors: v' = v M "
                '(verified by roadside boards facing the oncoming traffic)'
            },
        )
        collision_dimensions = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Dimensions of the collision box of the object'},
        )
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=2), {'is_unknown': True})
        unk2 = (IntegerBlock(length=2), {'is_unknown': True})


class Nfs4Polygon(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A single quad polygon of terrain or extra object. UV coordinates are not '
            'stored: the texture is mapped to the whole polygon, oriented according to '
            '`tex_flags`',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        vertices = (
            ArrayBlock(child=IntegerBlock(length=2, is_signed=False), length=4),
            {
                'description': 'Indexes of the 4 vertices in the vertex table of the enclosing track block '
                '(terrain polygons) or extra object (object polygons)'
            },
        )
        texture = (
            IntegerBlock(length=2, is_signed=False),
            {
                'description': 'Bits 0-10: index of the texture in the track QFS archive '
                "(<file>0.QFS), not counting the archive's mirrored texture copies (images with a "
                '"<mirrored>" text attachment). Other bits: rendering flags'
            },
        )
        tex_flags = (
            IntegerBlock(length=2, is_signed=False),
            {
                'description': 'UV orientation of the texture on this polygon. Base UV-s of the 4 vertices are '
                '(0,1), (1,1), (1,0), (0,0); bit 4 mirrors them horizontally, bits 7-8 rotate '
                'them by 90 degrees x value. Other bits unknown.'
            },
        )
        anim_flags = (
            IntegerBlock(length=1, is_signed=False),
            {'description': 'Used for animated textures: length/period', 'is_unknown': True},
        )


class Nfs4ExtraObject(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Extra object mesh: a standalone object placed on the track (billboard, animated '
            'object, physics prop). Type, position and array sizes are defined by the '
            '[Nfs4XObjHeader](#nfs4xobjheader) with the same index in the enclosing chunk',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        anim_data = (
            OptionalBlock(
                child=Nfs4AnimExtra(), criteria=lambda ctx: _object_header_field('type')(ctx) == 3, default_value=None
            ),
            {'description': 'Present when the corresponding `object_headers` entry has type == 3 (animated)'},
        )
        special_data = (
            OptionalBlock(
                child=Nfs4SpecialExtra(),
                criteria=lambda ctx: _object_header_field('type')(ctx) == 6,
                default_value=None,
            ),
            {'description': 'Present when the corresponding `object_headers` entry has type == 6 (special)'},
        )
        vertices = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=_object_header_field('num_vertices')),
            {
                'description': 'Vertices, relative to the object position `pt` of the header (rotated by '
                '`special_data.transform` for special objects)'
            },
        )
        vertex_shading = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=lambda ctx: len(ctx.data('vertices'))),
            {'description': 'Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex'},
        )
        polygons = (
            ArrayBlock(child=Nfs4Polygon(), length=_object_header_field('num_polygons')),
            {'description': 'Polygons of this object'},
        )


class Nfs4XObjChunk(CompoundBlock):
    def __init__(self, length, **kwargs):
        super().__init__(
            fields=[
                ('object_headers', ArrayBlock(child=Nfs4XObjHeader(), length=length), {}),
                (
                    'objects',
                    ArrayBlock(child=Nfs4ExtraObject(), length=lambda ctx: len(ctx.data('object_headers'))),
                    {},
                ),
            ],
            inline_description='A group of extra (out-of-terrain) objects: e.g. billboards, animated '
            'objects, physics props',
            **kwargs,
        )


class Nfs4TrkBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Track block body: terrain vertices and polygons at 3 levels of detail, plus '
            'objects placed in this segment of the track. All array sizes come from the '
            '[Nfs4TrkBlockHeader](#nfs4trkblockheader) with the same index',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        vertices = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=_block_header_field('num_vertices')),
            {'description': 'Vertices, global coordinates'},
        )
        vertex_shading = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=lambda ctx: len(ctx.data('vertices'))),
            {'description': 'Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex'},
        )
        polygon_vroad_data = (
            ArrayBlock(child=Nfs4PolygonVroadData(), length=_block_header_field('num_polygons')),
            {'description': 'Per-polygon reference into the global `vroad` array, plus flags'},
        )
        xobj = (
            ArrayBlock(child=Nfs4RefExtraObject(), length=_block_header_field('num_xobj/num')),
            {'description': 'References to extra objects placed in this block'},
        )
        xobj2 = (
            ArrayBlock(child=Nfs4RefExtraObject2(), length=_block_header_field('num_polyobj/num')),
            {'description': 'References to per-block objects placed in this block'},
        )
        soundsrc = (
            ArrayBlock(child=BytesBlock(length=16), length=_block_header_field('num_soundsrc/num')),
            {
                'description': 'Sound sources. Each 16-byte item: position (3 x 32-bit fixed point with 16 '
                'fraction bits) + 32-bit sound type'
            },
        )
        lightsrc = (
            ArrayBlock(child=BytesBlock(length=16), length=_block_header_field('num_lightsrc/num')),
            {
                'description': 'Light sources. Each 16-byte item: position (3 x 32-bit fixed point with 16 '
                'fraction bits) + 32-bit light type'
            },
        )
        polygons_low_res_track = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/0')),
            {'description': 'Low-res track polygons'},
        )
        polygons_low_res_misc = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/1')),
            {'description': 'Low-res misc (non-track) polygons'},
        )
        polygons_med_res_track = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/2')),
            {'description': 'Medium-res track polygons'},
        )
        polygons_med_res_misc = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/3')),
            {'description': 'Medium-res misc (non-track) polygons'},
        )
        polygons_high_res_track = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/4')),
            {'description': 'High-res track polygons'},
        )
        polygons_high_res_misc = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/5')),
            {'description': 'High-res misc (non-track) polygons'},
        )
        lanes = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/6')),
            {'description': 'Lane helper polygons, not meant to be rendered'},
        )
        polygons_high_res_misc_1 = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/7')),
            {
                'description': 'Additional polygon chunk, purpose unknown. Not rendered by the converter',
                'is_unknown': True,
            },
        )
        polygons_high_res_misc_2 = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/8')),
            {
                'description': 'Additional polygon chunk, purpose unknown. Not rendered by the converter',
                'is_unknown': True,
            },
        )
        polygons_high_res_misc_3 = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/9')),
            {
                'description': 'Additional polygon chunk, purpose unknown. Not rendered by the converter',
                'is_unknown': True,
            },
        )
        polygons_high_res_misc_4 = (
            ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/10')),
            {
                'description': 'Additional polygon chunk, purpose unknown. Not rendered by the converter',
                'is_unknown': True,
            },
        )
        extra_objects_0 = (
            Nfs4XObjChunk(length=_block_header_chunk_count(0)),
            {
                'description': 'Extra objects chunk #0 of this block. Amount of objects is '
                '`object_chunk_counts[0].num` of the block header'
            },
        )
        extra_objects_1 = (
            Nfs4XObjChunk(length=_block_header_chunk_count(1)),
            {
                'description': 'Extra objects chunk #1 of this block. Amount of objects is '
                '`object_chunk_counts[1].num` of the block header'
            },
        )
        extra_objects_2 = (
            Nfs4XObjChunk(length=_block_header_chunk_count(2)),
            {
                'description': 'Extra objects chunk #2 of this block. Amount of objects is '
                '`object_chunk_counts[2].num` of the block header'
            },
        )
        extra_objects_3 = (
            Nfs4XObjChunk(length=_block_header_chunk_count(3)),
            {
                'description': 'Extra objects chunk #3 of this block. Amount of objects is '
                '`object_chunk_counts[3].num` of the block header'
            },
        )


class Nfs4FrdMap(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Main track file (NFS4 High Stakes). The track is split into blocks (segments): '
            'block headers with all counts come first, then block bodies with vertices, '
            'polygons at 3 levels of detail and objects. Polygon textures index the track '
            'QFS archive (<track>0.QFS), skipping its mirrored texture copies; UV-s are not stored, texture orientation '
            'is defined by polygon flags',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk = (BytesBlock(length=28), {'description': 'Unknown header', 'is_unknown': True})
        num_blocks = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('blocks_headers')) - 1),
            {'description': 'Number of track blocks'},
        )
        num_vroad = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('vroad'))),
            {'description': 'Number of virtual road entries'},
        )
        vroad = (
            ArrayBlock(child=Nfs4VRoadBlock(), length=lambda ctx: ctx.data('num_vroad')),
            {
                'description': 'Virtual road (spline) data for the whole track, referenced by index '
                'from `blocks[].polygon_vroad_data`'
            },
        )
        blocks_headers = (
            ArrayBlock(child=Nfs4TrkBlockHeader(), length=lambda ctx: ctx.data('num_blocks') + 1),
            {
                'description': 'Metadata for every track block, incl. the counts used to size '
                'the corresponding entry of `blocks`'
            },
        )
        blocks = (
            ArrayBlock(child=Nfs4TrkBlock(), length=lambda ctx: ctx.data('num_blocks') + 1),
            {'description': 'Track block geometry and extra data'},
        )
        num_global_objects_0 = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: len(ctx.data('global_objects_0/object_headers')),
            ),
            {'usage': 'io,doc', 'description': 'Amount of objects in `global_objects_0`'},
        )
        global_objects_0 = (
            Nfs4XObjChunk(length=lambda ctx: ctx.parent.data('num_global_objects_0')),
            {'description': 'Extra objects not attached to any track block'},
        )
        num_global_objects_1 = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: len(ctx.data('global_objects_1/object_headers')),
            ),
            {'usage': 'io,doc', 'description': 'Amount of objects in `global_objects_1`'},
        )
        global_objects_1 = (
            Nfs4XObjChunk(length=lambda ctx: ctx.parent.data('num_global_objects_1')),
            {'description': 'Extra objects not attached to any track block. Special/physics props (type 6) live here'},
        )

    def serializer_class(self):
        from serializers import Nfs4FrdMapSerializer

        return Nfs4FrdMapSerializer
