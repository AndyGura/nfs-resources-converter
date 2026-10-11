from io import BufferedReader, SEEK_CUR, BytesIO

import numpy as np

from resources.eac.compressions.base import BaseCompressionAlgorithm

# QFS2: byte pair encoding. Header 0x46FB (0x47FB: 3 more bytes, the compressed size, follow), uncompressed size (u24
# BE), escape byte, number of patterns (u8), then 3 bytes per pattern: id, left byte, right byte. The game expands every
# byte of a pattern recursively with the final tables (TNFS DOS 0xa9c24, SE 0x4a96f4). In data, a pattern id gives
# its expansion, escape + 0 ends the stream, escape + any other byte gives that byte, any other byte is itself.
_PATTERN = 0x100
_ESCAPED = 0x200


class Qfs2Compression(BaseCompressionAlgorithm):
    def _read_value(self, buffer, patterns) -> bytes:
        value = buffer.read(1)
        if value in patterns.keys():
            return patterns[value]
        return value

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        start_offset = buffer.tell()
        uncompressed: bytearray = bytearray()
        hdr1, hdr2 = buffer.read(2)
        if hdr2 != 0xFB or (hdr1 & 0xFE) != 0x46:
            raise ValueError('Invalid QFS2 file header')
        if hdr1 & 1:
            # compressed size
            buffer.seek(3, SEEK_CUR)
        output_length = int.from_bytes(buffer.read(3), byteorder='big')
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
                # terminate char faced
                if value == b'\x00':
                    break
                use_value = False
                uncompressed.extend(value)
            else:
                value = self._read_value(buffer, patterns)
                if len(value) == 1 and value[0] == value_indicator:
                    use_value = True
                else:
                    uncompressed.extend(value)
        if len(uncompressed) != output_length:
            raise ValueError(
                f'Error while unpacking QFS archive: expected length {output_length}, actual length: {len(uncompressed)}'
            )
        return bytes(uncompressed)

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int) -> bytes:
        data = np.frombuffer(bytes(buffer.read(input_length)), dtype=np.uint8)
        if len(data) > 0xFFFFFF:
            raise ValueError(f'QFS2: {len(data)} bytes do not fit 24-bit uncompressed size')
        # The escape byte can be any byte but 0, escape followed by 0 ends the stream. The rarest one (EA's files use
        # one that the data doesn't have) costs least: every its occurrence takes 2 bytes
        counts = np.bincount(data, minlength=256)
        escape = 255 - int(np.argmin(counts[:0:-1]))
        # Tokens: byte value, _PATTERN + id of a pattern, _ESCAPED + byte value of an escaped literal (never in a pair)
        tokens = data.astype(np.int32)
        tokens[tokens == escape] |= _ESCAPED
        # Byte values that can't be ids: 0 (can't be escaped), escape and the components of earlier patterns (the game
        # expands components with the final tables, an id defined later would change an earlier pattern) and ids
        not_id = np.zeros(256, dtype=bool)
        not_id[[0, escape]] = True
        patterns = []
        while len(patterns) < 255 and len(tokens) > 1:
            pair = self._best_pair(tokens, not_id)
            if pair is None:
                break
            left, right, pattern_id, positions = pair
            tokens[tokens == pattern_id] |= _ESCAPED
            tokens[positions] = _PATTERN | pattern_id
            keep = np.ones(len(tokens), dtype=bool)
            keep[positions + 1] = False
            tokens = tokens[keep]
            for component in (left, right):
                if component < _PATTERN:
                    not_id[component] = True
            not_id[pattern_id] = True
            patterns.append((pattern_id, left & 0xFF, right & 0xFF))

        escaped = tokens >= _ESCAPED
        stream = np.stack([np.full(len(tokens), escape, dtype=np.uint8), (tokens & 0xFF).astype(np.uint8)], axis=1)
        stream = stream.ravel()[np.stack([escaped, np.ones(len(tokens), dtype=bool)], axis=1).ravel()]
        compressed = bytearray(b'\x46\xfb')
        compressed.extend(len(data).to_bytes(3, byteorder='big'))
        compressed.append(escape)
        compressed.append(len(patterns))
        for pattern in patterns:
            compressed.extend(pattern)
        compressed.extend(stream.tobytes())
        compressed.extend((escape, 0))
        return bytes(compressed)

    @staticmethod
    def _best_pair(tokens: np.ndarray, not_id: np.ndarray):
        """The pair of tokens which saves most bytes when replaced by a new pattern, as (left token, right token,
        pattern id, positions of non-overlapping occurrences), or None if no pair saves anything"""
        left, right = tokens[:-1], tokens[1:]
        pairable = (left < _ESCAPED) & (right < _ESCAPED)
        pair_counts = np.bincount((left[pairable] << 10) | right[pairable], minlength=_ESCAPED << 10)
        literal_counts = np.bincount(tokens[tokens < _PATTERN], minlength=256)
        id_candidates = np.flatnonzero(~not_id)
        id_candidates = id_candidates[np.argsort(literal_counts[id_candidates], kind='stable')][:3]
        if len(id_candidates) == 0:
            return None
        # the pair table entry and the escaped literals of the id cost 3 + their count bytes. Counts of pairs like
        # (a, a) include overlapping ones, so the exact count of the best candidates is checked
        top = np.argpartition(pair_counts, -16)[-16:]
        for key in top[np.argsort(-pair_counts[top])]:
            if pair_counts[key] <= 3:
                return None
            l, r = int(key) >> 10, int(key) & 0x3FF
            pattern_id = next((int(c) for c in id_candidates if c not in (l, r)), None)
            if pattern_id is None:
                continue
            positions = np.flatnonzero((left == l) & (right == r))
            if l == r:
                run_start = np.ones(len(positions), dtype=bool)
                run_start[1:] = positions[1:] != positions[:-1] + 1
                indices = np.arange(len(positions))
                positions = positions[(indices - np.maximum.accumulate(np.where(run_start, indices, 0))) % 2 == 0]
            if len(positions) - literal_counts[pattern_id] > 3:
                return l, r, pattern_id, positions
        return None
