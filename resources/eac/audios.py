from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import Utf8Field, IntegerBlock, BytesField
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.detached import DetachedBlock


class EacsAudio(CompoundBlock):
    block_description = 'An audio block, almost identical to AsfAudio, but can be included in single SoundBank file ' \
                        'with multiple other EACS blocks and has detached wave data, which is located somewhere in ' \
                        'the SoundBank file after all EACS blocks'

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='EACS', length=4, description='Resource ID')
        sampling_rate = IntegerBlock(static_size=4, description='Sampling rate of audio')
        sound_resolution = IntegerBlock(static_size=1, description='How many bytes in one wave data entry')
        channels = IntegerBlock(static_size=1, description='Channels amount. 1 is mono, 2 is stereo')
        compression = IntegerBlock(static_size=1,
                                   description='If equals to 2, wave data is compressed with IMA ADPCM codec: '
                                               'https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)'
                                               '#IMA_ADPCM_Decompression_Algorithm')
        unk0 = IntegerBlock(static_size=1)
        wave_data_length = IntegerBlock(static_size=4,
                                        description='Amount of wave data entries. Should be multiplied by '
                                                    'sound_resolution to calculated the size of data in bytes')
        repeat_loop_beginning = IntegerBlock(static_size=4,
                                             description='When audio ends, it repeats in loop from here. Should be '
                                                         'multiplied by sound_resolution to calculate offset in bytes')
        repeat_loop_length = IntegerBlock(static_size=4,
                                          description='If play audio in loop, at this point we should rewind to repeat_'
                                                      'loop_beginning. Should be multiplied by sound_resolution to '
                                                      'calculate offset in bytes')
        wave_data_offset = IntegerBlock(static_size=4, description='Offset of wave data start in current file, relative'
                                                                   ' to start of the file itself')
        wave_data = DetachedBlock(block=BytesField(),
                                  description='Wave data, located somewhere in file at wave_data_offset. if '
                                              'sound_resolution == 1, contains signed bytes, else - unsigned')

        unknown_fields = ['unk0']

    def _after_wave_data_offset_read(self, data, **kwargs):
        self.instance_fields_map['wave_data'].offset = data['wave_data_offset']
        self.instance_fields_map['wave_data'].size = data['wave_data_length'] * data['sound_resolution']


class AsfAudio(CompoundBlock):
    block_description = 'An audio file, which is supported by FFMPEG and can be converted using only it. Has some ' \
                        'explanation here: https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2) . It is ' \
                        'very similar to EACS audio, but has wave data in place, just after the header'

    @property
    def file_path(self):
        return self.id

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='1SNh', length=4, description='Resource ID')
        unknowns = ArrayBlock(length=8, child=IntegerBlock(static_size=1))
        sampling_rate = IntegerBlock(static_size=4, description='Sampling rate of audio')
        sound_resolution = IntegerBlock(static_size=1, description='How many bytes in one wave data entry')
        channels = IntegerBlock(static_size=1, description='Channels amount. 1 is mono, 2 is stereo')
        compression = IntegerBlock(static_size=1,
                                   description='If equals to 2, wave data is compressed with IMA ADPCM codec: '
                                               'https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)'
                                               '#IMA_ADPCM_Decompression_Algorithm')
        unk0 = IntegerBlock(static_size=1)
        wave_data_length = IntegerBlock(static_size=4,
                                        description='Amount of wave data entries. Should be multiplied by '
                                                    'sound_resolution to calculated the size of data in bytes')
        repeat_loop_beginning = IntegerBlock(static_size=4,
                                             description='When audio ends, it repeats in loop from here. Should be '
                                                         'multiplied by sound_resolution to calculate offset in bytes')
        repeat_loop_length = IntegerBlock(static_size=4,
                                          description='If play audio in loop, at this point we should rewind to repeat_'
                                                      'loop_beginning. Should be multiplied by sound_resolution to '
                                                      'calculate offset in bytes')
        wave_data_offset = IntegerBlock(static_size=4, description='Offset of wave data start in current file, relative'
                                                                   ' to start of the file itself')
        wave_data = BytesField(description='Wave data is here')

        unknown_fields = ['unknowns', 'unk0']
