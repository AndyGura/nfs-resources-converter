"""
EA-XA ADPCM decoder (EA sound banks *.BNK of NFS2 SE, NFS3, NFS4, NFS6), as described by vgmstream
(`ea_xa_decoder.c`) and https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2).

A frame holds 28 samples per channel. Version 1 (headers without the version tag 0x80):
- mono: 0x0F bytes, byte 0: coefficient index (high nibble) and shift (low nibble), then 14 bytes of 4-bit samples,
  high nibble first
- stereo: 0x1E bytes, byte 0: coefficient indices (left: high nibble, right: low nibble), byte 1: shifts, then 28
  bytes, each one a left (high nibble) and a right (low nibble) sample
Version 2 (header version tag 0x80 = 1, mono only): like version 1 mono, but a frame starting with 0xEE holds two
16-bit big endian history samples and 28 uncompressed 16-bit big endian samples (0x3D bytes)
"""

from typing import List

EA_XA_COEFFICIENTS = [(0, 0), (240, 0), (460, -208), (392, -220)]


def _clamp16(v: int) -> int:
    return -32768 if v < -32768 else 32767 if v > 32767 else v


def _decode_nibbles(nibbles, coefficient_index: int, shift: int, history, rounding: int, out: List[int]):
    coef1, coef2 = EA_XA_COEFFICIENTS[coefficient_index & 3]
    hist1, hist2 = history
    shift += 8
    for nibble in nibbles:
        sample = ((nibble << 28) - ((nibble & 8) << 29)) >> shift
        sample = _clamp16((sample + coef1 * hist1 + coef2 * hist2 + rounding) >> 8)
        out.append(sample)
        hist2, hist1 = hist1, sample
    return hist1, hist2


def decode_v1(data: bytes, channels: int, num_samples: int) -> bytes:
    """Decodes EA-XA v1 to 16-bit little endian PCM, channels interleaved"""
    if channels not in (1, 2):
        raise NotImplementedError(f'EA-XA v1 with {channels} channels is not supported')
    frame_size = 0x0F * channels
    histories = [(0, 0)] * channels
    decoded = [[] for _ in range(channels)]
    for frame_start in range(0, len(data) - frame_size + 1, frame_size):
        frame = data[frame_start : frame_start + frame_size]
        if channels == 1:
            nibbles = [n for b in frame[1:] for n in (b >> 4, b & 0xF)]
            histories[0] = _decode_nibbles(nibbles, frame[0] >> 4, frame[0] & 0xF, histories[0], 0, decoded[0])
        else:
            for ch in range(2):
                nibbles = [(b >> 4) if ch == 0 else (b & 0xF) for b in frame[2:]]
                coefficient_index = (frame[0] >> 4) if ch == 0 else (frame[0] & 0xF)
                shift = (frame[1] >> 4) if ch == 0 else (frame[1] & 0xF)
                histories[ch] = _decode_nibbles(nibbles, coefficient_index, shift, histories[ch], 0, decoded[ch])
        if len(decoded[0]) >= num_samples:
            break
    return _interleave(decoded, num_samples)


def decode_v2(data: bytes, num_samples: int) -> bytes:
    """Decodes mono EA-XA v2 to 16-bit little endian PCM"""
    out = []
    history = (0, 0)
    pos = 0
    while len(out) < num_samples and pos < len(data):
        if data[pos] == 0xEE:
            frame = data[pos : pos + 0x3D]
            if len(frame) < 0x3D:
                break
            history = (
                int.from_bytes(frame[1:3], 'big', signed=True),
                int.from_bytes(frame[3:5], 'big', signed=True),
            )
            out.extend(int.from_bytes(frame[5 + i * 2 : 7 + i * 2], 'big', signed=True) for i in range(28))
            pos += 0x3D
        else:
            frame = data[pos : pos + 0x0F]
            if len(frame) < 0x0F:
                break
            nibbles = [n for b in frame[1:] for n in (b >> 4, b & 0xF)]
            history = _decode_nibbles(nibbles, frame[0] >> 4, frame[0] & 0xF, history, 128, out)
            pos += 0x0F
    return _interleave([out], num_samples)


def _interleave(channels_samples: List[List[int]], num_samples: int) -> bytes:
    res = bytearray()
    for i in range(min(num_samples, min(len(x) for x in channels_samples))):
        for ch in channels_samples:
            res += (ch[i] & 0xFFFF).to_bytes(2, 'little')
    return bytes(res)
