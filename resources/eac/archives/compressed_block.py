from io import BytesIO, SEEK_CUR
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import AutoDetectBlock, BytesBlock
from resources.eac.car_specs import CarAiAndCrashBody, PlayerCarPhysics
from .shpi_block import ShpiBlock


class EacCompressedBlock(AutoDetectBlock):
    def __init__(self, **kwargs):
        from resources.eac.geometries import CrpGeometry

        super().__init__(
            possible_blocks=[
                ShpiBlock(),
                CarAiAndCrashBody(),
                PlayerCarPhysics(),
                CrpGeometry(),
                BytesBlock(length=(lambda ctx: ctx.read_bytes_amount)),
            ],
            **kwargs,
        )

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'custom_actions': [
                {
                    'method': 'save_uncompressed',
                    'title': 'Save uncompressed data',
                    'description': 'Saved uncompressed binary data to a new file',
                    'is_pure': True,
                    'args': [
                        {
                            'id': 'file_path',
                            'title': 'File path',
                            'type': 'file_output',
                            'file_name_suffix': '_uncompressed',
                        }
                    ],
                }
            ],
        }

    @staticmethod
    def _compression_for_header(flags: int, magic: int = 0xFB) -> 'BaseCompressionAlgorithm':
        if magic == 0xFB and (flags & 0b1111_1110) == 0x10:
            from resources.eac.compressions.ref_pack import RefPackCompression

            return RefPackCompression()
        elif magic == 0xFB and (flags & 0b1111_1110) == 0x46:
            from resources.eac.compressions.qfs2 import Qfs2Compression

            return Qfs2Compression()
        elif magic == 0xFB and (flags & 0b1111_1110) in [0x30, 0x32, 0x34]:
            from resources.eac.compressions.qfs3 import Qfs3Compression

            return Qfs3Compression()
        else:
            raise ValueError(f'Unknown compression algorithm: {flags:02x} {magic:02x}')

    def _detect_compression(self, buffer) -> 'BaseCompressionAlgorithm':
        header_bytes = buffer.read(2)
        buffer.seek(-2, SEEK_CUR)
        return self._compression_for_header(header_bytes[0], header_bytes[1])

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        flags = ctx.buffer.read(1)[0]
        ctx.buffer.seek(-1, SEEK_CUR)
        compression = self._detect_compression(ctx.buffer)
        uncompressed_bytes = compression.uncompress(ctx.buffer, read_bytes_amount)
        uncompressed = BytesIO(uncompressed_bytes)
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount)
        self_ctx.buffer = uncompressed
        self_ctx.read_bytes_amount = len(uncompressed_bytes)
        res = super().read(ctx=self_ctx, name='uncompressed', read_bytes_amount=len(uncompressed_bytes))
        # written back with the same algorithm: not every game is known to read every algorithm
        res['compression_flags'] = flags
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        uncompressed_bytes = super().write(data, ctx, name)
        # new data: QFS2, which TNFS reads
        flags = data.get('compression_flags', 0x46)
        compression = self._compression_for_header(flags)
        from resources.eac.compressions.qfs3 import Qfs3Compression

        if isinstance(compression, Qfs3Compression):
            # same delta coding as the original
            return compression.compress(
                BytesIO(uncompressed_bytes), len(uncompressed_bytes), delta_passes=((flags >> 1) & 3,)
            )
        return compression.compress(BytesIO(uncompressed_bytes), len(uncompressed_bytes))

    def action_save_uncompressed(self, read_data, file_path, **kwargs):
        inner_block = self.possible_blocks[read_data['choice_index']]
        res = inner_block.write(read_data['data'])
        with open(file_path, 'wb') as f:
            f.write(res)
