from io import BytesIO, SEEK_CUR
from os.path import getsize
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (AutoDetectBlock,
                                 BytesBlock)
from resources.eac.car_specs import CarSimplifiedPerformanceSpec, CarPerformanceSpec
from .shpi_block import ShpiBlock


class EacCompressedBlock(AutoDetectBlock):

    def __init__(self, **kwargs):
        from resources.eac.geometries import CrpGeometry
        super().__init__(possible_blocks=[ShpiBlock(),
                                          CarSimplifiedPerformanceSpec(),
                                          CarPerformanceSpec(),
                                          CrpGeometry(),
                                          BytesBlock(length=(lambda ctx: ctx.read_bytes_amount))],
                         **kwargs)

    @property
    def schema(self) -> Dict:
        return {**super().schema,
            'custom_actions': [
                {
                    'method': 'save_uncompressed',
                    'title': 'Save uncompressed data',
                    'description': 'Saved uncompressed binary data to a new file',
                    'is_pure': True,
                    'args': [
                        {'id': 'file_path', 'title': 'File path', 'type': 'file_output',
                         'file_name_suffix': '_uncompressed'}
                    ],
                }
            ]}

    def _detect_compression(self, buffer) -> 'BaseCompressionAlgorithm':
        header_bytes = buffer.read(2)
        buffer.seek(-2, SEEK_CUR)
        if header_bytes[1] == 0xfb and (header_bytes[0] & 0b1111_1110) == 0x10:
            from resources.eac.compressions.ref_pack import RefPackCompression
            return RefPackCompression()
        elif header_bytes[1] == 0xfb and header_bytes[0] == 0b0100_0110:
            from resources.eac.compressions.qfs2 import Qfs2Compression
            return Qfs2Compression()
        elif header_bytes[1] == 0xfb and header_bytes[0] in [0b0011_0000, 0b0011_0010, 0b0011_0100, 0b0011_0001,
                                                             0b0011_0011,
                                                             0b0011_0101]:
            from resources.eac.compressions.qfs3 import Qfs3Compression
            return Qfs3Compression()
        else:
            raise ValueError(f'Unknown compression algorithm: {header_bytes[0]:02x} {header_bytes[1]:02x}')

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        compression = self._detect_compression(ctx.buffer)
        uncompressed_bytes = compression.uncompress(ctx.buffer, read_bytes_amount)
        uncompressed = BytesIO(uncompressed_bytes)
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount)
        self_ctx.buffer = uncompressed
        self_ctx.read_bytes_amount = len(uncompressed_bytes)
        res = super().read(ctx=self_ctx, name='uncompressed', read_bytes_amount=len(uncompressed_bytes))
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        uncompressed_bytes = super().write(data, ctx, name)
        # NFS does not care which algorithm is used anyway
        from resources.eac.compressions.qfs2 import Qfs2Compression
        compression = Qfs2Compression()
        compressed = compression.compress(BytesIO(uncompressed_bytes), len(uncompressed_bytes))
        return compressed

    def action_save_uncompressed(self, name, file_path, **kwargs):
        # we do not store compressed buffer in the context, so read file again
        # FIXME it does not work at all:
        # 1) we treat resource id as file path (it contans things lie E---DRIVE/ on windows)
        # 2) qfs can be part of bigfblock, does not work again
        with open(name, 'rb', buffering=100 * 1024 * 1024) as bdata:
            compression = self._detect_compression(bdata)
            uncompressed_bytes = compression.uncompress(bdata, getsize(name))
            with open(file_path, 'wb') as f:
                f.write(uncompressed_bytes)
