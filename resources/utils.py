from parsers.resources.utils import transform_bitness, extract_number


def represent_value_as_str(value):
    return hex(value) if isinstance(value, int) else value

# transforms 0565, 1555 etc. colors to regular 8888
def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = transform_bitness(extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness),
                              alpha_bitness) if alpha_bitness else 0xFF
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return red << 24 | green << 16 | blue << 8 | alpha
