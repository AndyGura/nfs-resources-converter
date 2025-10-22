import json
import subprocess
import wave

from config import general_config
from library.utils import audio_ima_adpcm_codec
from serializers import BaseFileSerializer


class EacsAudioSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        wave_bytes = data['wave_data']
        if data['header']['compression'] == 2:
            wave_bytes = audio_ima_adpcm_codec.decode_block(wave_bytes, data['header']['channels'])
        else:
            # signed
            if data['header']['sound_resolution'] == 1:
                wav = list()
                for i in range(len(wave_bytes)):
                    wav.append(int.from_bytes(wave_bytes[i:i + 1], byteorder='little', signed=True) + 128)
                wave_bytes = bytes(wav)
            # unsigned
            else:
                wave_bytes = wave_bytes
        loop_start_time_ms = 1000 * data['header']['repeat_loop_beginning'] / data['header']['sampling_rate']
        loop_end_time_ms = loop_start_time_ms + 1000 * (data['header']['repeat_loop_length'] - 1) / data['header'][
            'sampling_rate']
        self._save_wave_data(data['header'], wave_bytes, path)
        with open(f'{path}.meta.json', 'w') as file:
            file.write(json.dumps({
                "loop_start_time_ms": loop_start_time_ms,
                "loop_end_time_ms": loop_end_time_ms
            }, indent=4))

    def _save_wave_data(self, eacs_header, wave_data, path):
        with wave.open(f'{path}.wav', "w") as wf:
            wf.setnchannels(eacs_header['channels'])
            wf.setsampwidth(eacs_header['sound_resolution'])
            wf.setframerate(eacs_header['sampling_rate'])
            wf.writeframesraw(wave_data)


class FfmpegSupportedAudioSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        subprocess.run(
            [general_config().ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", id, f'{path}.wav'],
            check=True)
        with open(f'{path}.meta.json', 'w') as file:
            loop_start_time_ms = 1000 * data['repeat_loop_beginning'] / data['sampling_rate']
            loop_end_time_ms = loop_start_time_ms + 1000 * data['repeat_loop_length'] / data['sampling_rate']
            file.write(json.dumps({
                "loop_start_time_ms": loop_start_time_ms,
                "loop_end_time_ms": loop_end_time_ms
            }, indent=4))
