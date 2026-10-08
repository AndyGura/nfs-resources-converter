from io import BytesIO
from typing import Dict

from library.read_blocks import BytesBlock
from resources.eac.archives import EacCompressedBlock


class NfsuJdlzCompressedBlock(EacCompressedBlock):
    """JDLZ-compressed file of NFS Underground (*.lzc). Uncompressed data is usually a chunk bundle"""

    def __init__(self, **kwargs):
        from resources.blackbox.maps.nfsu import NfsuChunkBundle, NfsuTrackBundle

        super(EacCompressedBlock, self).__init__(
            possible_blocks=[
                NfsuTrackBundle(),
                NfsuChunkBundle(),
                BytesBlock(length=(lambda ctx: ctx.read_bytes_amount)),
            ],
            **kwargs,
        )

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'JDLZ-compressed data (LZ77 variant with "JDLZ" header): NFS Underground *.lzc files',
        }

    def _detect_compression(self, buffer):
        from resources.eac.compressions.jdlz import JdlzCompression

        return JdlzCompression()

    def compress(self, uncompressed_bytes: bytes) -> bytes:
        from resources.eac.compressions.jdlz import JdlzCompression

        return JdlzCompression().compress(BytesIO(uncompressed_bytes), len(uncompressed_bytes))
