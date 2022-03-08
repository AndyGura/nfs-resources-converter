#!/usr/bin/env python
# -*- coding: utf-8
import struct

# https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)

INDEX_ADJUST = [
    -1, -1, -1, -1, 2, 4, 6, 8,
    -1, -1, -1, -1, 2, 4, 6, 8]  # index table

STEP_TABLE = [
    7, 8, 9, 10, 11, 12, 13, 14,
    16, 17, 19, 21, 23, 25, 28, 31,
    34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143,
    157, 173, 190, 209, 230, 253, 279, 307,
    337, 371, 408, 449, 494, 544, 598, 658,
    724, 796, 876, 963, 1060, 1166, 1282, 1411,
    1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024,
    3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484,
    7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
    15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767]  # quantize table


def _decode_sample(nibble, l_index, predictor):
    step = STEP_TABLE[l_index]
    l_index = l_index + INDEX_ADJUST[nibble]
    if l_index < 0:
        l_index = 0
    elif l_index > 88:
        l_index = 88
    sign = nibble & 8
    delta = nibble & 7
    diff = ((2 * delta + 1) * step) >> 3
    if sign:
        predictor -= diff
    else:
        predictor += diff
    return l_index, clip_int16(predictor)


def clip_int16(value: int) -> int:
    return ((value >> 31) ^ 0x7FFF
            if (value + 0x8000) & ~0xFFFF
            else value)


def decode_block(block, channels, indices=None, predictors=None):
    result = b''
    indices = [0] * channels or indices
    predictors = [0] * channels or predictors
    for i in range(0, len(block)):
        # FIXME works only for one channel stream!
        indices[0], predictors[0] = _decode_sample(block[i] >> 4, indices[0], predictors[0])
        result += struct.pack(b'h', predictors[0])
        indices[0], predictors[0] = _decode_sample(block[i] & 0x0F, indices[0], predictors[0])
        result += struct.pack(b'h', predictors[0])
    return result


__all__ = ["decode_block"]
