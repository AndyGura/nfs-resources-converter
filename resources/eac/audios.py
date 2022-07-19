from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import Utf8Field, IntegerBlock, BytesField
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.detached import DetachedBlock


class EacsAudio(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='EACS', length=4, description='Resource ID')
        sampling_rate = IntegerBlock(static_size=4, description='')
        sound_resolution = IntegerBlock(static_size=1, description='')
        channels = IntegerBlock(static_size=1, description='')
        compression = IntegerBlock(static_size=1, description='')
        unk0 = IntegerBlock(static_size=1)
        wave_data_length = IntegerBlock(static_size=4, description='')
        repeat_loop_beginning = IntegerBlock(static_size=4, description='')
        repeat_loop_length = IntegerBlock(static_size=4, description='')
        wave_data_offset = IntegerBlock(static_size=4, description='')
        wave_data = DetachedBlock(block=BytesField())

        unknown_fields = ['unk0']

    def _after_wave_data_offset_read(self, data, **kwargs):
        self.instance_fields_map['wave_data'].offset = data['wave_data_offset']
        self.instance_fields_map['wave_data'].size = data['wave_data_length'] * data['sound_resolution']


class AsfAudio(CompoundBlock):
    block_description = 'An audio file, which is supported by FFMPEG and can be converted using only it'

    @property
    def file_path(self):
        return self.id

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='1SNh', length=4, description='Resource ID')
        unknowns = ArrayBlock(length=8, child=IntegerBlock(static_size=1))
        sampling_rate = IntegerBlock(static_size=4, description='')
        sound_resolution = IntegerBlock(static_size=1, description='')
        channels = IntegerBlock(static_size=1, description='')
        compression = IntegerBlock(static_size=1, description='')
        unk0 = IntegerBlock(static_size=1)
        wave_data_length = IntegerBlock(static_size=4, description='')
        repeat_loop_beginning = IntegerBlock(static_size=4, description='')
        repeat_loop_length = IntegerBlock(static_size=4, description='')
        wave_data_offset = IntegerBlock(static_size=4, description='')
        wave_data = BytesField()

        unknown_fields = ['unknowns', 'unk0']
