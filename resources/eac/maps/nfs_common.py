from io import BytesIO

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock, UTF8Block, IntegerBlock, ArrayBlock, EnumByteBlock,
                                 EnumLookupDelegateBlock, BytesBlock, FixedPointBlock)
from library.read_blocks.misc.value_validators import Eq
from resources.eac.fields.misc import RGBBlock, Point3D


class TexturesMapExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'Texture reference. Polygons of the track (TRK) and of props refer to items of '
                                     'this table by index, the item defines the actual texture in the QFS archive '
                                     'and its orientation on the polygon'}

    class Fields(DeclarativeCompoundBlock.Fields):
        texture_number = (IntegerBlock(length=2, is_signed=False),
                          {'description': 'Index of the texture in the track QFS file (<track>0.QFS)'})
        unk = (IntegerBlock(length=1),
               {'is_unknown': True})
        alignment = (EnumByteBlock(enum_names=[(1, 'rotate_180'),
                                               (3, 'rotate_270'),
                                               (5, 'normal'),
                                               (9, 'rotate_90'),
                                               (16, 'flip_v'),
                                               (18, 'rotate_270_2'),
                                               (20, 'flip_h'),
                                               (24, 'rotate_90_2'),
                                               ]),
                     {'description': 'Orientation of the texture on the polygon, which game uses instead of UV-s. '
                                     'The converter uses base UV-s (0,1), (1,1), (1,0), (0,0) for the 4 polygon '
                                     'vertices and modifies them according to the enum value: rotate_* shift them '
                                     'by 1, 2 or 3 vertices, flip_h/flip_v mirror them'})
        luminosity = (RGBBlock(),
                      {'description': 'Luminosity color'})
        black = (RGBBlock(),
                 {'description': 'Unknown, usually black',
                  'is_unknown': True})


class PolygonMapExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'Polygon extra data: road surface orientation for a polygon of the block. Number '
                                     'of items here == np1 * 2, but sometimes less. Why?'}

    class Fields(DeclarativeCompoundBlock.Fields):
        vectors_idx = (IntegerBlock(length=1, is_signed=False),
                       {'description': 'An index of entry in road_vectors extrablock'})
        car_behavior = (EnumByteBlock(enum_names=[(0, 'unk0'),
                                                  (1, 'unk1'),
                                                  ]),
                        {'is_unknown': True})


class MedianExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'A record of median_polygons extrablock: references a polygon of the block, '
                                     'presumably marking it as a road median. Purpose is not confirmed'}

    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_idx = (IntegerBlock(length=1, is_signed=False),
                       {'description': 'Polygon index'})
        unk = (BytesBlock(length=7),
               {'is_unknown': True})


class AnimatedPropPositionFrame(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'A single keyframe of animated prop movement'}

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                    {'description': 'Object position in 3D space'})
        unk0 = (BytesBlock(length=8),
                {'description': 'Presumably object orientation at this keyframe',
                 'is_unknown': True})


class AnimatedPropPosition(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'Animation of prop position: a sequence of keyframes'}

    class Fields(DeclarativeCompoundBlock.Fields):
        num_frames = (IntegerBlock(length=2, is_signed=False,
                                   programmatic_value=lambda ctx: len(ctx.data('frames'))),
                      {'description': 'An amount of frames'})
        unk = (IntegerBlock(length=2),
               {'is_unknown': True})
        frames = (ArrayBlock(length=lambda ctx: ctx.data('num_frames'),
                             child=AnimatedPropPositionFrame()),
                  {'description': 'Animation frames'})


class PropExtraDataRecord(DeclarativeCompoundBlock):
    @property
    def schema(self):
        return {**super().schema,
                'block_description': '3D model placement (prop). Same 3D model can be used few times on the track. '
                                     'Records of type props_18 (in TRK blocks) and props_7 (in COL file) have this '
                                     'structure; the 3D model itself is in the prop_descriptions extrablock of the '
                                     'same block/file'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=2, is_signed=False,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'Block size in bytes'})
        type = (EnumByteBlock(enum_names=[(1, 'static_prop'),
                                          (3, 'animated_prop'),
                                          ]),
                {'description': 'Object type'})
        prop_descr_idx = (IntegerBlock(length=1, is_signed=False),
                          {'description': 'An index of 3D model in "prop_descriptions" extrablock'})
        position = (EnumLookupDelegateBlock(enum_field='type',
                                            blocks=[Point3D(
                                                child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                                                AnimatedPropPosition(),
                                                BytesBlock(length=lambda ctx: ctx.data('block_size') - 4)]),
                    {'description': 'Object positioning in 3D space: a single point for static_prop, a sequence of '
                                    'keyframes for animated_prop (the converter places the prop at the first '
                                    'keyframe). Block class picked according to `type`'})


class ColPolygon(DeclarativeCompoundBlock):
    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'A single polygon of terrain or prop'}

    class Fields(DeclarativeCompoundBlock.Fields):
        texture = (IntegerBlock(length=2, is_signed=False),
                   {'description': 'Texture number. It is not a number of texture in QFS file. Instead, it is an index '
                                   'of mapping entry in corresponding COL file, which contains real texture number'})
        texture2 = (IntegerBlock(length=2, is_signed=True),
                    {'description': '255 (texture number for the other side == none ?)',
                     'is_unknown': True})
        vertices = (ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=4),
                    {'description': 'Polygon vertices (indexes from vertex table)'})


class PropDescriptionExtraDataRecord(DeclarativeCompoundBlock):
    @property
    def schema(self):
        return {**super().schema,
                'block_description': '3D model of a prop. Placed on the track by records of props_* extrablocks, '
                                     'which reference this model by index'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'Block size in bytes'})
        num_vertices = (IntegerBlock(length=2, is_signed=False,
                                     programmatic_value=lambda ctx: len(ctx.data('vertices'))),
                        {'description': 'Amount of vertices'})
        num_polygons = (IntegerBlock(length=2, is_signed=False,
                                     programmatic_value=lambda ctx: len(ctx.data('polygons'))),
                        {'description': 'Amount of polygons'})
        vertices = (ArrayBlock(child=Point3D(child=FixedPointBlock(length=2, fraction_bits=8, is_signed=True)),
                               length=lambda ctx: ctx.data('num_vertices')),
                    {'description': 'Vertices, relative to the prop position'})
        polygons = (ArrayBlock(child=ColPolygon(),
                               length=lambda ctx: ctx.data('num_polygons')),
                    {'description': 'Polygons. Textures are referenced through the textures_map of the COL file, '
                                    'the same way as for terrain polygons'})
        padding = (BytesBlock(length=lambda ctx: ctx.data('block_size') - ctx.local_buffer_pos),
                   {'description': 'Unused space'})


class LanesExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'A lane marker: ties a vertex and a polygon of the block terrain to a position '
                                     'on a lane'}

    class Fields(DeclarativeCompoundBlock.Fields):
        vertex_idx = (IntegerBlock(length=1, is_signed=False),
                      {'description': 'Vertex number (inside background 3D structure : 0 to nv1+nv8)'})
        track_pos = (IntegerBlock(length=1, is_signed=False),
                     {'description': 'Position along track inside block (0 to 7)'})
        lat_pos = (IntegerBlock(length=1, is_signed=False),
                   {'description': 'Lateral position ? (constant in each lane), -1 at the end)'})
        polygon_idx = (IntegerBlock(length=1, is_signed=False),
                       {'description': 'Polygon number (inside full-res background 3D structure : 0 to np1)'})


class RoadVectorsExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'Orientation of the road surface: normal + forward vectors pair. Referenced by '
                                     'index from polygon_map records'}

    class Fields(DeclarativeCompoundBlock.Fields):
        normal = (Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True),
                  {'description': 'A normal vector of the road surface'})
        forward = (Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True),
                   {'description': 'A forward vector of the road (direction of the track)'})


class CollisionExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'A point of the track collision spline (road centre line) with road orientation '
                                     'vectors and distances to the road borders. Used by the physics engine; there are '
                                     '8 points per track block'}

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                    {'description': 'A global position of track collision spline point. The unit is meter'})
        normal = (Point3D(child=FixedPointBlock(length=1, fraction_bits=7, is_signed=True), normalized=True),
                  {'description': 'A normal vector of road surface'})
        forward = (Point3D(child=FixedPointBlock(length=1, fraction_bits=7, is_signed=True), normalized=True),
                   {'description': 'A forward vector'})
        right = (Point3D(child=FixedPointBlock(length=1, fraction_bits=7, is_signed=True), normalized=True),
                 {'description': 'A right vector'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        block_idx = (IntegerBlock(length=2, is_signed=False),
                     {'description': 'Index of the TRK block this point belongs to'})
        unk1 = (IntegerBlock(length=2),
                {'is_unknown': True})
        left_border = (FixedPointBlock(length=2, is_signed=False, fraction_bits=8),
                       {'description': 'Distance to left track border in meters'})
        right_border = (FixedPointBlock(length=2, is_signed=False, fraction_bits=8),
                        {'description': 'Distance to right track border in meters'})
        respawn_lat_pos = (IntegerBlock(length=2, is_signed=False),
                           {'description': 'Named by assumption (lateral position of car respawn). Values look like '
                                           'four packed 4-bit numbers, e.g. 0x1111, 0x1144, 0x1244',
                            'is_unknown': True})
        unk2 = (IntegerBlock(length=4),
                {'is_unknown': True})


class ColExtraBlock(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'A typed container of data records. The same structure is used for extrablocks '
                                     'inside TRK blocks and in the COL file; record type is defined by `type`'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'Block size in bytes'})
        type = (EnumByteBlock(enum_names=[(2, 'textures_map'),
                                          (4, 'block_numbers'),
                                          (5, 'polygon_map'),
                                          (6, 'median_polygons'),
                                          (7, 'props_7'),
                                          (8, 'prop_descriptions'),
                                          (9, 'lanes'),
                                          (13, 'road_vectors'),
                                          (15, 'collision_data'),
                                          (18, 'props_18'),
                                          (19, 'props_19'),
                                          ]),
                {'description': 'Type of the data records. textures_map, props_7, prop_descriptions and '
                                'collision_data are found in COL file; polygon_map, block_numbers, median_polygons, '
                                'props_18, prop_descriptions, lanes and road_vectors in TRK blocks'})
        unk = (IntegerBlock(length=1, value_validator=Eq(0)),
               {'is_unknown': True})
        num_data_records = (IntegerBlock(length=2,
                                         programmatic_value=lambda ctx: len(ctx.data('data_records'))),
                            {'description': 'Amount of data records'})
        data_records = (EnumLookupDelegateBlock(
            enum_field='type',
            blocks=[
                ArrayBlock(child=TexturesMapExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=IntegerBlock(length=2), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=PolygonMapExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=MedianExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=PropExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=PropDescriptionExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=LanesExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=RoadVectorsExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=CollisionExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=PropExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                ArrayBlock(child=PropExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
                BytesBlock(length=lambda ctx: ctx.data('block_size') - 8)
            ]),
                        {'description': 'Data records, block class picked according to `type`. Records of unknown '
                                        'types are kept as raw bytes'})


class MapColFile(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'Track additional data (COL file), a list of extrablocks: textures map (used by '
                                     'polygons of the TRK file), track-wide props with their 3D models and collision '
                                     'data (road centre line for the physics engine)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('COLL')),
                       {'description': 'Resource ID'})
        unk = (IntegerBlock(length=4, value_validator=Eq(11)),
               {'is_unknown': True})
        block_size = (IntegerBlock(length=4, is_signed=False,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'File size in bytes'})
        num_extrablocks = (IntegerBlock(length=4, is_signed=False),
                           {'description': 'Number of extrablocks'})
        extrablock_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                         length=lambda ctx: ctx.data('num_extrablocks')),
                              {'description': 'Offset to each of the extrablocks'})
        extrablocks_bytes = (
            BytesBlock(length=lambda ctx: ctx.data('block_size') - 16 - 4 * ctx.data('num_extrablocks')),
            {'description': 'A part of block, where extra blocks data is located. Offsets are defined in '
                            'previous "extrablock_offsets" field. Item type:'
                            '<br/>- [ColExtraBlock](#colextrablock)',
             'usage': 'io,doc'})
        extrablocks = (ArrayBlock(length=(0, 'num_extrablocks'), child=ColExtraBlock()),
                       {'description': 'Extrablocks. The first one is always textures_map, which TRK polygons refer '
                                       'to. Then typically prop_descriptions, props_7 and collision_data',
                        'usage': 'ui'})

    def serializer_class(self):
        from serializers import JsonSerializer
        return JsonSerializer

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        data['extrablocks'] = []
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, data)
        child_block = self.field_blocks_map.get('extrablocks').child
        for i, offset in enumerate(data['extrablock_offsets']):
            self_ctx.buffer.seek(self_ctx.read_start_offset + offset + 16)
            data['extrablocks'].append(child_block.unpack(self_ctx, name=str(i)))
        return data
