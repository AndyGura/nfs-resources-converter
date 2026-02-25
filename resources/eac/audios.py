from typing import Dict

from library.read_blocks import DeclarativeCompoundBlock, UTF8Block, IntegerBlock, BytesBlock, ArrayBlock
from library.read_blocks.misc.value_validators import Eq


class EacsAudioHeader(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A header for EACS audio. It is almost identical to AsfAudio when it is the only '
                                     'sound in the file (*.EAS), but also can be included in single SoundBank file '
                                     '(*.BNK), which has multiple EACS headers and wave data located separately'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('EACS'), length=4),
                       {'description': 'Resource ID'})
        sampling_rate = (IntegerBlock(length=4),
                         {'description': 'Sampling rate of audio'})
        sound_resolution = (IntegerBlock(length=1),
                            {'description': 'How many bytes in one wave data entry'})
        channels = (IntegerBlock(length=1),
                    {'description': 'Channels amount. 1 is mono, 2 is stereo'})
        compression = (IntegerBlock(length=1),
                       {'description': 'If equals to 2, wave data is compressed with [IMA ADPCM]('
                                       'https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)'
                                       '#IMA_ADPCM_Decompression_Algorithm) codec'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        wave_data_length = (IntegerBlock(length=4),
                            {'description': 'Amount of wave data entries. Should be multiplied by '
                                            'sound_resolution to calculated the size of data in bytes'})
        repeat_loop_beginning = (IntegerBlock(length=4),
                                 {'description': 'When audio ends, it repeats in loop from here. Should be '
                                                 'multiplied by sound_resolution to calculate offset in bytes'})
        repeat_loop_length = (IntegerBlock(length=4),
                              {'description': 'If play audio in loop, at this point we should rewind to repeat_'
                                              'loop_beginning. Should be multiplied by sound_resolution to '
                                              'calculate offset in bytes'})
        wave_data_offset = (IntegerBlock(length=4),
                            {'description': 'Offset of wave data start in current file, relative'
                                            ' to start of the file itself'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})


class SoundBankHeaderEntry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Uknown wrapper around EACS header block, which is used in *.BNK files'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk = (ArrayBlock(child=IntegerBlock(length=4), length=10),
               {'is_unknown': True})
        eacs_header = EacsAudioHeader()


class EacsAudioFile(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A file with single EACS audio entry',
                'custom_actions': [{
                    'method': 'silence',
                    'title': 'Silence',
                    'description': 'Makes this audio sample completely silent',
                    'is_pure': False,
                    'args': [],
                }]}

    class Fields(DeclarativeCompoundBlock.Fields):
        header = EacsAudioHeader()
        offset = (BytesBlock(
            length=(lambda ctx: ctx.data('header/wave_data_offset') - ctx.buffer.tell(),
                    'space up to offset `header.wave_data_offset` (global)')),
                  {'is_unknown': True})
        wave_data = (
            BytesBlock(length=(lambda ctx: min(ctx.read_bytes_remaining,
                                               ctx.data('header/wave_data_length')
                                               * ctx.data('header/sound_resolution')),
                               'min(`remaining file bytes`, '
                               '`header.wave_data_length` * `header.sound_resolution`)')),
            {'description': 'Wave data is here. If header.sound_resolution == 1, contains signed bytes, '
                            'else - unsigned',
             'custom_offset': 'wave_data_offset (global)'})

    def serializer_class(self):
        from serializers import EacsAudioSerializer
        return EacsAudioSerializer

    def action_silence(self, read_data, **kwargs):
        read_data['wave_data'] = b'\x00' * len(read_data['wave_data'])


class AsfAudio(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'An audio file, which is supported by FFMPEG and can be converted using only it. '
                                     'Has some explanation [here](https://wiki.multimedia.cx/index.php/Electronic_'
                                     'Arts_Formats_(2))'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('1SNh'), length=4),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=8),
                {'is_unknown': True})
        sampling_rate = (IntegerBlock(length=4),
                         {'description': 'Sampling rate of audio'})
        sound_resolution = (IntegerBlock(length=1),
                            {'description': 'How many bytes in one wave data entry'})
        channels = (IntegerBlock(length=1),
                    {'description': 'Channels amount. 1 is mono, 2 is stereo'})
        compression = (IntegerBlock(length=1),
                       {'description': 'If equals to 2, wave data is compressed with [IMA ADPCM codec]('
                                       'https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)'
                                       '#IMA_ADPCM_Decompression_Algorithm)'})
        unk1 = (IntegerBlock(length=1),
                {'is_unknown': True})
        wave_data_length = (IntegerBlock(length=4),
                            {'description': 'Amount of wave data entries. Should be multiplied by '
                                            'sound_resolution to calculated the size of data in bytes'})
        repeat_loop_beginning = (IntegerBlock(length=4),
                                 {'description': 'When audio ends, it repeats in loop from here. Should be '
                                                 'multiplied by sound_resolution to calculate offset in bytes'})
        repeat_loop_length = (IntegerBlock(length=4),
                              {'description': 'If play audio in loop, at this point we should rewind to repeat_'
                                              'loop_beginning. Should be multiplied by sound_resolution to '
                                              'calculate offset in bytes'})
        wave_data_offset = (IntegerBlock(length=4),
                            {'description': 'Offset of wave data start in current file, relative'
                                            ' to start of the file itself'})
        unk2 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = BytesBlock(
            length=(lambda ctx: ctx.data('wave_data_offset') + 40 - ctx.local_buffer_pos,
                    'space up to offset (wave_data_offset + 40)'), )
        wave_data = (BytesBlock(length=(lambda ctx: min(ctx.read_bytes_remaining,
                                                        ctx.data('wave_data_length') * ctx.data('sound_resolution')),
                                        'min(`remaining file bytes`, `wave_data_length` * `sound_resolution`)')),
                     {'description': 'Wave data is here',
                      'custom_offset': 'wave_data_offset + 40'})

    def serializer_class(self):
        from serializers import FfmpegSupportedAudioSerializer
        return FfmpegSupportedAudioSerializer
