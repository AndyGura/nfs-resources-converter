# **TNFSSE (PC) file specs** #

*Last time updated: 2025-01-03 09:38:58.848509+00:00*


# **Info by file extensions** #

**\*INFO** track settings with unknown purpose. That's a plain text file with some values, no problem to edit manually

**\*.AS4**, **\*.ASF**, **\*.EAS** audio + loop settings. [AsfAudio](#asfaudio)

**\*.BNK** sound bank. [SoundBank](#soundbank)

**\*.CFM** car 3D model. [WwwwBlock](#wwwwblock) with 4 entries:
- [OripGeometry](#oripgeometry) high-poly 3D model
- [ShpiBlock](#shpiblock) textures for high-poly model
- [OripGeometry](#oripgeometry) low-poly 3D model
- [ShpiBlock](#shpiblock) textures for low-poly model

**\*.FAM** track textures, props, skybox. [WwwwBlock](#wwwwblock) with 4 entries:
- [WwwwBlock](#wwwwblock) (background) contains few [ShpiBlock](#shpiblock) items, terrain textures
- [WwwwBlock](#wwwwblock) (foreground) contains few [ShpiBlock](#shpiblock) items, prop textures
- [ShpiBlock](#shpiblock) (skybox) contains horizon texture
- [WwwwBlock](#wwwwblock) (props) contains a series of consecutive [OripGeometry](#oripgeometry) + [ShpiBlock](#shpiblock) items, 3D props

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.PBS** car physics. [CarPerformanceSpec](#carperformancespec), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.PDN** car characteristic for unknown purpose. [CarSimplifiedPerformanceSpec](#carsimplifiedperformancespec), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.TGV** video, I just use ffmpeg to convert it

**\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. [TriMap](#trimap)

**GAMEDATA\CONFIG\CONFIG.DAT** Player name, best times, whether warrior car unlocked etc. [TnfsConfigDat](#tnfsconfigdat)

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
| 16 + num_items\*8 | **children** | ? | Array of `num_items + ?` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [Bitmap4Bit](#bitmap4bit)<br/>- [Bitmap8Bit](#bitmap8bit)<br/>- [PaletteReference](#palettereference)<br/>- [Palette24BitDos](#palette24bitdos)<br/>- [Palette24Bit](#palette24bit)<br/>- Bytes | A part of block, where items data is located. Offsets to some of the entries are defined in `items_descr` block. Between them there can be non-indexed entries (palettes and texts) |
### **WwwwBlock** ###
#### **Size**: 8..? bytes ####
#### **Description**: A block-container with various data: image archives, geometries, other wwww blocks. If has ORIP 3D model, next item is always SHPI block with textures to this 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "wwww" | Resource ID |
| 4 | **num_items** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 8 | **items_descr** | num_items\*4 | Array of `num_items` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file, relatively to wwww block start (where resource id string is presented) |
| 8 + num_items\*4 | **children** | ? | Array of `num_items` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [ShpiBlock](#shpiblock)<br/>- [OripGeometry](#oripgeometry)<br/>- [WwwwBlock](#wwwwblock)<br/>- Bytes | A part of block, where items data is located. Offsets are defined in previous block, lengths are calculated: either up to next item offset, or up to the end of this block |
### **SoundBank** ###
#### **Size**: 512..? bytes ####
#### **Description**: A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **items_descr** | 512 | Array of `128` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file. Zero values ignored |
| 512 | **items** | (amount of non-zero elements in items_descr)\*72 | Array of `amount of non-zero elements in items_descr` items<br/>Item type: [SoundBankHeaderEntry](#soundbankheaderentry) | EACS audio headers. Separate audios can be read easily using these because it contains file-wide offset to wave data, so it does not care wave data located, right after EACS header, or somewhere else like it is here in sound bank file |
| 512 + (amount of non-zero elements in items_descr)\*72 | **wave_data** | up to end of file | Bytes | Raw byte data, which is sliced according to provided offsets and used as wave data |
| N/A | **children** | 0 | Array of `0` items<br/>Item type: [EacsAudioFile](#eacsaudiofile) | Disregard this field, it is generated by parser from the data from previous fields for convenience: essentially this file is a set of EACS audio-s, but their structure is dispersed across the file |
## **Geometries** ##
### **OripGeometry** ###
#### **Size**: 112..? bytes ####
#### **Description**: Geometry block for 3D model with few materials ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "ORIP" | Resource ID |
| 4 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Total ORIP block size |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian). Always == 0x2bc | Looks like always 0x01F4 in 3DO version and 0x02BC in PC TNFSSE. ORIP type? |
| 12 | **unk1** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 16 | **num_vrtx** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices |
| 20 | **unk2** | 4 | Bytes | Unknown purpose |
| 24 | **vrtx_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertices |
| 28 | **num_uvs** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex UV-s (texture coordinates) |
| 32 | **uvs_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertex_uvs. Always equals to `112 + num_polygons*12` |
| 36 | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Amount of polygons |
| 40 | **polygons_ptr** | 4 | 4-bytes unsigned integer (little endian). Always == 0x70 | An offset to polygons block |
| 44 | **identifier** | 12 | UTF-8 string | Some ID of geometry, don't know the purpose |
| 56 | **num_tex_ids** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture names |
| 60 | **tex_ids_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture names block. Always equals to `112 + num_polygons*12 + num_uvs*8` |
| 64 | **num_tex_nmb** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture numbers |
| 68 | **tex_nmb_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture numbers block |
| 72 | **num_ren_ord** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in render_order block |
| 76 | **ren_ord_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of render_order block. Always equals to `tex_nmb_ptr + num_tex_nmb*20` |
| 80 | **vmap_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of polygon_vertex_map block |
| 84 | **num_fxp** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in fx_polys block |
| 88 | **fxp_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of fx_polys block. Always equals to `tex_nmb_ptr + num_tex_nmb*20 + num_ren_ord*28` |
| 92 | **num_lbl** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in labels block |
| 96 | **lbl_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of labels block. Always equals to `tex_nmb_ptr + num_tex_nmb*20 + num_ren_ord*28 + num_fxp*12` |
| 100 | **unknowns1** | 12 | Bytes | Unknown purpose |
| 112 | **polygons** | num_polygons\*12 | Array of `num_polygons` items<br/>Item type: [OripPolygon](#orippolygon) | A block with polygons of the geometry. Probably should be a start point when building model from this file |
| uvs_ptr | **vertex_uvs** | num_uvs\*8 | Array of `num_uvs` items<br/>Item size: 8 bytes<br/>Item type: Texture coordinates for vertex, where each coordinate is: 4-bytes unsigned integer (little endian). The unit is a pixels amount of assigned texture. So it should be changed when selecting texture with different size | A table of texture coordinates. Items are retrieved by index, located in vmap |
| tex_ids_ptr | **tex_ids** | num_tex_ids\*20 | Array of `num_tex_ids` items<br/>Item type: [OripTextureName](#oriptexturename) | A table of texture references. Items are retrieved by index, located in polygon item |
| tex_ids_ptr + num_tex_ids\*20 | **offset** | space up to offset `tex_nmb_ptr` | Bytes | In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in case of DIABLO.CFM it's length is equal to -3, meaning that last 3 bytes from texture names block are reused by next block |
| tex_nmb_ptr | **tex_nmb** | num_tex_nmb\*20 | Array of `num_tex_nmb` items<br/>Item size: 20 bytes<br/>Item type: Array of `20` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| ren_ord_ptr | **render_order** | num_ren_ord\*28 | Array of `num_ren_ord` items<br/>Item type: [RenderOrderBlock](#renderorderblock) | Render order. The exact mechanism how it works is unknown |
| fxp_ptr | **fx_polys** | num_fxp\*12 | Array of `num_fxp` items<br/>Item size: 12 bytes<br/>Item type: 12-bytes record, first 8 bytes is null-terminated UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | Indexes of polygons which participate in visual effects such as engine smoke, dust particles, tyre trails? Presented in car CFM-s.  |
| lbl_ptr | **labels** | num_lbl\*12 | Array of `num_lbl` items<br/>Item size: 12 bytes<br/>Item type: 12-bytes record, first 8 bytes is null-terminated UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | Marks special polygons for the game, where it should change texture on runtime such as tyres, tail lights |
| vrtx_ptr | **vertices** | num_vrtx\*12 | Array of `num_vrtx` items<br/>Item size: 12 bytes<br/>Item type: One of types:<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 7 bits is a fractional part<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 4 bits is a fractional part | A table of mesh vertices 3D coordinates. For cars uses 32:7 points, else 32:4. The unit is meter |
| vmap_ptr | **vmap** | ? | Array of `?` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | A LUT for both 3D and 2D vertices. Every item is an index of either item in vertices or vertex_uvs. When building 3D vertex, polygon defines offset_3d, a lookup to this table, and value from here is an index of item in vertices. When building UV-s, polygon defines offset_2d, a lookup to this table, and value from here is an index of item in vertex_uvs |
### **OripPolygon** ###
#### **Size**: 12 bytes ####
#### **Description**: A geometry polygon ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_type** | 1 | 1-byte unsigned integer | Huh, that's a srange field. From my tests, if it is xxx0_0011, the polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only one polygon for entire TNFS with type == 2 in burnt sienna props. If ignore this polygon everything still looks great |
| 1 | **mapping** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: two_sided<br/>1: flip_normal<br/>4: use_uv</details> | Rendering properties of the polygon |
| 2 | **texture_index** | 1 | 1-byte unsigned integer | The index of item in ORIP's tex_ids block |
| 3 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **offset_3d** | 4 | 4-bytes unsigned integer (little endian) | The index in vmap ORIP's table. This index represents first vertex of this polygon, so in order to determine all vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. Look at vmap description for more info |
| 8 | **offset_2d** | 4 | 4-bytes unsigned integer (little endian) | The same as offset_3d, also points to vmap, but used for texture coordinates. Look at vmap description for more info |
### **OripTextureName** ###
#### **Size**: 20 bytes ####
#### **Description**: A settings of the texture. From what is known, contains name of bitmap (not always a correct UTF-8) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 8 | Bytes | - |
| 8 | **file_name** | 4 | UTF-8 string | Name of bitmap in SHPI block |
| 12 | **unknown** | 8 | Bytes | Unknown purpose |
### **RenderOrderBlock** ###
#### **Size**: 28 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **identifier** | 8 | UTF-8 string | identifier ('NON-SORT', 'inside', 'surface', 'outside') |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | 0x8 for 'NON-SORT' or 0x1 for the others |
| 12 | **polygons_amount** | 4 | 4-bytes unsigned integer (little endian) | Polygons amount (3DO). For TNFSSE sometimes too big value |
| 16 | **polygon_sum** | 4 | 4-bytes unsigned integer (little endian) | 0 for 'NON-SORT'; block’s 10 size for 'inside'; equals block’s 10 size + number of polygons from ‘inside’ = XXX for 'surface'; equals XXX + number of polygons from 'surface' for 'outside'; (Description for 3DO orip file, TNFSSE version has only 9 blocks!) |
| 20 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 24 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
## **Maps** ##
### **TriMap** ###
#### **Size**: 90664..? bytes ####
#### **Description**: Map TRI file, represents terrain mesh, road itself, props locations etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x11 | Resource ID |
| 4 | **loop_chunk** | 2 | 2-bytes unsigned integer (little endian) | Index of chunk, on which game should use chunk #0 again. So for closed tracks this value should be equal to `num_chunks`, for open tracks it is 0 |
| 6 | **num_chunks** | 2 | 2-bytes unsigned integer (little endian) | number of terrain chunks (max 600) |
| 8 | **unk0** | 2 | 2-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 10 | **unk1** | 2 | 2-bytes unsigned integer (little endian). Always == 0x6 | Unknown purpose |
| 12 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 24 | **unknowns0** | 12 | Array of `12` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 36 | **chunks_size** | 4 | 4-bytes unsigned integer (little endian) | Size of terrain array in bytes (num_chunks * 0x120) |
| 40 | **rail_tex_id** | 4 | 4-bytes unsigned integer (little endian) | Do not know what is "railing". Doesn't look like a fence texture id, tested in TR1_001.FAM |
| 44 | **lookup_table** | 2400 | Array of `600` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | 600 consequent numbers, each value is previous + 288. Looks like a space needed by the original NFS engine |
| 2444 | **road_spline** | 86400 | Array of `2400` items<br/>Item type: [RoadSplinePoint](#roadsplinepoint) | Road spline is a series of points in 3D space, located at the center of road. Around this spline the track terrain mesh is built. TRI always has 2400 elements, however it uses only amount of vertices, equals to (num_chunks * 4), after them records filled with zeros. For opened tracks, finish line will be always located at spline point (num_chunks * 4 - 179) |
| 88844 | **ai_info** | 1800 | Array of `600` items<br/>Item type: [AIEntry](#aientry) | - |
| 90644 | **num_prop_descr** | 4 | 4-bytes unsigned integer (little endian) | - |
| 90648 | **num_props** | 4 | 4-bytes unsigned integer (little endian) | - |
| 90652 | **objs_hdr** | 4 | UTF-8 string. Always == "SJBO" | - |
| 90656 | **unk2** | 4 | 4-bytes unsigned integer (little endian). Always == 0x428c | Unknown purpose |
| 90660 | **unk3** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 90664 | **prop_descr** | num_prop_descr\*16 | Array of `num_prop_descr` items<br/>Item type: [PropDescr](#propdescr) | - |
| 90664 + num_prop_descr\*16 | **props** | num_props\*16 | Array of `num_props` items<br/>Item type: [MapProp](#mapprop) | - |
| 90664 + num_prop_descr\*16 + num_props\*16 | **terrain** | num_chunks\*288 | Array of `num_chunks` items<br/>Item type: [TerrainEntry](#terrainentry) | - |
### **RoadSplinePoint** ###
#### **Size**: 36 bytes ####
#### **Description**: The description of one single point of road spline. Thank you jeff-1amstudios for your [OpenNFS1](https://github.com/jeff-1amstudios/OpenNFS1) project ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **left_verge** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to the left edge of road. After this point the grip decreases |
| 1 | **right_verge** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to the right edge of road. After this point the grip decreases |
| 2 | **left_barrier** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to invisible wall on the left |
| 3 | **right_barrier** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to invisible wall on the right |
| 4 | **num_lanes** | 1 | Array of `2` sub-byte numbers. Each number consists of 4 bits | Amount of lanes. First number is amount of oncoming lanes, second number is amount of ongoing ones |
| 5 | **unk0** | 1 | Array of `2` sub-byte numbers. Each number consists of 4 bits | Unknown, DOS version of TNFS SE does not seem to read from this address at all. Appears to be a pair of 4-bit numbers, just like `num_lanes` and `verge_slide`, since all maps have value one of [0, 1, 16, 17], which seems to be the combination of two values [0-1, 0-1]. Most common value is 17 ([1, 1]) |
| 6 | **verge_slide** | 1 | Array of `2` sub-byte numbers. Each number consists of 4 bits | A slidiness of road areas between verge distance and barrier. First number for left verge, second number for right verge. Values above 3 cause unbearable slide in the game and make it impossible to return back to road. High values around maximum (15) cause lags and even crashes |
| 7 | **item_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: lane_split<br/>1: default_0<br/>2: lane_merge<br/>3: default_1<br/>4: tunnel<br/>5: cobbled_road<br/>7: right_tunnel_A9_A2<br/>8: unk_cl3_forest<br/>9: left_tunnel_A4_A7<br/>11: unk_autumn_valley_tribunes<br/>12: left_tunnel_A4_A8<br/>13: left_tunnel_A5_A8<br/>14: waterfall_audio_left_channel<br/>15: waterfall_audio_right_channel<br/>16: unk_al1_uphill<br/>17: transtropolis_noise_audio<br/>18: water_audio</details> | Modifier of this point. Affects terrain geometry and/or some gameplay features |
| 8 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Coordinates of this point in 3D space. The unit is meter |
| 20 | **slope** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Slope of the road at this point (angle if road goes up or down) |
| 22 | **slant_a** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Perpendicular angle of road |
| 24 | **orientation** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Rotation of road path, if view from the top. Equals to atan2(next_x - x, next_z - z) |
| 26 | **unk1** | 2 | 2-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 28 | **orientation_x** | 2 | 2-bytes signed integer (little endian) | Orientation vector is a 2D vector, normalized to ~32766 with angle == orientation field above, used for pseudo-3D effect on opponent cars. So orientation_x == cos(orientation) * 32766 |
| 30 | **slant_b** | 2 | EA games 16-bit angle (little-endian). 0 means 0 degrees, 0x10000 (max value + 1) means 360 degrees | has the same purpose as slant_a, but is a standard signed 16-bit value. Its value is positive for the left, negative for the right. The approximative relation between slant-A and slant-B is slant-B = -12.3 slant-A (remember that slant-A is 14-bit, though) |
| 32 | **orientation_nz** | 2 | 2-bytes signed integer (little endian) | Orientation vector is a 2D vector, normalized to ~32766 with angle == orientation field above, used for pseudo-3D effect on opponent cars. So orientation_nz == -sin(orientation) * 32766 |
| 34 | **unk2** | 2 | 2-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
### **PropDescr** ###
#### **Size**: 16 bytes ####
#### **Description**: The description of map prop: everything except terrain (road signs, buildings etc.) Thanks to jeff-1amstudios and his [OpenNFS1](https://github.com/jeff-1amstudios/OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202) project ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **flags** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>2: is_animated</details> | Different modes of prop |
| 1 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: unk<br/>1: model<br/>4: bitmap<br/>6: two_sided_bitmap</details> | Type of prop |
| 2 | **data** | 14 | One of types:<br/>- [ModelPropDescrData](#modelpropdescrdata)<br/>- [BitmapPropDescrData](#bitmappropdescrdata)<br/>- [TwoSidedBitmapPropDescrData](#twosidedbitmappropdescrdata)<br/>- Bytes | Settings of the prop. Block class picked according to `type` |
### **MapProp** ###
#### **Size**: 16 bytes ####
#### **Description**: The prop on the map. For instance: exactly the same road sign used 5 times on the map. In this case file will have 1 PropDescr for this road sign and 5 MapProps ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **road_point_idx** | 4 | 4-bytes signed integer (little endian) | Index of point of the road path spline, where prop is located. Sometimes has too big value, I skip those instances for now and it seems to look good. Probably should consider this value to be 16-bit integer, having some unknown 16-integer as next field. Also, why it is signed? |
| 4 | **prop_descr_idx** | 1 | 1-byte unsigned integer | Index of prop description, which should be used for this prop. Sometimes has too big value, I use object index % amount of prop descriptions for now and it seems to look good |
| 5 | **rotation** | 1 | EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees | Y-rotation, relative to rotation of referenced road spline vertex |
| 6 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 10 | **position** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Position in 3D space, relative to position of referenced road spline vertex. The unit is meter |
### **TerrainEntry** ###
#### **Size**: 288 bytes ####
#### **Description**: The terrain model around 4 spline points. It has good explanation in original [Denis Auroux NFS file specs](http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "TRKD" | - |
| 4 | **block_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **block_number** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 12 | **unknown** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 13 | **fence** | 1 | TNFS fence type field. fence type: [lrtttttt]<br/>l - flag is add left fence<br/>r - flag is add right fence<br/>tttttt - texture id | - |
| 14 | **texture_ids** | 10 | Array of `10` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Texture ids to be used for terrain |
| 24 | **rows** | 264 | Array of `4` items<br/>Item size: 66 bytes<br/>Item type: Array of `11` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 7 bits is a fractional part | Terrain vertex positions. The unit is meter |
### **AIEntry** ###
#### **Size**: 3 bytes ####
#### **Description**: The record describing AI behavior at given terrain chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **max_ai_speed** | 1 | 1-byte unsigned integer | Max speed among all AI drivers in m/s |
| 1 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 2 | **max_traffic_speed** | 1 | 1-byte unsigned integer | Max traffic speed in m/s. Oncoming traffic does not obey it |
### **ModelPropDescrData** ###
#### **Size**: 14 bytes ####
#### **Description**: Map prop settings if it is a 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | An index of prop in the track FAM file |
| 1 | **resource_id_2** | 1 | 1-byte unsigned integer | Seems to always be equal to `resource_id`, except for one prop on map CL1, which is not used on map |
| 2 | **unk0** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part. Always == 1.5 | Unknown purpose |
| 6 | **unk1** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | The purpose is unknown. Every single entry in TNFS files equals to 1.5 (0x00_80_01_00) just like `unk0`, except for one prop on CL1, which has broken texture palette and which is not used on the map anyways |
| 10 | **unk2** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part. Always == 3 | Unknown purpose |
### **BitmapPropDescrData** ###
#### **Size**: 14 bytes ####
#### **Description**: Map prop settings if it is a bitmap ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | Represents texture id. How to get texture name from this value [explained](http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) well by Denis Auroux |
| 1 | **resource_id_2** | 1 | 1-byte unsigned integer | Oftenly equals to `resource_id`, but can be different |
| 2 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 6 | **frame_count** | 1 | 1-byte unsigned integer | Frame amount for animated object. Ignored if flag `is_animated` not set |
| 7 | **animation_interval** | 1 | TNFS time field. 1-byte unsigned integer, equals to amount of ticks (amount of seconds * 60) | Interval between animation frames in seconds |
| 8 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 9 | **unk1** | 1 | 1-byte unsigned integer | Unknown purpose |
| 10 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters |
### **TwoSidedBitmapPropDescrData** ###
#### **Size**: 14 bytes ####
#### **Description**: Map prop settings if it is a two-sided bitmap (fake 3D model) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | Represents texture id. How to get texture name from this value [explained](http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) well by Denis Auroux |
| 1 | **resource_id_2** | 1 | 1-byte unsigned integer | Texture id of second sprite, rotated 90 degrees. Logic to determine texture name is the same as for resource_id |
| 2 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 6 | **width_2** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters of second bitmap |
| 10 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters |
## **Physics** ##
### **CarPerformanceSpec** ###
#### **Size**: 1912 bytes ####
#### **Description**: This block describes full car physics specification for car that player can drive. Thanks to [Five-Damned-Dollarz](https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e) and [marcos2250](https://github.com/marcos2250/tnfs-1995/blob/main/tnfs_files.c) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **mass_front** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Mass applied to front axle (kg) |
| 4 | **mass_rear** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Mass applied to rear axle (kg) |
| 8 | **mass** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Total car mass (kg). Always == `mass_front + mass_rear` |
| 12 | **inv_mass_f** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Inverted mass applied to front axle in kg, `1 / mass_front` |
| 16 | **inv_mass_r** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Inverted mass applied to rear axle in kg, `1 / mass_rear` |
| 20 | **inv_mass** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Inverted mass in kg, `1 / mass` |
| 24 | **drive_bias** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Bias for drive force (0.0-1.0, where 0 is RWD, 1 is FWD), determines the amount of force applied to front and rear axles: 0.7 will distribute force 70% on the front, 30% on the rear |
| 28 | **brake_bias_f** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Bias for brake force (0.0-1.0), determines the amount of braking force applied to front and rear axles: 0.7 will distribute braking force 70% on the front, 30% on the rear |
| 32 | **brake_bias_r** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Bias for brake force for rear axle. Always == `1 - brake_bias_f` |
| 36 | **mass_y** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Probably the height of mass center in meters |
| 40 | **brake_force** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Brake force in unknown units |
| 44 | **brake_force2** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Brake force, equals to `brake_force`. Not clear why PBS has two of these, first number is responsible for braking on reverse, neutral and first gears, second number is responsible for braking on second gear. Interestingly, all gears > 2 use both numbers with unknown rules. Tested it on lamborghini |
| 48 | **unk0** | 4 | Bytes | Unknown purpose |
| 52 | **drag** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Drag force, units are unknown |
| 56 | **top_speed** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Max vehicle speed in meters per second |
| 60 | **efficiency** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part |  |
| 64 | **wheel_base** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | The distance betweeen rear and front axles in meters |
| 68 | **burnout_div** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part |  |
| 72 | **wheel_track** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | The distance betweeen left and right wheels in meters |
| 76 | **unk1** | 8 | Bytes | Unknown purpose |
| 84 | **mps_to_rpm** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * gearRatio) |
| 88 | **num_gears** | 4 | 4-bytes unsigned integer (little endian) | Amount of drive gears + 2 (R,N?) |
| 92 | **final_drive** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Final drive ratio |
| 96 | **wheel_radius** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Wheel radius in meters |
| 100 | **inv_wheel_rad** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Inverted wheel radius in meters, `1 / wheel_radius` |
| 104 | **gear_ratios** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Only first `num_gears` values are used. First element is the reverse gear ratio, second one is unknown |
| 136 | **num_torques** | 4 | 4-bytes unsigned integer (little endian) | Torques LUT (lookup table) size |
| 140 | **roll_stiff_f** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Roll stiffness front axle |
| 144 | **roll_stiff_r** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Roll stiffness rear axle |
| 148 | **roll_axis_y** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Roll axis height |
| 152 | **unk2** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube? |
| 164 | **slip_cutoff** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Slip angle cut-off |
| 168 | **normal_loss** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Normal coefficient loss |
| 172 | **max_rpm** | 4 | 4-bytes unsigned integer (little endian) | Engine max RPM |
| 176 | **min_rpm** | 4 | 4-bytes unsigned integer (little endian) | Engine min RPM |
| 180 | **torques** | 480 | Array of `60` items<br/>Item size: 8 bytes<br/>Item type: Two 32bit unsigned integers (little-endian). First one is RPM, second is a torque | LUT of engine torque depending on RPM. `num_torques` first elements used |
| 660 | **upshifts** | 28 | Array of `7` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | RPM value, when automatic gear box should upshift. 1 element per drive gear |
| 688 | **gear_efficiency** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) |  |
| 720 | **inertia_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part |  |
| 724 | **roll_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Body roll factor |
| 728 | **pitch_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Body pitch factor |
| 732 | **friction_f** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Front axle friction factor |
| 736 | **friction_r** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Rear axle friction factor |
| 740 | **body_len** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Chassis body length in meters |
| 744 | **body_width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Chassis body width in meters |
| 748 | **auto_steer** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Max auto steer angle |
| 752 | **steer_mult** | 4 | 4-bytes unsigned integer (little endian) | auto_steer_mult_shift |
| 756 | **steer_div** | 4 | 4-bytes unsigned integer (little endian) | auto_steer_div_shift |
| 760 | **steer_model** | 4 | 4-bytes unsigned integer (little endian) | Steering model |
| 764 | **steer_vel** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Auto steer velocities |
| 780 | **steer_vel_ramp** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Auto steer velocity ramp |
| 784 | **steer_vel_att** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Auto steer velocity attenuation |
| 788 | **steer_ramp_mult** | 4 | 4-bytes unsigned integer (little endian) | auto_steer_ramp_mult_shift |
| 792 | **steer_ramp_div** | 4 | 4-bytes unsigned integer (little endian) | auto_steer_ramp_div_shift |
| 796 | **lat_acc_cutoff** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Lateral acceleration cut-off |
| 800 | **unk3** | 8 | Bytes | First 4 bytes is integer number, and TNFS after reading file divides it in half at 0x00440364 |
| 808 | **final_ratio** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Final drive torque ratio |
| 812 | **thrust_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Thrust to acceleration factor |
| 816 | **unk4** | 36 | Bytes | Unknown purpose |
| 852 | **shift_timer** | 4 | 4-bytes unsigned integer (little endian) | Seems to be ticks taken to shift. Tick is 1 / 60 of a second |
| 856 | **rpm_dec** | 4 | 4-bytes unsigned integer (little endian) | RPM decrease when gas pedal released |
| 860 | **rpm_acc** | 4 | 4-bytes unsigned integer (little endian) | RPM increase when gas pedal pressed |
| 864 | **drop_rpm_dec** | 4 | 4-bytes unsigned integer (little endian) | Clutch drop RPM decrease |
| 868 | **drop_rpm_inc** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Clutch drop RPM increase |
| 872 | **neg_torque** | 4 | 32-bit real number (little-endian, signed), where last 7 bits is a fractional part | Negative torque |
| 876 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Body height in meters |
| 880 | **center_y** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part |  |
| 884 | **grip_table_f** | 512 | Array of `512` items<br/>Item size: 1 byte<br/>Item type: 8-bit real number (little-endian, not signed), where last 4 bits is a fractional part | Grip table for front axle. Unit is unknown |
| 1396 | **grip_table_r** | 512 | Array of `512` items<br/>Item size: 1 byte<br/>Item type: 8-bit real number (little-endian, not signed), where last 4 bits is a fractional part | Grip table for rear axle. Unit is unknown. Windows version overwrites this table with values from "grip_table_f" at 0x00440349 |
| 1908 | **checksum** | 4 | 4-bytes unsigned integer (little endian) | Check sum of this block contents. Equals to sum of 1880 first bytes. If wrong, game sets field "efficiency" to zero |
### **CarSimplifiedPerformanceSpec** ###
#### **Size**: 460 bytes ####
#### **Description**: This block describes simpler version of car physics. Used by game for other cars ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **col_size_x** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Collision model size (x) in meters. Zero for all non-playable cars |
| 4 | **col_size_y** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Collision model size (y) in meters. Zero for all non-playable cars |
| 8 | **col_size_z** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Collision model size (z) in meters. Zero for all non-playable cars |
| 12 | **moment_of_inertia** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Not clear how to interpret |
| 16 | **mass** | 4 | 32-bit real number (little-endian, not signed), where last 6 bits is a fractional part | Vehicle mass (kg?) |
| 20 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 24 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **power_curve** | 400 | Array of `100` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Not clear how to interpret |
| 428 | **top_speeds** | 24 | Array of `6` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Maximum car speed (m/s) per gear |
| 452 | **max_rpm** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Max engine RPM |
| 456 | **gear_count** | 4 | 4-bytes unsigned integer (little endian) | Gears amount |
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
### **Palette24BitDos** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x22 | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | num_colors\*3 | Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
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
## **Audio** ##
### **AsfAudio** ###
#### **Size**: 40..? bytes ####
#### **Description**: An audio file, which is supported by FFMPEG and can be converted using only it. Has some explanation [here](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "1SNh" | Resource ID |
| 4 | **unk0** | 8 | Bytes | Unknown purpose |
| 12 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | Sampling rate of audio |
| 16 | **sound_resolution** | 1 | 1-byte unsigned integer | How many bytes in one wave data entry |
| 17 | **channels** | 1 | 1-byte unsigned integer | Channels amount. 1 is mono, 2 is stereo |
| 18 | **compression** | 1 | 1-byte unsigned integer | If equals to 2, wave data is compressed with [IMA ADPCM codec](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)#IMA_ADPCM_Decompression_Algorithm) |
| 19 | **unk1** | 1 | 1-byte unsigned integer | Unknown purpose |
| 20 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | Amount of wave data entries. Should be multiplied by sound_resolution to calculated the size of data in bytes |
| 24 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | When audio ends, it repeats in loop from here. Should be multiplied by sound_resolution to calculate offset in bytes |
| 28 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | If play audio in loop, at this point we should rewind to repeat_loop_beginning. Should be multiplied by sound_resolution to calculate offset in bytes |
| 32 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of wave data start in current file, relative to start of the file itself |
| 36 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 40 | **offset** | space up to offset (wave_data_offset + 40) | Bytes | - |
| wave_data_offset + 40 | **wave_data** | min(`remaining file bytes`, `wave_data_length` \* `sound_resolution`) | Bytes | Wave data is here |
### **EacsAudioFile** ###
#### **Size**: 32..? bytes ####
#### **Description**: A file with single EACS audio entry ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **header** | 32 | [EacsAudioHeader](#eacsaudioheader) | - |
| 32 | **offset** | space up to offset `header.wave_data_offset` (global) | Bytes | Unknown purpose |
| wave_data_offset (global) | **wave_data** | min(`remaining file bytes`, `header.wave_data_length` \* `header.sound_resolution`) | Bytes | Wave data is here. If header.sound_resolution == 1, contains signed bytes, else - unsigned |
### **SoundBankHeaderEntry** ###
#### **Size**: 72 bytes ####
#### **Description**: Uknown wrapper around EACS header block, which is used in *.BNK files ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk** | 40 | Array of `10` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 40 | **eacs_header** | 32 | [EacsAudioHeader](#eacsaudioheader) | - |
### **EacsAudioHeader** ###
#### **Size**: 32 bytes ####
#### **Description**: A header for EACS audio. It is almost identical to AsfAudio when it is the only sound in the file (*.EAS), but also can be included in single SoundBank file (*.BNK), which has multiple EACS headers and wave data located separately ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "EACS" | Resource ID |
| 4 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | Sampling rate of audio |
| 8 | **sound_resolution** | 1 | 1-byte unsigned integer | How many bytes in one wave data entry |
| 9 | **channels** | 1 | 1-byte unsigned integer | Channels amount. 1 is mono, 2 is stereo |
| 10 | **compression** | 1 | 1-byte unsigned integer | If equals to 2, wave data is compressed with [IMA ADPCM](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)#IMA_ADPCM_Decompression_Algorithm) codec |
| 11 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 12 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | Amount of wave data entries. Should be multiplied by sound_resolution to calculated the size of data in bytes |
| 16 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | When audio ends, it repeats in loop from here. Should be multiplied by sound_resolution to calculate offset in bytes |
| 20 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | If play audio in loop, at this point we should rewind to repeat_loop_beginning. Should be multiplied by sound_resolution to calculate offset in bytes |
| 24 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of wave data start in current file, relative to start of the file itself |
| 28 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
## **Misc** ##
### **TnfsConfigDat** ###
#### **Size**: 24402 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **player_name** | 42 | UTF-8 string | Player name, leading with zeros. Though game allows to set name with as many as 8 characters, the game seems to work fine with name up to 42 symbols, though some part of name will be cut off in the UI |
| 42 | **unk0** | 139 | Bytes | Unknown purpose |
| 181 | **city_stats** | 2667 | [TrackStats](#trackstats) | - |
| 2848 | **coastal_stats** | 2667 | [TrackStats](#trackstats) | - |
| 5515 | **alpine_stats** | 2667 | [TrackStats](#trackstats) | - |
| 8182 | **rusty_springs_stats** | 2667 | [TrackStats](#trackstats) | - |
| 10849 | **autumn_valley_stats** | 2667 | [TrackStats](#trackstats) | - |
| 13516 | **burnt_sienna_stats** | 2667 | [TrackStats](#trackstats) | - |
| 16183 | **vertigo_ridge_stats** | 2667 | [TrackStats](#trackstats) | - |
| 18850 | **transtropolis_stats** | 2667 | [TrackStats](#trackstats) | - |
| 21517 | **lost_vegas_stats** | 2667 | [TrackStats](#trackstats) | - |
| 24184 | **unk1** | 39 | [BestRaceRecord](#bestracerecord) | Unknown purpose |
| 24223 | **unk2** | 177 | Bytes | Unknown purpose |
| 24400 | **unlocks_level** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: none<br/>1: warrior_vegas_mirror<br/>2: warrior_vegas_mirror_rally</details> | Level of unlocked features: warrior car, lost vegas track, mirror track mode, rally track mode |
| 24401 | **unk3** | 1 | Bytes | Unknown purpose |
### **TrackStats** ###
#### **Size**: 2667 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **best_lap_1** | 39 | [BestRaceRecord](#bestracerecord) | Best single lap time (closed track). Best time of first segment for open track |
| 39 | **best_lap_2** | 39 | [BestRaceRecord](#bestracerecord) | Best time of second segment (open track). Zeros for closed track |
| 78 | **best_lap_3** | 39 | [BestRaceRecord](#bestracerecord) | Best time of third segment (open track). Zeros for closed track |
| 117 | **top_speed_1** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on first segment (open track). Zeros for closed track |
| 156 | **top_speed_2** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on second segment (open track). Zeros for closed track |
| 195 | **top_speed_3** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on third segment (open track). Zeros for closed track |
| 234 | **best_race_time_table_1** | 390 | Array of `10` items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with minimum amount of laps: for open track total time of all 3 segments, for closed track time of minimum selection of laps (2 or 4 depending on track) |
| 624 | **best_race_time_table_2** | 390 | Array of `10` items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with middle amount of laps (6 or 8 depending on track). Zeros for open track |
| 1014 | **best_race_time_table_3** | 390 | Array of `10` items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with maximum amount of laps (12 or 16 depending on track). Zeros for open track |
| 1404 | **top_race_speed** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on the whole race. Why it is not equal to max stat between top_speed_1, top_speed_2 and top_speed_3 for open track? |
| 1443 | **unk** | 1224 | Bytes | Unknown purpose |
### **BestRaceRecord** ###
#### **Size**: 39 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 11 | UTF-8 string | Racer name |
| 11 | **unk0** | 4 | Bytes | Unknown purpose |
| 15 | **car_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: RX-7<br/>1: NSX<br/>2: SUPRA<br/>3: 911<br/>4: CORVETTE<br/>5: VIPER<br/>6: 512TR<br/>7: DIABLO<br/>8: WAR_SLEW?<br/>9: WAR_WATCH?<br/>10: WAR_TOURNY?<br/>11: WAR?</details> | A car identifier. Last 4 options are unclear, names came from decompiled NFS.EXE |
| 16 | **unk1** | 11 | Bytes | Unknown purpose |
| 27 | **time** | 4 | TNFS time field. 4-bytes unsigned integer (little endian), equals to amount of ticks (amount of seconds * 60) | Total track time in seconds |
| 31 | **unk2** | 1 | Bytes | Unknown purpose |
| 32 | **top_speed** | 3 | TNFS top speed record. Appears to be 24-bit real number (sign unknown because big values show up as N/A in the game), little-endian, where last 8 bits is a fractional part. For determining speed, ONLY INTEGER PART of this number should be multiplied by 2,240000000001 and rounded up, e.g. 0xFF will be equal to 572mph. Note: probably game multiplies number by 2,24 with some fast algorithm so it rounds up even integer result, because 0xFA (*2,24 == 560.0) shows up in game as 561mph | Top speed |
| 35 | **game_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: time_trial<br/>1: head_to_head<br/>2: full_grid_race</details> | Game mode. In the game shown as "t.t.", "h.h." or empty string |
| 36 | **unk3** | 3 | Bytes. Always == b'\x00\x00\x00' | Unknown purpose |
