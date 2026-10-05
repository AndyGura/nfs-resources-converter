from io import BufferedReader, BytesIO

from resources.eac.compressions.base import BaseCompressionAlgorithm

# JDLZ: LZ77 compression of NFS Underground-era Black Box games (*.lzc files, compressed bundles and textures).
# Header (16 bytes): "JDLZ", 0x02, 0x10, 2 zero bytes, uncompressed length (u32), compressed length incl. header (u32).
# The stream mixes two flag bytes with the data: bits of the first one (LSB first) tell literal (0) from match (1),
# bits of the second one tell the kind of each match. A flag byte is read when the previous one is used up, at the
# start of the next token. Matches are 2 bytes:
# - short distance: (length - 3) >> 8 in high nibble of byte 0, distance - 1 (1..16) in its low nibble,
#   (length - 3) & 0xFF in byte 1. Length 3..4098
# - long distance: (distance - 17) >> 8 in 3 high bits of byte 0, length - 3 (3..34) in its 5 low bits,
#   (distance - 17) & 0xFF in byte 1. Distance 17..2064

_HEADER_LENGTH = 16
_SHORT_MAX_DISTANCE = 16
_SHORT_MAX_LENGTH = 4098
_LONG_MAX_DISTANCE = 2064
_LONG_MAX_LENGTH = 34


class JdlzCompression(BaseCompressionAlgorithm):
    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        inp = buffer.read(input_length)
        if inp[:4] != b'JDLZ':
            raise ValueError('Invalid JDLZ header')
        output_length = int.from_bytes(inp[8:12], 'little')
        out = bytearray(output_length)
        flags1 = flags2 = 1
        ip = _HEADER_LENGTH
        op = 0
        input_end = len(inp)
        while ip < input_end and op < output_length:
            if flags1 == 1:
                flags1 = inp[ip] | 0x100
                ip += 1
            if flags2 == 1:
                flags2 = inp[ip] | 0x100
                ip += 1
            if flags1 & 1:
                b0, b1 = inp[ip], inp[ip + 1]
                ip += 2
                if flags2 & 1:
                    length = (b1 | ((b0 & 0xF0) << 4)) + 3
                    distance = (b0 & 0x0F) + 1
                else:
                    distance = (b1 | ((b0 & 0xE0) << 3)) + 17
                    length = (b0 & 0x1F) + 3
                if distance >= length:
                    out[op : op + length] = out[op - distance : op - distance + length]
                else:
                    for i in range(length):
                        out[op + i] = out[op + i - distance]
                op += length
                flags2 >>= 1
            else:
                out[op] = inp[ip]
                op += 1
                ip += 1
            flags1 >>= 1
        if op != output_length:
            raise ValueError(f'Error while unpacking JDLZ: expected length {output_length}, actual length: {op}')
        return bytes(out)

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        data = buffer.read(input_length)
        n = len(data)
        out = bytearray(b'JDLZ\x02\x10\x00\x00' + n.to_bytes(4, 'little') + b'\x00\x00\x00\x00')
        flags1_pos = flags2_pos = -1
        flags1_bit = flags2_bit = 8
        # 3-byte sequence -> recent positions, for long distance matches
        positions = {}

        def find_match(pos):
            best_length, best_distance = 0, 0
            # short distance: repeated patterns, runs
            for distance in range(1, min(_SHORT_MAX_DISTANCE, pos) + 1):
                length = 0
                max_length = min(_SHORT_MAX_LENGTH, n - pos)
                while length < max_length and data[pos + length] == data[pos + length - distance]:
                    length += 1
                if length > best_length:
                    best_length, best_distance = length, distance
                    if length == max_length:
                        break
            if best_length >= _LONG_MAX_LENGTH or pos + 3 > n:
                return best_length, best_distance
            for candidate in reversed(positions.get(data[pos : pos + 3], ())):
                distance = pos - candidate
                if distance > _LONG_MAX_DISTANCE:
                    break
                if distance <= _SHORT_MAX_DISTANCE:
                    continue
                length = 0
                max_length = min(_LONG_MAX_LENGTH, n - pos)
                while length < max_length and data[pos + length] == data[candidate + length]:
                    length += 1
                if length > best_length:
                    best_length, best_distance = length, distance
                    if length == max_length:
                        break
            return best_length, best_distance

        def remember(pos):
            if pos + 3 <= n:
                chain = positions.setdefault(data[pos : pos + 3], [])
                chain.append(pos)
                if len(chain) > 32:
                    del chain[:16]

        pos = 0
        while pos < n:
            if flags1_bit == 8:
                flags1_pos, flags1_bit = len(out), 0
                out.append(0)
            if flags2_bit == 8:
                flags2_pos, flags2_bit = len(out), 0
                out.append(0)
            length, distance = find_match(pos)
            if length >= 3:
                out[flags1_pos] |= 1 << flags1_bit
                if distance <= _SHORT_MAX_DISTANCE:
                    out[flags2_pos] |= 1 << flags2_bit
                    out.append((((length - 3) >> 8) << 4) | (distance - 1))
                    out.append((length - 3) & 0xFF)
                else:
                    out.append((((distance - 17) >> 8) << 5) | (length - 3))
                    out.append((distance - 17) & 0xFF)
                flags2_bit += 1
                for i in range(pos, pos + length):
                    remember(i)
                pos += length
            else:
                out.append(data[pos])
                remember(pos)
                pos += 1
            flags1_bit += 1
        out[12:16] = len(out).to_bytes(4, 'little')
        return bytes(out)
