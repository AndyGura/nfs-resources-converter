from .buffer_utils import read_int, read_short, read_3int, read_byte


def memoize(function):
    memo = {}
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper

def my_import(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def format_exception(ex):
    return f'{ex.__class__.__name__}: {str(ex)}'


def represent_value_as_str(value):
    return hex(value) if isinstance(value, int) else value


# transforms 0b0000 (4 bit) color to 0b00000000 (8 bit)
# 0b000 => 0b00000000
# 0b111 => 0b11111111
@memoize
def transform_bitness(value: int, bitness: int) -> int:
    koef = 255 / (pow(2, bitness) - 1)
    return round((value & generate_bit_mask(bitness)) * koef)


# generates 0b01110 if args are 3, 1
@memoize
def generate_bit_mask(length, right_offset=0) -> int:
    return (pow(2, length) - 1) << right_offset

@memoize
def extract_number(value, length, right_offset=0) -> int:
    return (value & generate_bit_mask(length, right_offset)) >> right_offset

@memoize
def extract_numbers_with_bitness(color, *bitnesses):
    offset = 0
    res = []
    for bitness in bitnesses[::-1]:
        if bitness == 0:
            res.append(0)
            continue
        res.append(transform_bitness(extract_number(color, bitness, offset),
                                     bitness))
        offset += bitness
    return tuple(res[::-1])


# transforms 0565, 1555 etc. colors to regular 8888
# TODO remove, use extract_numbers_with_bitness
@memoize
def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = transform_bitness(extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness),
                              alpha_bitness) if alpha_bitness else 0xFF
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return red << 24 | green << 16 | blue << 8 | alpha
