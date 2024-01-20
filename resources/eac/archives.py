from io import BufferedReader, BytesIO
from typing import Dict

from library.read_blocks.array import ArrayBlock as ArrayBlockOld, ExplicitOffsetsArrayBlock, ByteArray
from library.read_blocks.atomic import Utf8Block as Utf8BlockOld, IntegerBlock as IntegerBlockOld
from library.read_blocks.compound import CompoundBlock as CompoundBlockOld
from library.read_blocks.literal import LiteralBlock
from library2.context import ReadContext
from library2.read_blocks import (CompoundBlock, DeclarativeCompoundBlock, UTF8Block, IntegerBlock, ArrayBlock,
                                  HeapBlock, AutoDetectBlock, SkipBlock, DelegateBlock)
from resources.eac.audios import EacsAudio
from resources.eac.bitmaps import Bitmap8Bit, Bitmap4Bit, Bitmap16Bit0565, Bitmap32Bit, Bitmap16Bit1555, Bitmap24Bit
from resources.eac.compressions.qfs2 import Qfs2Compression
from resources.eac.compressions.qfs3 import Qfs3Compression
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries import OripGeometry
from resources.eac.palettes import Palette24BitDos, Palette24Bit, Palette32Bit, Palette16Bit


class CompressedBlock(AutoDetectBlock):

    def __init__(self, **kwargs):
        super().__init__(possible_blocks=[
            ShpiBlock()
        ], **kwargs)
        self.algorithm = None

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        raise NotImplementedError
        uncompressed_bytes = self.algorithm(buffer, read_bytes_amount)
        uncompressed = BytesIO(uncompressed_bytes)
        self_ctx = ReadContext(buffer=uncompressed, name=name, parent=ctx, read_bytes_amount=len(uncompressed_bytes))
        return super().read(buffer=uncompressed, ctx=self_ctx, name=name, read_bytes_amount=len(uncompressed_bytes))


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


def build_children_block_fields(ctx):
    res = []
    shpi_start_offset = ctx.read_start_offset if isinstance(ctx, ReadContext) else None
    for i, c in enumerate(ctx.data('children_descriptions')):
        res.append((c['name'], c['offset'] - (ctx.buffer.tell() - shpi_start_offset), None))
    return res


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
                                                 'to SHPI block start (where resource id string is presented)'})

        children = (HeapBlock(child=AutoDetectBlock(possible_blocks=[Bitmap4Bit(),
                                                                     Bitmap8Bit(),
                                                                     Bitmap16Bit0565(),
                                                                     Bitmap32Bit(),
                                                                     Bitmap16Bit1555(),
                                                                     Bitmap24Bit(),
                                                                     Palette24BitDos(),
                                                                     Palette24Bit(),
                                                                     Palette32Bit(),
                                                                     Palette16Bit(),
                                                                     SkipBlock(error_strategy="return_exception")]),
                              length=lambda ctx: ctx.read_bytes_amount - (ctx.buffer.tell() - ctx.read_start_offset),
                              children_descr=lambda ctx: build_children_block_fields(ctx)),
                    {'description': 'A part of block, where items data is located. Offsets are defined in previous'
                                    ' block. After 8-bit bitmaps sometimes have additional palette, not referenced in '
                                    '"children_descriptions". Such palette should be assigned to prepending bitmap', })


class WwwwBlock(CompoundBlockOld):
    block_description = 'A block-container with various data: image archives, geometries, other wwww blocks. ' \
                        'If has ORIP 3D model, next item is always SHPI block with textures to this 3D model'

    class Fields(CompoundBlockOld.Fields):
        resource_id = Utf8BlockOld(required_value='wwww', length=4, description='Resource ID')
        children_count = IntegerBlockOld(static_size=4, is_signed=False, description='An amount of items')
        children_offsets = ArrayBlockOld(child=IntegerBlockOld(static_size=4, is_signed=False),
                                         length_label='children_count',
                                         description='An array of offsets to items data in file, relatively '
                                                     'to wwww block start (where resource id string is presented)')
        children = ExplicitOffsetsArrayBlock(child=LiteralBlock(
            possible_resources=[
                OripGeometry(error_handling_strategy='return'),
                ShpiBlock(error_handling_strategy='return'),
            ],
        ), length_label='children_count',
            description='A part of block, where items data is located. Offsets are defined in previous block, lengths '
                        'are calculated: either up to next item offset, or up to the end of block')

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if name.isdigit() and self.children and len(self.children) > int(name):
                return self.children[int(name)]
            raise ex

    def _after_children_count_read(self, data, state, **kwargs):
        if not state.get('children_offsets'):
            state['children_offsets'] = {}
        state['children_offsets']['length'] = data['children_count'].value

    def _after_children_offsets_read(self, data, state, initial_buffer_pointer, **kwargs):
        if not state.get('children'):
            state['children'] = {}
        state['children']['offsets'] = [x.value + initial_buffer_pointer for x in
                                        data['children_offsets'].value]


WwwwBlock.Fields.children.child.possible_resources.append(WwwwBlock(error_handling_strategy='return'))


class SoundBank(CompoundBlockOld):
    block_description = 'A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc.'

    class Fields(CompoundBlockOld.Fields):
        children_offsets = ArrayBlockOld(child=IntegerBlockOld(static_size=4, is_signed=False), length=128,
                                         description='An array of offsets to items data in file. Zero values seem to be '
                                                     'ignored, but for some reason the very first offset is 0 in most '
                                                     'files. The real audio data start is shifted 40 bytes forward for '
                                                     'some reason, so EACS is located at {offset from this array} + 40')
        children = ExplicitOffsetsArrayBlock(child=EacsAudio(),
                                             description='EACS blocks are here, placed at offsets from previous block. '
                                                         'Those EACS blocks don\'t have own wave data, there are 44 '
                                                         'bytes of unknown data instead, offsets in them are pointed '
                                                         'to wave data of this block')
        wave_data = ExplicitOffsetsArrayBlock(child=ByteArray(length_strategy="read_available"),
                                              description='A space, where wave data is located. Pointers are in '
                                                          'children EACS')

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if name.isdigit() and self.children and len(self.children) > int(name):
                return self.children[int(name)]
            raise ex

    def _after_children_offsets_read(self, data, total_size, state, initial_buffer_pointer, **kwargs):
        for offset in data['children_offsets']:
            if offset.value >= total_size:
                raise Exception(f'Child cannot start at offset {offset.value}. Resource length: {total_size}')
        # FIXME it is unknown what is + 40
        if not state.get('children'):
            state['children'] = {}
        state['children']['offsets'] = [x.value + initial_buffer_pointer + 40
                                        for x in data['children_offsets']
                                        if x.value > 0]

    def _after_children_read(self, data, initial_buffer_pointer, state, **kwargs):
        if not state.get('wave_data'):
            state['wave_data'] = {}
        state['wave_data']['offsets'] = [x.wave_data_offset.value + initial_buffer_pointer
                                         for x in data['children']]
        state['wave_data']['lengths'] = [x.wave_data_length.value * x.sound_resolution.value
                                         for x in data['children']]

    def _after_wave_data_read(self, data, **kwargs):
        for i, child in enumerate(data['children']):
            child.value['wave_data'] = data['wave_data'][i]
