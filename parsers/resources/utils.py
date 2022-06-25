# transforms 0b0000 (4 bit) color to 0b00000000 (8 bit)
# 0b000 => 0b00000000
# 0b111 => 0b11111111


def transform_bitness(value: int, bitness: int) -> int:
    koef = 255 / (pow(2, bitness) - 1)
    return round((value & generate_bit_mask(6)) * koef)


# generates 0b01110 if args are 3, 1
def generate_bit_mask(length, right_offset=0) -> int:
    return (pow(2, length) - 1) << right_offset


def extract_number(value, length, right_offset=0) -> int:
    return (value & generate_bit_mask(length, right_offset)) >> right_offset
