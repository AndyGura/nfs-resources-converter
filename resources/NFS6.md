# **NFS 6 Hot Pursuit 2 file specs** #

*Last time updated: 2026-10-05 13:26:45.456906+00:00*


# **Info by file extensions** #

**compNN.o**, **trackg.o**, **skyg.o**, **levelNN\levelG.o** track geometry. [EaglModel](#eaglmodel)

**levelNN\aipaths.dat** race route. [Nfs6AiPaths](#nfs6aipaths)

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

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
| 16 | **items_descr** | num_items\*9..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | Descriptions of items: offset, length and name of each of them |
| 16 + num_items\*9..? | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets and lengths are defined in previous block. Possible item types:<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file<br/>- [BigfBlock](#bigfblock)<br/>- pure TGA image |
### **BigfItemDescriptionBlock** ###
#### **Size**: 9..? bytes ####
#### **Description**: Description of a single item of BIGF archive ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | Offset of item data, relative to BIGF block start |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | Length of item data in bytes |
| 8 | **name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | Item name (file name). Used as file name when the archive is unpacked |
## **Geometries** ##
### **EaglModel** ###
#### **Size**: 52..? bytes ####
#### **Description**: EAGL model, used by NFS6 for track compartments, sky and other geometry. A 32-bit little-endian MIPS ELF relocatable object file with model data in ".data" section, where named symbols point to render methods, vertex/index buffers and texture references ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **magic** | 4 | 4-bytes unsigned integer (little endian). Always == 0x464c457f | ELF magic "\x7fELF" |
| 4 | **file_class** | 1 | 1-byte unsigned integer | 1: 32-bit |
| 5 | **data_encoding** | 1 | 1-byte unsigned integer | 1: little-endian |
| 6 | **elf_version** | 1 | 1-byte unsigned integer | Always 1 |
| 7 | **os_abi** | 1 | 1-byte unsigned integer | Always 0 |
| 8 | **padding** | 8 | Bytes | Zeros |
| 16 | **object_type** | 2 | 2-bytes unsigned integer (little endian) | 1: relocatable object file |
| 18 | **machine** | 2 | 2-bytes unsigned integer (little endian) | 8: MIPS |
| 20 | **version** | 4 | 4-bytes unsigned integer (little endian) | Always 1 |
| 24 | **entry** | 4 | 4-bytes unsigned integer (little endian) | Entry point, always 0 |
| 28 | **program_headers_offset** | 4 | 4-bytes unsigned integer (little endian) | Always 0, no program headers |
| 32 | **section_headers_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of section headers table |
| 36 | **flags** | 4 | 4-bytes unsigned integer (little endian) | MIPS flags |
| 40 | **header_size** | 2 | 2-bytes unsigned integer (little endian) | Size of this header, 52 |
| 42 | **program_header_size** | 2 | 2-bytes unsigned integer (little endian) | Always 0 |
| 44 | **program_headers_count** | 2 | 2-bytes unsigned integer (little endian) | Always 0 |
| 46 | **section_header_size** | 2 | 2-bytes unsigned integer (little endian) | Size of section header, 40 |
| 48 | **section_headers_count** | 2 | 2-bytes unsigned integer (little endian) | Amount of sections |
| 50 | **section_names_index** | 2 | 2-bytes unsigned integer (little endian) | Index of the section with section names |
| 52 | **sections_data** | section_headers_offset - 52 | Bytes | Sections: ".data" with the model, ".shstrtab" and ".strtab" string tables, ".symtab" symbol table (16-byte records: name offset, value, size, info, other, section index) and ".rel.data" relocations of ".data" (8-byte records: offset, symbol index << 8 | type) |
| 52 + section_headers_offset - 52 | **section_headers** | section_headers_count\*40 | Array of `section_headers_count` items<br/>Item type: [EaglSectionHeader](#eaglsectionheader) | Section headers table |
### **EaglSectionHeader** ###
#### **Size**: 40 bytes ####
#### **Description**: ELF32 section header ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of section name in the section names table |
| 4 | **section_type** | 4 | 4-bytes unsigned integer (little endian) | 1: program data (".data"), 2: symbol table, 3: string table, 9: relocations |
| 8 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Section flags |
| 12 | **address** | 4 | 4-bytes unsigned integer (little endian) | Virtual address, always 0 |
| 16 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of section data in the file |
| 20 | **size** | 4 | 4-bytes unsigned integer (little endian) | Size of section data in bytes |
| 24 | **link** | 4 | 4-bytes unsigned integer (little endian) | Index of related section (string table of symbol table) |
| 28 | **info** | 4 | 4-bytes unsigned integer (little endian) | Extra info (for relocations: index of the section the relocations apply to) |
| 32 | **alignment** | 4 | 4-bytes unsigned integer (little endian) | Section alignment |
| 36 | **entry_size** | 4 | 4-bytes unsigned integer (little endian) | Size of table entry, if section is a table |
## **Maps** ##
### **Nfs6AiPaths** ###
#### **Size**: 20..? bytes ####
#### **Description**: NFS6 race route (levelNN/aipaths.dat): the road graph for AI cars and the flight paths of the police helicopter. Opening it shows the route in 3D: the compartments listed in drvpath.ini next to it ("compNN.o" files in the parent folder) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **version** | 4 | 4-bytes unsigned integer (little endian) | Always 1 |
| 4 | **road_paths** | 8..? | [Nfs6AiPathGraph](#nfs6aipathgraph) | Roads for AI cars |
| 12..? | **helicopter_paths** | 8..? | [Nfs6AiPathGraph](#nfs6aipathgraph) | Flight paths of police helicopter |
### **Nfs6AiPathGraph** ###
#### **Size**: 8..? bytes ####
#### **Description**: A graph of paths ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **num_nodes** | 4 | 4-bytes unsigned integer (little endian) | Length of nodes array |
| 4 | **nodes** | num_nodes\*12 | Array of `num_nodes` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Graph nodes: start and end positions of every path |
| 4 + num_nodes\*12 | **num_paths** | 4 | 4-bytes unsigned integer (little endian) | Length of paths array |
| 8 + num_nodes\*12 | **paths** | num_paths\*36..? | Array of `num_paths` items<br/>Item type: [Nfs6AiPath](#nfs6aipath) | Paths |
### **Nfs6AiPath** ###
#### **Size**: 36..? bytes ####
#### **Description**: A road between two graph nodes. Paths with the same start/end node positions are connected ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 16 | UTF-8 string | Path name, e.g. "AI_center011" |
| 16 | **start_node** | 4 | 4-bytes unsigned integer (little endian) | Index of the graph node where the path starts |
| 20 | **end_node** | 4 | 4-bytes unsigned integer (little endian) | Index of the graph node where the path ends |
| 24 | **unk0** | 4 | Float number (little-endian) | Always 44.703 |
| 28 | **path_type** | 4 | 4-bytes unsigned integer (little endian) | Path kind. Main road is 1, alternative roads and shortcuts have other values (2, 3, 5, 8, 11) |
| 32 | **num_points** | 4 | 4-bytes unsigned integer (little endian) | Length of points array |
| 36 | **points** | num_points\*28 | Array of `num_points` items<br/>Item type: [Nfs6AiPathPoint](#nfs6aipathpoint) | Path points, from start node to end node |
### **Nfs6AiPathPoint** ###
#### **Size**: 28 bytes ####
#### **Description**: A point of the AI path ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Point position, Y is up |
| 12 | **left_width** | 4 | Float number (little-endian) | Distance from the path to the left edge of the drivable area (usually 10) |
| 16 | **right_width** | 4 | Float number (little-endian) | Distance from the path to the right edge of the drivable area, negative (usually -10) |
| 20 | **unk0** | 4 | Float number (little-endian) | Values from -9 to 6, maybe road bank |
| 24 | **unk1** | 4 | Float number (little-endian) | Values from 35 to 60, maybe recommended speed |
## **Images** ##
### **EacImage** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>64 (0x40): 4Bit PS1<br/>96 (0x60): DXT1 compressed bitmap<br/>97 (0x61): DXT3 compressed bitmap<br/>98 (0x62): DXT5 compressed bitmap<br/>109 (0x6d): 16Bit_4444 color format bitmap<br/>120 (0x78): 16Bit_0565 color format bitmap<br/>121 (0x79): 4Bit (swapped)<br/>122 (0x7a): 4Bit<br/>123 (0x7b): 8Bit<br/>125 (0x7d): 32Bit color format bitmap<br/>126 (0x7e): 16Bit_1555 color format bitmap<br/>127 (0x7f): 24Bit color format bitmap</details> | Resource ID |
| 1 | **palette_offset** | 3 | 3-bytes signed integer (little endian) | A local offset to the palette that should be used with this image (8Bit). In case of zero, game searches for !pal or !PAL in the SHPI |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **pivot** | 4 | Point in 2D space (x,y), where each coordinate is: 2-bytes unsigned integer (little endian) | Seems like x coordinate is not used at all. y coordinate is used in horizon textures in TNFS FAM files: higher value = image as horizon will be put higher on the screen. Seems to affect only open tracks |
| 12 | **position** | 4 | Point in 2D space (x,y), where each coordinate is: 2-bytes unsigned integer (little endian) | Bitmap position on screen. Used for menu/dash sprites. In NFS5 FSH files this is the position of the image in a texture page (atlas), which is used by CRP models: 12 lower bits of each coordinate are a signed value, 4 higher bits are flags (track textures have 6 or 7 in y flags for 64x64 or 128x128 images, likely the mipmap count) |
| 16 | **bitmap** | width \* height \* pixel_byteness | Bytes | Pixel color table. For 8Bit bitmap each value represents an index of color in the attached palette. Palette can be stored: <br/>- right after 8Bit image<br/>- as !pal/!PAL in the same SHPI<br/>- in a different SHPI before this one (if it is WWWW archive)<br/>- even in different QFS file (TNFS, CONTROL directory).<br/>Color model is selected according to `resource_id` field. Color models are described [here](eac_colors.md). DXT1/DXT3/DXT5 bitmaps are S3TC-compressed 4x4 pixel blocks (8, 16 and 16 bytes per block) |
| 16 + width \* height \* pixel_byteness | **pad** | 0..up to offset palette_offset | Optional (if palette_offset > 0): Padding bytes | Zeros in the end of block data |
| 16 + width \* height \* pixel_byteness..16 + width \* height \* pixel_byteness + up to offset palette_offset | **unk_7c** | 0..? | Optional (if 0x7C header found): [PaletteReference](#palettereference) | Unknown data with id 0x7C |
| 16 + width \* height \* pixel_byteness..? | **embedded_palette** | 0..? | Optional (if 8-bit bitmap and palette header found): [EacPalette](#eacpalette) | Embedded palette, which should be assigned to this bitmap (except for ga00 in TR2_001.FAM) |
| 16 + width \* height \* pixel_byteness..? | **embedded_palette_2** | 0..? | Optional (if 8-bit bitmap and palette header found): [EacPalette](#eacpalette) | Possibly one more embedded palette, unknown reason |
| 16 + width \* height \* pixel_byteness..? | **embedded_palette_3** | 0..? | Optional (if 8-bit bitmap and palette header found): [EacPalette](#eacpalette) | Possibly one more embedded palette, unknown reason |
| 16 + width \* height \* pixel_byteness..? | **embedded_palette_4** | 0..? | Optional (if 8-bit bitmap and palette header found): [EacPalette](#eacpalette) | Possibly one more embedded palette, unknown reason |
| 16 + width \* height \* pixel_byteness..? | **text** | 0..? | Optional (if 0x6F header found): [ShpiText](#shpitext) | Shpi text |
| 16 + width \* height \* pixel_byteness..? | **mipmaps** | 0..(1/4 + 1/16 + 1/64 + etc) \* width \* height \* pixel_byteness | Optional (if dimensions are powers of two and sufficient extra space): Bytes | Mipmaps pixel data in the same format as `bitmap` field. There are images with sizes w/2 x h/2, w/4 x h4, .... up to 1, in descending order. |
### **EacPalette** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black: thy are reserved for cop car siren ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>34 (0x22): 24BitDos color format palette<br/>36 (0x24): 24Bit color format palette<br/>41 (0x29): 16Bit_0565 color format palette<br/>42 (0x2a): 32Bit color format palette<br/>45 (0x2d): 16Bit_1555 color format palette</details> | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Equals to num_colors, except for some CRP structures in NFS5 |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | ? | Type according to enum `resource_id`:<br/>- Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (big endian)<br/>- Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (big endian)<br/>- Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `num_colors` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian)<br/>- Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Colors LUT. Color model is selected according to `resource_id` field. Color models are described [here](eac_colors.md) |
### **PaletteReference** ###
#### **Size**: 8..? bytes ####
#### **Description**: Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. Probably a reference to palette which should be used, that's why named so ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x7c | Resource ID |
| 4 | **num_unk1** | 4 | 4-bytes unsigned integer (little endian) | Length of unk1 array |
| 8 | **unk1** | num_unk1\*8 | Array of `num_unk1` items<br/>Item size: 8 bytes<br/>Item type: Bytes | Unknown purpose |
### **ShpiText** ###
#### **Size**: 8..? bytes ####
#### **Description**: An entry, which sometimes can be seen in the SHPI archive block after bitmap, contains some text. The purpose is unclear ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x6f | Resource ID |
| 1 | **unk** | 3 | Bytes | Unknown purpose |
| 4 | **len_text** | 4 | 4-bytes unsigned integer (little endian) | Length of 'text' utf8 block |
| 8 | **text** | len_text | UTF-8 string | Text contents |
## **Fonts** ##
### **FfnFont** ###
#### **Size**: 48..? bytes ####
#### **Description**: Bitmap font: a font atlas bitmap plus glyph definitions (position and size of each symbol in the atlas) and optional kerning table ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. One of ['"FNTF"', '"FNTP"', '"FNTS"', '"FNTX"', '"FNTM"', '"FNTG"', '"FNTA"', '"FntF"', '"FntP"', '"FntS"', '"FntX"', '"FntM"', '"FntG"', '"FntA"'] | Resource ID |
| 4 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | The length of this FFN block in bytes. Does not include bitmap embedded palette (and padding to it after bitmap data). For older versions (I set version <= 101, but it can be anywhere up to < 309), "padding_2" length not included as well |
| 8 | **version** | 2 | 2-bytes unsigned integer (little endian) | Font format version. Defines the layout of glyph definitions (see [GlyphDefinition](#glyphdefinition)) |
| 10 | **num_glyphs** | 2 | 2-bytes unsigned integer (little endian) | Amount of symbols, defined in this font |
| 12 | **flags** | 4 | Sub-byte compound block (little endian):<br/>13-bits int "pad"<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: 12-bytes<br/>&nbsp;&nbsp;- 1: 16-bytes<br/>2-bits enum:<br/>&nbsp;&nbsp;- 0: ASCII<br/>&nbsp;&nbsp;- 1: Unicode<br/>&nbsp;&nbsp;- 2: Shift-JIS<br/>&nbsp;&nbsp;- 3: Reserved<br/>4-bits int "layoutpad"<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: LTR<br/>&nbsp;&nbsp;- 1: RTL<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: Horizontal<br/>&nbsp;&nbsp;- 1: Vertical<br/>2-bits enum:<br/>&nbsp;&nbsp;- 0: Roman (english)<br/>&nbsp;&nbsp;- 1: Ideographic (Kanji)<br/>&nbsp;&nbsp;- 2: Hanging (Arabic)<br/>&nbsp;&nbsp;- 3: Unknown<br/>4-bits int "drawpad"<br/>1-bit flag "vram"<br/>1-bit flag "outline"<br/>1-bit flag "dropshadow"<br/>1-bit flag "antialiased" | Font flags: format of glyph definitions, encoding, layout and draw attributes |
| 16 | **center** | 2 | Point in 2D space (x,y), where each coordinate is: 1-byte unsigned integer | Unknown purpose |
| 18 | **ascent** | 1 | 1-byte unsigned integer | Distance from the baseline to the top of the glyphs in pixels. `ascent + descent` is the line height |
| 19 | **descent** | 1 | 1-byte unsigned integer | Distance from the baseline to the bottom of the glyphs in pixels |
| 20 | **definitions_ptr** | 4 | 4-bytes unsigned integer (little endian) | Pointer to definitions block |
| 24 | **kernings_ptr** | 4 | 4-bytes unsigned integer (little endian) | Pointer to kernings. 0 if there is no kernings table |
| 28 | **bdata_ptr** | 4 | 4-bytes unsigned integer (little endian) | Pointer to bitmap block |
| 32 | **padding_0** | up to offset definitions_ptr | Padding bytes | Unknown purpose |
| definitions_ptr | **definitions** | num_glyphs\*11..num_glyphs\*17 | Array of `num_glyphs` items<br/>Item type: [GlyphDefinition](#glyphdefinition) | Definitions of chars in this bitmap font |
| ? | **padding_1** | 0..up to offset kernings_ptr | Optional (if kernings_ptr != 0): Padding bytes | Unknown purpose |
| ? | **kernings** | 0..? | Optional (if kernings_ptr != 0): Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [KerningItem](#kerningitem) | Kerning pairs table |
| ? | **padding_2** | up to offset bdata_ptr | Padding bytes | Unknown purpose |
| bdata_ptr | **bitmap** | 16..? | [EacImage](#eacimage) | Font atlas bitmap data |
| ? | **remaining_bytes** | remaining bytes | Bytes | Unknown purpose |
### **GlyphDefinition** ###
#### **Size**: 11..17 bytes ####
#### **Description**: Glyph definition.<br/>- for FNT version < 200 has length 11 bytes.<br/>- for versions >= 200 and <= 309 - 12 bytes, last byte is padding.<br/>- for versions > 309 - 12th byte is num_kern.<br/>- for versions >= 321 it may be 16 bytes if "format" flag is set to 16-bytes ####
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
| 11 | **num_kern** | 0..1 | Optional (if ^^version > 309): 1-byte unsigned integer | Number of kerning pairs for this glyph |
| 11..12 | **pad** | 0..1 | Optional (if ^^version <= 309): 1-byte unsigned integer | Padding |
| 11..13 | **kern_index** | 0..2 | Optional (if ^^flags/format == 16-bytes): 2-bytes unsigned integer (little endian) | Index in kerning table? |
| 11..15 | **x_advance** | 0..2 | Optional (if ^^flags/format == 16-bytes): 2-bytes unsigned integer (little endian) | Gap between this symbol and next one in rendered text? |
### **KerningItem** ###
#### **Size**: 4 bytes ####
#### **Description**: Kerning pair: horizontal adjustment of the gap between two specific glyphs ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **left** | 2 | 2-bytes unsigned integer (little endian) | Code of left glyph |
| 2 | **kerning** | 1 | 1-byte signed integer | Kerning amount in pixels, added to the gap between the glyphs |
| 3 | **right** | 1 | 1-byte unsigned integer | Code of right glyph |
