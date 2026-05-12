# **NFS 4 High Stakes file specs** #

*Last time updated: 2026-05-12 08:14:33.611736+00:00*


# **Info by file extensions** #

**\*.FFN** bitmap font. [FfnFont](#ffnfont)
        
**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.VIV** archive with some data. [BigfBlock](#bigfblock)

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #
## **Archives** ##
### **ShpiBlock** ###
#### **Size**: 16..? bytes ####
#### **Description**: A container of images and palettes for them ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "SHPI" | Resource ID |
| 4 | **length** | 4 | 4-bytes unsigned integer (little endian) | The length of this SHPI block in bytes |
| 8 | **num_items** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 12 | **shpi_dir** | 4 | UTF-8 string | One of: "LN32", "GIMX", "WRAP". The purpose is unknown |
| 16 | **items_descr** | num_items\*8 | Array of `num_items` items<br/>Item size: 8 bytes<br/>Item type: 8-bytes record, first 4 bytes is a UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | An array of items, each of them represents name of SHPI item (image or palette) and offset to item data in file, relatively to SHPI block start (where resource id string is presented). Names are not always unique |
| 16 + num_items\*8 | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets to some of the entries are defined in `items_descr` block. Between them there can be non-indexed entries (palettes and texts). Possible item types:<br/>- [EacImage](#eacimage)<br/>- [EacPalette](#eacpalette) |
### **BigfBlock** ###
#### **Size**: 16..? bytes ####
#### **Description**: A block-container with various data: image archives, GEO geometries, sound banks, other BIGF blocks... ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "BIGF" | Resource ID |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | The length of this BIGF block in bytes |
| 8 | **num_items** | 4 | 4-bytes unsigned integer (big endian) | An amount of items |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **items_descr** | num_items\*9..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | - |
| 16 + num_items\*9..? | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets and lengths are defined in previous block. Possible item types:<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file<br/>- [BigfBlock](#bigfblock) |
### **BigfItemDescriptionBlock** ###
#### **Size**: 9..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | - |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | - |
| 8 | **name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | - |
## **Images** ##
### **EacImage** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>109 (0x6d): 16Bit_4444 color format bitmap<br/>120 (0x78): 16Bit_0565 color format bitmap<br/>121 (0x79): 4Bit (swapped)<br/>122 (0x7a): 4Bit<br/>123 (0x7b): 8Bit<br/>125 (0x7d): 32Bit color format bitmap<br/>126 (0x7e): 16Bit_1555 color format bitmap<br/>127 (0x7f): 24Bit color format bitmap</details> | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+<pixel_byteness>\*width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **pivot** | 4 | Point in 2D space (x,y), where each coordinate is: 2-bytes unsigned integer (little endian) | Seems like x coordinate is not used at all. y coordinate is used in horizon textures in TNFS FAM files: higher value = image as horizon will be put higher on the screen. Seems to affect only open tracks |
| 12 | **position** | 4 | Point in 2D space (x,y), where each coordinate is: 2-bytes unsigned integer (little endian) | Bitmap position on screen. Used for menu/dash sprites. Unknown for others |
| 16 | **bitmap** | width \* height \* pixel_byteness | Bytes | Pixel color table. For 8Bit bitmap each value represents an index of color in the attached palette. Palette can be stored: <br/>- right after 8Bit image<br/>- as !pal/!PAL in the same SHPI<br/>- in a different SHPI before this one (if it is WWWW archive)<br/>- even in different QFS file (TNFS, CONTROL directory).<br/>Color model is selected according to `resource_id` field. Color models are described [here](eac_colors.md) |
### **EacPalette** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black: thy are reserved for cop car siren ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>34 (0x22): 24BitDos color format palette<br/>36 (0x24): 24Bit color format palette<br/>41 (0x29): 16BitUnk color format palette<br/>42 (0x2a): 32Bit color format palette<br/>45 (0x2d): 16Bit_1555 color format palette</details> | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equals to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | ? | Type according to enum `resource_id`:<br/>- Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (big endian)<br/>- Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (big endian)<br/>- Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `num_colors` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian)<br/>- Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Colors LUT. Color model is selected according to `resource_id` field. Color models are described [here](eac_colors.md) |
## **Fonts** ##
### **FfnFont** ###
#### **Size**: 48..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. One of ['"FNTF"', '"FNTP"', '"FNTS"', '"FNTX"', '"FNTM"', '"FNTG"', '"FNTA"', '"FntF"', '"FntP"', '"FntS"', '"FntX"', '"FntM"', '"FntG"', '"FntA"'] | Resource ID |
| 4 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | The length of this FFN block in bytes. Does not include "remaining_bytes" length. For older versions (I set version <= 101, but it can be anywhere < 309), "padding_2" length is not included as well |
| 8 | **version** | 2 | 2-bytes unsigned integer (little endian) | - |
| 10 | **num_glyphs** | 2 | 2-bytes unsigned integer (little endian) | Amount of symbols, defined in this font |
| 12 | **flags** | 4 | Sub-byte compound block (little endian):<br/>1-bit flag "antialiased"<br/>1-bit flag "dropshadow"<br/>1-bit flag "outline"<br/>1-bit flag "vram"<br/>4-bits int "drawpad"<br/>2-bits enum:<br/>&nbsp;&nbsp;- 0: Roman (english)<br/>&nbsp;&nbsp;- 1: Ideographic (Kanji)<br/>&nbsp;&nbsp;- 2: Hanging (Arabic)<br/>&nbsp;&nbsp;- 3: Unknown<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: Horizontal<br/>&nbsp;&nbsp;- 1: Vertical<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: LTR<br/>&nbsp;&nbsp;- 1: RTL<br/>4-bits int "layoutpad"<br/>2-bits enum:<br/>&nbsp;&nbsp;- 0: ASCII<br/>&nbsp;&nbsp;- 1: Unicode<br/>&nbsp;&nbsp;- 2: Shift-JIS<br/>&nbsp;&nbsp;- 3: Reserved<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: 12-bytes<br/>&nbsp;&nbsp;- 1: 16-bytes<br/>13-bits int "pad" | - |
| 16 | **center** | 2 | Point in 2D space (x,y), where each coordinate is: 1-byte unsigned integer | - |
| 18 | **ascent** | 1 | 1-byte unsigned integer | - |
| 19 | **descent** | 1 | 1-byte unsigned integer | - |
| 20 | **definitions_ptr** | 4 | 4-bytes unsigned integer (little endian) | Pointer to definitions block |
| 24 | **kernings_ptr** | 4 | 4-bytes unsigned integer (little endian) | Pointer to kernings. 0 if there is no kernings table |
| 28 | **bdata_ptr** | 4 | 4-bytes unsigned integer (little endian) | Pointer to bitmap block |
| 32 | **padding_0** | up to offset definitions_ptr | Padding bytes | Unknown purpose |
| definitions_ptr | **definitions** | num_glyphs\*11..num_glyphs\*17 | Array of `num_glyphs` items<br/>Item type: [GlyphDefinition](#glyphdefinition) | Definitions of chars in this bitmap font |
| ? | **padding_1** | 0..up to offset kernings_ptr | Optional (if kernings_ptr != 0): Padding bytes | Unknown purpose |
| ? | **kernings** | 0..? | Optional (if kernings_ptr != 0): Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [KerningItem](#kerningitem) | - |
| ? | **padding_2** | up to offset bdata_ptr | Padding bytes | Unknown purpose |
| bdata_ptr | **bitmap** | 16..? | [EacImage](#eacimage) | Font atlas bitmap data |
| ? | **padding_3** | up to offset block_size + padding_2 length (version <= 101) | Padding bytes | Unknown purpose |
| block_size + padding_2 length (version <= 101) | **remaining_bytes** | remaining bytes | Bytes | Unknown purpose |
### **GlyphDefinition** ###
#### **Size**: 11..17 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **code** | 2 | 2-bytes unsigned integer (little endian) | Code of symbol |
| 2 | **width** | 1 | 1-byte unsigned integer | Width of symbol in font bitmap |
| 3 | **height** | 1 | 1-byte unsigned integer | Height of symbol in font bitmap |
| 4 | **x** | 2 | 2-bytes unsigned integer (little endian) | Position (x) of symbol in font bitmap |
| 6 | **y** | 2 | 2-bytes unsigned integer (little endian) | Position (y) of symbol in font bitmap |
| 8 | **advance** | 1 | 1-byte unsigned integer | Gap between this symbol and next one in rendered text |
| 9 | **x_offset** | 1 | 1-byte signed integer | Offset (x) for drawing the character image |
| 10 | **y_offset** | 1 | 1-byte signed integer | Offset (y) for drawing the character image |
| 11 | **num_kern** | 0..1 | Optional (if ^^version >= 300): 1-byte unsigned integer | Number of kerning pairs for this glyph |
| 11..12 | **pad** | 0..1 | Optional (if ^^version < 300): 1-byte unsigned integer | Padding |
| 11..13 | **kern_index** | 0..2 | Optional (if ^^flags/format == 16-bytes): 2-bytes unsigned integer (little endian) | Index in kerning table? |
| 11..15 | **x_advance** | 0..2 | Optional (if ^^flags/format == 16-bytes): 2-bytes unsigned integer (little endian) | Gap between this symbol and next one in rendered text? |
### **KerningItem** ###
#### **Size**: 4 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **left** | 2 | 2-bytes unsigned integer (little endian) | Code of left glyph |
| 2 | **kerning** | 1 | 1-byte signed integer | - |
| 3 | **right** | 1 | 1-byte unsigned integer | Code of right glyph |
