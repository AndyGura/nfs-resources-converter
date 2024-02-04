from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (CompoundBlock,
                                 DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 AutoDetectBlock,
                                 SkipBlock,
                                 BytesBlock)
from resources.eac.audios import EacsAudioHeader, EacsAudioFile
from resources.eac.bitmaps import Bitmap8Bit, Bitmap4Bit, Bitmap16Bit0565, Bitmap32Bit, Bitmap16Bit1555, Bitmap24Bit
from resources.eac.car_specs import CarSimplifiedPerformanceSpec, CarPerformanceSpec
from resources.eac.compressions.qfs2 import Qfs2Compression
from resources.eac.compressions.qfs3 import Qfs3Compression
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries import OripGeometry
from resources.eac.misc import ShpiText
from resources.eac.palettes import (Palette24BitDos,
                                    Palette24Bit,
                                    Palette32Bit,
                                    Palette16Bit,
                                    PaletteReference, Palette16BitDos)


class CompressedBlock(AutoDetectBlock):

    def __init__(self, **kwargs):
        super().__init__(possible_blocks=[ShpiBlock(),
                                          CarSimplifiedPerformanceSpec(),
                                          CarPerformanceSpec()],
                         **kwargs)
        self.algorithm = None

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
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


class ShpiBlock(DeclarativeCompoundBlock):

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
        children_count = (IntegerBlock(length=4),
                          {'description': 'An amount of items',
                           'programmatic_value': lambda ctx: len(ctx.data('children_descriptions'))})
        shpi_directory = (UTF8Block(length=4),
                          {'description': 'One of: "LN32", "GIMX", "WRAP". The purpose is unknown'})
        children_descriptions = (ArrayBlock(child=CompoundBlock(fields=[('name', UTF8Block(length=4), {}),
                                                                        ('offset', IntegerBlock(length=4), {})],
                                                                inline_description='8-bytes record, first 4 bytes is a UTF-8 string, last 4 bytes is an '
                                                                                   'unsigned integer (little-endian)'),
                                            length=(lambda ctx: ctx.data('children_count'), 'children_count')),
                                 {'description': 'An array of items, each of them represents name of SHPI item '
                                                 '(image or palette) and offset to item data in file, relatively '
                                                 'to SHPI block start (where resource id string is presented). '
                                                 'Names are not always unique'})
        children = (ArrayBlock(length=(0, 'children_count + ?'),
                               child=AutoDetectBlock(possible_blocks=[Bitmap4Bit(),
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
                                                                      SkipBlock(error_strategy="return_exception")])),
                    {'description': 'A part of block, where items data is located. Offsets to some of the entries are '
                                    'defined in `children_descriptions` block. Between them there can be non-indexed '
                                    'entries (palettes and texts)'})

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        offsets_sum = 0
        for offset in data['offset_payloads']:
            offsets_sum += len(offset)
        return super().estimate_packed_size(data, ctx) + offsets_sum

    def new_data(self):
        return {**super().new_data(),
                'shpi_directory': 'LN32',
                'children_aliases': [],
                'offset_payloads': [b'']}

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        shpi_start = buffer.tell()
        res = super().read(buffer, ctx, name, read_bytes_amount)
        self_ctx = [c for c in ctx.children if c.name == name][0] if ctx else ReadContext(buffer=buffer, data=res,
                                                                                          name=name, block=self,
                                                                                          parent=ctx,
                                                                                          read_bytes_amount=read_bytes_amount)

        abs_offsets = [{'name': x['name'], 'offset': shpi_start + x['offset']} for x in res['children_descriptions']]
        child_field = self.field_blocks_map['children'].child
        bitmap8_choice = next(i for i in range(len(child_field.possible_blocks)) if
                              isinstance(child_field.possible_blocks[i], Bitmap8Bit))
        children = []
        aliases = []
        offset_payloads = []
        for i, descr in enumerate(abs_offsets):
            if descr['offset'] > buffer.tell():
                offset_payloads.append(buffer.read(descr['offset'] - buffer.tell()))
            else:
                offset_payloads.append(b'')
                buffer.seek(descr["offset"])
            child = child_field.unpack(self_ctx.buffer, ctx=self_ctx)
            children.append(child)
            aliases.append(descr["name"])
            if res['shpi_directory'] != 'WRAP' and child['choice_index'] == bitmap8_choice:
                extra_offset = child['data']['block_size']
                if extra_offset > 0:
                    extra_offset += descr["offset"]
                    if i == len(abs_offsets) - 1 or extra_offset < abs_offsets[i + 1]['offset']:
                        offset_payloads.append(buffer.read(extra_offset - buffer.tell()))
                        extra = child_field.unpack(self_ctx.buffer, ctx=self_ctx, name=name)
                        children.append(extra)
                        aliases.append(None)
        if buffer.tell() < shpi_start + res['length']:
            diff = shpi_start + res['length'] - buffer.tell()
            offset_payloads.append(buffer.read(diff))
        buffer.seek(shpi_start + read_bytes_amount)
        res['children'] = children
        res['children_aliases'] = aliases
        res['offset_payloads'] = offset_payloads
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        children_heap = b''
        child_offsets = {}
        child_block = self.field_blocks_map['children'].child
        for i, item in enumerate(data['children']):
            children_heap += data['offset_payloads'][i]
            if data['children_aliases'][i] is not None:
                child_offsets[data['children_aliases'][i]] = len(children_heap)
            children_heap += child_block.pack(data=item, ctx=ctx, name=str(i))
        if len(data['offset_payloads']) > len(data['children']):
            for i in range(len(data['children']), len(data['offset_payloads'])):
                children_heap += data['offset_payloads'][i]
        data['children_descriptions'] = [{'name': name, 'offset': offset} for (name, offset) in child_offsets.items()]
        heap_offset = self.offset_to_child_when_packed(data, 'children')
        for x in data['children_descriptions']:
            x['offset'] += heap_offset
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


class WwwwBlock(DeclarativeCompoundBlock):

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
        children_count = (IntegerBlock(length=4),
                          {'description': 'An amount of items'})
        children_offsets = (ArrayBlock(child=IntegerBlock(length=4),
                                       length=(lambda ctx: ctx.data('children_count'), 'children_count')),
                            {'description': 'An array of offsets to items data in file, relatively '
                                            'to wwww block start (where resource id string is presented)'})
        children = (ArrayBlock(length=(0, 'children_count'), child=None),
                    {'description': 'A part of block, where items data is located. Offsets are defined in previous '
                                    'block, lengths are calculated: either up to next item offset, or up to the end '
                                    'of this block'})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # write array field child block for referencing self in possible blocks
        self.child_block = AutoDetectBlock(possible_blocks=[ShpiBlock(),
                                                            OripGeometry(),
                                                            self,
                                                            SkipBlock(error_strategy="return_exception")])
        self.field_blocks_map['children'].child = self.child_block

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        wwww_start = buffer.tell()
        res = super().read(buffer, ctx, name, read_bytes_amount)
        abs_offsets = [wwww_start + x for x in res['children_offsets']]
        self_ctx = [c for c in ctx.children if c.name == name][0] if ctx else ReadContext(buffer=buffer, data=res,
                                                                                          name=name, block=self,
                                                                                          parent=ctx,
                                                                                          read_bytes_amount=read_bytes_amount)
        for i, offset in enumerate(abs_offsets):
            if offset == wwww_start:
                res['children'].append(None)
                continue
            buffer.seek(offset)
            try:
                length = sorted(o for o in abs_offsets if o > offset)[0] - wwww_start
            except IndexError:
                length = read_bytes_amount
            res['children'].append(self.child_block.unpack(self_ctx.buffer,
                                                           ctx=self_ctx,
                                                           name=str(i),
                                                           read_bytes_amount=length))
        buffer.seek(wwww_start + read_bytes_amount)
        return res


class SoundBank(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc.',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        children_offsets = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=128),
                            {'description': 'An array of offsets to items data in file. Zero values seem to be '
                                            'ignored, but for some reason the very first offset is 0 in most '
                                            'files. The real audio data start is shifted 40 bytes forward for '
                                            'some reason, so EACS is located at {offset from this array} + 40'})
        children = (ArrayBlock(child=EacsAudioFile(), length=(0, 'len(x for x in children_offsets if x > 0)')),
                    {'description': 'Not a simple array of EACS audio file contents. Instead, it contains few '
                                    '[EACS headers](#eacsaudioheader) separately, and then one big wave data, which '
                                    'should be sliced into separate audios according to data in EACS headers. Parsing '
                                    'single EACS audio still works in a simple way though, because in each header '
                                    'global offset to wave data presented'})

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        bnk_start = buffer.tell()
        res = super().read(buffer, ctx, name, read_bytes_amount)
        abs_offsets = [bnk_start + x + 40 for x in res['children_offsets'] if x > 0]
        self_ctx = [c for c in ctx.children if c.name == name][0] if ctx else ReadContext(buffer=buffer, data=res,
                                                                                          name=name, block=self,
                                                                                          parent=ctx,
                                                                                          read_bytes_amount=read_bytes_amount)
        child_header_block = EacsAudioHeader()
        child_wave_data_block = BytesBlock(length=0)
        for i, offset in enumerate(abs_offsets):
            buffer.seek(offset)
            # EacsAudioFile will store offset bytes between header and wave data. We don't want it here because
            # *.BNK contains many headers first, and then has big sequence of wave data.
            # Let's build result object artificially
            header_data = child_header_block.unpack(buffer, ctx=self_ctx, name=str(i))
            buffer.seek(header_data['wave_data_offset'])
            child_wave_data_block._length = min(read_bytes_amount - buffer.tell(),
                                                header_data['wave_data_length'] * header_data['sound_resolution'])
            res['children'].append({
                'header': header_data,
                'offset': b'',
                'wave_data': child_wave_data_block.unpack(buffer)
            })
        buffer.seek(bnk_start + read_bytes_amount)
        return res
