# **NFS2SE file specs** #

*Last time updated: 2025-03-15 18:07:19.310391+00:00*


# **Info by file extensions** #

**\*.COL** track additional data. [MapColFile](#mapcolfile)
        
**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.TRK** main track file. [TrkMap](#trkmap)

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
| 16 | **items_descr** | num_items\*8..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | - |
| 16 + num_items\*8..? | **children** | ? | Array of `num_items` items<br/>Item size: ? bytes<br/>Item type: One of types:<br/>- [GeoGeometry](#geogeometry)<br/>- [ShpiBlock](#shpiblock)<br/>- [BigfBlock](#bigfblock)<br/>- Bytes |  |
### **BigfItemDescriptionBlock** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | - |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | - |
| 8 | **name** | ? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | - |
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
| 8 | **pos** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | position of part in 3d space. The unit is meter |
| 20 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 24 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **unk2** | 8 | 8-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 36 | **unk3** | 8 | 8-bytes unsigned integer (little endian). Always == 0x1 | Unknown purpose |
| 44 | **unk4** | 8 | 8-bytes unsigned integer (little endian). Always == 0x1 | Unknown purpose |
| 52 | **vertices** | num_vrtx\*6 | Array of `num_vrtx` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Vertex coordinates. The unit is meter |
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
## **Maps** ##
### **TrkMap** ###
#### **Size**: 32..? bytes ####
#### **Description**: Main track file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "TRAC" | Resource ID |
| 4 | **unk0** | 20 | Bytes | Unknown purpose |
| 24 | **num_superblocks** | 4 | 4-bytes unsigned integer (little endian) | Number of superblocks (nsblk) |
| 28 | **num_blocks** | 4 | 4-bytes unsigned integer (little endian) | Number of blocks (nblk) |
| 32 | **superblock_offsets** | num_superblocks\*4 | Array of `num_superblocks` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offset to each of the superblocks |
| 32 + num_superblocks\*4 | **block_positions** | num_blocks\*12 | Array of `num_blocks` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Positions of blocks in the world |
| 32 + num_superblocks\*4 + num_blocks\*12 | **skip_bytes** | up to offset superblock_offsets[0] | Bytes | Useless padding |
| superblock_offsets[0] | **superblocks** | num_superblocks\*12..? | Array of `num_superblocks` items<br/>Item type: [TrkSuperBlock](#trksuperblock) | Superblocks |
### **TrkSuperBlock** ###
#### **Size**: 12..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Superblock size in bytes |
| 4 | **num_blocks** | 4 | 4-bytes unsigned integer (little endian) | Number of blocks in this superblock. Usually 8 or less in the last superblock |
| 8 | **unk** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **block_offsets** | num_blocks\*4 | Array of `num_blocks` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offset to each of the blocks |
| 12 + num_blocks\*4 | **blocks** | num_blocks\*88..? | Array of `num_blocks` items<br/>Item type: [TrkBlock](#trkblock) | Blocks |
### **TrkBlock** ###
#### **Size**: 88..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes |
| 4 | **block_size_2** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes (duplicated) |
| 8 | **num_extrablocks** | 2 | 2-bytes unsigned integer (little endian) | Number of extrablocks |
| 10 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **block_idx** | 4 | 4-bytes unsigned integer (little endian) | Block index (serial number) |
| 16 | **bounds** | 48 | Array of `4` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Block bounding rectangle |
| 64 | **extrablocks_offset** | 4 | 4-bytes unsigned integer (little endian) | An offset to "extrablock_offsets" block from here |
| 68 | **nv8** | 2 | 2-bytes unsigned integer (little endian) | Number of stick-to-next vertices |
| 70 | **nv4** | 2 | 2-bytes unsigned integer (little endian) | Number of own vertices for 1/4 resolutio |
| 72 | **nv2** | 2 | 2-bytes unsigned integer (little endian) | Number of own vertices for 1/2 resolution |
| 74 | **nv1** | 2 | 2-bytes unsigned integer (little endian) | Number of own vertices for full resolution |
| 76 | **np4** | 2 | 2-bytes unsigned integer (little endian) | Number of polygons for 1/4 resolution |
| 78 | **np2** | 2 | 2-bytes unsigned integer (little endian) | Number of polygons for 1/2 resolution |
| 80 | **np1** | 2 | 2-bytes unsigned integer (little endian) | Number of polygons for full resolution |
| 82 | **unk1** | 6 | 6-bytes unsigned integer (little endian) | Unknown purpose |
| 88 | **vertices** | (nv8+nv1)\*6 | Array of `nv8+nv1` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Vertices |
| 88 + (nv8+nv1)\*6 | **polygons** | (np4+np2+np1)\*8 | Array of `np4+np2+np1` items<br/>Item type: [ColPolygon](#colpolygon) | Polygons |
| 88 + (nv8+nv1)\*6 + (np4+np2+np1)\*8 | **unk2** | up to (extrablocks_offset+64) | Bytes | Unknown purpose |
| extrablocks_offset + 64 | **extrablock_offsets** | num_extrablocks\*4 | Array of `num_extrablocks` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offset to each of the extrablocks |
| extrablocks_offset + 64 + num_extrablocks\*4 | **extrablocks** | ? | Array of `num_extrablocks` items<br/>Item type: [ColExtraBlock](#colextrablock) | Extrablocks |
### **MapColFile** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "COLL" | Resource ID |
| 4 | **unk** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb | Unknown purpose |
| 8 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | File size in bytes |
| 12 | **num_extrablocks** | 4 | 4-bytes unsigned integer (little endian) | Number of extrablocks |
| 16 | **extrablock_offsets** | num_extrablocks\*4 | Array of `num_extrablocks` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offset to each of the extrablocks |
| 16 + num_extrablocks\*4 | **extrablocks** | ? | Array of `num_extrablocks` items<br/>Item type: [ColExtraBlock](#colextrablock) | Extrablocks |
### **ColExtraBlock** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes |
| 4 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>2: textures_map<br/>4: block_numbers<br/>5: polygon_map<br/>6: median_polygons<br/>7: props_7<br/>8: prop_descriptions<br/>9: lanes<br/>13: road_vectors<br/>15: collision_data<br/>18: props_18<br/>19: props_19</details> | Type of the data records |
| 5 | **unk** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 6 | **num_data_records** | 2 | 2-bytes unsigned integer (little endian) | Amount of data records |
| 8 | **data_records** | ? | Type according to enum `type`:<br/>- Array of `num_data_records` items<br/>Item type: [TexturesMapExtraDataRecord](#texturesmapextradatarecord)<br/>- Array of `num_data_records` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `num_data_records` items<br/>Item type: [PolygonMapExtraDataRecord](#polygonmapextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [MedianExtraDataRecord](#medianextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropDescriptionExtraDataRecord](#propdescriptionextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [LanesExtraDataRecord](#lanesextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [RoadVectorsExtraDataRecord](#roadvectorsextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [CollisionExtraDataRecord](#collisionextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Bytes | Data records |
### **TexturesMapExtraDataRecord** ###
#### **Size**: 10 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **texture_number** | 2 | 2-bytes unsigned integer (little endian) | Texture number in QFS file |
| 2 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 3 | **alignment** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1: rotate_180<br/>3: rotate_270<br/>5: normal<br/>9: rotate_90<br/>16: flip_v<br/>18: rotate_270_2<br/>20: flip_h<br/>24: rotate_90_2</details> | Alignment data, which game uses instead of UV-s when rendering mesh.I use UV-s (0,1; 1,1; 1,0; 0,0) and modify them according to enum value names |
| 4 | **luminosity** | 3 | Color RGB values | Luminosity color |
| 7 | **black** | 3 | Color RGB values | Unknown, usually black |
### **PolygonMapExtraDataRecord** ###
#### **Size**: 2 bytes ####
#### **Description**: Polygon extra data. Number of items here == np1 * 2, but sometimes less. Why? ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vectors_idx** | 1 | 1-byte unsigned integer | An index of entry in road_vectors extrablock |
| 1 | **car_behavior** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0: unk0<br/>1: unk1</details> | - |
### **MedianExtraDataRecord** ###
#### **Size**: 8 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_idx** | 1 | 1-byte unsigned integer | Polygon index |
| 1 | **unk** | 7 | Bytes | Unknown purpose |
### **AnimatedPropPosition** ###
#### **Size**: 4..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **num_frames** | 2 | 2-bytes unsigned integer (little endian) | An amount of frames |
| 2 | **unk** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **frames** | num_frames\*20 | Array of `num_frames` items<br/>Item type: [AnimatedPropPositionFrame](#animatedproppositionframe) | Animation frames |
### **AnimatedPropPositionFrame** ###
#### **Size**: 20 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Object position in 3D space |
| 12 | **unk0** | 8 | Bytes | Unknown purpose |
### **PropExtraDataRecord** ###
#### **Size**: 4..? bytes ####
#### **Description**: 3D model placement (prop). Same 3D model can be used few times on the track ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 2 | 2-bytes unsigned integer (little endian) | Block size in bytes |
| 2 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1: static_prop<br/>3: animated_prop</details> | Object type |
| 3 | **prop_descr_idx** | 1 | 1-byte unsigned integer | An index of 3D model in "prop_descriptions" extrablock |
| 4 | **position** | ? | Type according to enum `type`:<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part<br/>- [AnimatedPropPosition](#animatedpropposition)<br/>- Bytes | Object positioning in 3D space |
### **PropDescriptionExtraDataRecord** ###
#### **Size**: 8..? bytes ####
#### **Description**: 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes |
| 4 | **num_vertices** | 2 | 2-bytes unsigned integer (little endian) | Amount of vertices |
| 6 | **num_polygons** | 2 | 2-bytes unsigned integer (little endian) | Amount of polygons |
| 8 | **vertices** | num_vertices\*6 | Array of `num_vertices` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Vertices |
| 8 + num_vertices\*6 | **polygons** | num_polygons\*8 | Array of `num_polygons` items<br/>Item type: [ColPolygon](#colpolygon) | Polygons |
| 8 + num_vertices\*6 + num_polygons\*8 | **padding** | custom_func | Bytes | Unused space |
### **LanesExtraDataRecord** ###
#### **Size**: 4 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vertex_idx** | 1 | 1-byte unsigned integer | Vertex number (inside background 3D structure : 0 to nv1+nv8) |
| 1 | **track_pos** | 1 | 1-byte unsigned integer | Position along track inside block (0 to 7) |
| 2 | **lat_pos** | 1 | 1-byte unsigned integer | Lateral position ? (constant in each lane), -1 at the end) |
| 3 | **polygon_idx** | 1 | 1-byte unsigned integer | Polygon number (inside full-res background 3D structure : 0 to np1) |
### **RoadVectorsExtraDataRecord** ###
#### **Size**: 12 bytes ####
#### **Description**: Block with normal + forward vectors pair ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part, normalized | - |
| 6 | **forward** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part, normalized | - |
### **CollisionExtraDataRecord** ###
#### **Size**: 36 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | A global position of track collision spline point. The unit is meter |
| 12 | **normal** | 3 | Point in 3D space (x,y,z), where each coordinate is: 8-bit real number (little-endian, signed), where last 7 bits is a fractional part, normalized | A normal vector of road surface |
| 15 | **forward** | 3 | Point in 3D space (x,y,z), where each coordinate is: 8-bit real number (little-endian, signed), where last 7 bits is a fractional part, normalized | A forward vector |
| 18 | **right** | 3 | Point in 3D space (x,y,z), where each coordinate is: 8-bit real number (little-endian, signed), where last 7 bits is a fractional part, normalized | A right vector |
| 21 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 22 | **block_idx** | 2 | 2-bytes unsigned integer (little endian) | - |
| 24 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 26 | **left_border** | 2 | 16-bit real number (little-endian, not signed), where last 8 bits is a fractional part | Distance to left track border in meters |
| 28 | **right_border** | 2 | 16-bit real number (little-endian, not signed), where last 8 bits is a fractional part | Distance to right track border in meters |
| 30 | **respawn_lat_pos** | 2 | 2-bytes unsigned integer (little endian) | - |
| 32 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **ColPolygon** ###
#### **Size**: 8 bytes ####
#### **Description**: A single polygon of terrain or prop ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **texture** | 2 | 2-bytes unsigned integer (little endian) | Texture number. It is not a number of texture in QFS file. Instead, it is an index of mapping entry in corresponding COL file, which contains real texture number |
| 2 | **texture2** | 2 | 2-bytes signed integer (little endian) | 255 (texture number for the other side == none ?) |
| 4 | **vertices** | 4 | Array of `4` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Polygon vertices (indexes from vertex table) |
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
