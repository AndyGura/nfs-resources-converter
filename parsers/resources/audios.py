import json
import subprocess
from io import BufferedReader, SEEK_CUR
from os import remove
from random import choice
from string import ascii_lowercase
from wave import Wave_write

import settings
from buffer_utils import read_utf_bytes, read_int, read_byte, read_signed_byte
from parsers.resources.base import BaseResource
from parsers.resources.codecs import audio_ima_adpcm_codec


class ASFAudio(BaseResource):
    loop_start_time_ms = 0
    loop_end_time_ms = 0

    def read(self, buffer: BufferedReader, length: int, path=None) -> int:
        if not settings.save_media_files:
            return length
        self.path = path
        type_annotation = read_utf_bytes(buffer, 4)
        if type_annotation != '1SNh':
            raise NotImplementedError('Support only EACS files starting with 1SNh block')
        # block_size(4), header block + ID string(4)
        buffer.seek(8, SEEK_CUR)
        sampling_rate = read_int(buffer)
        # sound_resolution(1) + channels(1) + compression(1) + type(1) + wave_data_length(4)
        buffer.seek(8, SEEK_CUR)
        repeat_loop_beginning = read_int(buffer)
        repeat_loop_length = read_int(buffer)
        self.loop_start_time_ms = 1000 * repeat_loop_beginning / sampling_rate
        self.loop_end_time_ms = self.loop_start_time_ms + 1000 * repeat_loop_length / sampling_rate
        return length

    def save_converted(self, path: str):
        if not settings.save_media_files:
            return
        subprocess.run(["ffmpeg", "-y", "-i", self.path, f'{path}.mp3'], check=True)
        with open(f'{path}.meta.json', 'w') as file:
            file.write(json.dumps({
                "loop_start_time_ms": self.loop_start_time_ms,
                "loop_end_time_ms": self.loop_end_time_ms
            }, indent=4))


class EacsAudio(BaseResource):
    loop_start_time_ms = 0
    loop_end_time_ms = 0
    wave_data = None
    loop_wave_data = None

    # TODO RX7 engine off sounds wrong: plays in one channel than in another. Doesn't happen in real game
    def read(self, buffer: BufferedReader, length: int, path=None) -> int:
        if not settings.save_media_files:
            return length
        self.wave_data = b""
        buffer.seek(4, SEEK_CUR)  # header block + ID string
        self.sampling_rate = read_int(buffer)
        self.sound_resolution = read_byte(buffer)
        self.channels = read_byte(buffer)
        self.compression = read_byte(buffer)
        buffer.seek(1, SEEK_CUR)  # type
        wave_data_length = read_int(buffer)
        repeat_loop_beginning = read_int(buffer)
        repeat_loop_length = read_int(buffer)
        wave_data_offset = read_int(buffer)
        buffer.seek(wave_data_offset)
        wave_bytes = []
        if self.compression == 2:
            self.wave_data = audio_ima_adpcm_codec.decode_block(buffer.read(length - 32), self.channels)
        else:
            # signed
            if self.sound_resolution == 1:
                for i in range(0, wave_data_length):
                    x = read_signed_byte(buffer)
                    wave_bytes.append(x + 128)
                self.wave_data = bytes(wave_bytes)
            # unsigned
            else:
                self.wave_data = buffer.read(wave_data_length * self.sound_resolution)
        self.loop_start_time_ms = 1000 * repeat_loop_beginning / (self.sampling_rate)
        self.loop_end_time_ms = self.loop_start_time_ms + 1000 * (repeat_loop_length - 1) / self.sampling_rate
        if settings.audio__save_car_sfx_loops:
            try:
                if self.parent.is_car_soundbank:
                    # not sure why * 2. It is needed for stereo but also for car honk sample (mono)
                    self.loop_wave_data = self.wave_data[repeat_loop_beginning * 2:(repeat_loop_beginning + repeat_loop_length) * 2] * 16
            except:
                pass
        return length

    def save_converted(self, path: str):
        if not settings.save_media_files:
            return
        self._save_wave_data(self.wave_data, path)
        if self.loop_wave_data:
            self._save_wave_data(self.loop_wave_data, f"{path}_loop")
        with open(f'{path}.meta.json', 'w') as file:
            file.write(json.dumps({
                "loop_start_time_ms": self.loop_start_time_ms,
                "loop_end_time_ms": self.loop_end_time_ms
            }, indent=4))

    def _save_wave_data(self, wave_data, path):
        temp_wav_file = '/tmp/' + ''.join(choice(ascii_lowercase) for i in range(12)) + '.wav'
        with open(temp_wav_file, 'w+b') as file:
            try:
                wave = Wave_write(file)
                wave.setnchannels(self.channels)
                wave.setsampwidth(self.sound_resolution)
                wave.setframerate(self.sampling_rate)
                wave.writeframesraw(wave_data)
                wave.close()
                subprocess.run(["ffmpeg", "-y", "-i", temp_wav_file, f'{path}.mp3'], check=True)
                remove(temp_wav_file)
            except Exception as ex:
                remove(f'{path}.wav')
                raise ex
