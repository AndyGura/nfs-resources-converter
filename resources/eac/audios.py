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
