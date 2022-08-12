from io import BufferedReader, BytesIO

from library.read_blocks.read_block import ReadBlock


class FileLink(ReadBlock):
    """Not really a read block, because it's not reading the file, just preserving file name"""

    def read(self, buffer: [BufferedReader, BytesIO], size: int, state):
        return self.wrap_result(value=state.get('id'), block_state=state)

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int):
        pass

    def from_raw_value(self, raw: bytes, state: dict):
        pass

    def to_raw_value(self, data, state) -> bytes:
        pass
