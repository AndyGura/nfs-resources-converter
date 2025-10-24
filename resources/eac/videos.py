from typing import Dict

from library.context import WriteContext, ReadContext
from library.exceptions import BlockDefinitionException
from library.read_blocks import DataBlock


class FfmpegSupportedVideo(DataBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A video file, which is supported by FFMPEG and can be converted using only it'}

    def serializer_class(self):
        from serializers import FfmpegSupportedVideoSerializer
        return FfmpegSupportedVideoSerializer

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        return name

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        raise BlockDefinitionException(ctx=ctx, message='Ffmpeg video cannot be written as data block')
