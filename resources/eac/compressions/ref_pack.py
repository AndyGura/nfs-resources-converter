from io import BufferedReader, SEEK_CUR, BytesIO

from library.utils.buffer_utils import read_byte
from resources.eac.compressions.base import BaseCompressionAlgorithm


# http://wiki.niotso.org/RefPack
# https://www.wiki.sc4devotion.com/index.php?title=DBPF_Compression
class RefPackCompression(BaseCompressionAlgorithm):

    def _parse_archive_flags(self, flags_byte):
        # specifies that the decompressed field and (if applicable) the compressed size field are 4-byte fields;
        # if this flag is unset, both of these fields are 3-byte fields.
        long_file = bool(flags_byte & 0b1000_0000)
        contains_compressed_size = bool(flags_byte & 0b0000_0001)
        return long_file, contains_compressed_size

    def _copy_bytes_to_output(self, buffer, uncompressed: bytearray, length):
        uncompressed.extend(buffer.read(length))

    def _reuse_bytes_in_output(self, buffer, uncompressed: bytearray, length, offset):
        if length > offset:
            old_length = len(uncompressed)
            while len(uncompressed) < old_length + length:
                uncompressed.extend(uncompressed[-offset].to_bytes(1, byteorder='big'))
        elif offset == length:
            uncompressed.extend(uncompressed[-offset:])
        elif length > 0:
            uncompressed.extend(uncompressed[-offset:-offset + length])

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        uncompressed: bytearray = bytearray()
        use_4_bytes, contains_compressed_size = self._parse_archive_flags(read_byte(buffer))
        buffer.seek(1, SEEK_CUR)  # skip RefPack indicator 0xfb
        output_length = (read_byte(buffer) << 16) + (read_byte(buffer) << 8) + read_byte(buffer)
        bytes_used = 5
        if contains_compressed_size:
            buffer.seek(3, SEEK_CUR)
            bytes_used = 8
        pack_code = read_byte(buffer)
        bytes_used = bytes_used + 1
        last_uncompressed_len = -1
        while pack_code < 0xFC:
            if last_uncompressed_len == len(uncompressed):
                raise ValueError(f'Error while unpacking QFS archive: infinite loop detected')
            last_uncompressed_len = len(uncompressed)
            pack_a, pack_b = read_byte(buffer), read_byte(buffer)
            bytes_used = bytes_used + 2
            if not (pack_code & 0x80):
                length = pack_code & 3
                buffer.seek(-1, SEEK_CUR)
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length - 1
                offset = ((pack_code >> 5) << 8) + pack_a + 1
                length = ((pack_code & 0x1c) >> 2) + 3
                self._reuse_bytes_in_output(buffer, uncompressed, length, offset)
            elif not pack_code & 0x40:
                length = (pack_a >> 6) & 3
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length
                offset = (pack_a & 0x3f) * 256 + pack_b + 1
                length = (pack_code & 0x3f) + 4
                self._reuse_bytes_in_output(buffer, uncompressed, length, offset)
            elif not pack_code & 0x20:
                pack_c = read_byte(buffer)
                length = pack_code & 3
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length + 1
                offset = ((pack_code & 0x10) << 12) + 256 * pack_a + pack_b + 1
                length = ((pack_code >> 2) & 3) * 256 + pack_c + 5
                self._reuse_bytes_in_output(buffer, uncompressed, length, offset)
            else:
                length = (pack_code & 0x1f) * 4 + 4
                buffer.seek(-2, SEEK_CUR)
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length - 2
            pack_code = read_byte(buffer)
            bytes_used = bytes_used + 1
        if bytes_used < input_length and len(uncompressed) < output_length:
            self._copy_bytes_to_output(buffer, uncompressed, input_length - bytes_used)
        if output_length != len(uncompressed):
            raise ValueError(
                f'Error while unpacking QFS archive: expected length {output_length}, actual length: {len(uncompressed)}')
        return bytes(uncompressed)
