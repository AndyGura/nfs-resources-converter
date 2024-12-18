from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 UTF8Block, BytesBlock, ArrayBlock)
from resources.eac.fields.misc import Point3D_32, Point3D_16


class TrkPolygon(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        texture = (IntegerBlock(length=2, is_signed=False),
                   {'description': 'Texture number'})
        texture2 = (IntegerBlock(length=2, is_signed=True),
                    {'description': '255 (texture number for the other side == none ?)'})
        vertices = ArrayBlock(child=IntegerBlock(length=1, is_signed=False), length=4)


class TrkBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Block size'})
        block_size_2 = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Block size (duplicated)'})
        num_extrablocks = (IntegerBlock(length=2, is_signed=False),
                           {'description': 'number of extrablocks'})
        unk = (IntegerBlock(length=2, is_signed=False),
               {'is_unknown': True})
        block_idx = (IntegerBlock(length=4, is_signed=False),
                     {'description': 'Block index (serial number)'})
        bounds = (ArrayBlock(child=Point3D_32(), length=4),
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
        np4 = (IntegerBlock(length=4, is_signed=False),
               {'description': ''})
        np2 = (IntegerBlock(length=4, is_signed=False),
               {'description': ''})
        np1 = (IntegerBlock(length=4, is_signed=False),
               {'description': ''})
        vertices = ArrayBlock(child=Point3D_16(),
                              length=(lambda ctx: ctx.data('nv8') + ctx.data('nv1'), 'nv8+nv1'))
        polygons = ArrayBlock(child=TrkPolygon(),
                              length=(lambda ctx: ctx.data('np4') + ctx.data('np2') + ctx.data('np1'), 'np4+np2+np1'))
        tmp = BytesBlock(
            length=lambda ctx: ctx.data('block_size') - 88 - 6 * (ctx.data('nv8') + ctx.data('nv1')) - 8 * (
                    ctx.data('np4') + ctx.data('np2') + ctx.data('np1')))


class TrkSuperBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Superblock size'})
        num_blocks = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Number of blocks in this superblock. Usually 8 or less in the last superblock'})
        unk = (IntegerBlock(length=4),
               {'is_unknown': True})
        block_offsets = ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                   length=(lambda ctx: ctx.data('num_blocks'), 'num_blocks'))
        blocks = (ArrayBlock(child=TrkBlock(),
                             length=(lambda ctx: ctx.data('num_blocks'), 'num_blocks')),
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
                                        length=(lambda ctx: ctx.data('num_superblocks'), 'num_superblocks'))
        block_positions = (ArrayBlock(child=Point3D_32(),
                                      length=(lambda ctx: ctx.data('num_blocks'), 'num_blocks')),
                           {'description': 'Coordinates of road spline points in 3D space'})
        skip_bytes = (BytesBlock(length=(lambda ctx: ctx.data('superblock_offsets/0') - ctx.buffer.tell(),
                                         'up to offset superblock_offsets[0]')),
                      {'description': 'Useless padding'})
        superblocks = (ArrayBlock(child=TrkSuperBlock(),
                                  length=(lambda ctx: ctx.data('num_superblocks'), 'num_superblocks')),
                       {'description': 'Superblocks',
                        'custom_offset': 'superblock_offsets[0]'})
