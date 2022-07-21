from io import BufferedReader, BytesIO
from typing import Literal


def read_int(buffer: [BufferedReader, BytesIO], byteorder: Literal["little", "big"] = 'little') -> int:
    return int.from_bytes(buffer.read(4), byteorder=byteorder)


def read_3int(buffer: [BufferedReader, BytesIO], byteorder: Literal["little", "big"] = 'little') -> int:
    return int.from_bytes(buffer.read(3), byteorder=byteorder)


def read_short(buffer: [BufferedReader, BytesIO], byteorder: Literal["little", "big"] = 'little') -> int:
    value = buffer.read(2)
    value = value.ljust(2, b'\0')
    return int.from_bytes(value, byteorder=byteorder)


def read_byte(buffer: [BufferedReader, BytesIO]) -> int:
    return int.from_bytes(buffer.read(1), byteorder='little')
