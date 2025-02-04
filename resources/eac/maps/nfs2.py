from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 UTF8Block, BytesBlock, ArrayBlock, DataBlock)
from library.read_blocks.numbers import EnumByteBlock
from library.read_blocks.smart_fields import EnumLookupDelegateBlock
from resources.eac.fields.misc import Point3D, RGBBlock


class TrkPolygon(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
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


class TexturesMapExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        texture_number = (IntegerBlock(length=2, is_signed=False),
                          {'description': 'Texture number in QFS file'})
        alignment_data = (IntegerBlock(length=2, is_signed=False),
                          {'description': 'Alignment data, which game uses instead of UV-s when rendering mesh. '
                                          'Seems to be a set of flags, but I haven\'t investigated it deeply yet'})
        luminosity = (RGBBlock(),
                      {'description': 'Luminosity color'})
        black = (RGBBlock(),
                 {'description': 'Unknown, usually black',
                  'is_unknown': True})


class PolygonMapExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        vectors_idx = IntegerBlock(length=1, is_signed=False)
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
        position = (Point3D(child_length=4, fraction_bits=16),
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
    def schema(self) -> Dict:
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
                                            blocks=[Point3D(child_length=4, fraction_bits=16),
                                                    AnimatedPropPosition(),
                                                    BytesBlock(length=lambda ctx: ctx.data('block_size') - 4)]),
                    {'description': 'Object positioning in 3D space'})


class PropDescriptionExtraDataRecord(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
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
        vertices = (ArrayBlock(child=Point3D(child_length=2, fraction_bits=8),
                               length=lambda ctx: ctx.data('num_vertices')),
                    {'description': 'Vertices'})
        polygons = (ArrayBlock(child=TrkPolygon(),
                               length=lambda ctx: ctx.data('num_polygons')),
                    {'description': 'Polygons'})
        padding = (BytesBlock(length=lambda ctx: ctx.data('block_size') - ctx.buffer.tell() + ctx.read_start_offset),
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
                       {'description': '{olygon number (inside full-res background 3D structure : 0 to np1)'})


class RoadVectorsExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        normal = Point3D(child_length=2, fraction_bits=16, normalized=True)
        forward = Point3D(child_length=2, fraction_bits=16, normalized=True)


class CollisionExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        position = Point3D(child_length=4, fraction_bits=16)
        vertical = Point3D(child_length=1, fraction_bits=8, normalized=True)
        forward = Point3D(child_length=1, fraction_bits=8, normalized=True)
        right = Point3D(child_length=1, fraction_bits=8, normalized=True)
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        block_idx = IntegerBlock(length=2, is_signed=False)
        unk1 = (IntegerBlock(length=2),
                {'is_unknown': True})
        left_border = IntegerBlock(length=2, is_signed=False)
        right_border = IntegerBlock(length=2, is_signed=False)
        respawn_lat_pos = IntegerBlock(length=2, is_signed=False)
        unk2 = (IntegerBlock(length=4),
                {'is_unknown': True})


class TrkExtraBlock(DeclarativeCompoundBlock):
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


class TrkBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        block_size_2 = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Block size in bytes (duplicated)',
                         'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        num_extrablocks = (IntegerBlock(length=2, is_signed=False),
                           {'description': 'Number of extrablocks'})
        unk0 = (IntegerBlock(length=2, is_signed=False),
                {'is_unknown': True})
        block_idx = (IntegerBlock(length=4, is_signed=False),
                     {'description': 'Block index (serial number)'})
        bounds = (ArrayBlock(child=Point3D(child_length=4, fraction_bits=16), length=4),
                  {'description': 'Block bounding rectangle'})
        extrablocks_offset = (IntegerBlock(length=4, is_signed=False),
                              {'description': 'An offset to "extrablock_offsets" block from here?'})
        nv8 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of stick-to-next vertices'})
        nv4 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of own vertices for 1/4 resolutio'})
        nv2 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of own vertices for 1/2 resolution'})
        nv1 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of own vertices for full resolution'})
        np4 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of polygons for 1/4 resolution'})
        np2 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of polygons for 1/2 resolution'})
        np1 = (IntegerBlock(length=2, is_signed=False),
               {'description': 'Number of polygons for full resolution'})
        unk1 = (IntegerBlock(length=6),
                {'is_unknown': True})
        vertices = (ArrayBlock(child=Point3D(child_length=2, fraction_bits=8),
                               length=lambda ctx: ctx.data('nv8') + ctx.data('nv1')),
                    {'description': 'Vertices'})
        polygons = (ArrayBlock(child=TrkPolygon(),
                               length=lambda ctx: ctx.data('np4') + ctx.data('np2') + ctx.data('np1')),
                    {'description': 'Polygons'})
        unk2 = (BytesBlock(
            length=lambda ctx: 64 + ctx.data('extrablocks_offset') + ctx.read_start_offset - ctx.buffer.tell()),
                {'is_unknown': True})
        extrablock_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                         length=lambda ctx: ctx.data('num_extrablocks')),
                              {'description': 'Offset to each of the extrablocks'})
        extrablocks = (ArrayBlock(length=(0, 'num_extrablocks'), child=TrkExtraBlock()),
                       {'description': 'Extrablocks'})

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        start_offset = buffer.tell()
        data = super().read(buffer, ctx, name, read_bytes_amount)
        extrablocks_offset = buffer.tell() - start_offset
        extrablocks_buf = BytesIO(buffer.read(data['block_size'] - (buffer.tell() - start_offset)))
        child_block = self.field_blocks_map.get('extrablocks').child
        self_ctx = ReadContext(buffer=buffer, data=data, name=name, block=self, parent=ctx,
                               read_bytes_amount=read_bytes_amount)
        for offset in data['extrablock_offsets']:
            extrablocks_buf.seek(offset - extrablocks_offset)
            data['extrablocks'].append(child_block.read(extrablocks_buf, self_ctx))
        return data


class TrkSuperBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Superblock size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        num_blocks = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Number of blocks in this superblock. Usually 8 or less in the last superblock'})
        unk = (IntegerBlock(length=4),
               {'is_unknown': True})
        block_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                    length=lambda ctx: ctx.data('num_blocks')),
                         {'description': 'Offset to each of the blocks'})
        blocks = (ArrayBlock(child=TrkBlock(),
                             length=lambda ctx: ctx.data('num_blocks')),
                  {'description': 'Blocks'})


class TrkMap(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Main track file'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, required_value='TRAC'),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=20),
                {'is_unknown': True})
        num_superblocks = (IntegerBlock(length=4, is_signed=False),
                           {'description': 'Number of superblocks (nsblk)',
                            'programmatic_value': lambda ctx: len(ctx.data('superblock_offsets'))})
        num_blocks = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Number of blocks (nblk)'})
        superblock_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                         length=lambda ctx: ctx.data('num_superblocks')),
                              {'description': 'Offset to each of the superblocks'})
        block_positions = (ArrayBlock(child=Point3D(child_length=4, fraction_bits=16),
                                      length=lambda ctx: ctx.data('num_blocks')),
                           {'description': 'Coordinates of road spline points in 3D space'})
        skip_bytes = (BytesBlock(length=(lambda ctx: ctx.data('superblock_offsets/0') - ctx.buffer.tell(),
                                         'up to offset superblock_offsets[0]')),
                      {'description': 'Useless padding'})
        superblocks = (ArrayBlock(child=TrkSuperBlock(),
                                  length=lambda ctx: ctx.data('num_superblocks')),
                       {'description': 'Superblocks',
                        'custom_offset': 'superblock_offsets[0]'})


class TrkMapCol(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, required_value='COLL'),
                       {'description': 'Resource ID'})
        unk = (IntegerBlock(length=4, required_value=11),
               {'is_unknown': True})
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'File size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        # TODO it is almost the same as we have in wwww. Share logic somehow?
        num_extrablocks = (IntegerBlock(length=4, is_signed=False),
                           {'description': 'Number of extrablocks'})
        extrablock_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                         length=lambda ctx: ctx.data('num_extrablocks')),
                              {'description': 'Offset to each of the extrablocks'})
        extrablocks = (ArrayBlock(length=(0, 'num_extrablocks'), child=TrkExtraBlock()),
                       {'description': 'Extrablocks'})

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        start_offset = buffer.tell()
        data = super().read(buffer, ctx, name, read_bytes_amount)
        buffer.seek(start_offset)
        block_buf = BytesIO(buffer.read(data['block_size']))
        child_block = self.field_blocks_map.get('extrablocks').child
        self_ctx = ReadContext(buffer=buffer, data=data, name=name, block=self, parent=ctx,
                               read_bytes_amount=read_bytes_amount)
        for offset in data['extrablock_offsets']:
            block_buf.seek(offset + 16)
            data['extrablocks'].append(child_block.read(block_buf, self_ctx))
        return data
