from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 CompoundBlock,
                                 IntegerBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 DecimalBlock,
                                 FixedPointBlock,
                                 OptionalBlock)
from resources.eac.fields.misc import Point3D

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
    return lambda ctx: _ancestor(ctx, 3).data(
        f'blocks_headers/{ctx.parent.name}/object_chunk_counts/{chunk_index}/num')


def _object_header_field(*path: str):
    # For use inside Nfs4ExtraObject.Fields: looks up a field of the corresponding entry (same
    # array index) of the enclosing Nfs4XObjChunk's own `object_headers` array, 2 context levels
    # above this object (Nfs4ExtraObject's own context -> the `objects` array context ->
    # Nfs4XObjChunk's own context).
    suffix = '/'.join(path)
    return lambda ctx: _ancestor(ctx, 2).data(f'object_headers/{ctx.name}/{suffix}')


class Nfs4VRoadBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        ref_point = (Point3D(child=DecimalBlock(length=4)),
                    {'description': 'A point on the track surface this virtual road entry describes'})
        normal = (Point3D(child=DecimalBlock(length=4)),
                  {'description': 'A normal vector of the road surface'})
        forward = (Point3D(child=DecimalBlock(length=4)),
                   {'description': 'A forward vector, along the road direction'})
        right = (Point3D(child=DecimalBlock(length=4)),
                 {'description': 'A right vector, across the road'})
        left_wall = (DecimalBlock(length=4), {'description': 'Distance to the left wall/edge'})
        right_wall = (DecimalBlock(length=4), {'description': 'Distance to the right wall/edge'})
        unk0 = (ArrayBlock(child=DecimalBlock(length=4), length=2), {'is_unknown': True})
        unk1 = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=5), {'is_unknown': True})


class Nfs4BlockCount(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        num = IntegerBlock(length=4, is_signed=False)
        unk = (IntegerBlock(length=4), {'is_unknown': True})


class Nfs4NeighbourData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block = (IntegerBlock(length=2, is_signed=True), {'description': 'Neighbouring block index, or -1'})
        unk = (IntegerBlock(length=2, is_signed=True), {'is_unknown': True})


class Nfs4TrkBlockHeader(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_chunk_sizes = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=11),
                               {'description': 'Amount of polygons in each of the 11 polygon chunks '
                                               '(see Nfs4TrkBlock) of this block'})
        polygon_chunk_sizes_dup = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=11),
                                   {'is_unknown': True})
        num_vertices = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Total amount of vertices stored for this block'})
        num_vertices_high = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        num_vertices_low = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        num_vertices_med = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        num_vertices_dup = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        num_vertices_obj = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        unk0 = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=2), {'is_unknown': True})
        position = (Point3D(child=DecimalBlock(length=4)),
                    {'description': 'Position of the block in the world'})
        bounds = (ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=4),
                  {'description': 'Block bounding rectangle'})
        neighbour_data = (ArrayBlock(child=Nfs4NeighbourData(), length=300), {'is_unknown': True})
        object_chunk_counts = (ArrayBlock(child=Nfs4BlockCount(), length=4),
                               {'description': 'Amount of extra objects in each of the 4 per-block '
                                               'extra object chunks (see Nfs4TrkBlock)'})
        num_polygons = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Amount of items in `polygon_vroad_data`'})
        bounds_min = Point3D(child=DecimalBlock(length=4))
        bounds_max = Point3D(child=DecimalBlock(length=4))
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        num_positions = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        num_xobj = (Nfs4BlockCount(), {'description': 'Amount of items in `xobj`'})
        num_polyobj = (Nfs4BlockCount(), {'description': 'Amount of items in `xobj2`'})
        num_soundsrc = (Nfs4BlockCount(), {'description': 'Amount of items in `soundsrc`'})
        num_lightsrc = (Nfs4BlockCount(), {'description': 'Amount of items in `lightsrc`'})
        neighbors = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=8), {'is_unknown': True})


class Nfs4PolygonVroadData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        hs_minmax = (ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=4), {'is_unknown': True})
        flags = (ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=5), {'is_unknown': True})
        unk = (IntegerBlock(length=1), {'is_unknown': True})
        vroad_idx = (IntegerBlock(length=2, is_signed=False),
                    {'description': 'Index of the corresponding entry in the top-level `vroad` array'})
        normal = (Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True),
                  {'description': 'A normal vector of the surface'})
        forward = (Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True),
                   {'description': 'A forward vector of the surface'})


class Nfs4RefExtraObject(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        pt = Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True))
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        global_index = (IntegerBlock(length=2, is_signed=False),
                        {'description': 'Sequence number of this object among all extra objects of the track'})
        unk1 = (BytesBlock(length=3), {'is_unknown': True})
        collision = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})


class Nfs4RefExtraObject2(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        type = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        id = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        pt = Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True))
        crossindex = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        unk1 = (BytesBlock(length=3), {'is_unknown': True})


class Nfs4XObjHeader(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        type = (IntegerBlock(length=4, is_signed=False),
                {'description': 'One of: 2, 4 (normal), 3 (animated), 6 (special/physics prop)'})
        index = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        pt = (Point3D(child=DecimalBlock(length=4)), {'description': 'Object position'})
        size = (IntegerBlock(length=4, is_signed=False), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        num_vertices = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Amount of vertices of the corresponding entry in `objects`'})
        unk2 = (ArrayBlock(child=IntegerBlock(length=4), length=2), {'is_unknown': True})
        num_polygons = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Amount of polygons of the corresponding entry in `objects`'})
        unk3 = (IntegerBlock(length=4), {'is_unknown': True})


class Nfs4AnimKeyframe(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        pt = Point3D(child=FixedPointBlock(length=4, fraction_bits=24, is_signed=True))
        unk = (ArrayBlock(child=IntegerBlock(length=2, is_signed=True), length=4), {'is_unknown': True})


class Nfs4AnimExtra(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        anim_type = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        anim_id = (IntegerBlock(length=1, is_signed=False), {'is_unknown': True})
        num_keyframes = (IntegerBlock(length=2, is_signed=False,
                                      programmatic_value=lambda ctx: len(ctx.data('keyframes'))),
                         {'usage': 'io,doc'})
        delay = (IntegerBlock(length=2, is_signed=False), {'description': 'Animation delay/period'})
        keyframes = ArrayBlock(child=Nfs4AnimKeyframe(), length=lambda ctx: ctx.data('num_keyframes'))


class Nfs4SpecialExtra(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        location = Point3D(child=DecimalBlock(length=4))
        mass = DecimalBlock(length=4)
        transform = (ArrayBlock(child=DecimalBlock(length=4), length=9),
                    {'description': '3x3 rotation/transform matrix'})
        collision_dimensions = Point3D(child=DecimalBlock(length=4))
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=2), {'is_unknown': True})
        unk2 = (IntegerBlock(length=2), {'is_unknown': True})


class Nfs4Polygon(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        vertices = ArrayBlock(child=IntegerBlock(length=2, is_signed=False), length=4)
        texture = (IntegerBlock(length=2, is_signed=False),
                  {'description': 'Bits 0-10: index of the texture in the track QFS archive '
                                  '(<file>0.QFS). Other bits: rendering flags'})
        tex_flags = (IntegerBlock(length=2, is_signed=False),
                    {'description': 'UV orientation of the texture on this polygon: bit 4 flips it, '
                                    'bits 7-8 select a rotation. Other bits unknown.'})
        anim_flags = (IntegerBlock(length=1, is_signed=False),
                     {'description': 'Used for animated textures: length/period', 'is_unknown': True})


class Nfs4ExtraObject(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        anim_data = (OptionalBlock(child=Nfs4AnimExtra(),
                                   criteria=lambda ctx: _object_header_field('type')(ctx) == 3,
                                   default_value=None),
                    {'description': 'Present when the corresponding `object_headers` entry has type == 3 (animated)'})
        special_data = (OptionalBlock(child=Nfs4SpecialExtra(),
                                      criteria=lambda ctx: _object_header_field('type')(ctx) == 6,
                                      default_value=None),
                       {'description': 'Present when the corresponding `object_headers` entry has type == 6 (special)'})
        vertices = (ArrayBlock(child=Point3D(child=DecimalBlock(length=4)),
                               length=_object_header_field('num_vertices')),
                    {'description': 'Vertices, global coordinates'})
        vertex_shading = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                     length=lambda ctx: len(ctx.data('vertices'))),
                          {'is_unknown': True})
        polygons = (ArrayBlock(child=Nfs4Polygon(), length=_object_header_field('num_polygons')),
                    {'description': 'Polygons of this object'})


class Nfs4XObjChunk(CompoundBlock):

    def __init__(self, length, **kwargs):
        super().__init__(fields=[
            ('object_headers', ArrayBlock(child=Nfs4XObjHeader(), length=length), {}),
            ('objects', ArrayBlock(child=Nfs4ExtraObject(), length=lambda ctx: len(ctx.data('object_headers'))), {}),
        ], inline_description='A group of extra (out-of-terrain) objects: e.g. billboards, animated '
                              'objects, physics props', **kwargs)


class Nfs4TrkBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        vertices = (ArrayBlock(child=Point3D(child=DecimalBlock(length=4)),
                               length=_block_header_field('num_vertices')),
                    {'description': 'Vertices, global coordinates'})
        vertex_shading = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                     length=lambda ctx: len(ctx.data('vertices'))),
                          {'is_unknown': True})
        polygon_vroad_data = (ArrayBlock(child=Nfs4PolygonVroadData(), length=_block_header_field('num_polygons')),
                              {'description': 'Per-polygon reference into the global `vroad` array, plus flags'})
        xobj = (ArrayBlock(child=Nfs4RefExtraObject(), length=_block_header_field('num_xobj/num')),
                {'is_unknown': True})
        xobj2 = (ArrayBlock(child=Nfs4RefExtraObject2(), length=_block_header_field('num_polyobj/num')),
                 {'is_unknown': True})
        soundsrc = (ArrayBlock(child=BytesBlock(length=16), length=_block_header_field('num_soundsrc/num')),
                    {'is_unknown': True})
        lightsrc = (ArrayBlock(child=BytesBlock(length=16), length=_block_header_field('num_lightsrc/num')),
                    {'is_unknown': True})
        polygons_low_res_track = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/0')),
                                  {'description': 'Low-res track polygons'})
        polygons_low_res_misc = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/1')),
                                 {'description': 'Low-res misc (non-track) polygons'})
        polygons_med_res_track = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/2')),
                                  {'description': 'Medium-res track polygons'})
        polygons_med_res_misc = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/3')),
                                 {'description': 'Medium-res misc (non-track) polygons'})
        polygons_high_res_track = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/4')),
                                   {'description': 'High-res track polygons'})
        polygons_high_res_misc = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/5')),
                                  {'description': 'High-res misc (non-track) polygons'})
        lanes = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/6')),
                {'description': 'Lane helper polygons, not meant to be rendered'})
        polygons_high_res_misc_1 = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/7')),
                                    {'is_unknown': True})
        polygons_high_res_misc_2 = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/8')),
                                    {'is_unknown': True})
        polygons_high_res_misc_3 = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/9')),
                                    {'is_unknown': True})
        polygons_high_res_misc_4 = (ArrayBlock(child=Nfs4Polygon(), length=_block_header_field('polygon_chunk_sizes/10')),
                                    {'is_unknown': True})
        extra_objects_0 = (Nfs4XObjChunk(length=_block_header_chunk_count(0)), {'is_unknown': True})
        extra_objects_1 = (Nfs4XObjChunk(length=_block_header_chunk_count(1)), {'is_unknown': True})
        extra_objects_2 = (Nfs4XObjChunk(length=_block_header_chunk_count(2)), {'is_unknown': True})
        extra_objects_3 = (Nfs4XObjChunk(length=_block_header_chunk_count(3)), {'is_unknown': True})


class Nfs4FrdMap(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Main track file (NFS4 High Stakes)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk = (BytesBlock(length=28),
               {'description': 'Unknown header', 'is_unknown': True})
        num_blocks = (IntegerBlock(length=4, is_signed=False,
                                   programmatic_value=lambda ctx: len(ctx.data('blocks_headers')) - 1),
                      {'description': 'Number of track blocks'})
        num_vroad = (IntegerBlock(length=4, is_signed=False,
                                  programmatic_value=lambda ctx: len(ctx.data('vroad'))),
                     {'description': 'Number of virtual road entries'})
        vroad = (ArrayBlock(child=Nfs4VRoadBlock(), length=lambda ctx: ctx.data('num_vroad')),
                 {'description': 'Virtual road (spline) data for the whole track, referenced by index '
                                 'from `blocks[].polygon_vroad_data`'})
        blocks_headers = (ArrayBlock(child=Nfs4TrkBlockHeader(), length=lambda ctx: ctx.data('num_blocks') + 1),
                          {'description': 'Metadata for every track block, incl. the counts used to size '
                                          'the corresponding entry of `blocks`'})
        blocks = (ArrayBlock(child=Nfs4TrkBlock(), length=lambda ctx: ctx.data('num_blocks') + 1),
                  {'description': 'Track block geometry and extra data'})
        num_global_objects_0 = (IntegerBlock(length=4, is_signed=False,
                                             programmatic_value=lambda ctx: len(
                                                 ctx.data('global_objects_0/object_headers'))),
                                {'usage': 'io,doc'})
        global_objects_0 = (Nfs4XObjChunk(length=lambda ctx: ctx.parent.data('num_global_objects_0')),
                            {'is_unknown': True})
        num_global_objects_1 = (IntegerBlock(length=4, is_signed=False,
                                             programmatic_value=lambda ctx: len(
                                                 ctx.data('global_objects_1/object_headers'))),
                                {'usage': 'io,doc'})
        global_objects_1 = (Nfs4XObjChunk(length=lambda ctx: ctx.parent.data('num_global_objects_1')),
                            {'is_unknown': True})

    def serializer_class(self):
        from serializers import Nfs4FrdMapSerializer
        return Nfs4FrdMapSerializer
