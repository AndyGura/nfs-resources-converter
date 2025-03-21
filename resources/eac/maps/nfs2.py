from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 UTF8Block,
                                 BytesBlock,
                                 ArrayBlock,
                                 DataBlock,
                                 FixedPointBlock)
from resources.eac.fields.misc import Point3D
from resources.eac.maps.nfs_common import ColPolygon, ColExtraBlock


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
        bounds = (
            ArrayBlock(child=Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)), length=4),
            {'description': 'Block bounding rectangle'})
        extrablocks_offset = (IntegerBlock(length=4, is_signed=False),
                              {'description': 'An offset to "extrablock_offsets" block from here'})
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
        vertices = (ArrayBlock(child=Point3D(child=FixedPointBlock(length=2, fraction_bits=8, is_signed=True)),
                               length=lambda ctx: ctx.data('nv8') + ctx.data('nv1')),
                    {'description': 'Vertices'})
        polygons = (ArrayBlock(child=ColPolygon(),
                               length=lambda ctx: ctx.data('np4') + ctx.data('np2') + ctx.data('np1')),
                    {'description': 'Polygons'})
        unk2 = (BytesBlock(
            length=(lambda ctx: 64 + ctx.data('extrablocks_offset') + ctx.read_start_offset - ctx.buffer.tell(),
                    'up to (extrablocks_offset+64)')),
                {'is_unknown': True})
        extrablock_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                         length=lambda ctx: ctx.data('num_extrablocks')),
                              {'description': 'Offset to each of the extrablocks',
                               'custom_offset': 'extrablocks_offset + 64'})
        extrablocks = (ArrayBlock(length=(0, 'num_extrablocks'), child=ColExtraBlock()),
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
        block_positions = (ArrayBlock(child=Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                                      length=lambda ctx: ctx.data('num_blocks')),
                           {'description': 'Positions of blocks in the world'})
        skip_bytes = (BytesBlock(length=(lambda ctx: ctx.data('superblock_offsets/0') - ctx.buffer.tell(),
                                         'up to offset superblock_offsets[0]')),
                      {'description': 'Useless padding'})
        superblocks = (ArrayBlock(child=TrkSuperBlock(),
                                  length=lambda ctx: ctx.data('num_superblocks')),
                       {'description': 'Superblocks',
                        'custom_offset': 'superblock_offsets[0]'})
