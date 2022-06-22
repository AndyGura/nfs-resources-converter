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


# transforms 0565, 1555 etc. colors to regular 8888
def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = transform_bitness(extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness),
                              alpha_bitness) if alpha_bitness else 0xFF
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return red << 24 | green << 16 | blue << 8 | alpha
