from typing import Dict

from library.context import ReadContext
from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    UTF8Block,
    BytesBlock,
    ArrayBlock,
    FixedPointBlock,
    Padding,
)
from library.read_blocks.misc.value_validators import Eq
from resources.eac.fields.misc import Point3D
from resources.eac.maps.nfs_common import ColPolygon, ColExtraBlock


class TrkBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Track block: a segment of the track with terrain mesh at 3 resolutions and '
            'extrablocks (props, lanes, road vectors etc.). Vertex coordinates are relative '
            'to the block position, defined in `block_positions` of the track file',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data()),
            ),
            {'description': 'Block size in bytes'},
        )
        block_size_2 = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data()),
            ),
            {'description': 'Block size in bytes (duplicated)'},
        )
        num_extrablocks = (IntegerBlock(length=2, is_signed=False), {'description': 'Number of extrablocks'})
        unk0 = (IntegerBlock(length=2, is_signed=False), {'is_unknown': True})
        block_idx = (IntegerBlock(length=4, is_signed=False), {'description': 'Block index (serial number)'})
        bounds = (
            ArrayBlock(child=Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)), length=4),
            {'description': 'Block bounding rectangle'},
        )
        extrablocks_offset = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'An offset to "extrablock_offsets" block from here'},
        )
        nv8 = (
            IntegerBlock(length=2, is_signed=False),
            {
                'description': 'Number of stick-to-next vertices: vertices shared with the next block, stored '
                'relative to the position of the next block'
            },
        )
        nv4 = (IntegerBlock(length=2, is_signed=False), {'description': 'Number of own vertices for 1/4 resolution'})
        nv2 = (IntegerBlock(length=2, is_signed=False), {'description': 'Number of own vertices for 1/2 resolution'})
        nv1 = (
            IntegerBlock(length=2, is_signed=False),
            {
                'description': 'Number of own vertices for full resolution. Vertex sets of lower resolutions are '
                'subsets of it: nv4 <= nv2 <= nv1'
            },
        )
        np4 = (IntegerBlock(length=2, is_signed=False), {'description': 'Number of polygons for 1/4 resolution'})
        np2 = (IntegerBlock(length=2, is_signed=False), {'description': 'Number of polygons for 1/2 resolution'})
        np1 = (IntegerBlock(length=2, is_signed=False), {'description': 'Number of polygons for full resolution'})
        unk1 = (IntegerBlock(length=6), {'is_unknown': True})
        vertices = (
            ArrayBlock(
                child=Point3D(child=FixedPointBlock(length=2, fraction_bits=8, is_signed=True)),
                length=lambda ctx: ctx.data('nv8') + ctx.data('nv1'),
            ),
            {
                'description': 'Vertices. The first nv8 items are relative to the position of the next block '
                '(`block_positions[block_idx + 1]`, or of block 0 for the last block), the '
                'remaining nv1 items are relative to the position of this block'
            },
        )
        polygons = (
            ArrayBlock(child=ColPolygon(), length=lambda ctx: ctx.data('np4') + ctx.data('np2') + ctx.data('np1')),
            {
                'description': 'Polygons: np4 polygons of the 1/4 resolution mesh, then np2 polygons of the 1/2 '
                'resolution mesh, then np1 polygons of the full resolution mesh. The three sets '
                'are alternative levels of detail of the same terrain; the converter exports the '
                'full resolution one. Vertex indexes point to `vertices`'
            },
        )
        unk2 = (
            Padding(to=(lambda ctx: 64 + ctx.data('extrablocks_offset'), 'extrablocks_offset + 64')),
            {'is_unknown': True},
        )
        extrablock_offsets = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=lambda ctx: ctx.data('num_extrablocks')),
            {'description': 'Offset to each of the extrablocks'},
        )
        extrablocks = (
            ArrayBlock(length=(0, 'num_extrablocks'), child=ColExtraBlock()),
            {
                'description': 'Extrablocks of the block. Typically: polygon_map, block_numbers, '
                'prop_descriptions + props_18 (props placed in this block), median_polygons, '
                'road_vectors, lanes',
                'usage': 'ui',
            },
        )
        extrablocks_bytes = (
            BytesBlock(length=lambda ctx: ctx.data('block_size') - ctx.local_buffer_pos),
            {
                'description': 'A part of block, where extrablocks data is located. Offsets to the entries '
                'are defined in `extrablock_offsets` block. Item type:'
                '<br/>- [ColExtraBlock](#colextrablock)',
                'usage': 'io,doc',
            },
        )

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
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A group of up to 8 consecutive track blocks'}

    class Fields(DeclarativeCompoundBlock.Fields):
        block_size = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data()),
            ),
            {'description': 'Superblock size in bytes'},
        )
        num_blocks = (
            IntegerBlock(length=4, is_signed=False),
            {'description': 'Number of blocks in this superblock. Usually 8 or less in the last superblock'},
        )
        unk = (IntegerBlock(length=4), {'is_unknown': True})
        block_offsets = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=lambda ctx: ctx.data('num_blocks')),
            {'description': 'Offset to each of the blocks'},
        )
        blocks = (ArrayBlock(child=TrkBlock(), length=lambda ctx: ctx.data('num_blocks')), {'description': 'Blocks'})


class TrkMap(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Main track file. The track is split into blocks (segments), grouped by 8 into '
            'superblocks. Each block has a terrain mesh at 3 resolutions and extrablocks '
            'with props. Polygon texture values index the textures_map extrablock of the '
            'accompanying COL file, which points to images in <track>0.QFS',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('TRAC')), {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=20), {'is_unknown': True})
        num_superblocks = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('superblock_offsets'))),
            {'description': 'Number of superblocks (nsblk)'},
        )
        num_blocks = (IntegerBlock(length=4, is_signed=False), {'description': 'Number of blocks (nblk)'})
        superblock_offsets = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=lambda ctx: ctx.data('num_superblocks')),
            {'description': 'Offset to each of the superblocks'},
        )
        block_positions = (
            ArrayBlock(
                child=Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                length=lambda ctx: ctx.data('num_blocks'),
            ),
            {
                'description': 'Positions of blocks in the world: a point on the road at the start of each '
                'block. Block vertices are relative to these points, and all positions '
                'together form the track path (closed loop)'
            },
        )
        skip_bytes = (
            Padding(to=(lambda ctx: ctx.data('superblock_offsets/0'), 'superblock_offsets[0]')),
            {'description': 'Useless padding'},
        )
        superblocks = (
            ArrayBlock(child=TrkSuperBlock(), length=lambda ctx: ctx.data('num_superblocks')),
            {'description': 'Superblocks'},
        )

    def serializer_class(self):
        from serializers import TrkMapSerializer

        return TrkMapSerializer
