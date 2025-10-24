from io import BytesIO

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock, UTF8Block, IntegerBlock, ArrayBlock, EnumByteBlock,
                                 EnumLookupDelegateBlock, BytesBlock, FixedPointBlock)
from resources.eac.fields.misc import RGBBlock, Point3D


class TexturesMapExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        texture_number = (IntegerBlock(length=2, is_signed=False),
                          {'description': 'Texture number in QFS file'})
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
                     {'description': 'Alignment data, which game uses instead of UV-s when rendering mesh.'
                                     'I use UV-s (0,1; 1,1; 1,0; 0,0) and modify them according to enum value names'})
        luminosity = (RGBBlock(),
                      {'description': 'Luminosity color'})
        black = (RGBBlock(),
                 {'description': 'Unknown, usually black',
                  'is_unknown': True})


class PolygonMapExtraDataRecord(DeclarativeCompoundBlock):

    @property
    def schema(self):
        return {**super().schema,
                'block_description': 'Polygon extra data. Number of items here == np1 * 2, but sometimes less. Why?'}

    class Fields(DeclarativeCompoundBlock.Fields):
        vectors_idx = (IntegerBlock(length=1, is_signed=False),
                       {'description': 'An index of entry in road_vectors extrablock'})
        car_behavior = EnumByteBlock(enum_names=[(0, 'unk0'),
                                                 (1, 'unk1'),
                                                 ])


class MedianExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_idx = (IntegerBlock(length=1, is_signed=False),
                       {'description': 'Polygon index'})
        unk = (BytesBlock(length=7),
               {'is_unknown': True})


class AnimatedPropPositionFrame(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                    {'description': 'Object position in 3D space'})
        unk0 = (BytesBlock(length=8),
                {'is_unknown': True})


class AnimatedPropPosition(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        num_frames = (IntegerBlock(length=2, is_signed=False),
                      {'description': 'An amount of frames',
                       'programmatic_value': lambda ctx: len(ctx.data('frames'))})
        unk = (IntegerBlock(length=2),
               {'is_unknown': True})
        frames = (ArrayBlock(length=lambda ctx: ctx.data('num_frames'),
                             child=AnimatedPropPositionFrame()),
                  {'description': 'Animation frames'})


class PropExtraDataRecord(DeclarativeCompoundBlock):
    @property
    def schema(self):
        return {**super().schema,
                'block_description': '3D model placement (prop). Same 3D model can be used few times on the track'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=2, is_signed=False),
                      {'description': 'Block size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
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
                    {'description': 'Object positioning in 3D space'})


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
                'block_description': '3D model'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        num_vertices = (IntegerBlock(length=2, is_signed=False),
                        {'description': 'Amount of vertices',
                         'programmatic_value': lambda ctx: len(ctx.data('vertices'))})
        num_polygons = (IntegerBlock(length=2, is_signed=False),
                        {'description': 'Amount of polygons',
                         'programmatic_value': lambda ctx: len(ctx.data('polygons'))})
        vertices = (ArrayBlock(child=Point3D(child=FixedPointBlock(length=2, fraction_bits=8, is_signed=True)),
                               length=lambda ctx: ctx.data('num_vertices')),
                    {'description': 'Vertices'})
        polygons = (ArrayBlock(child=ColPolygon(),
                               length=lambda ctx: ctx.data('num_polygons')),
                    {'description': 'Polygons'})
        padding = (BytesBlock(length=lambda ctx: ctx.data('block_size') - ctx.local_buffer_pos),
                   {'description': 'Unused space'})


class LanesExtraDataRecord(DeclarativeCompoundBlock):
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
                'block_description': 'Block with normal + forward vectors pair'}

    class Fields(DeclarativeCompoundBlock.Fields):
        normal = Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True)
        forward = Point3D(child=FixedPointBlock(length=2, fraction_bits=15, is_signed=True), normalized=True)


class CollisionExtraDataRecord(DeclarativeCompoundBlock):
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
        block_idx = IntegerBlock(length=2, is_signed=False)
        unk1 = (IntegerBlock(length=2),
                {'is_unknown': True})
        left_border = (FixedPointBlock(length=2, is_signed=False, fraction_bits=8),
                       {'description': 'Distance to left track border in meters'})
        right_border = (FixedPointBlock(length=2, is_signed=False, fraction_bits=8),
                        {'description': 'Distance to right track border in meters'})
        respawn_lat_pos = IntegerBlock(length=2, is_signed=False)
        unk2 = (IntegerBlock(length=4),
                {'is_unknown': True})


class ColExtraBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
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
                {'description': 'Type of the data records'})
        unk = (IntegerBlock(length=1, required_value=0),
               {'is_unknown': True})
        num_data_records = (IntegerBlock(length=2),
                            {'description': 'Amount of data records',
                             'programmatic_value': lambda ctx: len(ctx.data('data_records'))})
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
                        {'description': 'Data records'})


class MapColFile(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, required_value='COLL'),
                       {'description': 'Resource ID'})
        unk = (IntegerBlock(length=4, required_value=11),
               {'is_unknown': True})
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'File size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
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
             'usage': 'skip_ui'})
        extrablocks = (ArrayBlock(length=(0, 'num_extrablocks'), child=ColExtraBlock()),
                       {'description': 'Extrablocks',
                        'usage': 'ui_only'})

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
