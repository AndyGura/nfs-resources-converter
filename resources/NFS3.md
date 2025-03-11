# **NFS 3 Hot Pursuit file specs** #

*Last time updated: 2025-03-11 22:17:27.145553+00:00*


# **Info by file extensions** #

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FRD** main track file. [FrdMap](#frdmap)

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
| 16 + num_items\*8 | **children** | ? | Array of `num_items + ?` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [Bitmap4Bit](#bitmap4bit)<br/>- [Bitmap8Bit](#bitmap8bit)<br/>- [Bitmap16Bit0565](#bitmap16bit0565)<br/>- [Bitmap16Bit1555](#bitmap16bit1555)<br/>- [Bitmap24Bit](#bitmap24bit)<br/>- [Bitmap32Bit](#bitmap32bit)<br/>- [Palette16Bit](#palette16bit)<br/>- [Palette32Bit](#palette32bit)<br/>- Bytes | A part of block, where items data is located. Offsets to some of the entries are defined in `items_descr` block. Between them there can be non-indexed entries (palettes and texts) |
### **BigfBlock** ###
#### **Size**: 16..? bytes ####
#### **Description**: A block-container with various data: image archives, GEO geometries, sound banks, other BIGF blocks... ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "BIGF" | Resource ID |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | The length of this BIGF block in bytes |
| 8 | **num_items** | 4 | 4-bytes unsigned integer (big endian) | An amount of items |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **items_descr** | num_items\*8..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | - |
| 16 + num_items\*8..? | **children** | ? | Array of `num_items` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [ShpiBlock](#shpiblock)<br/>- [BigfBlock](#bigfblock)<br/>- Bytes |  |
### **BigfItemDescriptionBlock** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | - |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | - |
| 8 | **name** | ? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | - |
## **Maps** ##
### **FrdMap** ###
#### **Size**: 36..? bytes ####
#### **Description**: Main track file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk** | 28 | Bytes | Unknown header |
| 28 | **num_blocks** | 4 | 4-bytes unsigned integer (little endian) | Number of blocks |
| 32 | **blocks** | (num_blocks+1)\*1316..? | Array of `num_blocks+1` items<br/>Item type: [FrdBlock](#frdblock) | - |
| 32 + (num_blocks+1)\*1316..? | **polygon_blocks** | (num_blocks+1)\*44..? | Array of `num_blocks+1` items<br/>Item type: [FrdPolyBlock](#frdpolyblock) | - |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44..? | **extraobject_blocks** | (4\*(num_blocks+1))\*4..? | Array of `4*(num_blocks+1)` items<br/>Item size: 4..? bytes<br/>Item type: Array, prefixed with length field<br/>Item type: [ExtraObjectData](#extraobjectdata) | - |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1))\*4..? | **num_texture_blocks** | 4 | 4-bytes unsigned integer (little endian) | Length of texture_blocks array |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1))\*4 + 4..? | **texture_blocks** | num_texture_blocks\*47 | Array of `num_texture_blocks` items<br/>Item type: [TextureBlock](#textureblock) | - |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1))\*4 + 4 + num_texture_blocks\*47..? | **rest** | custom_func | Bytes | - |
### **FrdBlock** ###
#### **Size**: 1316..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **center** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | - |
| 12 | **bounds** | 48 | Array of `4` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | Block bounding rectangle |
| 60 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Number of vertices |
| 64 | **num_vertices_high** | 4 | 4-bytes unsigned integer (little endian) | Number of high-res vertices |
| 68 | **num_vertices_low** | 4 | 4-bytes unsigned integer (little endian) | Number of low-res vertices |
| 72 | **num_vertices_med** | 4 | 4-bytes unsigned integer (little endian) | Number of medium-res vertices |
| 76 | **num_vertices_dup** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 80 | **num_vertices_obj** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | Vertices |
| 84 + num_vertices\*12 | **vertex_shading** | num_vertices\*4 | Array of `num_vertices` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 | **neighbour_data** | 1200 | Array of `600` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 | **nStartPos** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 | **nPositions** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 | **nPolygons** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 | **nVRoad** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 | **nXobj** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 | **nPolyobj** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 | **nSoundsrc** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 | **nLightsrc** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 | **positions** | nPositions\*8 | Array of `nPositions` items<br/>Item type: [FrdPositionBlock](#frdpositionblock) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + nPositions\*8 | **polyData** | nPolygons\*8 | Array of `nPolygons` items<br/>Item type: [CompoundBlock](#compoundblock) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + nPositions\*8 + nPolygons\*8 | **vroadData** | nVRoad\*12 | Array of `nVRoad` items<br/>Item type: [CompoundBlock](#compoundblock) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + nPositions\*8 + nPolygons\*8 + nVRoad\*12 | **xobj** | nXobj\*20 | Array of `nXobj` items<br/>Item size: 20 bytes<br/>Item type: Bytes | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + nPositions\*8 + nPolygons\*8 + nVRoad\*12 + nXobj\*20 | **polyObj** | nPolyobj\*20 | Array of `nPolyobj` items<br/>Item size: 20 bytes<br/>Item type: Bytes | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + nPositions\*8 + nPolygons\*8 + nVRoad\*12 + nXobj\*20 + nPolyobj\*20 | **soundsrc** | nSoundsrc\*16 | Array of `nSoundsrc` items<br/>Item size: 16 bytes<br/>Item type: Bytes | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 + 1200 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + nPositions\*8 + nPolygons\*8 + nVRoad\*12 + nXobj\*20 + nPolyobj\*20 + nSoundsrc\*16 | **lightsrc** | nLightsrc\*16 | Array of `nLightsrc` items<br/>Item size: 16 bytes<br/>Item type: Bytes | Unknown purpose |
### **FrdPositionBlock** ###
#### **Size**: 8 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon** | 2 | 2-bytes unsigned integer (little endian) | - |
| 2 | **nPolygons** | 1 | 1-byte unsigned integer | - |
| 3 | **unk** | 1 | 1-byte unsigned integer | - |
| 4 | **extraNeighbor1** | 2 | 2-bytes unsigned integer (little endian) | - |
| 6 | **extraNeighbor2** | 2 | 2-bytes unsigned integer (little endian) | - |
### **TextureBlock** ###
#### **Size**: 47 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **width** | 2 | 2-bytes unsigned integer (little endian) | Texture width |
| 2 | **height** | 2 | 2-bytes unsigned integer (little endian) | Texture height |
| 4 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Blending related, hometown covered bridges godrays |
| 8 | **corners** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | 4x planar coordinates == tiling? |
| 40 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 44 | **is_lane** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: default<br/>1: lane</details> | 1 if not a real texture (lane), 0 usually |
| 45 | **texture_id** | 2 | 2-bytes unsigned integer (little endian) | index in QFS file |
## **Bitmaps** ##
### **Bitmap4Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Single-channel image, 4 bits per pixel. Used in FFN font files and some NFS2SE SHPI directories as some small sprites, like "dot". Seems to be always used as alpha channel, so we save it as white image with alpha mask ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7a | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+width\*height/2 + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels. Has to be an even number (at least in the FFN font) |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 4 | Bytes | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | height\*ceil((^width)\*4/8) | Array of `height` items<br/>Item size: ceil((^width)\*4/8) bytes<br/>Item type: Array of `^width` sub-byte numbers. Each number consists of 4 bits | Font atlas bitmap data, array of bitmap rows |
### **Bitmap8Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: 8bit bitmap can be serialized to image only with palette. Basically, for every pixel it uses 8-bit index of color in assigned palette. The tricky part is to determine how the game understands which palette to use. In most cases, if bitmap has embedded palette, it should be used, EXCEPT Autumn Valley fence texture: there embedded palette should be ignored. In all other cases it is tricky even more: it uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, palette can be in a different SHPI before this one. In CONTROL directory most of QFS files use !pal even from different QFS file! It is a mystery how to reliably pick palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7b | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 10 | **pivot_y** | 2 | 2-bytes unsigned integer (little endian) | For "horz" bitmap in TNFS FAM files: Y coordinate of the horizon line on the image. Higher value = image as horizon will be put higher on the screen. Seems to affect only open tracks |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width\*height | Array of `width*height` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Color indexes of bitmap pixels. The actual colors are in assigned to this bitmap palette |
### **Bitmap16Bit0565** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x78 | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 4 | Bytes | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width\*height\*2 | Array of `width*height` items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb. 0x7c0 (0x00FB00 RGB) is always transparent | Colors of bitmap pixels |
### **Bitmap16Bit1555** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7e | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 4 | Bytes | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width\*height\*2 | Array of `width*height` items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 1555 color, arrrrrgg_gggbbbbb | Colors of bitmap pixels |
### **Bitmap24Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7f | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+3\*width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 4 | Bytes | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width\*height\*3 | Array of `width*height` items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (little-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
### **Bitmap32Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7d | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+4\*width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 4 | Bytes | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width\*height\*4 | Array of `width*height` items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
## **Fonts** ##
### **FfnFont** ###
#### **Size**: 48..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "FNTF" | Resource ID |
| 4 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | The length of this FFN block in bytes |
| 8 | **unk0** | 1 | 1-byte unsigned integer. Always == 0x64 | Unknown purpose |
| 9 | **unk1** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 10 | **num_glyphs** | 2 | 2-bytes unsigned integer (little endian) | Amount of symbols, defined in this font |
| 12 | **unk2** | 6 | Bytes | Unknown purpose |
| 18 | **font_size** | 1 | 1-byte unsigned integer | Font size ? |
| 19 | **unk3** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 20 | **line_height** | 1 | 1-byte unsigned integer | Line height ? |
| 21 | **unk4** | 7 | Bytes. Always == b'\x00\x00\x00\x00\x00\x00\x00' | Unknown purpose |
| 28 | **bdata_ptr** | 2 | 2-bytes unsigned integer (little endian) | Pointer to bitmap block |
| 30 | **unk5** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 31 | **unk6** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 32 | **definitions** | num_glyphs\*11 | Array of `num_glyphs` items<br/>Item type: [GlyphDefinition](#glyphdefinition) | Definitions of chars in this bitmap font |
| 32 + num_glyphs\*11 | **skip_bytes** | up to offset bdata_ptr | Bytes | 4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36) |
| bdata_ptr | **bitmap** | 16..? | [Bitmap4Bit](#bitmap4bit) | Font atlas bitmap data |
### **GlyphDefinition** ###
#### **Size**: 11 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **code** | 2 | 2-bytes unsigned integer (little endian) | Code of symbol |
| 2 | **width** | 1 | 1-byte unsigned integer | Width of symbol in font bitmap |
| 3 | **height** | 1 | 1-byte unsigned integer | Height of symbol in font bitmap |
| 4 | **x** | 2 | 2-bytes unsigned integer (little endian) | Position (x) of symbol in font bitmap |
| 6 | **y** | 2 | 2-bytes unsigned integer (little endian) | Position (y) of symbol in font bitmap |
| 8 | **x_advance** | 1 | 1-byte unsigned integer | Gap between this symbol and next one in rendered text |
| 9 | **x_offset** | 1 | 1-byte signed integer | Offset (x) for drawing the character image |
| 10 | **y_offset** | 1 | 1-byte signed integer | Offset (y) for drawing the character image |
## **Palettes** ##
### **Palette16Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2d | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | num_colors\*2 | Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb. 0x7c0 (0x00FB00 RGB) is always transparent | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2a | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | num_colors\*4 | Array of `num_colors` items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
