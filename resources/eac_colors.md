# EA Games Color Models

This document describes various color models used in EA games.

## 4-bit (bitmap resource ids: 0x40, 0x79, 0x7A)
**Description**: Used for single-channel images, 4 bits per pixel. If resource id is 0x79, then values in each byte are swapped.

**Found in games**:
- `TNFS`
- `NFS2`
- `NFS2 SE`
- `NFS3`
- `NFS4`


## 8-bit (bitmap resource id: 0x7B)
**Description**: Used for single-channel images, 8 bits per pixel. Usually used for palette indices, but I found it also used for 
grayscale images in some cases.

**Found in games**:
- `TNFS`
- `NFS2`
- `NFS2 SE`
- `NFS3`
- `NFS4`
- `NFS5`
- `NFS6`

## 16-bit Colors

### 16Bit_4444 (bitmap resource id: 0x6D)
- **Description**: 16-bit 4444 color.
- **Bit layout**: `aaaarrrr_ggggbbbb` (2 bytes).

**Found in games**:
- `NFS5`

### 16Bit_0565 (bitmap resource id: 0x78)
- **Description**: 16-bit 0565 color.
- **Bit layout**: `rrrrrggg_gggbbbbb` (2 bytes).
- **Special Case**: `0x7c0` (corresponding to `0x00FB00` RGB) is treated as fully transparent (Alpha = 0). Tested on NFS2 tracks.

**Found in games**:
- `NFS2`
- `NFS2 SE`
- `NFS3`
- `NFS4`
- `NFS5`

### 16Bit_1555 (bitmap resource id: 0x7E, palette resource id: 0x2D)
- **Description**: 16-bit 1555 color.
- **Bit layout**: `arrrrrgg_gggbbbbb` (2 bytes).

**Found in games**:
- `NFS2 SE`
- `NFS3`
- `NFS4`
- `NFS5`

### 16Bit_0565 (palette resource id: 0x29)
- **Description**: 16-bit 0565 color.
- **Bit layout**: `rrrrrggg_gggbbbbb` (2 bytes).

**Found in games**:
- `NFS2 SE`
- `NFS4`
- `NFS5`

## 24-bit Colors

### 24Bit (little-endian in bitmap resource id 0x7F, big-endian in palette resource id 0x24)
- **Description**: Standard 24-bit color.
- **Bit layout**: `rrrrrrrr_gggggggg_bbbbbbbb` (3 bytes).

**Found in games**:
- `TNFS` in palettes only?
- `NFS2`
- `NFS2 SE`
- `NFS3` in bitmaps only?
- `NFS4` in bitmaps only?
- `NFS5` in bitmaps only?

### 24BitDos (palette resource id 0x22)
- **Description**: 24-bit DOS color format.
- **Bit layout**: `00rrrrrr_00gggggg_00bbbbbb` (3 bytes, big-endian).

**Found in games**:
- `TNFS`


## 32-bit Colors

### 32Bit (bitmap resource id 0x7D, palette resource id 0x2A)
- **Description**: 32-bit ARGB color.
- **Bit layout**: `aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb` (4 bytes).

**Found in games**:
- `NFS2`
- `NFS2 SE`
- `NFS3`
- `NFS4`
- `NFS5`
- `NFS6`

