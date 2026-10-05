"""S3TC (DXT1/DXT3/DXT5) block compression. Pixels are RGBA ints (0xRRGGBBAA), row by row, the same
internal representation `EacImage` uses for true color bitmaps."""

from collections import OrderedDict
from math import ceil
from typing import List

import numpy as np

DXT_BLOCK_BYTES = {'DXT1': 8, 'DXT3': 16, 'DXT5': 16}

# Compression is lossy, so original bytes of recently decoded images are kept: writing back unchanged pixels
# reproduces the original data instead of recompressing it
_DECODED_CACHE_SIZE = 4096
_decoded_cache: 'OrderedDict[tuple, bytes]' = OrderedDict()


def _cache_key(dxt_format: str, width: int, height: int, pixels: List[int]) -> tuple:
    return dxt_format, width, height, len(pixels), hash(tuple(pixels))


def dxt_byte_len(dxt_format: str, width: int, height: int) -> int:
    return max(1, ceil(width / 4)) * max(1, ceil(height / 4)) * DXT_BLOCK_BYTES[dxt_format]


def _rgb565_to_rgb888(c: np.ndarray) -> np.ndarray:
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], axis=-1).astype(np.int32)


def _rgb888_to_rgb565(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.int32)
    r = (rgb[..., 0] * 31 + 127) // 255
    g = (rgb[..., 1] * 63 + 127) // 255
    b = (rgb[..., 2] * 31 + 127) // 255
    return ((r << 11) | (g << 5) | b).astype(np.uint16)


def _blocks_to_pixels(blocks_rgba: np.ndarray, width: int, height: int) -> List[int]:
    # blocks_rgba: (blocks_y, blocks_x, 16, 4) -> image (height, width, 4)
    by, bx = blocks_rgba.shape[:2]
    image = blocks_rgba.reshape(by, bx, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(by * 4, bx * 4, 4)
    image = image[:height, :width].astype(np.uint32)
    packed = (image[..., 0] << 24) | (image[..., 1] << 16) | (image[..., 2] << 8) | image[..., 3]
    return [int(x) for x in packed.reshape(-1)]


def _pixels_to_blocks(pixels: List[int], width: int, height: int) -> np.ndarray:
    # returns (blocks_y, blocks_x, 16, 4), edge pixels repeated into the padding
    packed = np.asarray(pixels, dtype=np.uint32).reshape(height, width)
    image = np.stack([(packed >> 24) & 0xFF, (packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF], axis=-1)
    bx, by = max(1, ceil(width / 4)), max(1, ceil(height / 4))
    image = np.pad(image, ((0, by * 4 - height), (0, bx * 4 - width), (0, 0)), mode='edge')
    return image.reshape(by, 4, bx, 4, 4).transpose(0, 2, 1, 3, 4).reshape(by, bx, 16, 4).astype(np.int32)


def _decode_color_blocks(raw: np.ndarray, allow_1bit_alpha: bool) -> np.ndarray:
    # raw: (n, 8) uint8 -> (n, 16, 4)
    c0 = raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8)
    c1 = raw[:, 2].astype(np.int32) | (raw[:, 3].astype(np.int32) << 8)
    indices = (
        raw[:, 4].astype(np.uint32)
        | (raw[:, 5].astype(np.uint32) << 8)
        | (raw[:, 6].astype(np.uint32) << 16)
        | (raw[:, 7].astype(np.uint32) << 24)
    )
    rgb0, rgb1 = _rgb565_to_rgb888(c0), _rgb565_to_rgb888(c1)
    four_colors = (c0 > c1) | (not allow_1bit_alpha)
    four = four_colors[:, None]
    rgb2 = np.where(four, (2 * rgb0 + rgb1) // 3, (rgb0 + rgb1) // 2)
    rgb3 = np.where(four, (rgb0 + 2 * rgb1) // 3, 0)
    alpha = np.full(len(raw), 255, dtype=np.int32)
    palette = np.stack(
        [
            np.concatenate([rgb0, alpha[:, None]], axis=1),
            np.concatenate([rgb1, alpha[:, None]], axis=1),
            np.concatenate([rgb2, alpha[:, None]], axis=1),
            np.concatenate([rgb3, np.where(four_colors, 255, 0)[:, None]], axis=1),
        ],
        axis=1,
    )  # (n, 4, 4)
    pixel_indices = (indices[:, None] >> (2 * np.arange(16, dtype=np.uint32))) & 3
    return np.take_along_axis(palette, pixel_indices.astype(np.int64)[:, :, None], axis=1)


def _decode_dxt5_alpha(raw: np.ndarray) -> np.ndarray:
    # raw: (n, 8) uint8 -> (n, 16)
    a0 = raw[:, 0].astype(np.int32)
    a1 = raw[:, 1].astype(np.int32)
    bits = np.zeros(len(raw), dtype=np.uint64)
    for i in range(6):
        bits |= raw[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    eight = (a0 > a1)[:, None]
    k = np.arange(1, 7, dtype=np.int32)[None, :]
    interpolated8 = ((7 - k) * a0[:, None] + k * a1[:, None]) // 7
    k4 = np.arange(1, 5, dtype=np.int32)[None, :]
    interpolated6 = ((5 - k4) * a0[:, None] + k4 * a1[:, None]) // 5
    palette6 = np.concatenate(
        [interpolated6, np.zeros((len(raw), 1), np.int32), np.full((len(raw), 1), 255, np.int32)], axis=1
    )
    palette = np.concatenate([a0[:, None], a1[:, None], np.where(eight, interpolated8, palette6)], axis=1)
    pixel_indices = (bits[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)
    return np.take_along_axis(palette, pixel_indices.astype(np.int64), axis=1)


def decode_dxt(dxt_format: str, width: int, height: int, data: bytes) -> List[int]:
    bx, by = max(1, ceil(width / 4)), max(1, ceil(height / 4))
    block_len = DXT_BLOCK_BYTES[dxt_format]
    raw = np.frombuffer(bytes(data), dtype=np.uint8, count=bx * by * block_len).reshape(-1, block_len)
    if dxt_format == 'DXT1':
        rgba = _decode_color_blocks(raw, allow_1bit_alpha=True)
    else:
        rgba = _decode_color_blocks(raw[:, 8:], allow_1bit_alpha=False)
        if dxt_format == 'DXT3':
            nibbles = np.stack([raw[:, :8] & 0x0F, raw[:, :8] >> 4], axis=-1).reshape(-1, 16).astype(np.int32)
            rgba[:, :, 3] = nibbles * 17
        else:
            rgba[:, :, 3] = _decode_dxt5_alpha(raw[:, :8])
    pixels = _blocks_to_pixels(rgba.reshape(by, bx, 16, 4), width, height)
    _decoded_cache[_cache_key(dxt_format, width, height, pixels)] = raw.tobytes()
    if len(_decoded_cache) > _DECODED_CACHE_SIZE:
        _decoded_cache.popitem(last=False)
    return pixels


def _fit_color_endpoints(rgb: np.ndarray, transparent: np.ndarray, max_rgb: np.ndarray, min_rgb: np.ndarray):
    """Color block with given endpoint colors: (c0, c1, pixel indices, squared error per block)"""
    all_transparent = transparent.all(axis=1)
    max_rgb = np.where(all_transparent[:, None], 0, max_rgb)
    min_rgb = np.where(all_transparent[:, None], 0, min_rgb)
    c_max, c_min = _rgb888_to_rgb565(max_rgb).astype(np.int32), _rgb888_to_rgb565(min_rgb).astype(np.int32)
    has_transparency = transparent.any(axis=1)
    # 4-color mode requires c0 > c1, 3-color mode (with transparency) requires c0 <= c1
    c0 = np.where(has_transparency, np.minimum(c_min, c_max), np.maximum(c_min, c_max))
    c1 = np.where(has_transparency, np.maximum(c_min, c_max), np.minimum(c_min, c_max))
    four = (c0 > c1)[:, None]
    rgb0, rgb1 = _rgb565_to_rgb888(c0), _rgb565_to_rgb888(c1)
    palette = np.stack(
        [
            rgb0,
            rgb1,
            np.where(four, (2 * rgb0 + rgb1) // 3, (rgb0 + rgb1) // 2),
            np.where(four, (rgb0 + 2 * rgb1) // 3, 10000),
        ],
        axis=1,
    )  # (n, 4, 3)
    distances = ((rgb[:, :, None, :].astype(np.int64) - palette[:, None, :, :]) ** 2).sum(axis=-1)  # (n, 16, 4)
    indices = distances.argmin(axis=-1)
    error = np.where(transparent, 0, distances.min(axis=-1)).sum(axis=1)
    indices = np.where(transparent, 3, indices).astype(np.uint32)
    return c0, c1, indices, error


def _encode_color_blocks(blocks: np.ndarray, use_1bit_alpha: bool) -> np.ndarray:
    # blocks: (n, 16, 4) -> (n, 8) uint8. Endpoint candidates: corners of the block's color bounding box, and the
    # block's extreme colors along its principal color axis; the one with smaller error wins
    transparent = (blocks[:, :, 3] < 128) if use_1bit_alpha else np.zeros(blocks.shape[:2], dtype=bool)
    rgb = blocks[:, :, :3]
    block_indices = np.arange(len(blocks))

    bbox = _fit_color_endpoints(
        rgb,
        transparent,
        np.where(transparent[:, :, None], -1, rgb).max(axis=1),
        np.where(transparent[:, :, None], 256, rgb).min(axis=1),
    )

    weights = (~transparent).astype(np.float64)[:, :, None]
    mean = (rgb * weights).sum(axis=1) / np.maximum(weights.sum(axis=1), 1)
    centered = (rgb - mean[:, None, :]) * weights
    covariance = np.einsum('nki,nkj->nij', centered, centered)
    # power iteration, starting from the color farthest from the mean
    axis = centered[block_indices, (centered**2).sum(axis=2).argmax(axis=1)] + 1e-6
    for _ in range(8):
        axis = np.einsum('nij,nj->ni', covariance, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-9)
    projection = np.einsum('nki,ni->nk', rgb - mean[:, None, :], axis)
    principal = _fit_color_endpoints(
        rgb,
        transparent,
        rgb[block_indices, np.where(transparent, -1e9, projection).argmax(axis=1)],
        rgb[block_indices, np.where(transparent, 1e9, projection).argmin(axis=1)],
    )

    use_bbox = bbox[3] <= principal[3]
    c0 = np.where(use_bbox, bbox[0], principal[0])
    c1 = np.where(use_bbox, bbox[1], principal[1])
    indices = np.where(use_bbox[:, None], bbox[2], principal[2]).astype(np.uint32)
    packed_indices = (indices << (2 * np.arange(16, dtype=np.uint32))).sum(axis=1, dtype=np.uint64).astype(np.uint32)
    out = np.zeros((len(blocks), 8), dtype=np.uint8)
    out[:, 0], out[:, 1] = c0 & 0xFF, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 0xFF, c1 >> 8
    for i in range(4):
        out[:, 4 + i] = (packed_indices >> (8 * i)) & 0xFF
    return out


def _encode_dxt5_alpha(alpha: np.ndarray) -> np.ndarray:
    # alpha: (n, 16) -> (n, 8) uint8, 8-alpha mode (a0 > a1) or a single value when a0 == a1
    a0 = alpha.max(axis=1)
    a1 = alpha.min(axis=1)
    k = np.arange(1, 7, dtype=np.int32)[None, :]
    palette = np.concatenate([a0[:, None], a1[:, None], ((7 - k) * a0[:, None] + k * a1[:, None]) // 7], axis=1)
    indices = np.abs(alpha[:, :, None] - palette[:, None, :]).argmin(axis=-1).astype(np.uint64)
    indices[a0 == a1] = 0
    bits = (indices << (np.uint64(3) * np.arange(16, dtype=np.uint64))).sum(axis=1, dtype=np.uint64)
    out = np.zeros((len(alpha), 8), dtype=np.uint8)
    out[:, 0], out[:, 1] = a0, a1
    for i in range(6):
        out[:, 2 + i] = (bits >> np.uint64(8 * i)) & np.uint64(0xFF)
    return out


def encode_dxt(dxt_format: str, width: int, height: int, pixels: List[int]) -> bytes:
    """Pixels decoded by `decode_dxt` give back the original bytes; anything else goes through a simple compressor
    (no endpoint refinement)"""
    original = _decoded_cache.get(_cache_key(dxt_format, width, height, pixels))
    if original is not None:
        return original
    blocks = _pixels_to_blocks(pixels, width, height)
    by, bx = blocks.shape[:2]
    blocks = blocks.reshape(by * bx, 16, 4)
    if dxt_format == 'DXT1':
        out = _encode_color_blocks(blocks, use_1bit_alpha=True)
    else:
        color = _encode_color_blocks(blocks, use_1bit_alpha=False)
        if dxt_format == 'DXT3':
            nibbles = (blocks[:, :, 3] >> 4).astype(np.uint8).reshape(-1, 8, 2)
            alpha = nibbles[:, :, 0] | (nibbles[:, :, 1] << 4)
        else:
            alpha = _encode_dxt5_alpha(blocks[:, :, 3])
        out = np.concatenate([alpha, color], axis=1)
    return out.astype(np.uint8).tobytes()
