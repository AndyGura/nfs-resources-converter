import json
import os
import subprocess
import tempfile
from wave import Wave_write

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
        loop_wave_data = None
        if self.settings.audio__save_car_sfx_loops:
            try:
                # if car sound bank
                if 'SW.BNK' in id or 'TRAFFC.BNK' in id or 'TESTBANK.BNK' in id:
                    # aligning to channels. If not do that, some samples keep changing channels every loop
                    beginning = data['header']['sound_resolution'] * int(
                        data['header']['repeat_loop_beginning'] / data['header']['channels']) * data['header'][
                                    'channels']
                    ending = (data['header']['sound_resolution']
                              * int((data['header']['repeat_loop_beginning'] + data['header']['repeat_loop_length'])
                                    / data['header']['channels']) * data['header']['channels'])
                    loop_wave_data = wave_bytes[beginning:ending] * 16
            except Exception:
                pass
        self._save_wave_data(data['header'], wave_bytes, path)
        if loop_wave_data:
            self._save_wave_data(data['header'], loop_wave_data, f"{path}_loop")
        with open(f'{path}.meta.json', 'w') as file:
            file.write(json.dumps({
                "loop_start_time_ms": loop_start_time_ms,
                "loop_end_time_ms": loop_end_time_ms
            }, indent=4))

    def _save_wave_data(self, eacs_header, wave_data, path):
        file = tempfile.NamedTemporaryFile(mode='w+b', suffix='.wav', delete=False)
        try:
            wave = Wave_write(file)
            wave.setnchannels(eacs_header['channels'])
            wave.setsampwidth(eacs_header['sound_resolution'])
            wave.setframerate(eacs_header['sampling_rate'])
            wave.writeframesraw(wave_data)
            wave.close()
            args = [self.settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i",
                    file.name.replace('\\', '/'),
                    f'{path}.mp3']
            subprocess.run(args, check=True)
        except Exception as ex:
            raise ex
        finally:
            file.close()
            os.remove(file.name)


class FfmpegSupportedAudioSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        subprocess.run(
            [self.settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", id, f'{path}.mp3'],
            check=True)
        with open(f'{path}.meta.json', 'w') as file:
            loop_start_time_ms = 1000 * data['repeat_loop_beginning'] / data['sampling_rate']
            loop_end_time_ms = loop_start_time_ms + 1000 * data['repeat_loop_length'] / data['sampling_rate']
            file.write(json.dumps({
                "loop_start_time_ms": loop_start_time_ms,
                "loop_end_time_ms": loop_end_time_ms
            }, indent=4))
