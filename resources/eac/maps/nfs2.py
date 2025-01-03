from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 UTF8Block, BytesBlock, ArrayBlock, DataBlock, DelegateBlock, CompoundBlock)
from library.read_blocks.numbers import EnumByteBlock
from resources.eac.fields.misc import Point3D


class TrkPolygon(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        texture = (IntegerBlock(length=2, is_signed=False),
                   {'description': 'Texture number'})
        texture2 = (IntegerBlock(length=2, is_signed=True),
                    {'description': '255 (texture number for the other side == none ?)'})
        vertices = ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=4)


class TexturesMapExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        texture_number = IntegerBlock(length=2, is_signed=False)
        alignment_data = IntegerBlock(length=2, is_signed=False)
        rgb0 = IntegerBlock(length=3, is_signed=False)
        rgb1 = IntegerBlock(length=3, is_signed=False)


class PolygonMapExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        vectors_idx = IntegerBlock(length=1, is_signed=False)
        car_behavior = EnumByteBlock(enum_names=[(0, 'unk0'),
                                                 (1, 'unk1'),
                                                 ])


class PropExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=2, is_signed=False),
                      {'description': 'Block size'})
        type = EnumByteBlock(enum_names=[(1, 'static_prop'),
                                         (3, 'animated_prop'),
                                         ])
        prop_descr_idx = IntegerBlock(length=1, is_signed=False)
        position = DelegateBlock(possible_blocks=[
            Point3D(child_length=4, fraction_bits=16),
            CompoundBlock(fields=[('num_frames', IntegerBlock(length=2, is_signed=False), {}),
                                  ('unk', IntegerBlock(length=2), {'is_unknown': True}),
                                  ('frames', ArrayBlock(length=lambda ctx: ctx.data('num_frames'),
                                                        child=CompoundBlock(fields=[
                                                            ('position', Point3D(child_length=4, fraction_bits=16), {}),
                                                            ('unk0', IntegerBlock(length=2),
                                                             {'is_unknown': True}),
                                                            ('unk1', IntegerBlock(length=2),
                                                             {'is_unknown': True}),
                                                            ('unk2', IntegerBlock(length=2),
                                                             {'is_unknown': True}),
                                                            ('unk3', IntegerBlock(length=2),
                                                             {'is_unknown': True})])), {})]),
            BytesBlock(length=lambda ctx: ctx.data('block_size') - 4)],
            choice_index=lambda ctx, **_: (0 if ctx.data('type') == 'static_prop' else
                                           1 if ctx.data('type') == 'animated_prop' else 2)
        )


class PropDescriptionExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size'})
        num_vertices = (IntegerBlock(length=2, is_signed=False),
                        {'description': '',
                         'programmatic_value': lambda ctx: len(ctx.data('vertices'))})
        num_polygons = (IntegerBlock(length=2, is_signed=False),
                        {'description': '',
                         'programmatic_value': lambda ctx: len(ctx.data('polygons'))})
        vertices = ArrayBlock(child=Point3D(child_length=2, fraction_bits=8),
                              length=lambda ctx: ctx.data('num_vertices'))
        polygons = ArrayBlock(child=TrkPolygon(),
                              length=lambda ctx: ctx.data('num_polygons'))
        padding = BytesBlock(length=lambda ctx: ctx.data('block_size') - ctx.buffer.tell() + ctx.read_start_offset)


class RoadVectorsExtraDataRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        normal = Point3D(child_length=2, fraction_bits=15, normalized=True)
        forward = Point3D(child_length=2, fraction_bits=15, normalized=True)


class TrkExtraBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size'})
        type = EnumByteBlock(enum_names=[(2, 'textures_map'),
                                         (4, 'block_numbers'),
                                         (5, 'polygon_map'),
                                         (6, 'median_polygons'),
                                         (7, 'props_7'),
                                         (8, 'prop_descriptions'),
                                         (9, 'lanes'),
                                         (13, 'road_vectors'),
                                         (15, 'positions'),
                                         (18, 'props_18'),
                                         ])
        unk = IntegerBlock(length=1, required_value=0)
        num_data_records = IntegerBlock(length=2)
        data_records = DelegateBlock(possible_blocks=[
            ArrayBlock(child=TexturesMapExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
            ArrayBlock(child=IntegerBlock(length=2, is_signed=False), length=lambda ctx: ctx.data('num_data_records')),
            ArrayBlock(child=PolygonMapExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
            BytesBlock(length=lambda ctx: ctx.data('block_size') - 8),
            ArrayBlock(child=PropExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
            ArrayBlock(child=PropDescriptionExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
            BytesBlock(length=lambda ctx: ctx.data('block_size') - 8),
            ArrayBlock(child=RoadVectorsExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
            BytesBlock(length=lambda ctx: ctx.data('block_size') - 8),
            ArrayBlock(child=PropExtraDataRecord(), length=lambda ctx: ctx.data('num_data_records')),
            BytesBlock(length=lambda ctx: ctx.data('block_size') - 8)],
            choice_index=lambda ctx, **_: (0 if ctx.data('type') == 'textures_map' else
                                           1 if ctx.data('type') == 'block_numbers' else
                                           2 if ctx.data('type') == 'polygon_map' else
                                           3 if ctx.data('type') == 'median_polygons' else
                                           4 if ctx.data('type') == 'props_7' else
                                           5 if ctx.data('type') == 'prop_descriptions' else
                                           6 if ctx.data('type') == 'lanes' else
                                           7 if ctx.data('type') == 'road_vectors' else
                                           8 if ctx.data('type') == 'positions' else
                                           9 if ctx.data('type') == 'props_18' else 10)
        )


class TrkBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size'})
        block_size_2 = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Block size (duplicated)'})
        num_extrablocks = (IntegerBlock(length=2, is_signed=False),
                           {'description': 'number of extrablocks'})
        unk0 = (IntegerBlock(length=2, is_signed=False),
                {'is_unknown': True})
        block_idx = (IntegerBlock(length=4, is_signed=False),
                     {'description': 'Block index (serial number)'})
        bounds = (ArrayBlock(child=Point3D(child_length=4, fraction_bits=16), length=4),
                  {'description': 'Block bounding rectangle'})
        extrablocks_offset = (IntegerBlock(length=4, is_signed=False),
                              {'description': ''})
        nv8 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        nv4 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        nv2 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        nv1 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        np4 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        np2 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        np1 = (IntegerBlock(length=2, is_signed=False),
               {'description': ''})
        unk1 = (IntegerBlock(length=6),
                {'is_unknown': True})
        vertices = ArrayBlock(child=Point3D(child_length=2, fraction_bits=8),
                              length=lambda ctx: ctx.data('nv8') + ctx.data('nv1'))
        polygons = ArrayBlock(child=TrkPolygon(),
                              length=lambda ctx: ctx.data('np4') + ctx.data('np2') + ctx.data('np1'))
        unk2 = BytesBlock(
            length=lambda ctx: 64 + ctx.data('extrablocks_offset') + ctx.read_start_offset - ctx.buffer.tell())
        extrablock_offsets = ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                        length=lambda ctx: ctx.data('num_extrablocks'))
        extrablocks = ArrayBlock(length=(0, 'num_extrablocks'), child=TrkExtraBlock())

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
                      {'description': 'Superblock size'})
        num_blocks = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Number of blocks in this superblock. Usually 8 or less in the last superblock'})
        unk = (IntegerBlock(length=4),
               {'is_unknown': True})
        block_offsets = ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                   length=lambda ctx: ctx.data('num_blocks'))
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
        superblock_offsets = ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                        length=lambda ctx: ctx.data('num_superblocks'))
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
        unk = IntegerBlock(length=4, required_value=11)
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'File size'})
        # TODO it is almost the same as we have in wwww. Share logic somehow?
        num_extrablocks = (IntegerBlock(length=4, is_signed=False),
                           {'description': 'Number of extrablocks'})
        extrablock_offsets = ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                        length=lambda ctx: ctx.data('num_extrablocks'))
        extrablocks = ArrayBlock(length=(0, 'num_extrablocks'), child=TrkExtraBlock())

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
