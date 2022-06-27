# **File specs** #
## **Bitmaps** ##
### **Bitmap16Bit0565** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x78 | Resource ID |
| 1 | **block_size** | 3 | 3-byte unsigned integer | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 6 | **height** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-byte unsigned integer | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-byte unsigned integer | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 2 * (width * height) | Array of width * height items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 2\*width\*height) | Array of block_size - (16 + 2\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap8Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x7b | Resource ID |
| 1 | **block_size** | 3 | 3-byte unsigned integer | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 6 | **height** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-byte unsigned integer | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-byte unsigned integer | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width * height | Array of width * height items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Color indexes of bitmap pixels. The actual colors are in assigned to this bitmap palette |
| 16..? | **trailing_bytes** | block_size - (16 + width\*height) | Array of block_size - (16 + width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
| 16..? | **palette** (optional) | 0..1040 | One of types:<br/>[PaletteReference](#palettereference)<br/>[Palette24BitDos](#palette24bitdos)<br/>[Palette24Bit](#palette24bit)<br/>[Palette32Bit](#palette32bit)<br/>[Palette16Bit](#palette16bit) | Palette, assigned to this bitmap or reference to external palette?. The exact mechanism of choosing the correct palette (except embedded one) is unknown |
### **Bitmap32Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x7d | Resource ID |
| 1 | **block_size** | 3 | 3-byte unsigned integer | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 6 | **height** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-byte unsigned integer | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-byte unsigned integer | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 4 * (width * height) | Array of width * height items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 4\*width\*height) | Array of block_size - (16 + 4\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap16Bit1555** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x7e | Resource ID |
| 1 | **block_size** | 3 | 3-byte unsigned integer | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 6 | **height** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-byte unsigned integer | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-byte unsigned integer | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 2 * (width * height) | Array of width * height items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 1555 color, arrrrrgg_gggbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 2\*width\*height) | Array of block_size - (16 + 2\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap24Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x7f | Resource ID |
| 1 | **block_size** | 3 | 3-byte unsigned integer | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 6 | **height** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-byte unsigned integer | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-byte unsigned integer | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 3 * (width * height) | Array of width * height items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (little-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 3\*width\*height) | Array of block_size - (16 + 3\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
## **Palettes** ##
### **PaletteReference** ###
#### **Size**: 8 bytes ####
#### **Description**: Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. Probably a reference to palette which should be used, that's why named so ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x7c | Resource ID |
| 1 | **unknowns** | 7 | Array of 7 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
### **Palette24BitDos** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x22 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** (optional) | 3 * (0..256) | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
### **Palette24Bit** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x24 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** (optional) | 3 * (0..256) | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (big-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..1040 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x2a | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** (optional) | 4 * (0..256) | Array of 0..256 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette16Bit** ###
#### **Size**: 16..528 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x2d | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** (optional) | 2 * (0..256) | Array of 0..256 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors LUT |
