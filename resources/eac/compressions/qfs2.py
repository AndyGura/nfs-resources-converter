from io import BufferedReader, SEEK_CUR, BytesIO

from buffer_utils import read_3int
from buffer_utils import read_byte
from resources.eac.compressions.base import BaseCompressionAlgorithm


class Qfs2Compression(BaseCompressionAlgorithm):

    def _read_value(self, buffer, patterns) -> bytes:
        value = buffer.read(1)
        if value in patterns.keys():
            return patterns[value]
        return value

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        uncompressed: bytearray = bytearray()
        buffer.seek(2, SEEK_CUR)  # skip header
        output_length = read_3int(buffer, byteorder='big')
        value_indicator = read_byte(buffer)
        patterns_count = read_byte(buffer)
        bytes_used = 7
        patterns = {}
        for i in range(0, patterns_count):
            pattern_id = buffer.read(1)
            value1 = self._read_value(buffer, patterns)
            value2 = self._read_value(buffer, patterns)
            if pattern_id in patterns.keys():
                raise Exception('Duplicate id in QFS2 patterns')
            patterns[pattern_id] = value1 + value2
            bytes_used = bytes_used + 3
        use_value = False
        while bytes_used < input_length:
            if use_value:
                value = buffer.read(1)
                use_value = False
            else:
                value = self._read_value(buffer, patterns)
            if int.from_bytes(value, byteorder='little') == value_indicator:
                use_value = True
            else:
                uncompressed.extend(value)
            bytes_used = bytes_used + 1

        if output_length > len(uncompressed):
            raise ValueError(
                f'Error while unpacking QFS archive: expected length {output_length}, actual length: {len(uncompressed)}')
        return bytes(uncompressed)
