from io import BufferedReader, SEEK_CUR, BytesIO

from resources.eac.compressions.base import BaseCompressionAlgorithm

# Commands (P = 0..3 literals copied before the match, D = distance, L = match length):
# 2 bytes  0DDL LLPP DDDD DDDD                     D 1..1024,   L 3..10
# 3 bytes  10LL LLLL PPDD DDDD DDDD DDDD           D 1..16384,  L 4..67
# 4 bytes  110D LLPP DDDD DDDD DDDD DDDD LLLL LLLL D 1..131072, L 5..1028
# 1 byte   111N NNNN, N < 28                       (N + 1) * 4 literals
# 1 byte   1111 11PP                               end of stream, P literals follow
# Checked against the game's decoder (TNFS SE 0x4a823c)
_MAX_DISTANCE = 131072
_MAX_LENGTH = 1028
_MAX_LITERAL_RUN = 112
# how many earlier positions with the same 3 bytes are tried for every match: compression ratio vs speed
_MAX_CHAIN = 48


def _min_length(distance: int) -> int:
    return 3 if distance <= 1024 else 4 if distance <= 16384 else 5


def _common_length(data: bytes, a: int, b: int, limit: int) -> int:
    length = 0
    while length + 16 <= limit and data[a + length : a + length + 16] == data[b + length : b + length + 16]:
        length += 16
    while length < limit and data[a + length] == data[b + length]:
        length += 1
    return length


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
            uncompressed.extend(uncompressed[-offset : -offset + length])

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        uncompressed: bytearray = bytearray()
        use_4_bytes, contains_compressed_size = self._parse_archive_flags(buffer.read(1)[0])
        hdr2 = buffer.read(1)[0]
        if hdr2 != 0xFB:
            raise ValueError('Invalid RefPack file header')
        bytes_used = 5
        if contains_compressed_size:
            # compressed size comes first (TNFS SE 0x4a823c)
            buffer.seek(3, SEEK_CUR)
            bytes_used = 8
        output_length = (buffer.read(1)[0] << 16) + (buffer.read(1)[0] << 8) + buffer.read(1)[0]
        pack_code = buffer.read(1)[0]
        bytes_used = bytes_used + 1
        last_uncompressed_len = -1
        while pack_code < 0xFC:
            if last_uncompressed_len == len(uncompressed):
                raise ValueError(f'Error while unpacking QFS archive: infinite loop detected')
            last_uncompressed_len = len(uncompressed)
            pack_a, pack_b = buffer.read(1)[0], buffer.read(1)[0]
            bytes_used = bytes_used + 2
            if not (pack_code & 0x80):
                length = pack_code & 3
                buffer.seek(-1, SEEK_CUR)
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length - 1
                offset = ((pack_code >> 5) << 8) + pack_a + 1
                length = ((pack_code & 0x1C) >> 2) + 3
                self._reuse_bytes_in_output(buffer, uncompressed, length, offset)
            elif not pack_code & 0x40:
                length = (pack_a >> 6) & 3
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length
                offset = (pack_a & 0x3F) * 256 + pack_b + 1
                length = (pack_code & 0x3F) + 4
                self._reuse_bytes_in_output(buffer, uncompressed, length, offset)
            elif not pack_code & 0x20:
                pack_c = buffer.read(1)[0]
                length = pack_code & 3
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length + 1
                offset = ((pack_code & 0x10) << 12) + 256 * pack_a + pack_b + 1
                length = ((pack_code >> 2) & 3) * 256 + pack_c + 5
                self._reuse_bytes_in_output(buffer, uncompressed, length, offset)
            else:
                length = (pack_code & 0x1F) * 4 + 4
                buffer.seek(-2, SEEK_CUR)
                self._copy_bytes_to_output(buffer, uncompressed, length)
                bytes_used = bytes_used + length - 2
            pack_code = buffer.read(1)[0]
            bytes_used = bytes_used + 1
        if bytes_used < input_length and len(uncompressed) < output_length:
            self._copy_bytes_to_output(buffer, uncompressed, input_length - bytes_used)
        if output_length != len(uncompressed):
            raise ValueError(
                f'Error while unpacking QFS archive: expected length {output_length}, actual length: {len(uncompressed)}'
            )
        return bytes(uncompressed)

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int) -> bytes:
        data = bytes(buffer.read(input_length))
        n = len(data)
        if n > 0xFFFFFF:
            raise ValueError(f'RefPack: {n} bytes do not fit 24-bit uncompressed size')
        out = bytearray(b'\x10\xfb' + n.to_bytes(3, 'big'))
        # hash chains: last position of every 3-byte sequence, previous position with the same sequence
        head = {}
        prev = [-1] * n
        inserted = 0

        def insert_until(pos):
            nonlocal inserted
            for i in range(inserted, min(pos, n - 2)):
                key = data[i : i + 3]
                prev[i] = head.get(key, -1)
                head[key] = i
            inserted = max(inserted, pos)

        def find_match(pos):
            insert_until(pos)
            best_length, best_distance = 0, 0
            if pos + 3 > n:
                return best_length, best_distance
            max_length = min(_MAX_LENGTH, n - pos)
            candidate = head.get(data[pos : pos + 3], -1)
            chain = _MAX_CHAIN
            while candidate >= 0 and chain:
                distance = pos - candidate
                if distance > _MAX_DISTANCE:
                    break
                if data[candidate + best_length] == data[pos + best_length]:
                    length = _common_length(data, candidate, pos, max_length)
                    if length > best_length and length >= _min_length(distance):
                        best_length, best_distance = length, distance
                        if length == max_length:
                            break
                candidate = prev[candidate]
                chain -= 1
            return best_length, best_distance

        def flush_literal_runs(start, end):
            # leaves up to 3 literals for the next command
            while end - start >= 4:
                run = min(_MAX_LITERAL_RUN, (end - start) & ~3)
                out.append(0xE0 | (run // 4 - 1))
                out.extend(data[start : start + run])
                start += run
            return start

        literal_start = 0
        pos = 0
        match = find_match(0)
        while pos < n:
            length, distance = match
            if length == 0:
                pos += 1
                match = find_match(pos)
                continue
            # lazy matching: a longer match at the next byte is worth one literal
            next_match = find_match(pos + 1) if pos + 1 < n else (0, 0)
            if next_match[0] > length:
                pos += 1
                match = next_match
                continue
            literal_start = flush_literal_runs(literal_start, pos)
            literals = pos - literal_start
            offset = distance - 1
            if length <= 10 and distance <= 1024:
                out.append(((offset >> 8) << 5) | ((length - 3) << 2) | literals)
                out.append(offset & 0xFF)
            elif length <= 67 and distance <= 16384:
                out.append(0x80 | (length - 4))
                out.append((literals << 6) | (offset >> 8))
                out.append(offset & 0xFF)
            else:
                out.append(0xC0 | ((offset >> 16) << 4) | (((length - 5) >> 8) << 2) | literals)
                out.append((offset >> 8) & 0xFF)
                out.append(offset & 0xFF)
                out.append((length - 5) & 0xFF)
            out.extend(data[literal_start:pos])
            pos += length
            literal_start = pos
            match = find_match(pos) if pos < n else (0, 0)
        literal_start = flush_literal_runs(literal_start, n)
        out.append(0xFC | (n - literal_start))
        out.extend(data[literal_start:n])
        return bytes(out)
