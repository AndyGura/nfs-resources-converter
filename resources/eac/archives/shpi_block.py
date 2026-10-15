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
from library.read_blocks.archives import ArchiveBlock, pre_items_payload_length, slot_lengths
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
                    'description': 'Quantize all images of this SHPI to 8-bit on one new palette: it replaces the '
                    'palette of the SHPI (!pal, !PAL or 0000), or is added at the end under the name below. The '
                    'images lose their own palettes, the other items stay. Not for TNFS car textures (CFM)',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'palette_name',
                            'title': 'Palette name, when the SHPI has none',
                            'type': 'enum_string',
                            'default': '!pal',
                            'choices': ['!pal', '!PAL', '0000'],
                        },
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
        pre_items_payload = (
            BytesBlock(
                length=(
                    lambda ctx: pre_items_payload_length(ctx, [x['offset'] for x in ctx.data('items_descr')]),
                    'up to the first item offset',
                )
            ),
            {
                'description': 'Bytes between the end of `items_descr` and the first item: padding, or data which '
                'no item offset points to',
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

    def entry_kind_hint(self, head: bytes):
        from resources.eac.bitmaps import PALETTE_IDS

        if not head:
            return None
        if head[0] in PALETTE_IDS:
            return 'EacPalette'
        image_block = self.item_block.possible_blocks[self.item_block.get_choice_index_by_class_name('EacImage')]
        image_ids = [x for x, _ in image_block.field_blocks_map['resource_id'].enum_names]
        return 'EacImage' if head[0] in image_ids else 'BytesBlock'

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 16
        total_length += len(data.get('pre_items_payload', b''))
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
            )
        res['children'] = children
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        for i, child in enumerate(data['children']):
            item_data, post = self.entry_bytes(child, ctx, str(i))
            children.append((child['alias'], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
            data['data_bytes'] += post
        data['items_descr'] = [{'name': name, 'offset': offset} for (name, offset, _) in children if name is not None]
        heap_offset = 16 + len(data['items_descr']) * 8 + len(data.get('pre_items_payload', b''))
        for x in data['items_descr']:
            x['offset'] += heap_offset
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def action_convert_to_8bit(self, read_data, name, palette_name, palette_type, num_colors, id, **kwargs):
        """All images become 8Bit on one new palette: each image drops its own palettes (an embedded palette is used
        instead of the SHPI one), mipmaps are made again from the new pixels. The palette the images use now (found
        by name, `_get_palette_from_shpi`) is replaced in place; a SHPI without one gets `palette_name` (one of the
        names looked up) at the end (NFS2 tracks pick textures by their index). The other items stay. Not for TNFS car textures (CFM): the game recolors their
        entries 250..254, which the export / folder import with car_colors.json keeps"""
        from resources.eac.utils import quantize_images_to_8bit, build_8bit_palette
        from serializers.bitmaps import ImageSerializer

        if '.CFM__' in (id or '').upper():
            raise ValueError(
                'TNFS car textures keep the light colors in palette entries 250..254, which this conversion does not '
                'know about: export the textures and import the folder instead (car_colors.json)'
            )
        from resources.eac.utils import SHPI_PALETTE_NAMES, _get_palette_from_shpi

        children = read_data['children']
        # the palette the images of this SHPI use (by its name): replaced in place, keeping its name
        _, current_palette = _get_palette_from_shpi(self, read_data)
        palette_index = next(
            (i for i, c in enumerate(children) if current_palette is not None and c['item']['data'] is current_palette),
            None,
        )
        if palette_index is None and palette_name not in SHPI_PALETTE_NAMES:
            raise ValueError(
                f'The images find the palette of the SHPI by its name: {", ".join(SHPI_PALETTE_NAMES)}, '
                f'not "{palette_name}"'
            )
        if palette_index is None and any(c['alias'] == palette_name for c in children):
            # the lookup takes the first item of that name
            raise ValueError(f'An item is already named "{palette_name}": pick another palette name')
        image_choice = self.item_block.get_choice_index_by_class_name('EacImage')
        palette_choice = self.item_block.get_choice_index_by_class_name('EacPalette')
        image_block = self.item_block.possible_blocks[image_choice]
        image_indexes = [i for i, c in enumerate(children) if c['item']['choice_index'] == image_choice]
        if not image_indexes:
            raise ValueError('There are no images to convert')
        serializer = ImageSerializer()
        # 8Bit images whose palette is not in the file (NFS2 PAUSE menus): their colors are unknown here, and the new
        # palette would become theirs
        no_palette = [
            children[i]['alias']
            for i in image_indexes
            if children[i]['item']['data']['resource_id'] == '8Bit'
            and serializer._found_palette_colors(
                children[i]['item']['data'], image_block, join_id(id, 'children', str(i), 'item', 'data')
            )
            is None
        ]
        if no_palette:
            raise ValueError(
                f'These 8Bit images have no palette in this file, their colors are not known: {", ".join(no_palette)}'
            )
        # the images as they look now: all of them before any is changed, the palette of an 8Bit image is found by
        # comparing the image data
        images = [
            serializer.to_image(
                children[i]['item']['data'], block=image_block, id=join_id(id, 'children', str(i), 'item', 'data')
            )
            for i in image_indexes
        ]
        indices_per_image, packed_palette_colors = quantize_images_to_8bit(images, num_colors)
        for i, indices in zip(image_indexes, indices_per_image):
            image = children[i]['item']['data']
            image_block._clear_8bit_palette_fields(image)
            image['resource_id'] = '8Bit'
            image['bitmap'] = indices
            if image.get('mipmaps') is not None:
                image['mipmaps'] = None
                image_block.action_generate_mipmaps(image)
        if palette_index is None:
            palette_index = len(children)
            children.append({'post_offset_payload': b'', 'alias': palette_name, 'item': None})
        palette = build_8bit_palette(
            packed_palette_colors, palette_type, id=join_id(id, 'children', str(palette_index), 'item', 'data')
        )
        children[palette_index] = {
            **{k: children[palette_index][k] for k in children[palette_index]},
            'item': {'choice_index': palette_choice, 'data': palette},
        }

    def serializer_class(self):
        from serializers import ShpiArchiveSerializer

        return ShpiArchiveSerializer
