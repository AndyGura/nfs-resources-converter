from typing import Dict

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 UTF8Block,
                                 BytesBlock,
                                 ArrayBlock,
                                 FixedPointBlock)
from resources.eac.fields.misc import Point3D
from resources.eac.maps.nfs_common import ColPolygon, ColExtraBlock


class TrkBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'Block size in bytes'})
        block_size_2 = (IntegerBlock(length=4, is_signed=False,
                                     programmatic_value=lambda ctx: ctx.block.estimate_packed_size(
                                         ctx.get_full_data())),
                        {'description': 'Block size in bytes (duplicated)'})
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
            length=(lambda ctx: 64 + ctx.data('extrablocks_offset') - ctx.local_buffer_pos,
                    'up to (extrablocks_offset+64)')),
                {'is_unknown': True})
        extrablock_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                         length=lambda ctx: ctx.data('num_extrablocks')),
                              {'description': 'Offset to each of the extrablocks',
                               'custom_offset': 'extrablocks_offset + 64'})
        extrablocks = (ArrayBlock(length=(0, 'num_extrablocks'), child=ColExtraBlock()),
                       {'description': 'Extrablocks',
                        'usage': 'ui_only'})
        extrablocks_bytes = (BytesBlock(length=lambda ctx: ctx.data('block_size') - ctx.local_buffer_pos),
                             {
                                 'description': 'A part of block, where extrablocks data is located. Offsets to the entries '
                                                'are defined in `extrablock_offsets` block. Item type:'
                                                '<br/>- [ColExtraBlock](#colextrablock)',
                                 'usage': 'skip_ui'})

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        data['extrablocks'] = []
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, data)
        array_ctx = self_ctx.get_or_create_child('extrablocks', self, read_bytes_amount, data)
        end_pos = ctx.buffer.tell()
        child_block = self.field_blocks_map.get('extrablocks').child
        for i, offset in enumerate(data['extrablock_offsets']):
            ctx.buffer.seek(self_ctx.read_start_offset + offset)
            data['extrablocks'].append(child_block.unpack(array_ctx, name=str(i)))
        ctx.buffer.seek(end_pos)
        return data


class TrkSuperBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'Superblock size in bytes'})
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
        num_superblocks = (IntegerBlock(length=4, is_signed=False,
                                        programmatic_value=lambda ctx: len(ctx.data('superblock_offsets'))),
                           {'description': 'Number of superblocks (nsblk)'})
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

    def serializer_class(self):
        from serializers import TrkMapSerializer
        return TrkMapSerializer
