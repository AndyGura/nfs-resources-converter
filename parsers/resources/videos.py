import subprocess
from io import BufferedReader

import settings
from parsers.resources.base import BaseResource


class FFmpegSupportedVideo(BaseResource):
    # I'm so happy it happened! ffmpeg supports codec by default

    def read(self, buffer: BufferedReader, length: int, path=None) -> int:
        self.path = path
        return length

    def save_converted(self, path: str):
        super().save_converted(path)
        if not settings.save_media_files:
            return
        subprocess.run([settings.ffmpeg_executable, "-y", "-i", self.path,
                        # add video on black square so we will not have transparent pixels (displays wrong in chrome)
                        '-filter_complex',
                        'color=black,format=rgb24[c];[c][0]scale2ref[c][i];[c][i]overlay=format=auto:shortest=1,setsar=1',
                        "-c:v", "libx264",
                        "-c:a", "mp3",
                        "-vprofile", "main",
                        "-pix_fmt", "yuv420p",
                        f'{path}.mp4'], check=True)
