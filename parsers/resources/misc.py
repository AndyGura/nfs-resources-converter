from io import BufferedReader, SEEK_CUR

from buffer_utils import read_utf_bytes, read_byte
from parsers.resources.base import BaseResource


class BinaryResource(BaseResource):

    def __init__(self, id=None, length=None, save_binary_file=True):
        super().__init__()
        self.id = id
        self.length = length
        self.save_binary_file = save_binary_file

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        if self.length is not None:
            length = min(length, self.length)
        self.bytes = buffer.read(length)
        return length

    def save_converted(self, path: str):
        if self.save_binary_file:
            if self.id:
                path = f'{path}__{hex(self.id)}'
            with open(f'{path}.bin', 'w+b') as file:
                file.write(self.bytes)


class TextResource(BaseResource):

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.text = read_utf_bytes(buffer, length)
        return length

    def save_converted(self, path: str):
        with open(f'{path}.txt', 'w') as file:
            file.write(self.text)
