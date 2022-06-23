# **File specs** #
## **Bitmaps** ##
### **Bitmap16Bit1555** ###
#### **Size**: 16..inf bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x7e | Resource ID |
| 1 | **block_size** | 3 | 3-byte unsigned integer | Bitmap block size 16+2\*width\*height, but not always |
| 4 | **width** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 6 | **height** | 2 | 2-byte unsigned integer | Bitmap width in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-byte unsigned integer | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-byte unsigned integer | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 0..inf | Array of <width * height> items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 1555 color, arrrrrgg_gggbbbbb | Colors of bitmap pixels |
## **Palettes** ##
### **Palette24BitDos** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x22 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 0..768 | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
### **Palette24Bit** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x24 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 0..768 | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color, rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..1040 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x2a | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 0..1024 | Array of 0..256 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette16Bit** ###
#### **Size**: 16..528 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x2d | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 0..512 | Array of 0..256 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors LUT |
