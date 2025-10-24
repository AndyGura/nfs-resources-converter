from copy import deepcopy
from io import BytesIO
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 AutoDetectBlock,
                                 BytesBlock)
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.audios import EacsAudioFile, SoundBankHeaderEntry
from resources.eac.car_specs import CarSimplifiedPerformanceSpec, CarPerformanceSpec
from resources.eac.compressions.qfs2 import Qfs2Compression
from resources.eac.compressions.qfs3 import Qfs3Compression
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries import OripGeometry, GeoGeometry
from .base_archive_block import BaseArchiveBlock
from .shpi_block import ShpiBlock


class CompressedBlock(AutoDetectBlock):

    def __init__(self, **kwargs):
        super().__init__(possible_blocks=[ShpiBlock(),
                                          CarSimplifiedPerformanceSpec(),
                                          CarPerformanceSpec()],
                         **kwargs)
        self.algorithm = None

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        uncompressed_bytes = self.algorithm(ctx.buffer, read_bytes_amount)
        uncompressed = BytesIO(uncompressed_bytes)
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount)
        self_ctx.buffer = uncompressed
        self_ctx.data = { 'uncompressed': None }
        res = super().read(ctx=self_ctx, name='uncompressed', read_bytes_amount=len(uncompressed_bytes))
        return res


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
                                  length=lambda ctx: ctx.data('num_items')),
                       {'description': 'An array of offsets to items data in file, relatively to wwww block start '
                                       '(where resource id string is presented)'})
        data_bytes = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                      {'description': 'A part of block, where items data is located. Offsets are defined in previous '
                                      'block, lengths are calculated: either up to next item offset, or up to the end '
                                      'of this block. Possible item types:'
                                      '<br/>- [ShpiBlock](#shpiblock)'
                                      '<br/>- [OripGeometry](#oripgeometry)'
                                      '<br/>- [WwwwBlock](#wwwwblock)',
                       'usage': 'skip_ui'})
        children = (ArrayBlock(length=(0, 'num_items'), child=None),
                    {'usage': 'ui_only'})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # UI Array child block for referencing self in possible blocks
        self.child_block = AutoDetectBlock(possible_blocks=[
            ShpiBlock(),
            OripGeometry(),
            self,
            BytesBlock(length=(lambda ctx: next(x for x in (
                x - ctx.local_buffer_pos
                for x in (sorted(ctx.data('items_descr')) + [ctx.read_bytes_amount])
            ) if x > 0), 'item_length'))])
        self.field_blocks_map['children'].child = self.child_block

    def serializer_class(self):
        from serializers import WwwwArchiveSerializer
        return WwwwArchiveSerializer

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
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': res}, 'data_bytes')
        return [x + heap_offset for x in res]


class BigfItemDescriptionBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        offset = IntegerBlock(length=4, byte_order='big')
        length = IntegerBlock(length=4, byte_order='big')
        name = NullTerminatedUTF8Block(length=8)


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
        items_descr = ArrayBlock(length=lambda ctx: ctx.data('num_items'),
                                 child=BigfItemDescriptionBlock())
        data_bytes = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                      {'description': 'A part of block, where items data is located. Offsets and lengths are defined '
                                      'in previous block. Possible item types:'
                                      '<br/>- [GeoGeometry](#geogeometry)'
                                      '<br/>- [ShpiBlock](#shpiblock)'
                                      '<br/>- [BigfBlock](#bigfblock)',
                       'usage': 'skip_ui'})
        children = (ArrayBlock(length=(0, 'num_items'), child=None),
                    {'usage': 'ui_only'})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # write array field child block for referencing self in possible blocks
        child_block = AutoDetectBlock(possible_blocks=[
            GeoGeometry(),
            ShpiBlock(),
            self,
            BytesBlock(
                length=(lambda ctx: next(x
                                         for x in ctx.data('items_descr')
                                         if x['offset'] == ctx.local_buffer_pos)['length'],
                        'item_length'))])
        self.field_blocks_map['children'].child = child_block

    def serializer_class(self):
        from serializers import BigfArchiveSerializer
        return BigfArchiveSerializer

    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        return [(x['name'], block_start + x['offset'], x['length']) for x in data['items_descr']]

    def generate_items_descr(self, data, children):
        res = [{'name': name, 'offset': offset, 'length': length} for (name, offset, length) in children]
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': res}, 'data_bytes')
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
                                    'amount of non-zero elements in items_descr')),
                 {'description': 'EACS audio headers. Separate audios can be read easily using these because '
                                 'it contains file-wide offset to wave data, so it does not care wave data located, '
                                 'right after EACS header, or somewhere else like it is here in sound bank file'})
        wave_data = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                     {'description': 'Raw byte data, which is sliced according to provided offsets and used as wave '
                                     'data',
                      'usage': 'skip_ui'})
        children = (ArrayBlock(child=EacsAudioFile(), length=(0, 'amount of non-zero elements in items_descr')),
                    {'description': 'EACS audios',
                     'usage': 'ui_only'})

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
