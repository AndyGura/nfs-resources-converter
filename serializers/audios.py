import subprocess
from os import remove
from random import choice
from string import ascii_lowercase
from wave import Wave_write

import settings
from parsers.resources.codecs import audio_ima_adpcm_codec
from resources.eac.audios import EacsAudio, AsfAudio
from serializers import BaseFileSerializer
import json


class EacsAudioSerializer(BaseFileSerializer):

    def serialize(self, block: EacsAudio, path: str):
        super().serialize(block, path)
        if not settings.save_media_files:
            return
        wave_bytes = block.wave_data
        if block.compression == 2:
            wave_bytes = audio_ima_adpcm_codec.decode_block(block.wave_data, block.channels)
        else:
            # signed
            if block.sound_resolution == 1:
                wav = list()
                for i in range(len(wave_bytes)):
                    wav.append(int.from_bytes(wave_bytes[i:i+1], byteorder='little', signed=True) + 128)
                wave_bytes = bytes(wav)
            # unsigned
            else:
                wave_bytes = wave_bytes
        loop_start_time_ms = 1000 * block.repeat_loop_beginning / block.sampling_rate
        loop_end_time_ms = loop_start_time_ms + 1000 * (block.repeat_loop_length - 1) / block.sampling_rate
        loop_wave_data = None
        if settings.audio__save_car_sfx_loops:
            try:
                # if car sound bank
                if 'SW.BNK' in block.id or 'TRAFFC.BNK' in block.id or 'TESTBANK.BNK':
                    # not sure why * 2. It is needed for stereo but also for car honk sample (mono)
                    loop_wave_data = wave_bytes[block.repeat_loop_beginning * 2:(block.repeat_loop_beginning + block.repeat_loop_length) * 2] * 16
            except:
                pass
        self._save_wave_data(block, wave_bytes, path)
        if loop_wave_data:
            self._save_wave_data(block, loop_wave_data, f"{path}_loop")
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
                wave.setnchannels(eacs_block.channels)
                wave.setsampwidth(eacs_block.sound_resolution)
                wave.setframerate(eacs_block.sampling_rate)
                wave.writeframesraw(wave_data)
                wave.close()
                subprocess.run([settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", temp_wav_file, f'{path}.mp3'], check=True)
                remove(temp_wav_file)
            except Exception as ex:
                remove(f'{path}.wav')
                raise ex


class FfmpegSupportedAudioSerializer(BaseFileSerializer):

    def serialize(self, block: AsfAudio, path: str):
        super().serialize(block, path)
        if not settings.save_media_files:
            return
        subprocess.run([settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", block.file_path, f'{path}.mp3'], check=True)
        with open(f'{path}.meta.json', 'w') as file:
            loop_start_time_ms = 1000 * block.repeat_loop_beginning / block.sampling_rate
            loop_end_time_ms = loop_start_time_ms + 1000 * block.repeat_loop_length / block.sampling_rate
            file.write(json.dumps({
                    "loop_start_time_ms": loop_start_time_ms,
                    "loop_end_time_ms": loop_end_time_ms
                }, indent=4))
