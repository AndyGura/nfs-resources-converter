# **File specs** #
## **Palettes** ##
### **Palette24BitDos** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x22 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte field | Unknown purpose |
| 16 | **colors** | 0..768 | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
### **Palette24Bit** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x24 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte field | Unknown purpose |
| 16 | **colors** | 0..768 | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color, rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..1040 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x2a | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte field | Unknown purpose |
| 16 | **colors** | 0..1024 | Array of 0..256 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette16Bit** ###
#### **Size**: 16..528 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Always == 0x2d | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte field | Unknown purpose |
| 16 | **colors** | 0..512 | Array of 0..256 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors LUT |
