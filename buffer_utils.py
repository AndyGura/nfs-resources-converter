from io import BufferedReader, BytesIO
from typing import Literal


def read_utf_bytes(buffer: [BufferedReader, BytesIO], len: int) -> str:
    return buffer.read(len).decode('utf-8')


def read_int(buffer: [BufferedReader, BytesIO], byteorder: Literal["little", "big"] = 'little') -> int:
    return int.from_bytes(buffer.read(4), byteorder=byteorder)


def read_3int(buffer: [BufferedReader, BytesIO], byteorder: Literal["little", "big"] = 'little') -> int:
    return int.from_bytes(buffer.read(3), byteorder=byteorder)


def read_signed_int(buffer: [BufferedReader, BytesIO]) -> int:
    return int.from_bytes(buffer.read(4), byteorder='little', signed=True)


def read_short(buffer: [BufferedReader, BytesIO], byteorder: Literal["little", "big"] = 'little') -> int:
    value = buffer.read(2)
    value = value.ljust(2, b'\0')
    return int.from_bytes(value, byteorder=byteorder)


def read_byte(buffer: [BufferedReader, BytesIO]) -> int:
    return int.from_bytes(buffer.read(1), byteorder='little')


def read_signed_byte(buffer: [BufferedReader, BytesIO]) -> int:
    return int.from_bytes(buffer.read(1), byteorder='little', signed=True)


def read_nfs1_float32_7(buffer: [BufferedReader, BytesIO]) -> float:
    return float(read_signed_int(buffer) / 0x80)


def read_nfs1_float32_4(buffer: [BufferedReader, BytesIO]) -> float:
    return float(read_signed_int(buffer) / 0x10)
