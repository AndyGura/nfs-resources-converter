from heapq import nsmallest, nlargest
from io import BufferedReader, SEEK_CUR, BytesIO
from time import time

from library.utils.douby_linked_list import DoublyLinkedList
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
                if int.from_bytes(value, byteorder='little') == value_indicator:
                    use_value = True
                else:
                    uncompressed.extend(value)
        if len(uncompressed) != output_length:
            raise ValueError(
                f'Error while unpacking QFS archive: expected length {output_length}, actual length: {len(uncompressed)}')
        return bytes(uncompressed)

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        # FIXME games/nfs1/FRONTEND/ART/CHECK/GRAPHICS.QFS when compressed becomes bigger!!!
        # FIXME games/nfs1/FRONTEND/ART/JOYCAL.QFS when uncompressed returns different result!!!

        # constants; middle ground between speed and compression ratio
        passes = 8
        pairs_per_pass = 10

        start_time = time()
        data_dll = DoublyLinkedList.from_list(buffer.read(input_length))
        terminate_int = 0x00
        # TODO test if other escape ints supported on real NFS. Some files have many of them, and after compression they take more space than uncompressed
        escape_int = 0xFF
        patterns = {}

        def build_frequency_map():
            freq_array = [0] * 256
            freq_array_2 = [0] * (256 * 256)
            node = data_dll.head
            while node and node.next:
                # escape characters and patter ids are already escaped
                if node.data == escape_int:
                    if node.next:
                        node = node.next.next
                        continue
                    else:
                        break
                freq_array[node.data] += 1
                if node.next.data != escape_int:
                    freq_array_2[(node.data << 8) | (node.next.data)] += 1
                node = node.next
            return (
                nsmallest(256, (x for x in enumerate(freq_array) if x[0] not in [escape_int, terminate_int]), key=lambda item: item[1]),
                nlargest(256, (x for x in enumerate(freq_array_2) if x[1] > 0), key=lambda item: item[1]),
            )

        def replace_pattern_in_data(replacements):
            len_delta = 0
            node = data_dll.head
            while node:
                node_next = node.next
                for (pattern, left, right) in replacements:
                    if node.data == pattern:
                        data_dll.insert(escape_int, node.prev, node)
                        len_delta += 1
                        node = node_next
                        break
                    elif (node_next is not None and node.data == left and node_next.data == right):
                        data_dll.insert(pattern, node.prev, node_next.next)
                        len_delta -= 1
                        node = node_next.next
                        break
                else:
                    node = node_next
            return len_delta

        # escape "escape character"
        for node in data_dll.nodes():
            if node.data == escape_int:
                data_dll.insert(escape_int, node.prev, node)

        for p in range(passes):
            (frequency_map, frequency_map_2) = build_frequency_map()
            locked_values = set()
            this_pass_replacements = []
            for _ in range(pairs_per_pass):
                if len(frequency_map_2) == 0:
                    break
                (pattern_id, lfreq) = frequency_map.pop(0)
                try:
                    while (pattern_id in locked_values or pattern_id in patterns or pattern_id == 0):
                        (pattern_id, lfreq) = frequency_map.pop(0)
                except IndexError:
                    # exhausted list of indexes
                    break
                locked_values.add(pattern_id)
                (most_frequent_pair, pfreq) = frequency_map_2.pop(0)
                if (pfreq < (3 + lfreq) * 16):
                    break
                (left, right) = most_frequent_pair >> 8, most_frequent_pair & 0xff
                if left in locked_values or right in locked_values:
                    continue
                locked_values.add(left)
                locked_values.add(right)
                patterns[pattern_id] = (left, right)
                this_pass_replacements.append((pattern_id, left, right))
            saved_bytes_this_pass = -replace_pattern_in_data(this_pass_replacements)
            if saved_bytes_this_pass < input_length // 100:
                break

        compressed = bytearray()
        compressed.append(0b0100_0110)
        compressed.append(0xfb)
        compressed.extend(input_length.to_bytes(3, byteorder='big'))
        compressed.append(escape_int)
        compressed.append(len(patterns))
        for pattern_id, (left, right) in patterns.items():
            compressed.append(pattern_id)
            compressed.append(left)
            compressed.append(right)
        for item in data_dll.items():
            compressed.append(item)
        compressed.append(escape_int)
        compressed.append(terminate_int)

        print(f'Compressed {input_length} -> {len(compressed)} ({(100 * (input_length - len(compressed)) / input_length):.2f}%). Time spent: {time() - start_time:.2f} seconds')

        return bytes(compressed)
