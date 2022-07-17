from io import BufferedReader, BytesIO

from library.read_blocks.array import ArrayBlock, ExplicitOffsetsArrayBlock
from library.read_blocks.atomic import Utf8Field, IntegerBlock, BytesField
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.delegate import DelegateBlock
from library.read_blocks.literal import LiteralBlock
from resources.eac.audios import EacsAudio
from resources.eac.bitmaps import Bitmap16Bit0565, Bitmap24Bit, Bitmap16Bit1555, Bitmap32Bit, Bitmap8Bit, Bitmap4Bit
from resources.eac.compressions.qfs2 import Qfs2Compression
from resources.eac.compressions.qfs3 import Qfs3Compression
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries import OripGeometry
from resources.eac.palettes import (
    Palette16Bit,
    Palette32Bit,
    Palette24Bit,
    Palette24BitDos,
)


class CompressedBlock(DelegateBlock):
    block_description = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = None
        self.delegate_block_class = None

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        uncompressed_bytes = self.algorithm(buffer, size)
        uncompressed = BytesIO(uncompressed_bytes)
        if self.delegate_block_class is None:
            from library import probe_block_class
            self.delegate_block_class = probe_block_class(uncompressed, self.id + '_UNCOMPRESSED')
        self.delegated_block = self.delegate_block_class()
        return super().read(uncompressed, len(uncompressed_bytes))


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


class ShpiChildDescription(CompoundBlock):
    block_description = '8-bytes record, first 4 bytes is a UTF-8 string, last 4 bytes is an ' \
                        'unsigned integer (little-endian)'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        name = Utf8Field(length=4)
        offset = IntegerBlock(static_size=4, is_signed=False)


class ShpiBlock(CompoundBlock):
    block_description = 'A container of images and palettes for them'

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='SHPI', length=4, description='Resource ID')
        length = IntegerBlock(static_size=4, is_signed=False, description='The length of this SHPI block in bytes')
        children_count = IntegerBlock(static_size=4, is_signed=False, description='An amount of items')
        shpi_directory = Utf8Field(length=4, description='One of: "LN32", "GIMX", "WRAP". The purpose is unknown')
        children_descriptions = ArrayBlock(child=ShpiChildDescription(),
                                           description='An array of items, each of them represents name of SHPI item '
                                                       '(image or palette) and offset to item data in file, relatively '
                                                       'to SHPI block start (where resource id string is presented)')
        children = ExplicitOffsetsArrayBlock(child=LiteralBlock(
            possible_resources=[
                Bitmap16Bit0565(error_handling_strategy='return'),
                Bitmap4Bit(error_handling_strategy='return'),
                Bitmap8Bit(error_handling_strategy='return'),
                Bitmap32Bit(error_handling_strategy='return'),
                Bitmap16Bit1555(error_handling_strategy='return'),
                Bitmap24Bit(error_handling_strategy='return'),
                Palette24BitDos(error_handling_strategy='return'),
                Palette24Bit(error_handling_strategy='return'),
                Palette32Bit(error_handling_strategy='return'),
                Palette16Bit(error_handling_strategy='return'),
            ],
            error_handling_strategy='return',
        ), description='A part of block, where items data is located. Offsets are defined in previous block, lengths '
                       'are calculated: either up to next item offset, or up to the end of block')

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if self.children_descriptions:
                for i, item_name in enumerate(x.name for x in self.children_descriptions):
                    if item_name == name:
                        return self.children[i]
            raise ex

    def _after_children_count_read(self, data, **kwargs):
        self.instance_fields_map['children_descriptions'].length = data['children_count']

    def _after_children_descriptions_read(self, data, **kwargs):
        for description in data['children_descriptions']:
            description.name = description.name.replace('/', '_')
        self.instance_fields_map['children'].offsets = [x.offset + self.initial_buffer_pointer for x in
                                                        data['children_descriptions']]

    def _after_children_read(self, data, **kwargs):
        for i, child in enumerate(data['children']):
            child.id = self._id + ('/' if '__' in self._id else '__') + data['children_descriptions'][i].name


class WwwwBlock(CompoundBlock):
    block_description = 'A block-container with various data: image archives, geometries, other wwww blocks. ' \
                        'If has ORIP 3D model, next item is always SHPI block with textures to this 3D model'

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='wwww', length=4, description='Resource ID')
        children_count = IntegerBlock(static_size=4, is_signed=False, description='An amount of items')
        children_offsets = ArrayBlock(child=IntegerBlock(static_size=4, is_signed=False),
                                      description='An array of offsets to items data in file, relatively '
                                                  'to wwww block start (where resource id string is presented)')
        children = ExplicitOffsetsArrayBlock(child=LiteralBlock(
            possible_resources=[
                OripGeometry(error_handling_strategy='return'),
                ShpiBlock(error_handling_strategy='return'),
            ],
        ), description='A part of block, where items data is located. Offsets are defined in previous block, lengths '
                       'are calculated: either up to next item offset, or up to the end of block')

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if name.isdigit() and self.children and len(self.children) > int(name):
                return self.children[int(name)]
            raise ex

    def _after_children_count_read(self, data, **kwargs):
        self.instance_fields_map['children_offsets'].length = data['children_count']

    def _after_children_offsets_read(self, data, **kwargs):
        self.instance_fields_map['children'].offsets = [x + self.initial_buffer_pointer for x in
                                                        data['children_offsets']]


WwwwBlock.Fields.children.child.possible_resources.append(WwwwBlock(error_handling_strategy='return'))
WwwwBlock.Fields.children.child.instantiate_kwargs['possible_resources'].append(
    WwwwBlock(error_handling_strategy='return'))


class SoundBank(CompoundBlock):
    block_description = 'A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc.'

    class Fields(CompoundBlock.Fields):
        children_offsets = ArrayBlock(child=IntegerBlock(static_size=4, is_signed=False), length=128,
                                      description='An array of offsets to items data in file. Zero values seem to be '
                                                  'ignored, but for some reason the very first offset is 0 in most '
                                                  'files. The real audio data start is shifted 40 bytes forward for '
                                                  'some reason, so EACS is located at {offset from this array} + 40')
        children = ExplicitOffsetsArrayBlock(child=EacsAudio(),
                                             description='EACS blocks are here, placed at offsets from previous block. '
                                                         'Those EACS blocks don\'t have own wave data, there are 44 '
                                                         'bytes of unknown data instead, offsets in them are pointed '
                                                         'to wave data of this block')
        wave_data = ExplicitOffsetsArrayBlock(child=BytesField(length_strategy="read_available"),
                                              description='A space, where wave data is located. Pointers are in '
                                                          'children EACS')

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if name.isdigit() and self.children and len(self.children) > int(name):
                return self.children[int(name)]
            raise ex

    def _after_children_offsets_read(self, data, total_size, **kwargs):
        for offset in data['children_offsets']:
            if offset >= total_size:
                raise Exception(f'Child cannot start at offset {offset}. Resource length: {total_size}')
        # FIXME it is unknown what is + 40
        self.instance_fields_map['children'].offsets = [x + self.initial_buffer_pointer + 40
                                                        for x in data['children_offsets']
                                                        if x > 0]

    def _after_children_read(self, data, **kwargs):
        self.instance_fields_map['wave_data'].offsets = [x.wave_data_offset + self.initial_buffer_pointer
                                                         for x in data['children']]
        self.instance_fields_map['wave_data'].lengths = [x.wave_data_length * x.sound_resolution
                                                         for x in data['children']]

    def _after_wave_data_read(self, data, **kwargs):
        for i, child in enumerate(data['children']):
            child.wave_data = data['wave_data'][i]
