import subprocess

import settings
from resources.eac.videos import FfmpegSupportedVideo
from serializers import BaseFileSerializer


class FfmpegSupportedVideoSerializer(BaseFileSerializer):

    def serialize(self, block: FfmpegSupportedVideo, path: str):
        super().serialize(block, path)
        if not settings.save_media_files:
            return
        subprocess.run([settings.ffmpeg_executable, "-y", "-nostats", '-loglevel', '0', "-i", block.file_path,
                        # add video on black square so we will not have transparent pixels (displays wrong in chrome)
                        '-filter_complex',
                        'color=black,format=rgb24[c];[c][0]scale2ref[c][i];[c][i]overlay=format=auto:shortest=1,setsar=1',
                        "-c:v", "libx264",
                        "-c:a", "mp3",
                        "-vprofile", "main",
                        "-pix_fmt", "yuv420p",
                        f'{path}.mp4'], check=True)
