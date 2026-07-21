from io import BufferedReader, SEEK_CUR, BytesIO

from resources.eac.compressions.base import BaseCompressionAlgorithm


class Qfs2Compression(BaseCompressionAlgorithm):

    def _read_value(self, buffer, patterns) -> bytes:
        value = buffer.read(1)
        if value in patterns.keys():
            return patterns[value]
        return value

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        start_offset = buffer.tell()
        uncompressed: bytearray = bytearray()
        # skip header
        buffer.seek(1, SEEK_CUR)
        hdr2 = buffer.read(1)[0]
        if hdr2 != 0xfb:
            raise ValueError("Invalid QFS2 file header")
        output_length = int.from_bytes(buffer.read(3), byteorder='big') + 1
        value_indicator = buffer.read(1)[0]
        patterns_count = buffer.read(1)[0]
        patterns = {}
        for i in range(0, patterns_count):
            pattern_id = buffer.read(1)
            value1 = self._read_value(buffer, patterns)
            value2 = self._read_value(buffer, patterns)
            if pattern_id in patterns.keys():
                raise Exception('Duplicate id in QFS2 patterns')
            patterns[pattern_id] = value1 + value2
        use_value = False
        while buffer.tell() - start_offset < input_length:
            if use_value:
                value = buffer.read(1)
                use_value = False
                uncompressed.extend(value)
            else:
                value = self._read_value(buffer, patterns)
                if int.from_bytes(value, byteorder='little') == value_indicator:
                    use_value = True
                else:
                    uncompressed.extend(value)
        if len(uncompressed) > output_length:
            raise ValueError(
                f'Error while unpacking QFS archive: expected length {output_length}, actual length: {len(uncompressed)}')
        while len(uncompressed) < output_length:
            uncompressed.extend(b'\x00')
        return bytes(uncompressed)

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        data = buffer.read(input_length)
        symbols = [bytes([b]) for b in data]

        patterns = {}
        escape_byte = b'\xff'
        # TODO actual compression
        # patterns = {
        #     b'\x01': (b'\x82', b'\x03', None)
        # }

        compressed = bytearray()
        compressed.append(0b0100_0110)
        compressed.append(0xfb)
        compressed.extend(input_length.to_bytes(3, byteorder='big'))
        compressed.extend(escape_byte)
        compressed.append(len(patterns))
        for pattern_id, (left, right, _) in patterns.items():
            compressed.extend(pattern_id)
            compressed.extend(left)
            compressed.extend(right)
        for symbol in symbols:
            if symbol in patterns or symbol == escape_byte:
                compressed.extend(escape_byte)
            compressed.extend(symbol)
        compressed.extend(b'\xff')

        return bytes(compressed)
