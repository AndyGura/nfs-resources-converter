from functools import lru_cache
from math import ceil

from .buffer_utils import read_int, read_short, read_3int, read_byte
from .path_join import path_join


def format_exception(ex):
    return f'{ex.__class__.__name__}: {str(ex)}'


def represent_value_as_str(value):
    return hex(value) if isinstance(value, int) else value


# transforms 0b0000 (4 bit) color to 0b00000000 (8 bit)
# 0b000 => 0b00000000
# 0b111 => 0b11111111
@lru_cache(maxsize=1024)
def transform_bitness(value: int, bitness: int) -> int:
    v = value << (8 - bitness)
    for i in range(1, ceil(8 / bitness)):
        v = v | v >> (bitness * i)
    return v


# generates 0b01110 if args are 3, 1
@lru_cache()
def generate_bit_mask(length, right_offset=0) -> int:
    return ((1 << length) - 1) << right_offset


def extract_number(value, length, right_offset=0) -> int:
    return (value & generate_bit_mask(length, right_offset)) >> right_offset
