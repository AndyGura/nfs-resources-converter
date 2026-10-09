from io import BufferedReader, BytesIO

from resources.eac.compressions.base import BaseCompressionAlgorithm
from resources.eac.compressions.qfs3 import Qfs3Compression


class HuffCompression(BaseCompressionAlgorithm):
    """
    HUFF: QFS3 Huffman stream behind a 16-byte header. Used by NFSU2 for some textures of compressed texture packs.

    Layout (little-endian):
        4 bytes  "HUFF"
        u8       1
        u8       0x10 (header length)
        u16      0
        u32      uncompressed size
        u32      compressed size (header excluded)
        ...      QFS3 stream (0x30FB header), see Qfs3Compression
    """

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int) -> bytes:
        data = buffer.read(input_length) if input_length is not None else buffer.read()
        if data[:4] != b'HUFF' or len(data) < 16:
            raise ValueError('Invalid HUFF header')
        uncompressed_size = int.from_bytes(data[8:12], 'little')
        compressed_size = int.from_bytes(data[12:16], 'little')
        payload = data[16 : 16 + compressed_size]
        out = Qfs3Compression().uncompress(BytesIO(payload), len(payload))
        if len(out) != uncompressed_size:
            raise ValueError(f'HUFF: expected length {uncompressed_size}, actual length: {len(out)}')
        return out

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int) -> bytes:
        data = bytes(buffer.read(input_length))
        # delta-coded QFS3 streams are not known to be used (nor checked in the game) behind a HUFF header
        payload = Qfs3Compression().compress(BytesIO(data), len(data), delta_passes=(0,))
        return b'HUFF\x01\x10\x00\x00' + len(data).to_bytes(4, 'little') + len(payload).to_bytes(4, 'little') + payload
