import subprocess
from os import remove
from random import choice
from string import ascii_lowercase
from wave import Wave_write

import settings
from library.read_data import ReadData
from library.utils import audio_ima_adpcm_codec
from resources.eac.audios import EacsAudio, AsfAudio
from serializers import BaseFileSerializer
import json


class EacsAudioSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[EacsAudio], path: str):
        super().serialize(data, path)
        wave_bytes = data.wave_data.value
        if data.compression == 2:
            wave_bytes = audio_ima_adpcm_codec.decode_block(wave_bytes, data.channels.value)
        else: 
            # signed
            if data.sound_resolution == 1:
                wav = list()
                for i in range(len(wave_bytes)):
                    wav.append(int.from_bytes(wave_bytes[i:i+1], byteorder='little', signed=True) + 128)
                wave_bytes = bytes(wav)
            # unsigned
            else:
                wave_bytes = wave_bytes
        loop_start_time_ms = 1000 * data.repeat_loop_beginning.value / data.sampling_rate.value
        loop_end_time_ms = loop_start_time_ms + 1000 * (data.repeat_loop_length.value - 1) / data.sampling_rate.value
        loop_wave_data = None
        if settings.audio__save_car_sfx_loops:
            try:
                # if car sound bank
                if 'SW.BNK' in data.id or 'TRAFFC.BNK' in data.id or 'TESTBANK.BNK' in data.id:
                    # aligning to channels. If not do that, some samples keep changing channels every loop
                    beginning = data.sound_resolution.value * int(data.repeat_loop_beginning.value / data.channels.value) * data.channels.value
                    ending = data.sound_resolution.value * int((data.repeat_loop_beginning.value + data.repeat_loop_length.value) / data.channels.value) * data.channels.value
                    loop_wave_data = wave_bytes[beginning:ending] * 16
            except:
                pass
        self._save_wave_data(data, wave_bytes, path)
        if loop_wave_data:
            self._save_wave_data(data, loop_wave_data, f"{path}_loop")
        with open(f'{path}.meta.json', 'w') as file:
            file.write(json.dumps({
                "loop_start_time_ms": loop_start_time_ms,
                "loop_end_time_ms": loop_end_time_ms
            }, indent=4))

    def _save_wave_data(self, eacs_block, wave_data, path):
        temp_wav_file = '/tmp/' + ''.join(choice(ascii_lowercase) for i in range(12)) + '.wav'
        with open(temp_wav_file, 'w+b') as file:
            try:
                wave = Wave_write(file)
                wave.setnchannels(eacs_block.channels.value)
                wave.setsampwidth(eacs_block.sound_resolution.value)
                wave.setframerate(eacs_block.sampling_rate.value)
                wave.writeframesraw(wave_data)
                wave.close()
                subprocess.run([settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", temp_wav_file, f'{path}.mp3'], check=True)
            except Exception as ex:
                raise ex
            finally:
                remove(temp_wav_file)


class FfmpegSupportedAudioSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[AsfAudio], path: str):
        super().serialize(data, path)
        subprocess.run([settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", data.id, f'{path}.mp3'], check=True)
        with open(f'{path}.meta.json', 'w') as file:
            loop_start_time_ms = 1000 * data.repeat_loop_beginning.value / data.sampling_rate.value
            loop_end_time_ms = loop_start_time_ms + 1000 * data.repeat_loop_length.value / data.sampling_rate.value
            file.write(json.dumps({
                    "loop_start_time_ms": loop_start_time_ms,
                    "loop_end_time_ms": loop_end_time_ms
                }, indent=4))
