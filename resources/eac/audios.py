from library.read_blocks.array_field import ArrayBlock
from library.read_blocks.atomic import Utf8Field, IntegerField, BytesField
from library.read_blocks.compound_block import CompoundBlock
from library.read_blocks.detached_block import DetachedBlock


class EacsAudio(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='EACS', length=4, description='Resource ID')
        sampling_rate = IntegerField(static_size=4, description='')
        sound_resolution = IntegerField(static_size=1, description='')
        channels = IntegerField(static_size=1, description='')
        compression = IntegerField(static_size=1, description='')
        unk0 = IntegerField(static_size=1, is_unknown=True)
        wave_data_length = IntegerField(static_size=4, description='')
        repeat_loop_beginning = IntegerField(static_size=4, description='')
        repeat_loop_length = IntegerField(static_size=4, description='')
        wave_data_offset = IntegerField(static_size=4, description='')
        wave_data = DetachedBlock(block=BytesField())

    def _after_wave_data_offset_read(self, data, buffer, **kwargs):
        # TODO recheck this. Now initial buffer pointer commented out for preserving output audio like it was before refactoring
        self.instance_fields_map['wave_data'].offset = data['wave_data_offset']  # + self.initial_buffer_pointer)
        self.instance_fields_map['wave_data'].size = data['wave_data_length'] * data['sound_resolution']


class AsfAudio(CompoundBlock):
    block_description = 'An audio file, which is supported by FFMPEG and can be converted using only it'

    @property
    def file_path(self):
        return self.id

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='1SNh', length=4, description='Resource ID')
        unknowns = ArrayBlock(length=8, child=IntegerField(static_size=1), is_unknown=True)
        sampling_rate = IntegerField(static_size=4, description='')
        sound_resolution = IntegerField(static_size=1, description='')
        channels = IntegerField(static_size=1, description='')
        compression = IntegerField(static_size=1, description='')
        unk0 = IntegerField(static_size=1, is_unknown=True)
        wave_data_length = IntegerField(static_size=4, description='')
        repeat_loop_beginning = IntegerField(static_size=4, description='')
        repeat_loop_length = IntegerField(static_size=4, description='')
        wave_data_offset = IntegerField(static_size=4, description='')
        wave_data = BytesField()
