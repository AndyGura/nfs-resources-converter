# **NFS 3 Hot Pursuit file specs** #

*Last time updated: 2026-07-01 22:07:03.102619+00:00*


# **Info by file extensions** #

**\*.COL** track additional data. [MapColFile](#mapcolfile)
        
**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FRD** main track file. [FrdMap](#frdmap)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), [compressed](eac_compressions.md)

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
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44..? | **extraobject_blocks** | (4\*(num_blocks+1))\*4..? | Array of `4*(num_blocks+1)` items<br/>Item size: 4..? bytes<br/>Item type: Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [ExtraObjectBlock](#extraobjectblock) | - |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1))\*4..? | **num_texture_blocks** | 4 | 4-bytes unsigned integer (little endian) | Length of texture_blocks array |
| 36 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1))\*4..? | **texture_blocks** | num_texture_blocks\*47 | Array of `num_texture_blocks` items<br/>Item type: [TextureBlock](#textureblock) | - |
### **FrdBlock** ###
#### **Size**: 1316..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position of the block in the world |
| 12 | **bounds** | 48 | Array of `4` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Block bounding rectangle |
| 60 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Number of vertices |
| 64 | **num_vertices_high** | 4 | 4-bytes unsigned integer (little endian) | Number of high-res vertices |
| 68 | **num_vertices_low** | 4 | 4-bytes unsigned integer (little endian) | Number of low-res vertices |
| 72 | **num_vertices_med** | 4 | 4-bytes unsigned integer (little endian) | Number of medium-res vertices |
| 76 | **num_vertices_dup** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 80 | **num_vertices_obj** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertices. Coordinates are global |
| 84 + num_vertices\*12 | **vertex_shading** | num_vertices\*4 | Array of `num_vertices` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 84 + num_vertices\*12 + num_vertices\*4 | **neighbour_data** | 1200 | Array of `600` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Unknown purpose |
| 1284 + num_vertices\*12 + num_vertices\*4 | **num_start_pos** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1288 + num_vertices\*12 + num_vertices\*4 | **num_positions** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1292 + num_vertices\*12 + num_vertices\*4 | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1296 + num_vertices\*12 + num_vertices\*4 | **num_vroad** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1300 + num_vertices\*12 + num_vertices\*4 | **num_xobj** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1304 + num_vertices\*12 + num_vertices\*4 | **num_polyobj** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1308 + num_vertices\*12 + num_vertices\*4 | **num_soundsrc** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1312 + num_vertices\*12 + num_vertices\*4 | **num_lightsrc** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 | **positions** | num_positions\*8 | Array of `num_positions` items<br/>Item type: [FrdPositionBlock](#frdpositionblock) | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 | **polygons** | num_polygons\*8 | Array of `num_polygons` items<br/>Item type: [FrdBlockPolygonData](#frdblockpolygondata) | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 | **vroad** | num_vroad\*12 | Array of `num_vroad` items<br/>Item type: [FrdBlockVroadData](#frdblockvroaddata) | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 | **xobj** | num_xobj\*20 | Array of `num_xobj` items<br/>Item size: 20 bytes<br/>Item type: Bytes | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 | **polyobj** | num_polyobj\*20 | Array of `num_polyobj` items<br/>Item size: 20 bytes<br/>Item type: Bytes | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*20 | **soundsrc** | num_soundsrc\*16 | Array of `num_soundsrc` items<br/>Item size: 16 bytes<br/>Item type: Bytes | Unknown purpose |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*20 + num_soundsrc\*16 | **lightsrc** | num_lightsrc\*16 | Array of `num_lightsrc` items<br/>Item size: 16 bytes<br/>Item type: Bytes | Unknown purpose |
### **FrdPositionBlock** ###
#### **Size**: 8 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon** | 2 | 2-bytes unsigned integer (little endian) | - |
| 2 | **num_polygons** | 1 | 1-byte unsigned integer | - |
| 3 | **unk** | 1 | 1-byte unsigned integer | - |
| 4 | **extra_neighbor1** | 2 | 2-bytes unsigned integer (little endian) | - |
| 6 | **extra_neighbor2** | 2 | 2-bytes unsigned integer (little endian) | - |
### **FrdBlockPolygonData** ###
#### **Size**: 8 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vroad_idx** | 1 | 1-byte unsigned integer | - |
| 1 | **flags** | 1 | 1-byte unsigned integer | - |
| 2 | **unk** | 6 | Bytes | Unknown purpose |
### **FrdBlockVroadData** ###
#### **Size**: 12 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 16 bits is a fractional part, normalized | A normal vector of the surface |
| 6 | **forward** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 16 bits is a fractional part, normalized | A forward vector of the surface |
### **FrdPolyBlock** ###
#### **Size**: 44..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygons** | 28..? | Array of `7` items<br/>Item type: [FrdPolygonsBlock](#frdpolygonsblock) | - |
| 28..? | **polyobj** | 16..? | Array of `4` items<br/>Item type: [FrdPolyObjBlock](#frdpolyobjblock) | - |
### **FrdPolygonsBlock** ###
#### **Size**: 4..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **sz** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **data** | ? | One of types:<br/>- Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [FrdPolygonRecord](#frdpolygonrecord)<br/>- Bytes | This data is presented only if sz != 0 |
### **FrdPolygonRecord** ###
#### **Size**: 14 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vertices** | 8 | Array of `4` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | - |
| 8 | **tex_id** | 2 | 2-bytes unsigned integer (little endian) | - |
| 10 | **tex_flags** | 2 | 2-bytes unsigned integer (little endian) | - |
| 12 | **flags** | 1 | 1-byte unsigned integer | - |
| 13 | **unk** | 1 | 1-byte unsigned integer | - |
### **FrdPolyObjBlock** ###
#### **Size**: 4..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **sz** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **data** | ? | One of types:<br/>- Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [FrdPolyObjPolygonsBlock](#frdpolyobjpolygonsblock)<br/>- Bytes | This data is presented only if sz > 0 |
### **FrdPolyObjPolygonsBlock** ###
#### **Size**: 4..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **data** | ? | One of types:<br/>- Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [FrdPolygonRecord](#frdpolygonrecord)<br/>- Bytes | This data is presented only if type == 1 |
### **ExtraObjectBlock** ###
#### **Size**: 36..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **cross_type** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **cross_no** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **data** | 16..? | One of types:<br/>- [ExtraObjectDataCrossType4](#extraobjectdatacrosstype4)<br/>- [ExtraObjectDataCrossType1](#extraobjectdatacrosstype1) | - |
| 28..? | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | - |
| 32..? | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | - |
| 32 + num_vertices\*12..? | **vertex_shading** | num_vertices\*4 | Array of `num_vertices` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | - |
| 32 + num_vertices\*12 + num_vertices\*4..? | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Length of polygons array |
| 36 + num_vertices\*12 + num_vertices\*4..? | **polygons** | num_polygons\*14 | Array of `num_polygons` items<br/>Item type: [FrdPolygonRecord](#frdpolygonrecord) | - |
### **ExtraObjectDataCrossType1** ###
#### **Size**: 24..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk** | 18 | Bytes | - |
| 18 | **type** | 1 | 1-byte unsigned integer. Always == 0x3 | - |
| 19 | **objno** | 1 | 1-byte unsigned integer | - |
| 20 | **num_animdata** | 2 | 2-bytes unsigned integer (little endian) | - |
| 22 | **anim_delay** | 2 | 2-bytes unsigned integer (little endian) | - |
| 24 | **animdata** | num_animdata\*20 | Array of `num_animdata` items<br/>Item type: [AnimData](#animdata) | - |
### **AnimData** ###
#### **Size**: 20 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **pt** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | - |
| 12 | **od** | 8 | Array of `4` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | - |
### **ExtraObjectDataCrossType4** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **pt_ref** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | - |
| 12 | **anim_memory** | 4 | 4-bytes unsigned integer (little endian) | - |
### **TextureBlock** ###
#### **Size**: 47 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **width** | 2 | 2-bytes unsigned integer (little endian) | Texture width |
| 2 | **height** | 2 | 2-bytes unsigned integer (little endian) | Texture height |
| 4 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Blending related, hometown covered bridges godrays |
| 8 | **corners** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | 4x planar coordinates == tiling? |
| 40 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 44 | **is_lane** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): default<br/>1 (0x1): lane</details> | 1 if not a real texture (lane), 0 usually |
| 45 | **texture_id** | 2 | 2-bytes unsigned integer (little endian) | index in QFS file |
### **MapColFile** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "COLL" | Resource ID |
| 4 | **unk** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb | Unknown purpose |
| 8 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | File size in bytes |
| 12 | **num_extrablocks** | 4 | 4-bytes unsigned integer (little endian) | Number of extrablocks |
| 16 | **extrablock_offsets** | num_extrablocks\*4 | Array of `num_extrablocks` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offset to each of the extrablocks |
| 16 + num_extrablocks\*4 | **extrablocks_bytes** | block_size-16-4\*num_extrablocks | Bytes | A part of block, where extra blocks data is located. Offsets are defined in previous "extrablock_offsets" field. Item type:<br/>- [ColExtraBlock](#colextrablock) |
### **ColExtraBlock** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes |
| 4 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>2 (0x2): textures_map<br/>4 (0x4): block_numbers<br/>5 (0x5): polygon_map<br/>6 (0x6): median_polygons<br/>7 (0x7): props_7<br/>8 (0x8): prop_descriptions<br/>9 (0x9): lanes<br/>13 (0xd): road_vectors<br/>15 (0xf): collision_data<br/>18 (0x12): props_18<br/>19 (0x13): props_19</details> | Type of the data records |
| 5 | **unk** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 6 | **num_data_records** | 2 | 2-bytes unsigned integer (little endian) | Amount of data records |
| 8 | **data_records** | ? | Type according to enum `type`:<br/>- Array of `num_data_records` items<br/>Item type: [TexturesMapExtraDataRecord](#texturesmapextradatarecord)<br/>- Array of `num_data_records` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `num_data_records` items<br/>Item type: [PolygonMapExtraDataRecord](#polygonmapextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [MedianExtraDataRecord](#medianextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropDescriptionExtraDataRecord](#propdescriptionextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [LanesExtraDataRecord](#lanesextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [RoadVectorsExtraDataRecord](#roadvectorsextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [CollisionExtraDataRecord](#collisionextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Bytes | Data records |
### **TexturesMapExtraDataRecord** ###
#### **Size**: 10 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **texture_number** | 2 | 2-bytes unsigned integer (little endian) | Texture number in QFS file |
| 2 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 3 | **alignment** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1 (0x1): rotate_180<br/>3 (0x3): rotate_270<br/>5 (0x5): normal<br/>9 (0x9): rotate_90<br/>16 (0x10): flip_v<br/>18 (0x12): rotate_270_2<br/>20 (0x14): flip_h<br/>24 (0x18): rotate_90_2</details> | Alignment data, which game uses instead of UV-s when rendering mesh.I use UV-s (0,1; 1,1; 1,0; 0,0) and modify them according to enum value names |
| 4 | **luminosity** | 3 | Color RGB values | Luminosity color |
| 7 | **black** | 3 | Color RGB values | Unknown, usually black |
### **PolygonMapExtraDataRecord** ###
#### **Size**: 2 bytes ####
#### **Description**: Polygon extra data. Number of items here == np1 * 2, but sometimes less. Why? ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vectors_idx** | 1 | 1-byte unsigned integer | An index of entry in road_vectors extrablock |
| 1 | **car_behavior** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): unk0<br/>1 (0x1): unk1</details> | - |
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
| 2 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1 (0x1): static_prop<br/>3 (0x3): animated_prop</details> | Object type |
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
| 8 + num_vertices\*6 + num_polygons\*8 | **padding** | block_size-local_offset | Bytes | Unused space |
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
## **Images** ##
### **EacImage** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>64 (0x40): 4Bit PS1<br/>109 (0x6d): 16Bit_4444 color format bitmap<br/>120 (0x78): 16Bit_0565 color format bitmap<br/>121 (0x79): 4Bit (swapped)<br/>122 (0x7a): 4Bit<br/>123 (0x7b): 8Bit<br/>125 (0x7d): 32Bit color format bitmap<br/>126 (0x7e): 16Bit_1555 color format bitmap<br/>127 (0x7f): 24Bit color format bitmap</details> | Resource ID |
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
| 12 | **flags** | 4 | Sub-byte compound block (little endian):<br/>13-bits int "pad"<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: 12-bytes<br/>&nbsp;&nbsp;- 1: 16-bytes<br/>2-bits enum:<br/>&nbsp;&nbsp;- 0: ASCII<br/>&nbsp;&nbsp;- 1: Unicode<br/>&nbsp;&nbsp;- 2: Shift-JIS<br/>&nbsp;&nbsp;- 3: Reserved<br/>4-bits int "layoutpad"<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: LTR<br/>&nbsp;&nbsp;- 1: RTL<br/>1-bits enum:<br/>&nbsp;&nbsp;- 0: Horizontal<br/>&nbsp;&nbsp;- 1: Vertical<br/>2-bits enum:<br/>&nbsp;&nbsp;- 0: Roman (english)<br/>&nbsp;&nbsp;- 1: Ideographic (Kanji)<br/>&nbsp;&nbsp;- 2: Hanging (Arabic)<br/>&nbsp;&nbsp;- 3: Unknown<br/>4-bits int "drawpad"<br/>1-bit flag "vram"<br/>1-bit flag "outline"<br/>1-bit flag "dropshadow"<br/>1-bit flag "antialiased" | - |
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
| 11 | **num_kern** | 0..1 | Optional (if ^^version > 309): 1-byte unsigned integer | Number of kerning pairs for this glyph |
| 11..12 | **pad** | 0..1 | Optional (if ^^version <= 309): 1-byte unsigned integer | Padding |
| 11..13 | **kern_index** | 0..2 | Optional (if ^^flags/format == 16-bytes): 2-bytes unsigned integer (little endian) | Index in kerning table? |
| 11..15 | **x_advance** | 0..2 | Optional (if ^^flags/format == 16-bytes): 2-bytes unsigned integer (little endian) | Gap between this symbol and next one in rendered text? |
### **KerningItem** ###
#### **Size**: 4 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **left** | 2 | 2-bytes unsigned integer (little endian) | Code of left glyph |
| 2 | **kerning** | 1 | 1-byte signed integer | - |
| 3 | **right** | 1 | 1-byte unsigned integer | Code of right glyph |
