import heapq
import re
from io import BufferedReader, BytesIO
from itertools import accumulate

import numpy as np

from resources.eac.compressions.base import BaseCompressionAlgorithm


class _BitReader:
    """MSB-first bit reader over a bytes object. Bits past the end of data read as zeros (the game's decoder
    prefetches 16-bit words the same way), but running far past the end is treated as a corrupt stream."""

    _OVERRUN_ALLOWANCE = 4

    def __init__(self, data: bytes, pos: int = 0):
        self._data = data
        self._limit = len(data) + self._OVERRUN_ALLOWANCE
        self._pos = pos
        self._buf = 0  # only the lowest `_count` bits are meaningful
        self._count = 0

    def _fill(self, n: int):
        while self._count < n:
            if self._pos < len(self._data):
                byte = self._data[self._pos]
            elif self._pos < self._limit:
                byte = 0
            else:
                raise ValueError('Error while unpacking QFS3 archive: unexpected end of data')
            self._pos += 1
            self._buf = (self._buf << 8) | byte
            self._count += 8

    def peek(self, n: int) -> int:
        self._fill(n)
        return (self._buf >> (self._count - n)) & ((1 << n) - 1)

    def skip(self, n: int):
        self._fill(n)
        self._count -= n
        self._buf &= (1 << self._count) - 1

    def read(self, n: int) -> int:
        value = self.peek(n)
        self.skip(n)
        return value


_MAX_CODE_LENGTH = 16
_RUN = re.compile(rb'(.)\1+', re.DOTALL)


def _number_bits(number: int) -> str:
    """Number encoding of QFS3 as a string of bits, see Qfs3Compression"""
    value = bin(number + 4)[2:]
    return '0' * (len(value) - 3) + value


def _huffman_code_lengths(frequencies: dict[int, int]) -> dict[int, int]:
    """Code length of every symbol, at most _MAX_CODE_LENGTH. Needs 2 symbols at least, gives a complete code"""
    while True:
        heap = [(frequency, i, (symbol,)) for i, (symbol, frequency) in enumerate(sorted(frequencies.items()))]
        heapq.heapify(heap)
        lengths = dict.fromkeys(frequencies, 0)
        counter = len(heap)
        while len(heap) > 1:
            frequency_a, _, symbols_a = heapq.heappop(heap)
            frequency_b, _, symbols_b = heapq.heappop(heap)
            for symbol in symbols_a + symbols_b:
                lengths[symbol] += 1
            heapq.heappush(heap, (frequency_a + frequency_b, counter, symbols_a + symbols_b))
            counter += 1
        if max(lengths.values()) <= _MAX_CODE_LENGTH:
            return lengths
        # flatter frequencies give shorter longest codes
        frequencies = {symbol: max(1, frequency >> 1) for symbol, frequency in frequencies.items()}


class Qfs3Compression(BaseCompressionAlgorithm):
    """
    QFS3: canonical Huffman coding with an escape symbol for run-length/literal/end codes, optionally followed
    by delta decoding of the output. Used by TNFS for *.QFS image archives and *.PBS performance specs.

    Layout (all integers big-endian, everything after the header is a MSB-first bit stream):
        u8   flags:  0x30 = plain, 0x32 = output is delta-coded, 0x34 = output is delta-coded twice;
                     bit 0 set means the compressed size field is present
        u8   0xFB
        u24  compressed size (only if flags bit 0 is set; ignored)
        u24  uncompressed size
        u8   escape symbol
        Huffman tree, code lengths first: for L = 1, 2, ...: number of symbols with code length L (see number
             encoding below), until the code space is exhausted (Kraft sum reaches 1)
        symbols in canonical order, each encoded as number+1 = distance to the symbol from the previous one,
             counting only byte values not assigned yet, cyclic over 0..255 (starting before 0)
        data: Huffman codes. The escape symbol is followed by a number N:
             N > 0            repeat the last output byte N times
             N == 0, bit 1    end of stream
             N == 0, bit 0    next 8 bits are a literal byte

    Number encoding (Elias-gamma-like): Z zero bits, a one bit, then (Z+2) value bits V;
    number = (1 << (Z+2)) + V - 4. Smallest numbers 0..3 thus take 3 bits: 1xx.
    """

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int) -> bytes:
        data = buffer.read(input_length) if input_length is not None else buffer.read()
        if len(data) < 2 or data[1] != 0xFB or (data[0] & 0xF8) != 0x30:
            raise ValueError('Invalid QFS3 file header')
        flags = data[0]
        reader = _BitReader(data, pos=5 if flags & 0x01 else 2)
        output_length = reader.read(24)
        escape = reader.read(8)

        counts = self._read_code_length_counts(reader)
        symbols = self._read_symbols(reader, sum(counts))
        lut_symbol, lut_length = self._build_lookup_table(counts, symbols)
        max_length = len(counts)

        out = bytearray()
        while True:
            code = reader.peek(max_length)
            symbol = lut_symbol[code]
            reader.skip(lut_length[code])
            if symbol != escape:
                out.append(symbol)
                continue
            run_length = self._read_number(reader)
            if run_length:
                if not out:
                    raise ValueError('Error while unpacking QFS3 archive: run-length code before any output')
                out.extend(out[-1:] * run_length)
                if len(out) > output_length:
                    raise ValueError('Error while unpacking QFS3 archive: writes more than declared length')
            elif reader.read(1):
                break
            else:
                out.append(reader.read(8))
        if len(out) != output_length:
            raise ValueError(
                f'Error while unpacking QFS3 archive: expected length {output_length}, actual length: {len(out)}'
            )

        delta_passes = {0x30: 0, 0x32: 1, 0x34: 2}.get(flags & 0xFE, 0)
        for _ in range(delta_passes):
            out = bytearray(accumulate(out, lambda a, b: (a + b) & 0xFF))
        return bytes(out)

    @staticmethod
    def _read_number(reader: _BitReader) -> int:
        zeros = 0
        while not reader.read(1):
            zeros += 1
            if zeros > 24:
                raise ValueError('Error while unpacking QFS3 archive: corrupt number encoding')
        bits = zeros + 2
        return (1 << bits) + reader.read(bits) - 4

    @classmethod
    def _read_code_length_counts(cls, reader: _BitReader) -> list[int]:
        """Returns counts[L - 1] = number of symbols with Huffman code length L."""
        counts = []
        next_code = 0  # first unassigned canonical code of the current length
        while True:
            length = len(counts) + 1
            if length > 16:
                raise ValueError('Error while unpacking QFS3 archive: Huffman code longer than 16 bits')
            count = cls._read_number(reader)
            counts.append(count)
            next_code = (next_code << 1) + count
            if next_code > (1 << length):
                raise ValueError('Error while unpacking QFS3 archive: over-subscribed Huffman tree')
            if count and next_code == (1 << length):
                return counts

    @classmethod
    def _read_symbols(cls, reader: _BitReader, amount: int) -> bytearray:
        if amount > 256:
            raise ValueError('Error while unpacking QFS3 archive: too many Huffman symbols')
        symbols = bytearray()
        used = bytearray(256)
        symbol = 0xFF
        for _ in range(amount):
            distance = cls._read_number(reader) + 1
            while distance:
                symbol = (symbol + 1) & 0xFF
                if not used[symbol]:
                    distance -= 1
            used[symbol] = 1
            symbols.append(symbol)
        return symbols

    @staticmethod
    def _build_lookup_table(counts: list[int], symbols: bytearray) -> tuple[bytearray, bytearray]:
        """Direct lookup tables indexed by the next `max_length` bits of the stream: symbol and its code length."""
        max_length = len(counts)
        table_size = 1 << max_length
        lut_symbol = bytearray(table_size)
        lut_length = bytearray(table_size)
        code = 0
        symbol_index = 0
        for length, count in enumerate(counts, start=1):
            span = 1 << (max_length - length)
            for _ in range(count):
                start = code * span
                lut_symbol[start : start + span] = symbols[symbol_index : symbol_index + 1] * span
                lut_length[start : start + span] = bytes([length]) * span
                code += 1
                symbol_index += 1
            code <<= 1
        return lut_symbol, lut_length

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int, delta_passes=(0, 1, 2)) -> bytes:
        """Tries the output delta-coded given numbers of times, returns the shortest result"""
        data = np.frombuffer(bytes(buffer.read(input_length)), dtype=np.uint8)
        if len(data) > 0xFFFFFF:
            raise ValueError(f'QFS3: {len(data)} bytes do not fit 24-bit uncompressed size')
        results = []
        for passes in delta_passes:
            delta = data.copy()
            for _ in range(passes):
                delta[1:] = delta[1:] - delta[:-1]
            results.append(self._compress(delta.tobytes(), 0x30 + 2 * passes))
        return min(results, key=len)

    @staticmethod
    def _compress(data: bytes, flags: int) -> bytes:
        counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        # escaped literals cost the escape code + 12 bits, the rarest byte is the cheapest escape
        escape = int(np.argmin(counts))
        # every byte of a run but the first one can be repeated by the escape code + number of repeats instead
        runs = [(match.start(), match.end() - match.start() - 1) for match in _RUN.finditer(data)]
        literal_frequencies = {symbol: int(count) for symbol, count in enumerate(counts) if count and symbol != escape}
        # an escape for every escaped literal and the end of stream
        escape_frequency = int(counts[escape]) + 1
        lengths = None
        used_runs = []
        # code lengths depend on which runs get repeated, which depends on code lengths. Starting from long runs only,
        # a few rounds settle (TNFS files come out a bit shorter than EA's)
        for _ in range(4):
            frequencies = dict(literal_frequencies)
            frequencies[escape] = escape_frequency
            used_runs = []
            for start, repeats in runs:
                byte = data[start]
                if lengths is None:
                    use = repeats >= 8
                else:
                    literal_bits = lengths[byte] if byte != escape else lengths[escape] + 12
                    use = lengths[escape] + 2 * (repeats + 4).bit_length() - 3 < repeats * literal_bits
                if use:
                    used_runs.append((start, repeats))
                    frequencies[escape] += 1
                    if byte != escape:
                        frequencies[byte] -= repeats
                    else:
                        frequencies[escape] -= repeats
            frequencies = {symbol: frequency for symbol, frequency in frequencies.items() if frequency > 0}
            if len(frequencies) == 1:
                frequencies[(escape + 1) & 0xFF] = 1
            lengths = dict.fromkeys(range(256), 0) | _huffman_code_lengths(frequencies)

        # canonical codes in the order the decoder assigns them: by length, then by value
        symbols = sorted(
            (symbol for symbol in range(256) if lengths[symbol]), key=lambda symbol: (lengths[symbol], symbol)
        )
        max_length = lengths[symbols[-1]]
        codes = {}
        code = 0
        length = 1
        for symbol in symbols:
            code <<= lengths[symbol] - length
            length = lengths[symbol]
            codes[symbol] = format(code, f'0{length}b')
            code += 1
        bits = []
        for length in range(1, max_length + 1):
            bits.append(_number_bits(sum(1 for symbol in symbols if lengths[symbol] == length)))
        used = bytearray(256)
        previous = 0xFF
        for symbol in symbols:
            distance = 0
            value = previous
            while value != symbol:
                value = (value + 1) & 0xFF
                if not used[value]:
                    distance += 1
            bits.append(_number_bits(distance - 1))
            used[symbol] = 1
            previous = symbol

        escape_code = codes[escape]
        literal_codes = [codes.get(byte) or escape_code + '1000' + format(byte, '08b') for byte in range(256)]
        literal_codes[escape] = escape_code + '1000' + format(escape, '08b')
        position = 0
        for start, repeats in used_runs:
            bits.append(''.join(map(literal_codes.__getitem__, data[position : start + 1])))
            bits.append(escape_code + _number_bits(repeats))
            position = start + 1 + repeats
        bits.append(''.join(map(literal_codes.__getitem__, data[position:])))
        bits.append(escape_code + '1001')
        bit_string = ''.join(bits)
        bit_string += '0' * (-len(bit_string) % 8)
        header = bytes([flags, 0xFB]) + len(data).to_bytes(3, 'big') + bytes([escape])
        return header + int('1' + bit_string, 2).to_bytes(len(bit_string) // 8 + 1, 'big')[1:]
