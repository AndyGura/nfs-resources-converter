from resources.basic.array_field import ArrayField
from resources.basic.atomic import Utf8Field, IntegerField, BytesField
from resources.basic.compound_block import CompoundBlock


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
        wave_data = BytesField(length_strategy="read_available")

    def _after_wave_data_offset_read(self, data, buffer, **kwargs):
        # FIXME it is unknown what is + 40
        buffer.seek(data['wave_data_offset'] + self.initial_buffer_pointer + 40)
        self.instance_fields_map['wave_data'].length = data['wave_data_length']


class AsfAudio(CompoundBlock):
    block_description = 'An audio file, which is supported by FFMPEG and can be converted using only it'

    @property
    def file_path(self):
        return self.id

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='1SNh', length=4, description='Resource ID')
        unknowns = ArrayField(length=8, child=IntegerField(static_size=1), is_unknown=True)
        sampling_rate = IntegerField(static_size=4, description='')
        sound_resolution = IntegerField(static_size=1, description='')
        channels = IntegerField(static_size=1, description='')
        compression = IntegerField(static_size=1, description='')
        unk0 = IntegerField(static_size=1, is_unknown=True)
        wave_data_length = IntegerField(static_size=4, description='')
        repeat_loop_beginning = IntegerField(static_size=4, description='')
        repeat_loop_length = IntegerField(static_size=4, description='')
        wave_data_offset = IntegerField(static_size=4, description='')
        wave_data = BytesField(length_strategy="read_available")
