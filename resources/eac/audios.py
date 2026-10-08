from copy import deepcopy
from io import SEEK_CUR
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (
    DeclarativeCompoundBlock,
    UTF8Block,
    IntegerBlock,
    BytesBlock,
    Padding,
    ArrayBlock,
    EnumByteBlock,
    OptionalBlock,
    BitFlagsBlock,
)
from library.read_blocks.misc.value_validators import Eq


class EacsAudioHeader(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A header for EACS audio. It is almost identical to AsfAudio when it is the only '
            'sound in the file (*.EAS), but also can be included in single SoundBank file '
            '(*.BNK), which has multiple EACS headers and wave data located separately',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('EACS'), length=4), {'description': 'Resource ID'})
        sampling_rate = (IntegerBlock(length=4), {'description': 'Sampling rate of audio'})
        sound_resolution = (IntegerBlock(length=1), {'description': 'How many bytes in one wave data entry'})
        channels = (IntegerBlock(length=1), {'description': 'Channels amount. 1 is mono, 2 is stereo'})
        compression = (
            IntegerBlock(length=1),
            {
                'description': 'If equals to 2, wave data is compressed with [IMA ADPCM]('
                'https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)'
                '#IMA_ADPCM_Decompression_Algorithm) codec'
            },
        )
        unk0 = (IntegerBlock(length=1), {'is_unknown': True})
        wave_data_length = (
            IntegerBlock(length=4),
            {
                'description': 'Amount of wave data entries. Should be multiplied by '
                'sound_resolution to calculated the size of data in bytes'
            },
        )
        repeat_loop_beginning = (
            IntegerBlock(length=4),
            {
                'description': 'When audio ends, it repeats in loop from here. Should be '
                'multiplied by sound_resolution to calculate offset in bytes'
            },
        )
        repeat_loop_length = (
            IntegerBlock(length=4),
            {
                'description': 'If play audio in loop, at this point we should rewind to repeat_'
                'loop_beginning. Should be multiplied by sound_resolution to '
                'calculate offset in bytes'
            },
        )
        wave_data_offset = (
            IntegerBlock(length=4),
            {'description': 'Offset of wave data start in current file, relative to start of the file itself'},
        )
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})


class SoundBankHeaderEntry(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': "TNFS sound bank (*.BNK) entry: the game's playback settings for a sample, "
            'followed by its EACS header. Field meanings come from the game code, as decoded by the '
            '[tnfs-1995](https://github.com/marcos2250/tnfs-1995) project',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        voice_mask = (
            IntegerBlock(length=4),
            {
                'description': "Bit mask of the game's mixer channels (voices) this sample may play on (bit n = "
                'channel n), used by the DOS voice allocator `sfx_voice_alloc` (0x96760). The collision bank '
                'duplicates looped wavs under several indices, each with a different bit. Examples: collision bank '
                'wind 0x29 has bit 5 (wind channel 5), waterfall 0x3e bit 11 (channel 0xb), the hits bits 4 and 5 '
                '(one-shot channel 4), car bank engine_off bit 1 (channel 1), car bank horn bit 14 (player horn '
                'channel 0xe). The exception is car bank engine_on: bit 6, played on channel 0',
            },
        )
        eacs_header_offset = (
            IntegerBlock(length=4),
            {'description': 'Offset of `eacs_header` in the file: offset of this entry + 40'},
        )
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        random_range = (
            IntegerBlock(length=4),
            {
                'description': 'Random pitch range in cents. At every voice start (DOS 0x96d22) the pitch offset of '
                'the voice is `pitch_offset` + a random value in [-random_range, +random_range]. 300 for hits, '
                '150-250 for gear clicks, 600 for collision bank entry 0x50, 0 for loops'
            },
        )
        pitch_offset = (
            IntegerBlock(length=4, is_signed=True),
            {
                'description': 'Base pitch offset in cents, added to every pitch the voice plays at (see '
                '`random_range`, `bend_range_semitones`). 0 in all TNFS banks'
            },
        )
        priority = (IntegerBlock(length=1), {'description': 'Playback priority'})
        unk3 = (IntegerBlock(length=1), {'is_unknown': True})
        unk4 = (
            IntegerBlock(length=1, is_signed=True),
            {
                'is_unknown': True,
                'description': 'Read by no binary (DOS voice start, DOS driver code, Win95 SE voice start 0x48eed8): '
                'meaning unknown. 0 in most entries; -5, -6, -12 and 2 in some collision bank entries',
            },
        )
        bend_range_semitones = (
            IntegerBlock(length=1),
            {
                'description': 'Pitch bend range in semitones. The game plays a sample at pitch value 0..127 '
                '(64 = original pitch). Every pitch set computes cents = (value - 64) * bend_range_semitones * 100 / '
                '64 + the pitch offset of the voice (`pitch_offset` + random, see `random_range`), the playback rate '
                'is the base rate * 2 ^ (cents / 1200) (DOS 0xa6fbd, table 0xa5470)'
            },
        )
        pan = (IntegerBlock(length=1), {'description': 'Pan, 0..127, 64 is center'})
        volume = (
            IntegerBlock(length=1),
            {
                'description': 'Volume, 0..127, with a random +-`random_volume_range`. The final volume is master '
                'volume * entry volume * channel volume / 127^2'
            },
        )
        random_volume_range = (
            IntegerBlock(length=1),
            {
                'description': 'Random volume range: the volume is `volume` +- a random value up to it. 0 in all TNFS banks'
            },
        )
        driver = (IntegerBlock(length=1), {'description': 'Sound driver of the sample. 0 or 0x0a in TNFS banks'})
        flags = (
            BitFlagsBlock(length=1, flag_names=[(0, 'stereo_pair')]),
            {
                'description': 'Bit 0: stereo pair, the next sample of the bank is the other channel (`*3D` / `*3` '
                'banks: collision bank 0x30-0x3a even entries and 0x3f, opponent bank 0x43 and 0x45)'
            },
        )
        unk5 = (BytesBlock(length=11), {'is_unknown': True})
        eacs_header = (
            EacsAudioHeader(),
            {
                'description': 'EACS header. Its `wave_data_offset` points into the wave data region of the '
                'sound bank file'
            },
        )


class EacsAudioFile(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A file with single EACS audio entry',
            'custom_actions': [
                {
                    'method': 'silence',
                    'title': 'Silence',
                    'description': 'Makes this audio sample completely silent',
                    'is_pure': False,
                    'args': [],
                }
            ],
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        header = (EacsAudioHeader(), {'description': 'EACS header: sampling rate, resolution, channels, loop settings'})
        offset = (Padding(to=lambda ctx: ctx.data('header/wave_data_offset'), is_global=True), {'is_unknown': True})
        wave_data = (
            BytesBlock(
                length=(
                    lambda ctx: min(
                        ctx.read_bytes_remaining,
                        ctx.data('header/wave_data_length') * ctx.data('header/sound_resolution'),
                    ),
                    'min(`remaining file bytes`, `header.wave_data_length` * `header.sound_resolution`)',
                )
            ),
            {
                'description': 'Wave data is here. If header.sound_resolution == 1, contains signed bytes, '
                'else - unsigned'
            },
        )

    def serializer_class(self):
        from serializers import EacsAudioSerializer

        return EacsAudioSerializer

    def action_silence(self, read_data, **kwargs):
        read_data['wave_data'] = b'\x00' * len(read_data['wave_data'])


class AsfAudio(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'An audio file, which is supported by FFMPEG and can be converted using only it. '
            'Has some explanation [here](https://wiki.multimedia.cx/index.php/Electronic_'
            'Arts_Formats_(2))',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('1SNh'), length=4), {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=8), {'is_unknown': True})
        sampling_rate = (IntegerBlock(length=4), {'description': 'Sampling rate of audio'})
        sound_resolution = (IntegerBlock(length=1), {'description': 'How many bytes in one wave data entry'})
        channels = (IntegerBlock(length=1), {'description': 'Channels amount. 1 is mono, 2 is stereo'})
        compression = (
            IntegerBlock(length=1),
            {
                'description': 'If equals to 2, wave data is compressed with [IMA ADPCM codec]('
                'https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)'
                '#IMA_ADPCM_Decompression_Algorithm)'
            },
        )
        unk1 = (IntegerBlock(length=1), {'is_unknown': True})
        wave_data_length = (
            IntegerBlock(length=4),
            {
                'description': 'Amount of wave data entries. Should be multiplied by '
                'sound_resolution to calculated the size of data in bytes'
            },
        )
        repeat_loop_beginning = (
            IntegerBlock(length=4),
            {
                'description': 'When audio ends, it repeats in loop from here. Should be '
                'multiplied by sound_resolution to calculate offset in bytes'
            },
        )
        repeat_loop_length = (
            IntegerBlock(length=4),
            {
                'description': 'If play audio in loop, at this point we should rewind to repeat_'
                'loop_beginning. Should be multiplied by sound_resolution to '
                'calculate offset in bytes'
            },
        )
        wave_data_offset = (
            IntegerBlock(length=4),
            {'description': 'Offset of wave data start in current file, relative to start of the file itself'},
        )
        unk2 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (
            Padding(to=(lambda ctx: ctx.data('wave_data_offset') + 40, 'wave_data_offset + 40')),
            {'description': 'Padding between the header and wave data'},
        )
        wave_data = (
            BytesBlock(
                length=(
                    lambda ctx: min(
                        ctx.read_bytes_remaining, ctx.data('wave_data_length') * ctx.data('sound_resolution')
                    ),
                    'min(`remaining file bytes`, `wave_data_length` * `sound_resolution`)',
                )
            ),
            {'description': 'Wave data is here'},
        )

    def serializer_class(self):
        from serializers import FfmpegSupportedAudioSerializer

        return FfmpegSupportedAudioSerializer


EA_SOUND_PATCH_TAGS = [
    (0x06, 'priority'),
    (0x07, 'unk_0x07'),
    (0x08, 'release_envelope'),
    (0x09, 'playback_envelope'),
    (0x0A, 'bend_range_semitones'),
    (0x0B, 'bank_channels'),
    (0x0C, 'pan'),
    (0x0D, 'random_pan_range'),
    (0x0E, 'volume'),
    (0x0F, 'random_volume_range'),
    (0x10, 'detune'),
    (0x11, 'random_detune_range'),
    (0x12, 'unk_0x12'),
    (0x13, 'effect_bus'),
    (0x80, 'version'),
    (0x82, 'channels'),
    (0x83, 'codec'),
    (0x84, 'sampling_rate'),
    (0x85, 'num_samples'),
    (0x86, 'loop_start'),
    (0x87, 'loop_end'),
    (0x88, 'data_offset'),
    (0x89, 'data_offset_channel_2'),
    (0x8A, 'unk_0x8a'),
    (0x8B, 'unk_0x8b'),
    (0x8C, 'flags'),
    (0x91, 'unk_0x91'),
    (0x92, 'unk_0x92'),
    (0x93, 'unk_0x93'),
    (0xA0, 'codec_2'),
    (0xFC, 'padding'),
    (0xFD, 'info_start'),
    (0xFE, 'layer_end'),
    (0xFF, 'end'),
]
# tags without a value
EA_SOUND_PATCH_MARKERS = ['padding', 'info_start', 'layer_end', 'end']


def _ea_sound_patch_tag_count(ctx) -> int:
    """Amount of tags of the patch at the current buffer position, up to and including the end tag 0xFF"""
    start = ctx.buffer.tell()
    count = 0
    try:
        while True:
            tag = ctx.buffer.read(1)
            if not tag:
                return count
            count += 1
            if tag[0] == 0xFF:
                return count
            if tag[0] in (0xFC, 0xFD, 0xFE):
                continue
            length = ctx.buffer.read(1)
            if not length:
                return count
            ctx.buffer.seek(length[0], SEEK_CUR)
    finally:
        ctx.buffer.seek(start)


class EaSoundPatchTag(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A tag of EA sound patch: tag id, then (except for tags 0xFC-0xFF) the length of the '
            'value and the value, big endian unsigned. Tag meanings follow '
            '[vgmstream](https://github.com/vgmstream/vgmstream) (`ea_schl.c`), the ones named `unk_*` are not known',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        tag = (EnumByteBlock(enum_names=EA_SOUND_PATCH_TAGS), {'description': 'Tag id'})
        value_length = (
            OptionalBlock(
                IntegerBlock(length=1),
                criteria=(
                    lambda ctx: ctx.data('tag') not in EA_SOUND_PATCH_MARKERS,
                    'tag is not padding, info_start, layer_end or end',
                ),
            ),
            {'description': 'Length of value in bytes. 0 means value 0'},
        )
        value = (
            OptionalBlock(
                BytesBlock(length=(lambda ctx: ctx.data('value_length'), 'value_length')),
                criteria=(
                    lambda ctx: ctx.data('tag') not in EA_SOUND_PATCH_MARKERS,
                    'tag is not padding, info_start, layer_end or end',
                ),
            ),
            {'description': 'Value, big endian unsigned integer'},
        )

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        res = super().read(ctx, name, read_bytes_amount)
        if res['tag'] in EA_SOUND_PATCH_MARKERS:
            res['value_length'] = res['value'] = None
        else:
            res['value'] = int.from_bytes(res['value'], 'big')
        return res

    def _to_native(self, data):
        if data['tag'] in EA_SOUND_PATCH_MARKERS:
            return data
        data = deepcopy(data)
        data['value'] = int(data['value']).to_bytes(data['value_length'], 'big')
        return data

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return 1 if data['tag'] in EA_SOUND_PATCH_MARKERS else 2 + data['value_length']

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(self._to_native(data), ctx, name)


class EaSoundPatch(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA sound patch ("PT" header): a sound of a BNKl sound bank as a list of tags. '
            'Tags before `info_start` are playback settings (priority, volume, pan, pitch bend range...), tags '
            'after it describe the wave data: `num_samples`, `channels` (default 1), `sampling_rate` (default '
            '22050), loop sample indices `loop_start` and `loop_end` (inclusive; a sample loops when it has one of '
            'them, from 0 / up to the last sample when the other one is missing), `data_offset` (wave data offset '
            'from the start of the bank file) and the codec. Without the `version` tag, `codec` 7 is EA-XA ADPCM v1, '
            '9 is EA MicroTalk 10:1 (speech), no `codec` tag is 16-bit little endian PCM. With `version` 1, '
            '`codec_2` 8 is 16-bit little endian PCM, 9 is signed 8-bit PCM, no `codec_2` tag is EA-XA ADPCM v2. '
            'Stereo samples are interleaved. A sound can have several layers, played together, separated by the '
            '`layer_end` tag, each one with its own settings and wave data (NFS3 player car engines add a short '
            'mono loop to the stereo engine sample)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        platform_magic = (UTF8Block(length=2, value_validator=Eq('PT')), {'description': 'Patch header magic'})
        platform = (IntegerBlock(length=2), {'description': 'Platform id, 0 is PC'})
        tags = (
            ArrayBlock(child=EaSoundPatchTag(), length=(_ea_sound_patch_tag_count, 'up to and including tag "end"')),
            {'description': 'Tags'},
        )

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        tag_block = self.field_blocks_map['tags'].child
        return 4 + sum(tag_block.estimate_packed_size(x) for x in data['tags'])

    @staticmethod
    def layers(data) -> list:
        """Tags of every layer as a dict {tag name: value}"""
        res = [{}]
        for tag in data['tags']:
            if tag['tag'] == 'layer_end':
                res.append({})
            elif tag['tag'] not in EA_SOUND_PATCH_MARKERS:
                res[-1][tag['tag']] = tag['value']
        return res
