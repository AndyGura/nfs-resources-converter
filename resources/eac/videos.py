import os
from typing import Dict, List, Optional

from library.context import BaseContext, WriteContext, ReadContext
from library.exceptions import BlockDefinitionException
from library.read_blocks import DataBlock


class FfmpegSupportedVideo(DataBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A video file, which is supported by FFMPEG and can be converted using only it',
        }

    def get_target_games(self, data, ctx: BaseContext) -> Optional[List[str]]:
        # by the file extension (data is the file name): other EA streams (ASF music, AST speech...) are in many games
        extension = os.path.splitext(data)[1].upper() if isinstance(data, str) else ''
        return {'.TGV': ['tnfs'], '.UV': ['nfs2', 'nfs2_se']}.get(extension)

    def serializer_class(self):
        from serializers import FfmpegSupportedVideoSerializer

        return FfmpegSupportedVideoSerializer

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        return name

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        raise BlockDefinitionException(ctx=ctx, message='Ffmpeg video cannot be written as data block')
