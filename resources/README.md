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
- [WwwwBlock](#wwwwblock) contains a series of consecutive [OripGeometry](#oripgeometry) + [ShpiBlock](#shpiblock) items, 3D props

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.PBS** car physics. [CarPerformanceSpec](#carperformancespec), **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.PDN** car characteristic for unknown purpose. [CarSimplifiedPerformanceSpec](#carsimplifiedperformancespec), **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.TGV** video, I just use ffmpeg to convert it

**\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. [TriMap](#trimap)


# **Block specs** #
## **Archives** ##
### **ShpiBlock** ###
#### **Size**: 16..? bytes ####
#### **Description**: A container of images and palettes for them ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == SHPI | Resource ID |
| 4 | **length** | 4 | 4-bytes unsigned integer (little endian) | The length of this SHPI block in bytes |
| 8 | **children_count** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 12 | **shpi_directory** | 4 | UTF-8 string | One of: "LN32", "GIMX", "WRAP". The purpose is unknown |
| 16 | **children_descriptions** | 8 * (children_count) | Array of children_count items<br/>Item size: 8 bytes<br/>Item type: 8-bytes record, first 4 bytes is a UTF-8 string, last 4 bytes is an unsigned integer (little-endian) | An array of items, each of them represents name of SHPI item (image or palette) and offset to item data in file, relatively to SHPI block start (where resource id string is presented) |
| 16..? | **children** | ? | Array of children_count items with custom offset to items<br/>Item size: 16..? bytes<br/>Item type: One of types:<br/>- [Bitmap16Bit0565](#bitmap16bit0565)<br/>- [Bitmap4Bit](#bitmap4bit)<br/>- [Bitmap8Bit](#bitmap8bit)<br/>- [Bitmap32Bit](#bitmap32bit)<br/>- [Bitmap16Bit1555](#bitmap16bit1555)<br/>- [Bitmap24Bit](#bitmap24bit)<br/>- [Palette24BitDos](#palette24bitdos)<br/>- [Palette24Bit](#palette24bit)<br/>- [Palette32Bit](#palette32bit)<br/>- [Palette16Bit](#palette16bit) | A part of block, where items data is located. Offsets are defined in previous block, lengths are calculated: either up to next item offset, or up to the end of block |
### **WwwwBlock** ###
#### **Size**: 8..? bytes ####
#### **Description**: A block-container with various data: image archives, geometries, other wwww blocks. If has ORIP 3D model, next item is always SHPI block with textures to this 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == wwww | Resource ID |
| 4 | **children_count** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 8 | **children_offsets** | 4 * (?) | Array of ? items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file, relatively to wwww block start (where resource id string is presented) |
| 8..? | **children** | ? | Array of children_count items with custom offset to items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [OripGeometry](#oripgeometry)<br/>- [ShpiBlock](#shpiblock)<br/>- [WwwwBlock](#wwwwblock) | A part of block, where items data is located. Offsets are defined in previous block, lengths are calculated: either up to next item offset, or up to the end of block |
### **SoundBank** ###
#### **Size**: 512..? bytes ####
#### **Description**: A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **children_offsets** | 4 * (128) | Array of 128 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file. Zero values seem to be ignored, but for some reason the very first offset is 0 in most files. The real audio data start is shifted 40 bytes forward for some reason, so EACS is located at {offset from this array} + 40 |
| 512 | **children** | ? | Array of ? items with custom offset to items<br/>Item type: [EacsAudio](#eacsaudio) | EACS blocks are here, placed at offsets from previous block. Those EACS blocks don't have own wave data, there are 44 bytes of unknown data instead, offsets in them are pointed to wave data of this block |
| 512..? | **wave_data** | ? | Array of ? items with custom offset to items<br/>Item size: 0..? bytes<br/>Item type:  | A space, where wave data is located. Pointers are in children EACS |
## **Geometries** ##
### **OripGeometry** ###
#### **Size**: 112..? bytes ####
#### **Description**: Geometry block for 3D model with few materials. The structure is fuzzy and hard to understand ¯\\_(ツ)_/¯. Offsets here can drift, data is not properly aligned, so it has explicitly defined offsets to some blocks ####
<details>
<summary>Click to see block specs (31 fields)</summary>

| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == ORIP | Resource ID |
| 4 | **unknowns0** | 12 | Array of 12 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **vertex_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices |
| 20 | **unknowns1** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 24 | **vertex_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertex_block |
| 28 | **vertex_uvs_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex UV-s (texture coordinates) |
| 32 | **vertex_uvs_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertex_uvs_block |
| 36 | **polygon_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of polygons |
| 40 | **polygon_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to polygons block |
| 44 | **identifier** | 12 | UTF-8 string | Some ID of geometry, don't know the purpose |
| 56 | **texture_names_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture names |
| 60 | **texture_names_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture names block |
| 64 | **texture_number_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture numbers |
| 68 | **texture_number_block_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture numbers block |
| 72 | **unk0_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in unk0 block |
| 76 | **unk0_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of unk0 block |
| 80 | **polygon_vertex_map_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of polygon_vertex_map block |
| 84 | **unk1_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in unk1 block |
| 88 | **unk1_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of unk1 block |
| 92 | **labels_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in labels block |
| 96 | **labels_block_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of labels block |
| 100 | **unknowns2** | 12 | Array of 12 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 112 | **polygons_block** | 12 * (polygon_count) | Array of polygon_count items<br/>Item type: [OripPolygon](#orippolygon) | A block with polygons of the geometry. Probably should be a start point when building model from this file |
| 112..? | **vertex_uvs_block** | 8 * (vertex_uvs_count) | Array of vertex_uvs_count items<br/>Item size: 8 bytes<br/>Item type: Texture coordinates for vertex, where each coordinate is: 4-bytes unsigned integer (little endian). The unit is a pixels amount of assigned texture. So it should be changed when selecting texture with different size | A table of texture coordinates. Items are retrieved by index, located in polygon_vertex_map_block |
| 112..? | **texture_names_block** | 20 * (texture_names_count) | Array of texture_names_count items<br/>Item type: [OripTextureName](#oriptexturename) | A table of texture references. Items are retrieved by index, located in polygon item |
| 112..? | **texture_number_map_block** | 20 * (texture_number_count) | Array of texture_number_count items<br/>Item size: 20 bytes<br/>Item type: Array of 20 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 112..? | **unk0_block** | 28 * (unk0_count) | Array of unk0_count items<br/>Item size: 28 bytes<br/>Item type: Array of 28 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 112..? | **unk1_block** | 12 * (unk1_count) | Array of unk1_count items<br/>Item size: 12 bytes<br/>Item type: Array of 12 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 112..? | **labels_block** | 12 * (labels_count) | Array of labels_count items<br/>Item size: 12 bytes<br/>Item type: Array of 12 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 112..? | **vertex_block** | 12 * (vertex_count) | Array of vertex_count items<br/>Item size: 12 bytes<br/>Item type: One of types:<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 7 bits is a fractional part. The unit is meter<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 4 bits is a fractional part. The unit is meter | A table of mesh vertices in 3D space. For cars it consists of 32:7 points, else 32:4 |
| 112..? | **polygon_vertex_map_block** | 4 * ((up to end of block)) | Array of (up to end of block) items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | A LUT for both 3D and 2D vertices. Every item is an index of either item in vertex_block or vertex_uvs_block. When building 3D vertex, polygon defines offset_3d, a lookup to this table, and value from here is an index of item in vertex_block. When building UV-s, polygon defines offset_2d, a lookup to this table, and value from here is an index of item in vertex_uvs_block |
</details>

### **OripPolygon** ###
#### **Size**: 12 bytes ####
#### **Description**: A geometry polygon ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_type** | 1 | 1-byte unsigned integer | Huh, that's a srange field. From my tests, if it is xxx0_0011, the polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only one polygon for entire TNFS with type == 2 in burnt sienna props. If ignore this polygon everything still looks great |
| 1 | **normal** | 1 | 1-byte unsigned integer | Strange field #2: no clue what it supposed to mean, TNFS doesnt have any shading so I don't believe they made a normal map back then. I assume that: values 17, 19 mean two-sided polygon; 18, 2, 3, 48, 50, 10, 6 - default polygon in order (0-1-2); 0, 1, 16 - back-faced polygon (order is 0-2-1) |
| 2 | **texture_index** | 1 | 1-byte unsigned integer | The index of item in ORIP's texture_names block |
| 3 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **offset_3d** | 4 | 4-bytes unsigned integer (little endian) | The index in polygon_vertex_map_block ORIP's table. This index represents first vertex of this polygon, so in order to determine all vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. Look at polygon_vertex_map_block description for more info |
| 8 | **offset_2d** | 4 | 4-bytes unsigned integer (little endian) | The same as offset_3d, also points to polygon_vertex_map_block, but used for texture coordinates. Look at polygon_vertex_map_block description for more info |
### **OripTextureName** ###
#### **Size**: 20 bytes ####
#### **Description**: A settings of the texture. From what is known, contains name of bitmap ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Sometimes UTF8 string, but not always. Unknown purpose |
| 4 | **unknown0** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 8 | **file_name** | 4 | UTF-8 string | Name of bitmap in SHPI block |
| 12 | **unknown1** | 8 | Array of 8 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
## **Maps** ##
### **TriMap** ###
#### **Size**: 90664..? bytes ####
#### **Description**: Map TRI file, represents terrain mesh, road itself, proxy object locations etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x11 | Resource ID |
| 4 | **unknowns0** | 8 | Array of 8 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part. The unit is meter | Unknown purpose |
| 24 | **unknowns1** | 12 | Array of 12 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 36 | **scenery_data_length** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 40 | **unknowns2** | 2404 | Array of 2404 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 2444 | **road_spline** | 36 * (2400) | Array of 2400 items<br/>Item type: [RoadSplinePoint](#roadsplinepoint) | Road spline is a series of points in 3D space, located at the center of road. Around this spline the track terrain mesh is built. TRI always has 2400 elements, however it uses some amount of vertices, after them records filled with zeros |
| 88844 | **unknowns3** | 1800 | Array of 1800 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 90644 | **proxy_objects_count** | 4 | 4-bytes unsigned integer (little endian) | - |
| 90648 | **proxy_object_instances_count** | 4 | 4-bytes unsigned integer (little endian) | - |
| 90652 | **object_header_text** | 4 | UTF-8 string. Always == SJBO | - |
| 90656 | **unknowns4** | 8 | Array of 8 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 90664 | **proxy_objects** | 16 * (proxy_objects_count) | Array of proxy_objects_count items<br/>Item type: [ProxyObject](#proxyobject) | - |
| 90664..? | **proxy_object_instances** | 16 * (proxy_object_instances_count) | Array of proxy_object_instances_count items<br/>Item type: [ProxyObjectInstance](#proxyobjectinstance) | - |
| 90664..? | **terrain** | 288 * (spline_points_amount / 4) | Array of spline_points_amount / 4 items<br/>Item type: [TerrainEntry](#terrainentry) | - |
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
| 7 | **spline_item_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: lane_split<br/>1: default<br/>2: lane_merge<br/>4: tunnel<br/>5: cobbled_road<br/>7: right_tunnel_A2_A9<br/>12: left_tunnel_A9_A4<br/>13: left_tunnel_A9_A5<br/>14: waterfall_audio_left_channel<br/>15: waterfall_audio_right_channel<br/>18: water_audio</details> | Modifier of this point. Affects terrain geometry and/or some gameplay features |
| 8 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part. The unit is meter | Coordinates of this point in 3D space |
| 20 | **slope** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Slope of the road at this point (angle if road goes up or down) |
| 22 | **slant_a** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Perpendicular angle of road |
| 24 | **orientation** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Rotation of road path, if view from the top |
| 26 | **unknowns1** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 28 | **orientation_y** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Not quite sure about it. Denis Auroux gives more info about this http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt |
| 30 | **slant_b** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Not quite sure about it. Denis Auroux gives more info about this http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt |
| 32 | **orientation_x** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Not quite sure about it. Denis Auroux gives more info about this http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt |
| 34 | **unknowns2** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
### **ProxyObject** ###
#### **Size**: 16 bytes ####
#### **Description**: The description of map proxy object: everything except terrain (road signs, buildings etc.) Thanks to jeff-1amstudios and his OpenNFS1 project: https://github.com/jeff-1amstudios/OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202 ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **flags** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>2: is_animated</details> | Different modes of proxy object |
| 1 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1: model<br/>4: bitmap<br/>6: two_sided_bitmap</details> | Type of proxy object |
| 2 | **resource_id** | 1 | 1-byte unsigned integer | Texture/model id. For 3D prop is an index of prop in the track FAM file, for 2D represents texture id. How to get texture name from this value explained well by Denis Auroux http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt |
| 3 | **resource_2_id** | 1 | 1-byte unsigned integer | Texture id of second sprite, rotated 90 degrees, in two-sided bitmap. Logic to determine texture name is the same as for resource_id. Applicable for 2D prop with type two_sided_bitmap |
| 4 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 8 | **frame_count** | 1 | 1-byte unsigned integer | Frame amount for animated object |
| 9 | **unknowns0** | 3 | Array of 3 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown, animation speed should be somewhere in it |
| 12 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters, applicable for 2D props |
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
#### **Description**: The terrain model around 4 spline points. It has good explanation in original Aurox NFS file specs: http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **id** | 4 | UTF-8 string. Always == TRKD | - |
| 4 | **block_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **block_number** | 4 | 4-bytes unsigned integer (little endian) | - |
| 12 | **unknown** | 1 | 1-byte unsigned integer | Unknown purpose |
| 13 | **fence** | 1 | TNFS fence type field. fence type: [lrtttttt]<br/>l - flag is add left fence<br/>r - flag is add right fence<br/>tttttt - texture id | - |
| 14 | **texture_ids** | 10 | Array of 10 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Texture ids to be used for terrain |
| 24 | **rows** | 66 * (4) | Array of 4 items<br/>Item size: 66 bytes<br/>Item type: Array of 11 items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 7 bits is a fractional part. The unit is meter | Terrain vertex positions |
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
| 28 | **brake_bias** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | how much car rotates when brake? |
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
| 884 | **grip_curve_front** | 512 | Array of 512 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 1396 | **grip_curve_rear** | 512 | Array of 512 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
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
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 2 * (width * height) | Array of width * height items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 2\*width\*height) | Array of block_size - (16 + 2\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap4Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Single-channel image, 4 bits per pixel. Used in FFN font files and some NFS2SE SHPI directories as some small sprites, like "dot". Seems to be always used as alpha channel, so we save it as white image with alpha mask ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7a | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 0..? | Array of width * height sub-byte numbers. Each number consists of 4 bits | Font atlas bitmap data |
### **Bitmap8Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: 8bit bitmap can be serialized to image only with palette. Basically, for every pixel it uses 8-bit index of color in assigned palette. The tricky part is to determine how the game understands which palette to use. In most cases, if bitmap has embedded palette, it should be used, EXCEPT Autumn Valley fence texture: there embedded palette should be ignored. In all other cases it is tricky even more: it uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, palette can be in a different SHPI before this one. In CONTROL directory most of QFS files use !pal even from different QFS file! It is a mystery how to reliably pick palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7b | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width * height | Array of width * height items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Color indexes of bitmap pixels. The actual colors are in assigned to this bitmap palette |
| 16..? | **trailing_bytes** | block_size - (16 + width\*height) | Array of block_size - (16 + width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
| 16..? | **palette** (optional) | 8..1040 | One of types:<br/>- [PaletteReference](#palettereference)<br/>- [Palette24BitDos](#palette24bitdos)<br/>- [Palette24Bit](#palette24bit)<br/>- [Palette32Bit](#palette32bit)<br/>- [Palette16Bit](#palette16bit) | Palette, assigned to this bitmap or reference to external palette?. The exact mechanism of choosing the correct palette (except embedded one) is unknown |
### **Bitmap32Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7d | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 4 * (width * height) | Array of width * height items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 4\*width\*height) | Array of block_size - (16 + 4\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap16Bit1555** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7e | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 2 * (width * height) | Array of width * height items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 1555 color, arrrrrgg_gggbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 2\*width\*height) | Array of block_size - (16 + 2\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap24Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7f | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 3 * (width * height) | Array of width * height items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (little-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 3\*width\*height) | Array of block_size - (16 + 3\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
## **Fonts** ##
### **FfnFont** ###
#### **Size**: 48..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == FNTF | Resource ID |
| 4 | **file_size** | 4 | 4-bytes unsigned integer (little endian) | This file size in bytes |
| 8 | **unknowns0** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 10 | **symbols_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of symbols, defined in this font |
| 12 | **unknowns1** | 16 | Array of 16 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 28 | **bitmap_data_pointer** | 2 | 2-bytes unsigned integer (little endian) | Pointer to bitmap block |
| 30 | **unknowns2** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 32 | **definitions** | 11 * (symbols_amount) | Array of symbols_amount items<br/>Item type: [SymbolDefinitionRecord](#symboldefinitionrecord) | Definitions of chars in this bitmap font |
| 32..? | **skip_bytes** | up to offset bitmap_data_pointer | Array of up to offset bitmap_data_pointer items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer. Always == 0xad | 4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36) |
| 32..? | **bitmap** | 16..? | [Bitmap4Bit](#bitmap4bit) | Font atlas bitmap data |
### **SymbolDefinitionRecord** ###
#### **Size**: 11 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **code** | 2 | 2-bytes unsigned integer (little endian) | Code of symbol |
| 2 | **glyph_width** | 1 | 1-byte unsigned integer | Width of symbol in font bitmap |
| 3 | **glyph_height** | 1 | 1-byte unsigned integer | Height of symbol in font bitmap |
| 4 | **glyph_x** | 2 | 2-bytes unsigned integer (little endian) | Position (x) of symbol in font bitmap |
| 6 | **glyph_y** | 2 | 2-bytes unsigned integer (little endian) | Position (Y) of symbol in font bitmap |
| 8 | **x_advance** | 1 | 1-byte unsigned integer | Gap between this symbol and next one in rendered text |
| 9 | **x_offset** | 1 | 1-byte signed integer | Offset (x) for drawing the character image |
| 10 | **y_offset** | 1 | 1-byte signed integer | Offset (y) for drawing the character image |
## **Palettes** ##
### **PaletteReference** ###
#### **Size**: 8 bytes ####
#### **Description**: Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. Probably a reference to palette which should be used, that's why named so ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7c | Resource ID |
| 1 | **unknowns** | 7 | Array of 7 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
### **Palette24BitDos** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x22 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 3 * (0..256) | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
### **Palette24Bit** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x24 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 3 * (0..256) | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (big-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..1040 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2a | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 4 * (0..256) | Array of 0..256 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette16Bit** ###
#### **Size**: 16..528 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2d | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 2 * (0..256) | Array of 0..256 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors LUT |
## **Audio** ##
### **AsfAudio** ###
#### **Size**: 36..? bytes ####
#### **Description**: An audio file, which is supported by FFMPEG and can be converted using only it ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == 1SNh | Resource ID |
| 4 | **unknowns** | 8 | Array of 8 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | - |
| 16 | **sound_resolution** | 1 | 1-byte unsigned integer | - |
| 17 | **channels** | 1 | 1-byte unsigned integer | - |
| 18 | **compression** | 1 | 1-byte unsigned integer | - |
| 19 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 20 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 24 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | - |
| 28 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 32 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | - |
| 36 | **wave_data** | 0..? |  | - |