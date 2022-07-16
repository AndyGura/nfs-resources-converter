from io import BufferedReader, BytesIO

from library.read_blocks.read_block import ReadBlock


class FileLink(ReadBlock):
    """Not really a read block, because it's not reading the file, just preserving file name"""

    @property
    def file_path(self):
        return self.id

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        pass

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        pass

    def from_raw_value(self, raw: bytes):
        pass

    def to_raw_value(self, value) -> bytes:
        pass
