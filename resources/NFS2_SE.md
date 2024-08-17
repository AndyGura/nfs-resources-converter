# **NFS2SE file specs** #

*Last time updated: 2024-08-17 03:48:24.441533+00:00*


# **Info by file extensions** #

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.UV** video, I just use ffmpeg to convert it

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
| 16 + num_items\*8 | **children** | ? | Array of `num_items + ?` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [Bitmap4Bit](#bitmap4bit)<br/>- [Bitmap8Bit](#bitmap8bit)<br/>- [Bitmap16Bit0565](#bitmap16bit0565)<br/>- [Bitmap16Bit1555](#bitmap16bit1555)<br/>- [Bitmap24Bit](#bitmap24bit)<br/>- [Bitmap32Bit](#bitmap32bit)<br/>- [PaletteReference](#palettereference)<br/>- [Palette16BitDos](#palette16bitdos)<br/>- [Palette16Bit](#palette16bit)<br/>- [Palette24Bit](#palette24bit)<br/>- [Palette32Bit](#palette32bit)<br/>- [ShpiText](#shpitext)<br/>- Bytes | A part of block, where items data is located. Offsets to some of the entries are defined in `items_descr` block. Between them there can be non-indexed entries (palettes and texts) |
### **BigfBlock** ###
#### **Size**: 16..? bytes ####
#### **Description**: A block-container with various data: image archives, GEO geometries, sound banks, other BIGF blocks... ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "BIGF" | Resource ID |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | The length of this BIGF block in bytes |
| 8 | **num_items** | 4 | 4-bytes unsigned integer (big endian) | An amount of items |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **items_descr** | num_items\*8..? | Array of `num_items` items<br/>Item type: [CompoundBlock](#compoundblock) | - |
| ? | **children** | ? | Array of `num_items` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [GeoGeometry](#geogeometry)<br/>- [ShpiBlock](#shpiblock)<br/>- [BigfBlock](#bigfblock)<br/>- Bytes |  |
## **Geometries** ##
### **GeoGeometry** ###
#### **Size**: 1804..? bytes ####
#### **Description**: A set of 3D meshes, used for cars and props. Contains multiple meshes with high details, medium and low LOD-s. Below `part_hp_x` is a high-poly part, `part_mp_x` and `part_lp_x` are medium and low-poly parts respectively ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **unk1** | 128 | Array of `32` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 132 | **unk2** | 8 | 8-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 140 | **part_hp_0** | 52..? | [GeoMesh](#geomesh) | High-Poly Additional Body Part |
| 192..? | **part_hp_1** | 52..? | [GeoMesh](#geomesh) | High-Poly Main Body Part |
| 244..? | **part_hp_2** | 52..? | [GeoMesh](#geomesh) | High-Poly Ground Part |
| 296..? | **part_hp_3** | 52..? | [GeoMesh](#geomesh) | High-Poly Front Part |
| 348..? | **part_hp_4** | 52..? | [GeoMesh](#geomesh) | High-Poly Back Part |
| 400..? | **part_hp_5** | 52..? | [GeoMesh](#geomesh) | High-Poly Left Side Part |
| 452..? | **part_hp_6** | 52..? | [GeoMesh](#geomesh) | High-Poly Right Side Part |
| 504..? | **part_hp_7** | 52..? | [GeoMesh](#geomesh) | High-Poly Additional Left Side Part |
| 556..? | **part_hp_8** | 52..? | [GeoMesh](#geomesh) | High-Poly Additional Right Side Part |
| 608..? | **part_hp_9** | 52..? | [GeoMesh](#geomesh) | High-Poly Spoiler Part |
| 660..? | **part_hp_10** | 52..? | [GeoMesh](#geomesh) | High-Poly Additional Part |
| 712..? | **part_hp_11** | 52..? | [GeoMesh](#geomesh) | High-Poly Backlights |
| 764..? | **part_hp_12** | 52..? | [GeoMesh](#geomesh) | High-Poly Front Right Wheel |
| 816..? | **part_hp_13** | 52..? | [GeoMesh](#geomesh) | High-Poly Front Right Wheel Part |
| 868..? | **part_hp_14** | 52..? | [GeoMesh](#geomesh) | High-Poly Front Left Wheel |
| 920..? | **part_hp_15** | 52..? | [GeoMesh](#geomesh) | High-Poly Front Left Wheel Part |
| 972..? | **part_hp_16** | 52..? | [GeoMesh](#geomesh) | High-Poly Rear Right Wheel |
| 1024..? | **part_hp_17** | 52..? | [GeoMesh](#geomesh) | High-Poly Rear Right Wheel Part |
| 1076..? | **part_hp_18** | 52..? | [GeoMesh](#geomesh) | High-Poly Rear Left Wheel |
| 1128..? | **part_hp_19** | 52..? | [GeoMesh](#geomesh) | High-Poly Rear Left Wheel Part |
| 1180..? | **part_mp_0** | 52..? | [GeoMesh](#geomesh) | Medium-Poly Additional Body Part |
| 1232..? | **part_mp_1** | 52..? | [GeoMesh](#geomesh) | Medium-Poly Main Body Part |
| 1284..? | **part_mp_2** | 52..? | [GeoMesh](#geomesh) | Medium-Poly Ground Part |
| 1336..? | **part_lp_0** | 52..? | [GeoMesh](#geomesh) | Low-Poly Wheel Part |
| 1388..? | **part_lp_1** | 52..? | [GeoMesh](#geomesh) | Low-Poly Main Part |
| 1440..? | **part_lp_2** | 52..? | [GeoMesh](#geomesh) | Low-Poly Side Part |
| 1492..? | **part_res_0** | 52..? | [GeoMesh](#geomesh) | Reserved space for part |
| 1544..? | **part_res_1** | 52..? | [GeoMesh](#geomesh) | Reserved space for part |
| 1596..? | **part_res_2** | 52..? | [GeoMesh](#geomesh) | Reserved space for part |
| 1648..? | **part_res_3** | 52..? | [GeoMesh](#geomesh) | Reserved space for part |
| 1700..? | **part_res_4** | 52..? | [GeoMesh](#geomesh) | Reserved space for part |
| 1752..? | **part_res_5** | 52..? | [GeoMesh](#geomesh) | Reserved space for part |
### **GeoMesh** ###
#### **Size**: 52..? bytes ####
#### **Description**: A single mesh, can use multiple textures ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **num_vrtx** | 4 | 4-bytes unsigned integer (little endian) | number of vertices in block |
| 4 | **num_plgn** | 4 | 4-bytes unsigned integer (little endian) | number of polygons in block |
| 8 | **pos** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part. The unit is meter | position of part in 3d space |
| 20 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 24 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **unk2** | 8 | 8-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 36 | **unk3** | 8 | 8-bytes unsigned integer (little endian). Always == 0x1 | Unknown purpose |
| 44 | **unk4** | 8 | 8-bytes unsigned integer (little endian). Always == 0x1 | Unknown purpose |
| 52 | **vertices** | num_vrtx\*6 | Array of `num_vrtx` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part. The unit is meter | Vertex coordinates |
| 52 + num_vrtx\*6 | **offset** | (num_vrtx % 2) ? 6 : 0 | Bytes | Data offset, happens when `num_vrtx` is odd |
| 52 + ceil(num_vrtx/2)\*12 | **polygons** | num_plgn\*12 | Array of `num_plgn` items<br/>Item type: [GeoPolygon](#geopolygon) | Array of mesh polygons |
### **GeoPolygon** ###
#### **Size**: 12 bytes ####
#### **Description**: A single polygon of the mesh. Texture coordinates seem to be hardcoded in game:for triangles `[[0, 0], [1, 0], [1, 1]]` if "uv_flip" else `[[0, 1], [1, 1], [1, 0]]`, for quads `[[0, 1], [1, 1], [1, 0], [0, 0]]` if "uv_flip" else `[[0, 0], [1, 0], [1, 1], [0, 1]]` ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **mapping** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: is_triangle<br/>1: uv_flip<br/>2: flip_normal<br/>4: double_sided</details> | Polygon properties. "is_triangle" means that 3th and 4th vertices in the polygon are the same, "uv_flip" changes texture coordinates, "flip normal" inverts normal vector of the polygon, "double-sided" makes polygon visible from the other side. |
| 1 | **unk0** | 3 | 3-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **vertex_indices** | 4 | Array of `4` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Indexes of vertices |
| 8 | **texture_name** | 4 | UTF-8 string | ID of texture from neighbouring QFS file |
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
| 16 | **bitmap** | height\*ceil((width)\*4/8) | Array of `height` items<br/>Item size: ceil((width)\*4/8) bytes<br/>Item type: Array of `width` sub-byte numbers. Each number consists of 4 bits | Font atlas bitmap data, array of bitmap rows |
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
### **PaletteReference** ###
#### **Size**: 8..? bytes ####
#### **Description**: Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. Probably a reference to palette which should be used, that's why named so ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7c | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **unk1_length** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **unk1** | 2\*unk1_length\*4 | Array of `2*unk1_length` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
### **Palette16BitDos** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x29 | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | num_colors\*2 | Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 16-bit color, not tested properly | Colors LUT |
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
### **Palette24Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x24 | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | num_colors\*3 | Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (big-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
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
## **Misc** ##
### **ShpiText** ###
#### **Size**: 8..? bytes ####
#### **Description**: An entry, which sometimes can be seen in the SHPI archive block after bitmap, contains some text. The purpose is unclear ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x6f | Resource ID |
| 1 | **unk** | 3 | Bytes | Unknown purpose |
| 4 | **length** | 4 | 4-bytes unsigned integer (little endian) | Text length |
| 8 | **text** | length | UTF-8 string | Text itself |
