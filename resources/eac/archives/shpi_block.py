from io import SEEK_CUR
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (
    CompoundBlock,
    DeclarativeCompoundBlock,
    UTF8Block,
    IntegerBlock,
    ArrayBlock,
    AutoDetectBlock,
    BytesBlock,
    LengthPrefixedArrayBlock,
)
from library.read_blocks.archives import ArchiveBlock, read_gap, slot_lengths
from library.read_blocks.misc.value_validators import Eq
from library.utils.id import join_id
from resources.eac.bitmaps import EacImage, EacPalette


def determine_shpi_length(ctx):
    if ctx.read_bytes_remaining is None:
        return ctx.data('length') - 16 - 8 * ctx.data('num_items')
    return ctx.read_bytes_remaining


class ShpiBlock(ArchiveBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A container of images and palettes for them',
            'custom_actions': [
                {
                    'method': 'convert_to_8bit',
                    'title': 'Convert all images to 8Bit',
                    'description': 'Quantize all images in this SHPI block to 8-bit with single palette',
                    'is_pure': False,
                    'args': [
                        {'id': 'palette_name', 'title': 'Palette name', 'type': 'string', 'default': '!pal'},
                        {
                            'id': 'palette_type',
                            'title': 'Palette type',
                            'type': 'enum_string',
                            'choices': [
                                '24BitDos color format palette',
                                '24Bit color format palette',
                                '16Bit_0565 color format palette',
                                '32Bit color format palette',
                                '16Bit_1555 color format palette',
                            ],
                        },
                        {
                            'id': 'num_colors',
                            'title': 'Max number of colors',
                            'description': 'Maximum number of colors in the palette. Last transparent color is included',
                            'type': 'number',
                            'default': 256,
                        },
                    ],
                }
            ],
        }

    def __init__(self, **kwargs):
        super().__init__(
            item_block=AutoDetectBlock(
                possible_blocks=[
                    EacImage(),
                    EacPalette(),
                    BytesBlock(
                        length=(
                            lambda ctx: next(
                                x
                                for x in (
                                    x['offset'] - ctx.local_buffer_pos
                                    for x in (
                                        sorted(ctx.data('items_descr'), key=lambda x: x['offset'])
                                        + [{'offset': ctx.read_bytes_amount}]
                                    )
                                )
                                if x > 0
                            ),
                            'item_length',
                        )
                    ),
                ]
            ),
            alias_field=UTF8Block(length=4),
            **kwargs,
        )

    class Fields(ArchiveBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('SHPI')), {'description': 'Resource ID'})
        length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
            {'description': 'The length of this SHPI block in bytes'},
        )
        num_items = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
            {'usage': 'io,doc', 'description': 'An amount of items'},
        )
        shpi_dir = (
            UTF8Block(length=4),
            {'is_unknown': True, 'description': 'One of: "LN32", "GIMX", "WRAP". The purpose is unknown'},
        )
        items_descr = (
            ArrayBlock(
                child=CompoundBlock(
                    fields=[('name', UTF8Block(length=4), {}), ('offset', IntegerBlock(length=4), {})],
                    inline_description='8-bytes record, first 4 bytes is a UTF-8 '
                    'string, last 4 bytes is an unsigned integer '
                    '(little-endian)',
                ),
                length=lambda ctx: ctx.data('num_items'),
            ),
            {
                'usage': 'io,doc',
                'description': 'An array of items, each of them represents name of SHPI item (image or palette)'
                ' and offset to item data in file, relatively to SHPI block start (where '
                'resource id string is presented). Names are not always unique',
            },
        )
        data_bytes = (
            BytesBlock(length=lambda ctx: determine_shpi_length(ctx)),
            {
                'usage': 'io,doc',
                'description': 'A part of block, where items data is located. Offsets to some of the entries are '
                'defined in `items_descr` block. Between them there can be non-indexed '
                'entries (palettes and texts). Possible item types:'
                '<br/>- [EacImage](#eacimage)'
                '<br/>- [EacPalette](#eacpalette)',
            },
        )
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def new_data(self, patch=None):
        return {**super().new_data(), 'shpi_dir': 'LN32'}

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 16
        for i, child in enumerate(data['children']):
            total_length += sum(self.entry_sizes(child, ctx))
            if child['alias'] is not None:
                total_length += 8
        return total_length

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()

        # read block length and use it here
        ctx.buffer.seek(4, SEEK_CUR)
        read_bytes_amount = self.field_blocks_map['length'].read(ctx)
        ctx.buffer.seek(block_start)

        res, self_ctx, region_start, region_length = self.read_header(ctx, name, read_bytes_amount)
        end_pos = region_start + region_length

        entries = sorted(list(enumerate(res['items_descr'])), key=lambda x: x[1]['offset'])
        offsets = [block_start + x['offset'] for _, x in entries]
        lengths = slot_lengths(offsets, end_pos)
        # entries are parsed later in lazy mode: keep header (with io-only fields) for their contexts
        entry_ctx = self_ctx.detached(ctx.buffer, data=dict(res)) if self_ctx.lazy else self_ctx
        children = [None] * len(entries)
        for i, ((descr_index, descr), offset, length) in enumerate(zip(entries, offsets, lengths)):
            children[descr_index] = self.read_entry(
                entry_ctx,
                name=f'{descr_index}_{descr["name"]}',
                offset=offset,
                length=length,
                alias=descr['name'],
                pre_offset_payload=read_gap(ctx, region_start, offset) if i == 0 else b'',
            )
        res['children'] = children
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        for i, child in enumerate(data['children']):
            pre, item_data, post = self.entry_bytes(child, ctx, str(i))
            data['data_bytes'] += pre
            children.append((child['alias'], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
            data['data_bytes'] += post
        data['items_descr'] = [{'name': name, 'offset': offset} for (name, offset, _) in children if name is not None]
        heap_offset = 16 + len(data['items_descr']) * 8
        for x in data['items_descr']:
            x['offset'] += heap_offset
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def action_convert_to_8bit(self, read_data, name, palette_name, palette_type, num_colors, id, **kwargs):
        # notes for future:

        # TNFS CFM files: last 6 colors are special for cars:
        # palette name is '!PAL'
        # 250th, 251th - cop red blinker
        # 252th, 253th - cop blue blinker
        # 254th is replaced with tail colors in the game
        # 255th is transparent
        # Also CFM has additional !xxx palette

        # TNFS FAM files:
        # palette name is '!PAL'

        import tempfile

        tmp_dir = tempfile.TemporaryDirectory()
        serializer = self.serializer_class()()
        serializer.patch_settings(
            {
                'images__save_image_positions': False,
                'images__save_palettes': False,
                'images__save_mipmaps': False,
                'images__save_embedded_palette': False,
                'images__save_texts': False,
            }
        )
        serializer.serialize(data=read_data, path=tmp_dir.name, block=self, id=name)

        bitmap_choice_index = self.item_block.get_choice_index_by_class_name('EacImage')
        read_data['children'] = [x for x in read_data['children'] if x['item']['choice_index'] == bitmap_choice_index]

        from library.utils import path_join
        from PIL import Image

        images = [Image.open(path_join(tmp_dir.name, x['alias'] + '.png')) for x in read_data['children']]

        from resources.eac.utils import quantize_images_to_8bit, build_8bit_palette

        indices_per_image, packed_palette_colors = quantize_images_to_8bit(images, num_colors)
        for child, indices in zip(read_data['children'], indices_per_image):
            child['item']['data']['resource_id'] = '8Bit'
            child['item']['data']['bitmap'] = indices

        pal = build_8bit_palette(packed_palette_colors, palette_type, id=join_id(id, 'children', '0', 'item', 'data'))
        read_data['children'].insert(
            0,
            {
                'pre_offset_payload': b'',
                'post_offset_payload': b'',
                'alias': palette_name,
                'item': {'choice_index': self.item_block.get_choice_index_by_class_name('EacPalette'), 'data': pal},
            },
        )

    def serializer_class(self):
        from serializers import ShpiArchiveSerializer

        return ShpiArchiveSerializer
