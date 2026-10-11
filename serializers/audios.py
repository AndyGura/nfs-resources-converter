import json
import subprocess
import traceback
import wave
from typing import List, Dict, Tuple

from config import general_config
from library.utils import audio_ima_adpcm_codec, audio_ea_xa_codec, format_exception, path_join
from serializers import BaseFileSerializer


class EacsAudioSerializer(BaseFileSerializer):
    def serialize(self, data: dict, path: str, id=None, block=None, meta: dict = None, **kwargs) -> List[str]:
        super().serialize(data, path)
        wave_bytes = data['wave_data']
        if data['header']['compression'] == 2:
            wave_bytes = audio_ima_adpcm_codec.decode_block(wave_bytes, data['header']['channels'])
        else:
            # signed
            if data['header']['sound_resolution'] == 1:
                wav = list()
                for i in range(len(wave_bytes)):
                    wav.append(int.from_bytes(wave_bytes[i : i + 1], byteorder='little', signed=True) + 128)
                wave_bytes = bytes(wav)
            # unsigned
            else:
                wave_bytes = wave_bytes
        loop_start_time_ms = 1000 * data['header']['repeat_loop_beginning'] / data['header']['sampling_rate']
        loop_end_time_ms = (
            loop_start_time_ms + 1000 * (data['header']['repeat_loop_length'] - 1) / data['header']['sampling_rate']
        )
        self._save_wave_data(data['header'], wave_bytes, path)
        with open(f'{path}.meta.json', 'w') as file:
            file.write(
                json.dumps(
                    {
                        'loop': data['header']['repeat_loop_length'] > 0,
                        'loop_start_time_ms': loop_start_time_ms,
                        'loop_end_time_ms': loop_end_time_ms,
                        **(meta or {}),
                    },
                    indent=4,
                )
            )
        return [f'{path}.wav', f'{path}.meta.json']

    def _save_wave_data(self, eacs_header, wave_data, path):
        with wave.open(f'{path}.wav', 'w') as wf:
            wf.setnchannels(eacs_header['channels'])
            wf.setsampwidth(eacs_header['sound_resolution'])
            wf.setframerate(eacs_header['sampling_rate'])
            wf.writeframesraw(wave_data)


class FfmpegSupportedAudioSerializer(BaseFileSerializer):
    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        wav_path = f'{path}.wav'
        meta_path = f'{path}.meta.json'
        subprocess.run(
            [general_config().ffmpeg_executable, '-y', '-nostats', '-loglevel', '0', '-i', id, wav_path], check=True
        )
        with open(meta_path, 'w') as file:
            loop_start_time_ms = 1000 * data['repeat_loop_beginning'] / data['sampling_rate']
            loop_end_time_ms = loop_start_time_ms + 1000 * data['repeat_loop_length'] / data['sampling_rate']
            file.write(
                json.dumps(
                    {
                        'loop': data['repeat_loop_length'] > 0,
                        'loop_start_time_ms': loop_start_time_ms,
                        'loop_end_time_ms': loop_end_time_ms,
                    },
                    indent=4,
                )
            )
        return [wav_path, meta_path]


def decode_ea_sound_patch_layer(layer: Dict, wave_data: bytes) -> Tuple[bytes, int, int]:
    """Wave data of a layer of `EaSoundPatch` as (PCM bytes, sample width in bytes, channels). 8-bit PCM is unsigned,
    16-bit is signed little endian, as in WAV files"""
    channels = layer.get('channels', 1)
    num_samples = layer['num_samples']
    if layer.get('version', 0) == 0:
        codec = layer.get('codec')
        if codec is None:
            return wave_data[: num_samples * channels * 2], 2, channels
        if codec == 7:
            frames = (num_samples + 27) // 28
            return (
                audio_ea_xa_codec.decode_v1(wave_data[: frames * 0x0F * channels], channels, num_samples),
                2,
                channels,
            )
        raise NotImplementedError(f'Unsupported codec {codec}' + (' (EA MicroTalk)' if codec == 9 else ''))
    codec = layer.get('codec_2')
    if codec == 8:
        return wave_data[: num_samples * channels * 2], 2, channels
    if codec == 9:
        return bytes((x + 128) & 0xFF for x in wave_data[: num_samples * channels]), 1, channels
    if codec is None and channels == 1:
        return audio_ea_xa_codec.decode_v2(wave_data, num_samples), 2, channels
    raise NotImplementedError(f'Unsupported codec {codec} with {channels} channels, header version {layer["version"]}')


class EaSoundBankSerializer(BaseFileSerializer):
    """Every layer of every sound to `<index>.wav` + `<index>.meta.json` (`<index>_layer_<n>` for the second and next
    layers of a sound), index in hex as in TNFS sound banks"""

    # tags, which describe wave data and are not needed next to a wav file
    WAVE_DATA_TAGS = ['data_offset', 'data_offset_channel_2', 'unk_0x8a', 'codec', 'codec_2', 'version']

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        patch_block = block.field_blocks_map['items'].child
        output = []
        skipped = []
        for index, item in zip(block.item_indices(data), data['items']):
            for layer_index, layer in enumerate(patch_block.layers(item)):
                name = hex(index) + (f'_layer_{layer_index}' if layer_index > 0 else '')
                try:
                    output.extend(self._serialize_layer(layer, block.wave_data(data, layer), path_join(path, name)))
                except Exception as ex:
                    traceback.print_exc()
                    skipped.append((name, format_exception(ex)))
        if skipped:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped:
                    f.write('%s\t\t%s\n' % item)
            output.append(path_join(path, 'skipped.txt'))
        return output

    def _serialize_layer(self, layer: Dict, wave_data: bytes, path: str) -> List[str]:
        pcm, sample_width, channels = decode_ea_sound_patch_layer(layer, wave_data)
        sampling_rate = layer.get('sampling_rate', 22050)
        num_samples = layer['num_samples']
        with wave.open(f'{path}.wav', 'w') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sampling_rate)
            wf.writeframesraw(pcm)
        is_loop = 'loop_start' in layer or 'loop_end' in layer
        loop_start = layer.get('loop_start', 0)
        loop_end = layer.get('loop_end', num_samples - 1)
        meta = {
            'loop': is_loop,
            'loop_start_time_ms': 1000 * loop_start / sampling_rate if is_loop else 0,
            'loop_end_time_ms': 1000 * loop_end / sampling_rate
            if is_loop
            else 1000 * (num_samples - 1) / sampling_rate,
            **{k: v for k, v in layer.items() if k not in self.WAVE_DATA_TAGS},
        }
        with open(f'{path}.meta.json', 'w') as file:
            file.write(json.dumps(meta, indent=4))
        return [f'{path}.wav', f'{path}.meta.json']
