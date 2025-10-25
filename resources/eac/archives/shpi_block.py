import traceback
from typing import Dict

from config import general_config
from library.read_blocks import (CompoundBlock,
                                 DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 AutoDetectBlock,
                                 BytesBlock)
from resources.eac.bitmaps import Bitmap8Bit, Bitmap4Bit, Bitmap16Bit0565, Bitmap32Bit, Bitmap16Bit1555, Bitmap24Bit
from resources.eac.misc import ShpiText
from resources.eac.palettes import (Palette24BitDos,
                                    Palette24Bit,
                                    Palette32Bit,
                                    Palette16Bit,
                                    PaletteReference,
                                    Palette16BitDos)
from .base_archive_block import BaseArchiveBlock


def determine_shpi_length(ctx):
    try:
        return ctx.read_bytes_remaining
    except Exception:
        return ctx.data('length') - 16 - 8 * ctx.data('num_items')


class ShpiBlock(BaseArchiveBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A container of images and palettes for them',
            'serializable_to_disc': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, required_value='SHPI'),
                       {'description': 'Resource ID'})
        length = (IntegerBlock(length=4,
                               programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                  {'description': 'The length of this SHPI block in bytes'})
        num_items = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
                     {'description': 'An amount of items'})
        shpi_dir = (UTF8Block(length=4),
                    {'description': 'One of: "LN32", "GIMX", "WRAP". The purpose is unknown'})
        items_descr = (ArrayBlock(child=CompoundBlock(fields=[('name', UTF8Block(length=4), {}),
                                                              ('offset', IntegerBlock(length=4), {})],
                                                      inline_description='8-bytes record, first 4 bytes is a UTF-8 '
                                                                         'string, last 4 bytes is an unsigned integer '
                                                                         '(little-endian)'),
                                  length=lambda ctx: ctx.data('num_items')),
                       {'description': 'An array of items, each of them represents name of SHPI item (image or palette)'
                                       ' and offset to item data in file, relatively to SHPI block start (where '
                                       'resource id string is presented). Names are not always unique'})
        data_bytes = (BytesBlock(length=lambda ctx: determine_shpi_length(ctx)),
                      {
                          'description': 'A part of block, where items data is located. Offsets to some of the entries are '
                                         'defined in `items_descr` block. Between them there can be non-indexed '
                                         'entries (palettes and texts). Possible item types:'
                                         '<br/>- [Bitmap4Bit](#bitmap4bit)'
                                         '<br/>- [Bitmap8Bit](#bitmap8bit)'
                                         '<br/>- [Bitmap16Bit0565](#bitmap16bit0565)'
                                         '<br/>- [Bitmap16Bit1555](#bitmap16bit1555)'
                                         '<br/>- [Bitmap24Bit](#bitmap24bit)'
                                         '<br/>- [Bitmap32Bit](#bitmap32bit)'
                                         '<br/>- [PaletteReference](#palettereference)'
                                         '<br/>- [Palette16BitDos](#palette16bitdos)'
                                         '<br/>- [Palette16Bit](#palette16bit)'
                                         '<br/>- [Palette24BitDos](#palette24bitdos)'
                                         '<br/>- [Palette24Bit](#palette24bit)'
                                         '<br/>- [Palette32Bit](#palette32bit)'
                                         '<br/>- [ShpiText](#shpitext)',
                          'usage': 'skip_ui'})
        children = (ArrayBlock(length=(0, 'num_items + ?'),
                               child=AutoDetectBlock(possible_blocks=[
                                   Bitmap4Bit(),
                                   Bitmap8Bit(),
                                   Bitmap16Bit0565(),
                                   Bitmap16Bit1555(),
                                   Bitmap24Bit(),
                                   Bitmap32Bit(),
                                   PaletteReference(),
                                   Palette16BitDos(),
                                   Palette16Bit(),
                                   Palette24BitDos(),
                                   Palette24Bit(),
                                   Palette32Bit(),
                                   ShpiText(),
                                   BytesBlock(length=(lambda ctx: next(x for x in (
                                       x['offset'] - ctx.local_buffer_pos
                                       for x in (sorted(ctx.data('items_descr'), key=lambda x: x['offset'])
                                                 + [{'offset': ctx.read_bytes_amount}])
                                   ) if x > 0), 'item_length'))])),
                    {'usage': 'ui_only'})

    def new_data(self):
        return {**super().new_data(), 'shpi_dir': 'LN32'}

    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        return [(x['name'], block_start + x['offset'], None) for x in data['items_descr']]

    def generate_items_descr(self, data, children):
        res = [{'name': name, 'offset': offset} for (name, offset, _) in children if name is not None]
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': res}, 'data_bytes')
        for x in res:
            x['offset'] += heap_offset
        return res

    def serializer_class(self):
        from serializers import ShpiArchiveSerializer
        return ShpiArchiveSerializer

    def handle_archive_child(self, abs_offsets, i, self_ctx):
        (alias, offset, length) = abs_offsets[i]
        offset_payloads = []
        aliases = []
        children = []
        buffer = self_ctx.buffer
        # pre-child payload and positioning
        if offset > buffer.tell():
            offset_payloads.append(buffer.read(offset - buffer.tell()))
        else:
            offset_payloads.append(b'')
            buffer.seek(offset)
        child_field = self.field_blocks_map['children'].child
        try:
            child = child_field.unpack(ctx=self_ctx, name=f"{i}_{alias}", read_bytes_amount=length)
        except Exception as ex:
            if general_config().print_errors:
                traceback.print_exc()
            try:
                bytes_choice = next(idx
                                    for idx, blk in enumerate(child_field.possible_blocks)
                                    if isinstance(blk, BytesBlock))
            except StopIteration:
                bytes_choice = -1
            buffer.seek(offset)
            child = {'choice_index': bytes_choice, 'data': buffer.read(length)}
        children.append(child)
        aliases.append(alias)
        # Try to read optional extra block after 8-bit bitmap data
        try:
            bitmap8_choice = next(
                idx for idx, blk in enumerate(child_field.possible_blocks) if isinstance(blk, Bitmap8Bit))
        except StopIteration:
            bitmap8_choice = -1
        if bitmap8_choice != -1 and self_ctx.data('shpi_dir') != 'WRAP' and child.get('choice_index') == bitmap8_choice:
            extra_abs = offset + child['data']['block_size']
            next_abs = abs_offsets[i + 1][1] if i < len(abs_offsets) - 1 else None
            if child['data']['block_size'] > 0 and (next_abs is None or extra_abs < next_abs):
                if extra_abs > buffer.tell():
                    offset_payloads.append(buffer.read(extra_abs - buffer.tell()))
                else:
                    offset_payloads.append(b'')
                    buffer.seek(extra_abs)
                extra = child_field.unpack(ctx=self_ctx, name=f'extra_{i}')
                children.append(extra)
                aliases.append(None)
        return offset_payloads, aliases, children
