import traceback
from copy import deepcopy
from io import SEEK_CUR
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 AutoDetectBlock,
                                 BytesBlock)
from library.read_blocks.archives import ArchiveBlock
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.audios import EacsAudioFile, SoundBankHeaderEntry
from .shpi_block import ShpiBlock, PaletteReference
from .compressed_block import EacCompressedBlock


class WwwwBlock(ArchiveBlock):

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
        }
        delattr(self, 'schema_call_recv')
        return schema

    def __init__(self, **kwargs):
        from resources.eac.geometries import OripGeometry
        super().__init__(item_block=AutoDetectBlock(possible_blocks=[
            ShpiBlock(),
            OripGeometry(),
            self,
            BytesBlock(length=(lambda ctx: next(x for x in (
                x - ctx.local_buffer_pos
                for x in (sorted(ctx.data('items_descr')) + [ctx.read_bytes_amount])
            ) if x > 0), 'item_length'))]),
            **kwargs)

    class Fields(ArchiveBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('wwww'), length=4),
                       {'description': 'Resource ID'})
        num_items = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
                     {'description': 'An amount of items'})
        items_descr = (ArrayBlock(child=IntegerBlock(length=4),
                                  length=lambda ctx: ctx.data('num_items')),
                       {'usage': 'io,doc',
                        'description': 'An array of offsets to items data in file, relatively to wwww block start '
                                       '(where resource id string is presented)'})
        data_bytes = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                      {'usage': 'io,doc',
                       'description': 'A part of block, where items data is located. Offsets are defined in previous '
                                      'block, lengths are calculated: either up to next item offset, or up to the end '
                                      'of this block. Possible item types:'
                                      '<br/>- [ShpiBlock](#shpiblock)'
                                      '<br/>- [OripGeometry](#oripgeometry)'
                                      '<br/>- [WwwwBlock](#wwwwblock)'})
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 8
        for i, child in enumerate(data['children']):
            total_length += len(child['pre_offset_payload']) + len(child['post_offset_payload'])
            total_length += self.item_block.estimate_packed_size(data=child['item'], ctx=ctx)
            total_length += 4
        return total_length

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()
        res = super().read(ctx, name, read_bytes_amount)
        end_pos = ctx.buffer.tell()
        ctx.buffer.seek(-len(res['data_bytes']), SEEK_CUR)
        res['children'] = []

        offsets = [block_start + x for x in res['items_descr']]
        lengths = []
        for offset in offsets:
            try:
                lengths.append(sorted(x for x in offsets if x > offset)[0] - offset)
            except IndexError:
                lengths.append(block_start + read_bytes_amount - offset)
        abs_offsets = list(zip(offsets, lengths))

        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, res)
        try:
            bytes_choice = self.item_block.get_choice_index_by_class_name('BytesBlock')
        except StopIteration:
            bytes_choice = -1
        for i, (offset, length) in enumerate(abs_offsets):
            child = {'item': None, 'pre_offset_payload': b'', 'post_offset_payload': b''}
            res['children'].append(child)
            if offset > ctx.buffer.tell():
                child['pre_offset_payload'] = ctx.buffer.read(offset - ctx.buffer.tell())
            else:
                ctx.buffer.seek(offset)
            try:
                child['item'] = self.item_block.unpack(ctx=self_ctx, name=str(i), read_bytes_amount=length)
            except Exception:
                traceback.print_exc()
                ctx.buffer.seek(offset)
                child['item'] = {'choice_index': bytes_choice, 'data': ctx.buffer.read(length)}
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        del res['data_bytes']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        data['items_descr'] = []
        for i, child in enumerate(data['children']):
            item_data = self.item_block.pack(data=child['item'], ctx=ctx, name=str(i))
            data['items_descr'].append(len(data['data_bytes']))
            data['data_bytes'] += child['pre_offset_payload']
            data['data_bytes'] += item_data
            data['data_bytes'] += child['post_offset_payload']
        heap_offset = 8 + len(data['items_descr']) * 4
        data['items_descr'] = [x + heap_offset for x in data['items_descr']]
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def serializer_class(self):
        from serializers import WwwwArchiveSerializer
        return WwwwArchiveSerializer


class BigfItemDescriptionBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        offset = IntegerBlock(length=4, byte_order='big')
        length = IntegerBlock(length=4, byte_order='big')
        name = NullTerminatedUTF8Block(length=8)


class BigfBlock(ArchiveBlock):

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
        }
        delattr(self, 'schema_call_recv')
        return schema

    def __init__(self, **kwargs):
        from resources.eac.geometries import GeoGeometry
        super().__init__(item_block=AutoDetectBlock(possible_blocks=[
            GeoGeometry(),
            ShpiBlock(),
            EacCompressedBlock(),
            self,
            BytesBlock(
                length=(lambda ctx: next(x
                                         for x in ctx.data('items_descr')
                                         if x['offset'] == ctx.local_buffer_pos)['length'],
                        'item_length'))]),
            alias_field=NullTerminatedUTF8Block(length=8),
            **kwargs)

    class Fields(ArchiveBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('BIGF')),
                       {'description': 'Resource ID'})
        length = (IntegerBlock(length=4, byte_order='big',
                               programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                  {'description': 'The length of this BIGF block in bytes'})
        num_items = (IntegerBlock(length=4, byte_order='big',
                                  programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
                     {'description': 'An amount of items'})
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        items_descr = (ArrayBlock(length=lambda ctx: ctx.data('num_items'),
                                  child=BigfItemDescriptionBlock()),
                       {'usage': 'io,doc'})
        data_bytes = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                      {'usage': 'io,doc',
                       'description': 'A part of block, where items data is located. Offsets and lengths are defined '
                                      'in previous block. Possible item types:'
                                      '<br/>- [GeoGeometry](#geogeometry)'
                                      '<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file'
                                      '<br/>- [BigfBlock](#bigfblock)'})
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 16
        for i, child in enumerate(data['children']):
            total_length += len(child['pre_offset_payload']) + len(child['post_offset_payload'])
            total_length += self.item_block.estimate_packed_size(data=child['item'], ctx=ctx)
            total_length += 9 + len(child['alias'])
        return total_length

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()
        res = super().read(ctx, name, read_bytes_amount)
        end_pos = ctx.buffer.tell()
        ctx.buffer.seek(-len(res['data_bytes']), SEEK_CUR)
        res['children'] = []

        abs_offsets = [
            (i, x['name'], block_start + x['offset'], x['length'])
            for i, x in sorted(list(enumerate(res['items_descr'])), key=lambda x: x[1]['offset'])
        ]
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, res)
        try:
            bytes_choice = self.item_block.get_choice_index_by_class_name('BytesBlock')
        except StopIteration:
            bytes_choice = -1
        children_map = [None] * len(abs_offsets)
        for i, (descr_index, alias, offset, length) in enumerate(abs_offsets):
            child = {'item': None, 'alias': alias, 'pre_offset_payload': b'', 'post_offset_payload': b''}
            children_map[descr_index] = [child]
            if offset > ctx.buffer.tell():
                child['pre_offset_payload'] = ctx.buffer.read(offset - ctx.buffer.tell())
            else:
                ctx.buffer.seek(offset)
            try:
                child['item'] = self.item_block.unpack(ctx=self_ctx, name=f"{descr_index}_{alias}",
                                                       read_bytes_amount=length)
            except Exception:
                traceback.print_exc()
                ctx.buffer.seek(offset)
                child['item'] = {'choice_index': bytes_choice, 'data': ctx.buffer.read(length)}
        if res.get('length') is not None and ctx.buffer.tell() < block_start + res['length']:
            diff = block_start + res['length'] - ctx.buffer.tell()
            children_map[abs_offsets[-1][0]][-1]['post_offset_payload'] = ctx.buffer.read(diff)
        res['children'] = []
        for cs in children_map:
            res['children'].extend(cs)
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        del res['data_bytes']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        for i, child in enumerate(data['children']):
            data['data_bytes'] += child['pre_offset_payload']
            item_data = self.item_block.pack(data=child['item'], ctx=ctx, name=str(i))
            children.append((child['alias'], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
            data['data_bytes'] += child['post_offset_payload']
        data['items_descr'] = [{'name': name, 'offset': offset, 'length': length} for (name, offset, length) in children
                               if name is not None]
        heap_offset = 16
        for x in data['items_descr']:
            heap_offset += 9 + len(x['name'])
        for x in data['items_descr']:
            x['offset'] += heap_offset
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def serializer_class(self):
        from serializers import BigfArchiveSerializer
        return BigfArchiveSerializer


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
                                    'amount of non-zero elements in items_descr')),
                 {'description': 'EACS audio headers. Separate audios can be read easily using these because '
                                 'it contains file-wide offset to wave data, so it does not care wave data located, '
                                 'right after EACS header, or somewhere else like it is here in sound bank file'})
        wave_data = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                     {'description': 'Raw byte data, which is sliced according to provided offsets and used as wave '
                                     'data',
                      'usage': 'io,doc'})
        children = (ArrayBlock(child=EacsAudioFile(), length=(0, 'amount of non-zero elements in items_descr')),
                    {'description': 'EACS audios',
                     'usage': 'ui'})

    def serializer_class(self):
        from serializers import SoundBankSerializer
        return SoundBankSerializer

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        bnk_start = ctx.buffer.tell()
        res = super().read(ctx, name, read_bytes_amount)

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
