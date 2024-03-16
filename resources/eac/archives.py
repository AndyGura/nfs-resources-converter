from abc import abstractmethod, ABC
from copy import deepcopy
from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (CompoundBlock,
                                 DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 AutoDetectBlock,
                                 BytesBlock,
                                 DataBlock)
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.audios import EacsAudioFile, SoundBankHeaderEntry
from resources.eac.bitmaps import Bitmap8Bit, Bitmap4Bit, Bitmap16Bit0565, Bitmap32Bit, Bitmap16Bit1555, Bitmap24Bit
from resources.eac.car_specs import CarSimplifiedPerformanceSpec, CarPerformanceSpec
from resources.eac.compressions.qfs2 import Qfs2Compression
from resources.eac.compressions.qfs3 import Qfs3Compression
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries import OripGeometry, GeoGeometry
from resources.eac.misc import ShpiText
from resources.eac.palettes import (Palette24BitDos,
                                    Palette24Bit,
                                    Palette32Bit,
                                    Palette16Bit,
                                    PaletteReference,
                                    Palette16BitDos)


class CompressedBlock(AutoDetectBlock):

    def __init__(self, **kwargs):
        super().__init__(possible_blocks=[ShpiBlock(),
                                          CarSimplifiedPerformanceSpec(),
                                          CarPerformanceSpec()],
                         **kwargs)
        self.algorithm = None

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        uncompressed_bytes = self.algorithm(buffer, read_bytes_amount)
        uncompressed = BytesIO(uncompressed_bytes)
        self_ctx = ReadContext(buffer=uncompressed, name=name + '_UNCOMPRESSED', parent=ctx,
                               read_bytes_amount=len(uncompressed_bytes))
        return super().read(buffer=uncompressed, ctx=self_ctx, read_bytes_amount=len(uncompressed_bytes))


class RefPackBlock(CompressedBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = RefPackCompression().uncompress


class Qfs2Block(CompressedBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = Qfs2Compression().uncompress


class Qfs3Block(CompressedBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = Qfs3Compression().uncompress


### A block, which contains multiple data blocks, consist of header with item descriptions and
### separate space when items themselves located.
###
### Expects implementation to have fields `items_descr` which returns list of descriptions and `children`,
### which describes children.
###
### In returned data, besides `children`, provides additional fields:
### - `offset_payloads` - byte arrays with data, found between children. This list always has length len(children) + 1
### - `children_aliases` - list of strings, identifiers of items. This list always has the same length as children.
### Aliases can repeat
class BaseArchiveBlock(DeclarativeCompoundBlock, ABC):

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        offsets_sum = 0
        # CompoundBlock does not know about payloads between items
        for offset in data['offset_payloads']:
            offsets_sum += len(offset)
        return super().estimate_packed_size(data, ctx) + offsets_sum

    def new_data(self):
        # CompoundBlock does not create those custom fields
        return {**super().new_data(),
                'children_aliases': [],
                'offset_payloads': [b'']}

    ### should transform data['items_descr'] to list of tuples (alias, offset, length)
    @abstractmethod
    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        raise NotImplementedError

    ### should transform list of tuples (alias, offset, length) to data['items_descr']
    @abstractmethod
    def generate_items_descr(self, data, children):
        raise NotImplementedError

    def handle_archive_child(self, buffer, abs_offsets, i, self_ctx):
        (alias, offset, length) = abs_offsets[i]
        if offset > buffer.tell():
            offset_payload = buffer.read(offset - buffer.tell())
        else:
            offset_payload = b''
            buffer.seek(offset)
        child = self.field_blocks_map['children'].child.unpack(self_ctx.buffer, ctx=self_ctx, name=alias,
                                                               read_bytes_amount=length)
        return [offset_payload], [alias], [child]

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        block_start = buffer.tell()
        res = super().read(buffer, ctx, name, read_bytes_amount)
        self_ctx = next(c for c in ctx.children if c.name == name)
        abs_offsets = self.parse_abs_offsets(block_start, res, read_bytes_amount)
        children = []
        aliases = []
        offset_payloads = []
        for i in range(len(abs_offsets)):
            # recursive reference, happens in wwww blocks
            if abs_offsets[i][1] == block_start:
                offset_payloads.append(b'')
                aliases.append(None)
                children.append(None)
                continue
            (op, a, c) = self.handle_archive_child(buffer, abs_offsets, i, self_ctx)
            offset_payloads.extend(op)
            aliases.extend(a)
            children.extend(c)
        if res.get('length') is not None and buffer.tell() < block_start + res['length']:
            diff = block_start + res['length'] - buffer.tell()
            offset_payloads.append(buffer.read(diff))
        if read_bytes_amount is not None:
            buffer.seek(block_start + read_bytes_amount)
        res['children'] = children
        res['children_aliases'] = aliases
        res['offset_payloads'] = offset_payloads
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        children_heap = b''
        children = []
        child_block = self.field_blocks_map['children'].child
        for i, item in enumerate(data['children']):
            children_heap += data['offset_payloads'][i]
            item_data = child_block.pack(data=item, ctx=ctx, name=str(i))
            children.append((data['children_aliases'][i], len(children_heap), len(item_data)))
            children_heap += item_data
        if len(data['offset_payloads']) > len(data['children']):
            for i in range(len(data['children']), len(data['offset_payloads'])):
                children_heap += data['offset_payloads'][i]
        data['items_descr'] = self.generate_items_descr(data, children)
        self_ctx = WriteContext(data=data, name=name, block=self, parent=ctx)
        res = bytes()
        for name, field in (x for x in self.field_blocks if x[0] != 'children'):
            programmatic_value_func = self.field_extras_map.get(name, {}).get('programmatic_value')
            if programmatic_value_func is not None:
                val = programmatic_value_func(self_ctx)
            else:
                val = data[name]
            res += field.pack(data=val, ctx=self_ctx, name=name)
        res += children_heap
        return res


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
        length = (IntegerBlock(length=4),
                  {'description': 'The length of this SHPI block in bytes',
                   'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        num_items = (IntegerBlock(length=4),
                     {'description': 'An amount of items',
                      'programmatic_value': lambda ctx: len(ctx.data('items_descr'))})
        shpi_dir = (UTF8Block(length=4),
                    {'description': 'One of: "LN32", "GIMX", "WRAP". The purpose is unknown'})
        items_descr = (ArrayBlock(child=CompoundBlock(fields=[('name', UTF8Block(length=4), {}),
                                                              ('offset', IntegerBlock(length=4), {})],
                                                      inline_description='8-bytes record, first 4 bytes is a UTF-8 '
                                                                         'string, last 4 bytes is an unsigned integer '
                                                                         '(little-endian)'),
                                  length=(lambda ctx: ctx.data('num_items'), 'num_items')),
                       {'description': 'An array of items, each of them represents name of SHPI item (image or palette)'
                                       ' and offset to item data in file, relatively to SHPI block start (where '
                                       'resource id string is presented). Names are not always unique'})
        children = (ArrayBlock(length=(0, 'num_items + ?'),
                               child=AutoDetectBlock(possible_blocks=[
                                   Bitmap4Bit(),
                                   Bitmap8Bit(),
                                   Bitmap16Bit0565(),
                                   Bitmap32Bit(),
                                   Bitmap16Bit1555(),
                                   Bitmap24Bit(),
                                   Palette24BitDos(),
                                   Palette24Bit(),
                                   Palette32Bit(),
                                   Palette16Bit(),
                                   Palette16BitDos(),
                                   PaletteReference(),
                                   ShpiText(),
                                   BytesBlock(length=(lambda ctx: next(x for x in (
                                       x['offset'] + ctx.read_start_offset - ctx.buffer.tell()
                                       for x in (sorted(ctx.data('items_descr'), key=lambda x: x['offset'])
                                                 + [{'offset': ctx.read_bytes_amount}])
                                   ) if x > 0), 'item_length'))])),
                    {'description': 'A part of block, where items data is located. Offsets to some of the entries are '
                                    'defined in `items_descr` block. Between them there can be non-indexed '
                                    'entries (palettes and texts)'})

    def new_data(self):
        return {**super().new_data(), 'shpi_dir': 'LN32'}

    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        return [(x['name'], block_start + x['offset'], None) for x in data['items_descr']]

    def handle_archive_child(self, buffer, abs_offsets, i, self_ctx):
        (offset_payloads, aliases, children) = super().handle_archive_child(buffer, abs_offsets, i, self_ctx)
        (alias, offset, length) = abs_offsets[i]
        child_field = self.field_blocks_map['children'].child
        bitmap8_choice = next(i for i in range(len(child_field.possible_blocks)) if
                              isinstance(child_field.possible_blocks[i], Bitmap8Bit))
        if self_ctx.data('shpi_dir') != 'WRAP' and children[0]['choice_index'] == bitmap8_choice:
            extra_offset = children[0]['data']['block_size']
            if extra_offset > 0:
                extra_offset += offset
                if i == len(abs_offsets) - 1 or extra_offset < abs_offsets[i + 1][1]:
                    offset_payloads.append(buffer.read(extra_offset - buffer.tell()))
                    extra = child_field.unpack(self_ctx.buffer, ctx=self_ctx, name=self_ctx.name)
                    children.append(extra)
                    aliases.append(None)
        return offset_payloads, aliases, children

    def generate_items_descr(self, data, children):
        res = [{'name': name, 'offset': offset} for (name, offset, _) in children if name is not None]
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': res}, 'children')
        for x in res:
            x['offset'] += heap_offset
        return res


class WwwwBlock(BaseArchiveBlock):

    @property
    def schema(self) -> Dict:
        # this schema has recursion problem. Workaround applied here
        if getattr(self, 'schema_call_recv', False):
            return {
                'block_class_mro': '__'.join(
                    [x.__name__ for x in self.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
                'is_recursive_ref': True,
            }
        self.schema_call_recv = True
        schema = {
            **super().schema,
            'block_description': 'A block-container with various data: image archives, geometries, other wwww blocks. '
                                 'If has ORIP 3D model, next item is always SHPI block with textures to this 3D model',
            'serializable_to_disc': True,
        }
        delattr(self, 'schema_call_recv')
        return schema

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(required_value='wwww', length=4),
                       {'description': 'Resource ID'})
        num_items = (IntegerBlock(length=4),
                     {'description': 'An amount of items',
                      'programmatic_value': lambda ctx: len(ctx.data('items_descr'))})
        items_descr = (ArrayBlock(child=IntegerBlock(length=4),
                                  length=(lambda ctx: ctx.data('num_items'), 'num_items')),
                       {'description': 'An array of offsets to items data in file, relatively to wwww block start '
                                       '(where resource id string is presented)'})
        children = (ArrayBlock(length=(0, 'num_items'), child=None),
                    {'description': 'A part of block, where items data is located. Offsets are defined in previous '
                                    'block, lengths are calculated: either up to next item offset, or up to the end '
                                    'of this block'})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # write array field child block for referencing self in possible blocks
        self.child_block = AutoDetectBlock(possible_blocks=[
            ShpiBlock(),
            OripGeometry(),
            self,
            BytesBlock(length=(lambda ctx: next(x for x in (
                x + ctx.read_start_offset - ctx.buffer.tell()
                for x in (sorted(ctx.data('items_descr')) + [ctx.read_bytes_amount])
            ) if x > 0), 'item_length'))])
        self.field_blocks_map['children'].child = self.child_block

    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        offsets = [block_start + x for x in data['items_descr']]
        lengths = []
        for offset in offsets:
            try:
                lengths.append(sorted(x for x in offsets if x > offset)[0] - offset)
            except IndexError:
                lengths.append(block_start + read_bytes_amount - offset)
        return [(str(i), o, l) for i, (o, l) in enumerate(zip(offsets, lengths))]

    def generate_items_descr(self, data, children):
        res = [offset for (_, offset, _) in children]
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': res}, 'children')
        return [x + heap_offset for x in res]


class BigfBlock(BaseArchiveBlock):

    @property
    def schema(self) -> Dict:
        # this schema has recursion problem. Workaround applied here
        if getattr(self, 'schema_call_recv', False):
            return {
                'block_class_mro': '__'.join(
                    [x.__name__ for x in self.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
                'is_recursive_ref': True,
            }
        self.schema_call_recv = True
        schema = {
            **super().schema,
            'block_description': 'A block-container with various data: image archives, GEO geometries, sound banks, '
                                 'other BIGF blocks...',
            'serializable_to_disc': False,
        }
        delattr(self, 'schema_call_recv')
        return schema

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, required_value='BIGF'),
                       {'description': 'Resource ID'})
        length = (IntegerBlock(length=4, byte_order='big'),
                  {'description': 'The length of this BIGF block in bytes',
                   'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        num_items = (IntegerBlock(length=4, byte_order='big'),
                     {'description': 'An amount of items',
                      'programmatic_value': lambda ctx: len(ctx.data('items_descr'))})
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        items_descr = ArrayBlock(length=(lambda ctx: ctx.data('num_items'), 'num_items'),
                                 child=CompoundBlock(fields=[('offset', IntegerBlock(length=4, byte_order='big'), {}),
                                                             ('length', IntegerBlock(length=4, byte_order='big'), {}),
                                                             ('name', NullTerminatedUTF8Block(length=8), {})]))
        children = (ArrayBlock(length=(0, 'num_items'), child=None),
                    {'description': ''})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # write array field child block for referencing self in possible blocks
        child_block = AutoDetectBlock(possible_blocks=[
            GeoGeometry(),
            ShpiBlock(),
            self,
            BytesBlock(
                length=(lambda ctx:
                        next(x for x in ctx.data('items_descr')
                             if x['offset'] == ctx.buffer.tell() - ctx.read_start_offset)['length'],
                        'item_length'))])
        self.field_blocks_map['children'].child = child_block

    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        return [(x['name'], block_start + x['offset'], x['length']) for x in data['items_descr']]

    def generate_items_descr(self, data, children):
        res = [{'name': name, 'offset': offset, 'length': length} for (name, offset, length) in children]
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': res}, 'children')
        for x in res:
            x['offset'] += heap_offset
        return res


class SoundBank(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A pack of SFX samples (short audios). Used mostly for car engine sounds, '
                                 'crash sounds etc.',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        items_descr = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=128),
                       {'description': 'An array of offsets to items data in file. Zero values ignored'})
        items = (ArrayBlock(child=SoundBankHeaderEntry(),
                            length=(lambda ctx: len([x for x in ctx.data('items_descr') if x > 0]),
                                    '(amount of non-zero elements in items_descr)')),
                 {'description': 'EACS audio headers. Separate audios can be read easily using these because '
                                 'it contains file-wide offset to wave data, so it does not care wave data located, '
                                 'right after EACS header, or somewhere else like it is here in sound bank file'})
        wave_data = (BytesBlock(length=(lambda ctx: ctx.read_bytes_amount - ctx.buffer.tell(), 'up to end of file')),
                     {'description': 'Raw byte data, which is sliced according to provided offsets and used as wave '
                                     'data'})
        children = (ArrayBlock(child=EacsAudioFile(), length=0),
                    {'description': 'Disregard this field, it is generated by parser from the data from previous '
                                    'fields for convenience: essentially this file is a set of EACS audio-s, but their '
                                    'structure is dispersed across the file',
                     'custom_offset': 'N/A'})

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        bnk_start = buffer.tell()
        res = super().read(buffer, ctx, name, read_bytes_amount)

        # EacsAudioFile will store offset bytes between header and wave data. We don't want it here because
        # *.BNK contains many headers first, and then has big sequence of wave data.
        # Let's build result object artificially
        global_wave_offset = bnk_start + self.offset_to_child_when_packed(res, 'wave_data')
        res['children'] = []
        res['children_offsets'] = []
        slices = []
        last_slice_end = 0
        for item in res['items']:
            offset = item['eacs_header']['wave_data_offset'] - global_wave_offset
            length = item['eacs_header']['wave_data_length'] * item['eacs_header']['sound_resolution'] * \
                     item['eacs_header']['channels']
            res['children_offsets'].append(res['wave_data'][last_slice_end:offset])
            last_slice_end = offset + length
            slices.append((offset, offset + length))
            res['children'].append({
                'header': item['eacs_header'],
                'offset': b'',
                'wave_data': res['wave_data'][offset:offset + length]
            })
        res['children_offsets'].append(res['wave_data'][last_slice_end:])
        res['wave_data'] = b''
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        wave_data_heap = b''
        wave_data_offset = self.offset_to_child_when_packed(data, 'wave_data')
        wave_pointers = []
        for i, child in enumerate(data['children']):
            wave_data_heap += data['children_offsets'][i]
            try:
                wave_pointers.append(wave_data_offset + wave_data_heap.index(child['wave_data']))
            except ValueError:
                wave_pointers.append(wave_data_offset + len(wave_data_heap))
                wave_data_heap += child['wave_data']
        wave_data_heap += data['children_offsets'][-1]
        for i, item in enumerate(data['items']):
            item['eacs_header']['wave_data_offset'] = wave_pointers[i]
        data_to_write = deepcopy(data)
        data_to_write['wave_data'] = wave_data_heap
        data_to_write['children'] = []
        return super().write(data_to_write, ctx, name)
