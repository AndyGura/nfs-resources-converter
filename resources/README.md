# **File specs** #

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

**\*.PBS** car physics. [CarPerformanceSpec](#carperformancespec), **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.PDN** car characteristic for unknown purpose. [CarSimplifiedPerformanceSpec](#carsimplifiedperformancespec), **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.TGV** video, I just use ffmpeg to convert it

**\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. [TriMap](#trimap)

**GAMEDATA\CONFIG\CONFIG.DAT** Player name, best times, whether warrior car unlocked etc. [TnfsConfigDat](#tnfsconfigdat)


# **Block specs** #
## **Archives** ##
### **ShpiBlock** ###
#### **Size**: 16..? bytes ####
#### **Description**: A container of images and palettes for them ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "SHPI" | Resource ID |
| 4 | **length** | 4 | 4-bytes unsigned integer (little endian) | The length of this SHPI block in bytes |
| 8 | **children_count** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 12 | **shpi_directory** | 4 | UTF-8 string | One of: "LN32", "GIMX", "WRAP". The purpose is unknown |
| 16 | **children_descriptions** | children_count\*8 | Array of `children_count` items<br/>Item size: 8 bytes<br/>Item type: 8-bytes record, first 4 bytes is a UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | An array of items, each of them represents name of SHPI item (image or palette) and offset to item data in file, relatively to SHPI block start (where resource id string is presented). Names are not always unique |
| 16 + children_count\*8 | **children** | ? | Array of `children_count + ?` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [Bitmap4Bit](#bitmap4bit)<br/>- [Bitmap8Bit](#bitmap8bit)<br/>- [Bitmap16Bit0565](#bitmap16bit0565)<br/>- [Bitmap32Bit](#bitmap32bit)<br/>- [Bitmap16Bit1555](#bitmap16bit1555)<br/>- [Bitmap24Bit](#bitmap24bit)<br/>- [Palette24BitDos](#palette24bitdos)<br/>- [Palette24Bit](#palette24bit)<br/>- [Palette32Bit](#palette32bit)<br/>- [Palette16Bit](#palette16bit)<br/>- [Palette16BitDos](#palette16bitdos)<br/>- [PaletteReference](#palettereference)<br/>- [ShpiText](#shpitext)<br/>- Nothing, block skipped | A part of block, where items data is located. Offsets to some of the entries are defined in `children_descriptions` block. Between them there can be non-indexed entries (palettes and texts) |
### **WwwwBlock** ###
#### **Size**: 8..? bytes ####
#### **Description**: A block-container with various data: image archives, geometries, other wwww blocks. If has ORIP 3D model, next item is always SHPI block with textures to this 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "wwww" | Resource ID |
| 4 | **children_count** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 8 | **children_offsets** | children_count\*4 | Array of `children_count` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file, relatively to wwww block start (where resource id string is presented) |
| 8 + children_count\*4 | **children** | ? | Array of `children_count` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [ShpiBlock](#shpiblock)<br/>- [OripGeometry](#oripgeometry)<br/>- [WwwwBlock](#wwwwblock)<br/>- Nothing, block skipped | A part of block, where items data is located. Offsets are defined in previous block, lengths are calculated: either up to next item offset, or up to the end of this block |
### **SoundBank** ###
#### **Size**: 512..? bytes ####
#### **Description**: A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **children_offsets** | 4 * (128) | Array of 128 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file. Zero values seem to be ignored, but for some reason the very first offset is 0 in most files. The real audio data start is shifted 40 bytes forward for some reason, so EACS is located at {offset from this array} + 40 |
| 512 | **children** | ? | Array of ? items with custom offset to items<br/>Item type: [EacsAudio](#eacsaudio) | EACS blocks are here, placed at offsets from previous block. Those EACS blocks don't have own wave data, there are 44 bytes of unknown data instead, offsets in them are pointed to wave data of this block |
| 512..? | **wave_data** | ? | Array of ? items with custom offset to items<br/>Item size: 0..? bytes<br/>Item type: Raw bytes sequence | A space, where wave data is located. Pointers are in children EACS |
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
| 16 | **vertex_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices |
| 20 | **unk2** | 4 | Bytes | Unknown purpose |
| 24 | **vertex_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertex_block |
| 28 | **vertex_uvs_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex UV-s (texture coordinates) |
| 32 | **vertex_uvs_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertex_uvs_block. Always equals to `112+polygon_count*12` |
| 36 | **polygon_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of polygons |
| 40 | **polygon_block_offset** | 4 | 4-bytes unsigned integer (little endian). Always == 0x70 | An offset to polygons block |
| 44 | **identifier** | 12 | UTF-8 string | Some ID of geometry, don't know the purpose |
| 56 | **texture_names_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture names |
| 60 | **texture_names_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture names block. Always equals to `112+polygon_count*12+vertex_uvs_count*8` |
| 64 | **texture_number_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture numbers |
| 68 | **texture_number_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture numbers block |
| 72 | **render_order_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in render_order block |
| 76 | **render_order_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of render_order block. Always equals to `texture_number_block_offset+texture_number_count*20` |
| 80 | **polygon_vertex_map_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of polygon_vertex_map block |
| 84 | **labels0_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in labels0 block |
| 88 | **labels0_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of labels0 block. Always equals to `texture_number_block_offset+texture_number_count*20+render_order_count*28` |
| 92 | **labels_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in labels block |
| 96 | **labels_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of labels block. Always equals to `texture_number_block_offset+texture_number_count*20+render_order_count*28+labels0_count*12` |
| 100 | **unknowns1** | 12 | Bytes | Unknown purpose |
| 112 | **polygons_block** | polygon_count\*12 | Array of `polygon_count` items<br/>Item type: [OripPolygon](#orippolygon) | A block with polygons of the geometry. Probably should be a start point when building model from this file |
| vertex_uvs_block_offset | **vertex_uvs_block** | vertex_uvs_count\*8 | Array of `vertex_uvs_count` items<br/>Item size: 8 bytes<br/>Item type: Texture coordinates for vertex, where each coordinate is: 4-bytes unsigned integer (little endian). The unit is a pixels amount of assigned texture. So it should be changed when selecting texture with different size | A table of texture coordinates. Items are retrieved by index, located in polygon_vertex_map_block |
| texture_names_block_offset | **texture_names_block** | texture_names_count\*20 | Array of `texture_names_count` items<br/>Item type: [OripTextureName](#oriptexturename) | A table of texture references. Items are retrieved by index, located in polygon item |
| texture_names_block_offset + texture_names_count\*20 | **offset** | space up to offset `texture_number_block_offset` | Bytes | In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in case of DIABLO.CFM it's length is equal to -3, meaning that last 3 bytes from texture names block are reused by next block |
| texture_number_block_offset | **texture_number_map_block** | texture_number_count\*20 | Array of `texture_number_count` items<br/>Item size: 20 bytes<br/>Item type: Array of `20` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| render_order_block_offset | **render_order_block** | render_order_count\*28 | Array of `render_order_count` items<br/>Item type: [RenderOrderBlock](#renderorderblock) | Render order. The exact mechanism how it works is unknown |
| labels0_block_offset | **labels0_block** | labels0_count\*12 | Array of `labels0_count` items<br/>Item size: 12 bytes<br/>Item type: 12-bytes record, first 8 bytes is a UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | Unclear |
| labels_block_offset | **labels_block** | labels_count\*12 | Array of `labels_count` items<br/>Item size: 12 bytes<br/>Item type: 12-bytes record, first 8 bytes is a UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | Describes tires, smoke and car lights. Smoke effect under the wheel will be displayed on drifting, accelerating and braking in the place where texture is shown. 3DO version ORIP description: "Texture indexes referenced from records in block 10 and block 11th. Texture index shows that wheel or back light will be displayed on the polygon number defined in block 10." - the issue is that TNFSSE orip files consist of 9 blocks |
| vertex_block_offset | **vertex_block** | vertex_count\*12 | Array of `vertex_count` items<br/>Item size: 12 bytes<br/>Item type: One of types:<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 7 bits is a fractional part. The unit is meter<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 4 bits is a fractional part. The unit is meter | A table of mesh vertices in 3D space. For cars it consists of 32:7 points, else 32:4 |
| polygon_vertex_map_block_offset | **polygon_vertex_map_block** | ?\*4 | Array of `?` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | A LUT for both 3D and 2D vertices. Every item is an index of either item in vertex_block or vertex_uvs_block. When building 3D vertex, polygon defines offset_3d, a lookup to this table, and value from here is an index of item in vertex_block. When building UV-s, polygon defines offset_2d, a lookup to this table, and value from here is an index of item in vertex_uvs_block |
### **OripPolygon** ###
#### **Size**: 12 bytes ####
#### **Description**: A geometry polygon ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_type** | 1 | 1-byte unsigned integer | Huh, that's a srange field. From my tests, if it is xxx0_0011, the polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only one polygon for entire TNFS with type == 2 in burnt sienna props. If ignore this polygon everything still looks great |
| 1 | **mapping** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: two_sided<br/>1: flip_normal<br/>4: use_uv</details> | Rendering properties of the polygon |
| 2 | **texture_index** | 1 | 1-byte unsigned integer | The index of item in ORIP's texture_names block |
| 3 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **offset_3d** | 4 | 4-bytes unsigned integer (little endian) | The index in polygon_vertex_map_block ORIP's table. This index represents first vertex of this polygon, so in order to determine all vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. Look at polygon_vertex_map_block description for more info |
| 8 | **offset_2d** | 4 | 4-bytes unsigned integer (little endian) | The same as offset_3d, also points to polygon_vertex_map_block, but used for texture coordinates. Look at polygon_vertex_map_block description for more info |
### **OripTextureName** ###
#### **Size**: 20 bytes ####
#### **Description**: A settings of the texture. From what is known, contains name of bitmap ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 8 | UTF-8 string | - |
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
#### **Description**: Map TRI file, represents terrain mesh, road itself, proxy object locations etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x11 | Resource ID |
| 4 | **num_segments** | 2 | 2-bytes unsigned integer (little endian) | 0 for open tracks, num segments for closed |
| 6 | **terrain_length** | 2 | 2-bytes unsigned integer (little endian) | number of terrain chunks (max 600) |
| 8 | **unk0** | 2 | 2-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 10 | **unk1** | 2 | 2-bytes unsigned integer (little endian). Always == 0x6 | Unknown purpose |
| 12 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part. The unit is meter | Unknown purpose |
| 24 | **unknowns0** | 12 | Array of 12 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 36 | **terrain_block_size** | 4 | 4-bytes unsigned integer (little endian) | Size of terrain array in bytes (terrain_length * 0x120) |
| 40 | **railing_texture_id** | 4 | 4-bytes unsigned integer (little endian) | Do not know what is "railing". Doesn't look like a fence texture id, tested in TR1_001.FAM |
| 44 | **lookup_table** | 4 * (600) | Array of 600 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | 600 consequent numbers, each value is previous + 288. Looks like a space needed by the original NFS engine |
| 2444 | **road_spline** | 36 * (2400) | Array of 2400 items<br/>Item type: [RoadSplinePoint](#roadsplinepoint) | Road spline is a series of points in 3D space, located at the center of road. Around this spline the track terrain mesh is built. TRI always has 2400 elements, however it uses only amount of vertices, equals to (terrain_length * 4), after them records filled with zeros. For opened tracks, finish line will be always located at spline point (terrain_length * 4 - 179) |
| 88844 | **ai_info** | 3 * (600) | Array of 600 items<br/>Item type: [AIEntry](#aientry) | - |
| 90644 | **proxy_objects_count** | 4 | 4-bytes unsigned integer (little endian) | - |
| 90648 | **proxy_object_instances_count** | 4 | 4-bytes unsigned integer (little endian) | - |
| 90652 | **object_header_text** | 4 | UTF-8 string. Always == SJBO | - |
| 90656 | **unk2** | 4 | 4-bytes unsigned integer (little endian). Always == 0x428c | Unknown purpose |
| 90660 | **unk3** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 90664 | **proxy_objects** | 16 * (proxy_objects_count) | Array of proxy_objects_count items<br/>Item type: [ProxyObject](#proxyobject) | - |
| 90664..? | **proxy_object_instances** | 16 * (proxy_object_instances_count) | Array of proxy_object_instances_count items<br/>Item type: [ProxyObjectInstance](#proxyobjectinstance) | - |
| 90664..? | **terrain** | 288 * (terrain_length) | Array of terrain_length items<br/>Item type: [TerrainEntry](#terrainentry) | - |
### **RoadSplinePoint** ###
#### **Size**: 36 bytes ####
#### **Description**: The description of one single point of road spline. Thank you jeff-1amstudios for your OpenNFS1 project: https://github.com/jeff-1amstudios/OpenNFS1 ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **left_verge_distance** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to the left edge of road. After this point the grip decreases |
| 1 | **right_verge_distance** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to the right edge of road. After this point the grip decreases |
| 2 | **left_barrier_distance** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to invisible wall on the left |
| 3 | **right_barrier_distance** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to invisible wall on the right |
| 4 | **unknowns0** | 3 | Array of 3 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 7 | **spline_item_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: lane_split<br/>1: default_0<br/>2: lane_merge<br/>3: default_1<br/>4: tunnel<br/>5: cobbled_road<br/>7: right_tunnel_A9_A2<br/>9: left_tunnel_A4_A7<br/>12: left_tunnel_A4_A8<br/>13: left_tunnel_A5_A8<br/>14: waterfall_audio_left_channel<br/>15: waterfall_audio_right_channel<br/>17: transtropolis_noise_audio<br/>18: water_audio</details> | Modifier of this point. Affects terrain geometry and/or some gameplay features |
| 8 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part. The unit is meter | Coordinates of this point in 3D space |
| 20 | **slope** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Slope of the road at this point (angle if road goes up or down) |
| 22 | **slant_a** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Perpendicular angle of road |
| 24 | **orientation** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Rotation of road path, if view from the top. Equals to atan2(next_x - x, next_z - z) |
| 26 | **unknowns1** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 28 | **orientation_vector_x** | 2 | 2-bytes signed integer (little endian) | Orientation vector is a 2D vector, normalized to ~32766 with angle == orientation field above, used for pseudo-3D effect on opponent cars. So orientation_vector_x == cos(orientation) * 32766 |
| 30 | **slant_b** | 2 | EA games 16-bit angle (little-endian). 0 means 0 degrees, 0x10000 (max value + 1) means 360 degrees | has the same purpose as slant_a, but is a standard signed 16-bit value. Its value is positive for the left, negative for the right. The approximative relation between slant-A and slant-B is slant-B = -12.3 slant-A (remember that slant-A is 14-bit, though) |
| 32 | **orientation_vector_neg_z** | 2 | 2-bytes signed integer (little endian) | Orientation vector is a 2D vector, normalized to ~32766 with angle == orientation field above, used for pseudo-3D effect on opponent cars. So orientation_vector_neg_z == -sin(orientation) * 32766 |
| 34 | **unknowns2** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
### **ProxyObject** ###
#### **Size**: 16 bytes ####
#### **Description**: The description of map proxy object: everything except terrain (road signs, buildings etc.) Thanks to jeff-1amstudios and his OpenNFS1 project: https://github.com/jeff-1amstudios/OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202 ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **flags** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>2: is_animated</details> | Different modes of proxy object |
| 1 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: unk<br/>1: model<br/>4: bitmap<br/>6: two_sided_bitmap</details> | Type of proxy object |
| 2 | **proxy_object_data** | 14 | One of types:<br/>- [ModelProxyObjectData](#modelproxyobjectdata)<br/>- [BitmapProxyObjectData](#bitmapproxyobjectdata)<br/>- [TwoSidedBitmapProxyObjectData](#twosidedbitmapproxyobjectdata)<br/>- [UnknownProxyObjectData](#unknownproxyobjectdata) | Settings of the prop. Block class picked according to <type> |
### **ProxyObjectInstance** ###
#### **Size**: 16 bytes ####
#### **Description**: The occurrence of proxy object. For instance: exactly the same road sign used 5 times on the map. In this case file will have 1 ProxyObject for this road sign and 5 ProxyObjectInstances ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **reference_road_spline_vertex** | 4 | 4-bytes signed integer (little endian) | Sometimes has too big value, I skip those instances for now and it seems to look good. Probably should consider this value to be 16-bit integer, having some unknown 16-integer as next field. Also, why it is signed? |
| 4 | **proxy_object_index** | 1 | 1-byte unsigned integer | Sometimes has too big value, I use object index % amount of proxies for now and it seems to look good |
| 5 | **rotation** | 1 | EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees | Y-rotation, relative to rotation of referenced road spline vertex |
| 6 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 10 | **position** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part. The unit is meter | Position in 3D space, relative to position of referenced road spline vertex |
### **TerrainEntry** ###
#### **Size**: 288 bytes ####
#### **Description**: The terrain model around 4 spline points. It has good explanation in original Denis Auroux NFS file specs: http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == TRKD | - |
| 4 | **block_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **block_number** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 12 | **unknown** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 13 | **fence** | 1 | TNFS fence type field. fence type: [lrtttttt]<br/>l - flag is add left fence<br/>r - flag is add right fence<br/>tttttt - texture id | - |
| 14 | **texture_ids** | 10 | Array of 10 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Texture ids to be used for terrain |
| 24 | **rows** | 66 * (4) | Array of 4 items<br/>Item size: 66 bytes<br/>Item type: Array of 11 items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 7 bits is a fractional part. The unit is meter | Terrain vertex positions |
### **AIEntry** ###
#### **Size**: 3 bytes ####
#### **Description**: The record describing AI behavior at given terrain chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **ai_speed** | 1 | 1-byte unsigned integer | Speed (m/h ?? ) of AI racer |
| 1 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 2 | **traffic_speed** | 1 | 1-byte unsigned integer | Speed (m/h ?? ) of traffic car |
### **ModelProxyObjectData** ###
#### **Size**: 14 bytes ####
#### **Description**: The proxy object settings if it is a 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | An index of prop in the track FAM file |
| 1 | **unknowns** | 13 | Array of 13 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
### **BitmapProxyObjectData** ###
#### **Size**: 14 bytes ####
#### **Description**: The proxy object settings if it is a bitmap ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | Represents texture id. How to get texture name from this value explained well by Denis Auroux http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt |
| 1 | **proxy_number** | 1 | 1-byte unsigned integer | Seems to be always equal to own index * 4 |
| 2 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 6 | **frame_count** | 1 | 1-byte unsigned integer | Frame amount for animated object. Ignored if flag `is_animated` not set |
| 7 | **animation_interval** | 1 | EA games time interval field: 0 = 0ms, 256 = 4000ms (4 seconds). Max value (255) is 3984.375ms | Interval between animation frames |
| 8 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 9 | **unk1** | 1 | 1-byte unsigned integer | Unknown purpose |
| 10 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters |
### **TwoSidedBitmapProxyObjectData** ###
#### **Size**: 14 bytes ####
#### **Description**: The proxy object settings if it is a two-sided bitmap (fake 3D model) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | Represents texture id. How to get texture name from this value explained well by Denis Auroux http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt |
| 1 | **resource_2_id** | 1 | 1-byte unsigned integer | Texture id of second sprite, rotated 90 degrees. Logic to determine texture name is the same as for resource_id |
| 2 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 6 | **width_2** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters of second bitmap |
| 10 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters |
### **UnknownProxyObjectData** ###
#### **Size**: 14 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unknowns** | 14 | Array of 14 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
## **Physics** ##
### **CarPerformanceSpec** ###
#### **Size**: 1912 bytes ####
#### **Description**: This block describes full car physics specification for car that player can drive. Looks like it's not used for opponent cars and such files do not exist for traffic/cop cars at all. Big thanks to Five-Damned-Dollarz, he seems to be the only one guy who managed to understand most of the fields in this block. His specification: https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e ####
<details>
<summary>Click to see block specs (65 fields)</summary>

| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **mass_front_axle** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | The meaning is theoretical. For all cars value is mass / 2 |
| 4 | **mass_rear_axle** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | The meaning is theoretical. For all cars value is mass / 2 |
| 8 | **mass** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Car mass |
| 12 | **unknowns0** | 4 * (4) | Array of 4 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 28 | **brake_bias** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Bias for brake force (0.0-1.0), determines the amount of braking force applied to front and rear axles: 0.7 will distribute braking force 70% on the front, 30% on the rear |
| 32 | **unknowns1** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 36 | **center_of_gravity** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | probably the height of mass center in meters |
| 40 | **max_brake_decel** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 44 | **unknowns2** | 4 * (2) | Array of 2 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 52 | **drag** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 56 | **top_speed** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 60 | **efficiency** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 64 | **body__wheel_base** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | The distance betweeen rear and front axles in meters |
| 68 | **burnout_div** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 72 | **body__wheel_track** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | The distance betweeen left and right wheels in meters |
| 76 | **unknowns3** | 4 * (2) | Array of 2 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 84 | **mps_to_rpm_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * gearRatio) |
| 88 | **transmission__gears_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of drive gears + 2 (R,N?) |
| 92 | **transmission__final_drive_ratio** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 96 | **roll_radius** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 100 | **unknowns4** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 104 | **transmission__gear_ratios** | 4 * (8) | Array of 8 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Only first <gear_count> values are used. First element is the reverse gear ratio, second one is unknown |
| 136 | **engine__torque_count** | 4 | 4-bytes unsigned integer (little endian) | Torques LUT (lookup table) size |
| 140 | **front_roll_stiffness** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 144 | **rear_roll_stiffness** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 148 | **roll_axis_height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 152 | **unknowns5** | 4 * (3) | Array of 3 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube? |
| 164 | **slip_angle_cutoff** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 168 | **normal_coefficient_loss** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 172 | **engine__max_rpm** | 4 | 4-bytes unsigned integer (little endian) | - |
| 176 | **engine__min_rpm** | 4 | 4-bytes unsigned integer (little endian) | - |
| 180 | **engine__torques** | 8 * (60) | Array of 60 items<br/>Item type: [EngineTorqueRecord](#enginetorquerecord) | LUT (lookup table) of engine torque depending on RPM. <engine__torque_count> first elements used |
| 660 | **transmission__upshifts** | 4 * (5) | Array of 5 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | RPM value, when automatic gear box should upshift. 1 element per drive gear |
| 680 | **unknowns6** | 2 * (4) | Array of 4 items<br/>Item size: 2 bytes<br/>Item type: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Unknown purpose |
| 688 | **unknowns7** | 4 * (7) | Array of 7 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 716 | **unknowns8** | 2 * (2) | Array of 2 items<br/>Item size: 2 bytes<br/>Item type: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Unknown purpose |
| 720 | **inertia_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 724 | **body_roll_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 728 | **body_pitch_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 732 | **front_friction_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 736 | **rear_fricton_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 740 | **body__length** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Chassis body length in meters |
| 744 | **body__width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Chassis body width in meters |
| 748 | **steering__max_auto_steer_angle** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 752 | **steering__auto_steer_mult_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 756 | **steering__auto_steer_div_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 760 | **steering__steering_model** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 764 | **steering__auto_steer_velocities** | 4 * (4) | Array of 4 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 780 | **steering__auto_steer_velocity_ramp** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 784 | **steering__auto_steer_velocity_attenuation** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 788 | **steering__auto_steer_ramp_mult_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 792 | **steering__auto_steer_ramp_div_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 796 | **lateral_accel_cutoff** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 800 | **unknowns9** | 4 * (13) | Array of 13 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 852 | **engine_shifting__shift_timer** | 4 | 4-bytes unsigned integer (little endian) | Unknown exactly, but it seems to be ticks taken to shift. Tick is probably 100ms |
| 856 | **engine_shifting__rpm_decel** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 860 | **engine_shifting__rpm_accel** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 864 | **engine_shifting__clutch_drop_decel** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 868 | **engine_shifting__neg_torque** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 872 | **body__clearance** | 4 | 32-bit real number (little-endian, signed), where last 7 bits is a fractional part | - |
| 876 | **body__height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 880 | **center_x** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 884 | **unknowns10** | 512 | Array of 512 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown values. in 3DO version "grip_curve_front" is here, takes the same space |
| 1396 | **unknowns11** | 512 | Array of 512 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown values. in 3DO version "grip_curve_rear" is here, takes the same space |
| 1908 | **hash** | 4 | 4-bytes unsigned integer (little endian) | Check sum of this block contents |
</details>

### **EngineTorqueRecord** ###
#### **Size**: 8 bytes ####
#### **Description**: Engine torque for given RPM record ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **rpm** | 4 | 4-bytes unsigned integer (little endian) | - |
| 4 | **torque** | 4 | 4-bytes unsigned integer (little endian) | - |
### **CarSimplifiedPerformanceSpec** ###
#### **Size**: 460 bytes ####
#### **Description**: This block describes simpler version of car physics. It is not clear how and when is is used ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unknowns0** | 4 * (3) | Array of 3 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown. Some values for playable cars, always zeros for non-playable |
| 12 | **moment_of_inertia** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Not clear how to interpret |
| 16 | **unknowns1** | 4 * (3) | Array of 3 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 28 | **power_curve** | 4 * (100) | Array of 100 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Not clear how to interpret |
| 428 | **top_speeds** | 4 * (6) | Array of 6 items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Maximum car speed (m/s) per gear |
| 452 | **max_rpm** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Max engine RPM |
| 456 | **gear_count** | 4 | 4-bytes unsigned integer (little endian) | Gears amount |
## **Bitmaps** ##
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
| 16 | **bitmap** | ceil((width\*height)\*4/8) | Array of `width*height` sub-byte numbers. Each number consists of 4 bits | Font atlas bitmap data |
### **Bitmap8Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: 8bit bitmap can be serialized to image only with palette. Basically, for every pixel it uses 8-bit index of color in assigned palette. The tricky part is to determine how the game understands which palette to use. In most cases, if bitmap has embedded palette, it should be used, EXCEPT Autumn Valley fence texture: there embedded palette should be ignored. In all other cases it is tricky even more: it uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, palette can be in a different SHPI before this one. In CONTROL directory most of QFS files use !pal even from different QFS file! It is a mystery how to reliably pick palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7b | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 4 | Bytes | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width\*height | Array of `width*height` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Color indexes of bitmap pixels. The actual colors are in assigned to this bitmap palette |
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
## **Fonts** ##
### **FfnFont** ###
#### **Size**: 48..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "FNTF" | Resource ID |
| 4 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | The length of this FFN block in bytes |
| 8 | **unk0** | 1 | 1-byte unsigned integer. Always == 0x64 | Unknown purpose |
| 9 | **unk1** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 10 | **symbols_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of symbols, defined in this font |
| 12 | **unk2** | 6 | Bytes | Unknown purpose |
| 18 | **font_size** | 1 | 1-byte unsigned integer | Font size ? |
| 19 | **unk3** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 20 | **line_height** | 1 | 1-byte unsigned integer | Line height ? |
| 21 | **unk4** | 7 | Bytes. Always == b'\x00\x00\x00\x00\x00\x00\x00' | Unknown purpose |
| 28 | **bitmap_data_pointer** | 2 | 2-bytes unsigned integer (little endian) | Pointer to bitmap block |
| 30 | **unk5** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 31 | **unk6** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 32 | **definitions** | symbols_amount\*11 | Array of `symbols_amount` items<br/>Item type: [SymbolDefinitionRecord](#symboldefinitionrecord) | Definitions of chars in this bitmap font |
| 32 + symbols_amount\*11 | **skip_bytes** | up to offset bitmap_data_pointer | Bytes | 4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36) |
| bitmap_data_pointer | **bitmap** | 16..? | [Bitmap4Bit](#bitmap4bit) | Font atlas bitmap data |
### **SymbolDefinitionRecord** ###
#### **Size**: 11 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **code** | 2 | 2-bytes unsigned integer (little endian) | Code of symbol |
| 2 | **glyph_width** | 1 | 1-byte unsigned integer | Width of symbol in font bitmap |
| 3 | **glyph_height** | 1 | 1-byte unsigned integer | Height of symbol in font bitmap |
| 4 | **glyph_x** | 2 | 2-bytes unsigned integer (little endian) | Position (x) of symbol in font bitmap |
| 6 | **glyph_y** | 2 | 2-bytes unsigned integer (little endian) | Position (y) of symbol in font bitmap |
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
| 4 | **colors_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **colors_amount1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to colors_amount? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | colors_amount\*3 | Array of `colors_amount` items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
### **Palette24Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x24 | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **colors_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **colors_amount1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to colors_amount? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | colors_amount\*3 | Array of `colors_amount` items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (big-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2a | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **colors_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **colors_amount1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to colors_amount? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | colors_amount\*4 | Array of `colors_amount` items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette16Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2d | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **colors_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **colors_amount1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to colors_amount? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | colors_amount\*2 | Array of `colors_amount` items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb. 0x7c0 (0x00FB00 RGB) is always transparent | Colors LUT |
### **Palette16BitDos** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black for unknown reason ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x29 | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **colors_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **colors_amount1** | 2 | 2-bytes unsigned integer (little endian) | Always equal to colors_amount? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | colors_amount\*2 | Array of `colors_amount` items<br/>Item size: 2 bytes<br/>Item type: 16-bit color, not tested properly | Colors LUT |
## **Audio** ##
### **AsfAudio** ###
#### **Size**: 36..? bytes ####
#### **Description**: An audio file, which is supported by FFMPEG and can be converted using only it. Has some explanation here: https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2) . It is very similar to EACS audio, but has wave data in place, just after the header ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == 1SNh | Resource ID |
| 4 | **unknowns** | 8 | Array of 8 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | Sampling rate of audio |
| 16 | **sound_resolution** | 1 | 1-byte unsigned integer | How many bytes in one wave data entry |
| 17 | **channels** | 1 | 1-byte unsigned integer | Channels amount. 1 is mono, 2 is stereo |
| 18 | **compression** | 1 | 1-byte unsigned integer | If equals to 2, wave data is compressed with IMA ADPCM codec: https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)#IMA_ADPCM_Decompression_Algorithm |
| 19 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 20 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | Amount of wave data entries. Should be multiplied by sound_resolution to calculated the size of data in bytes |
| 24 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | When audio ends, it repeats in loop from here. Should be multiplied by sound_resolution to calculate offset in bytes |
| 28 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | If play audio in loop, at this point we should rewind to repeat_loop_beginning. Should be multiplied by sound_resolution to calculate offset in bytes |
| 32 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of wave data start in current file, relative to start of the file itself |
| 36 | **wave_data** | 0..? | Raw bytes sequence | Wave data is here |
### **EacsAudio** ###
#### **Size**: 28..? bytes ####
#### **Description**: An audio block, almost identical to AsfAudio, but can be included in single SoundBank file with multiple other EACS blocks and has detached wave data, which is located somewhere in the SoundBank file after all EACS blocks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == EACS | Resource ID |
| 4 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | Sampling rate of audio |
| 8 | **sound_resolution** | 1 | 1-byte unsigned integer | How many bytes in one wave data entry |
| 9 | **channels** | 1 | 1-byte unsigned integer | Channels amount. 1 is mono, 2 is stereo |
| 10 | **compression** | 1 | 1-byte unsigned integer | If equals to 2, wave data is compressed with IMA ADPCM codec: https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)#IMA_ADPCM_Decompression_Algorithm |
| 11 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 12 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | Amount of wave data entries. Should be multiplied by sound_resolution to calculated the size of data in bytes |
| 16 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | When audio ends, it repeats in loop from here. Should be multiplied by sound_resolution to calculate offset in bytes |
| 20 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | If play audio in loop, at this point we should rewind to repeat_loop_beginning. Should be multiplied by sound_resolution to calculate offset in bytes |
| 24 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of wave data start in current file, relative to start of the file itself |
| - | **wave_data** | 0..? | Detached block, located somewhere in file, knowing it's offset.Does not take place inside parent block | Wave data, located somewhere in file at wave_data_offset. if sound_resolution == 1, contains signed bytes, else - unsigned |
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
| 234 | **best_race_time_table_1** | 39 * (10) | Array of 10 items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with minimum amount of laps: for open track total time of all 3 segments, for closed track time of minimum selection of laps (2 or 4 depending on track) |
| 624 | **best_race_time_table_2** | 39 * (10) | Array of 10 items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with middle amount of laps (6 or 8 depending on track). Zeros for open track |
| 1014 | **best_race_time_table_3** | 39 * (10) | Array of 10 items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with maximum amount of laps (12 or 16 depending on track). Zeros for open track |
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
| 27 | **time** | 4 | TNFS time field (in physics ticks?). 4-bytes unsigned integer, little-endian, equals to amount of seconds * 60 | Total track time |
| 31 | **unk2** | 1 | Bytes | Unknown purpose |
| 32 | **top_speed** | 3 | TNFS top speed record. Appears to be 24-bit real number (sign unknown because big values show up as N/A in the game), little-endian, where last 8 bits is a fractional part. For determining speed, ONLY INTEGER PART of this number should be multiplied by 2,240000000001 and rounded up, e.g. 0xFF will be equal to 572mph. Note: probably game multiplies number by 2,24 with some fast algorithm so it rounds up even integer result, because 0xFA (*2,24 == 560.0) shows up in game as 561mph | Top speed |
| 35 | **game_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: time_trial<br/>1: head_to_head<br/>2: full_grid_race</details> | Game mode. In the game shown as "t.t.", "h.h." or empty string |
| 36 | **unk3** | 3 | Bytes. Always == b'\x00\x00\x00' | Unknown purpose |
### **ShpiText** ###
#### **Size**: 8..? bytes ####
#### **Description**: An entry, which sometimes can be seen in the SHPI archive block after bitmap, contains some text. The purpose is unclear ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x6f | Resource ID |
| 1 | **unk** | 3 | Bytes | Unknown purpose |
| 4 | **length** | 4 | 4-bytes unsigned integer (little endian) | Text length |
| 8 | **text** | length | UTF-8 string | Text itself |
