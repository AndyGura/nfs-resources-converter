# **NFS 4 High Stakes file specs** #

*Last time updated: 2026-10-05 13:26:45.369440+00:00*


# **Info by file extensions** #

**\*.FCE** 3D model (car.fce in car.viv: car model). [Fce4Geometry](#fce4geometry)

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FRD** main track file. [Nfs4FrdMap](#nfs4frdmap)

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
| 16 | **items_descr** | num_items\*9..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | Descriptions of items: offset, length and name of each of them |
| 16 + num_items\*9..? | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets and lengths are defined in previous block. Possible item types:<br/>- [Fce4Geometry](#fce4geometry)<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file<br/>- [BigfBlock](#bigfblock)<br/>- pure TGA image |
### **BigfItemDescriptionBlock** ###
#### **Size**: 9..? bytes ####
#### **Description**: Description of a single item of BIGF archive ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | Offset of item data, relative to BIGF block start |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | Length of item data in bytes |
| 8 | **name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | Item name (file name). Used as file name when the archive is unpacked |
## **Geometries** ##
### **Fce4Geometry** ###
#### **Size**: 8248..? bytes ####
#### **Description**: FCE 3D model, version 4 (NFS4: High Stakes, Motor City Online). Used for cars (car.fce in car.viv), dashboards (dash.fce), police officers, helicopter, menu models. Consists of up to 64 parts, each of them is a separate mesh with own position, and up to 16 "dummies": named points, which are used for lights, license plates, smoke and water effects. In addition to FCE3, every vertex has a "damaged" position, used when car is crashed. Coordinate system: X points right, Y up, Z forward. The unit is meter. Texture is a TGA image car00.tga, which is located next to car.fce in car.viv. Alpha channel of the texture defines which car color is applied to the pixel: 224 primary, 164 interior, 96 secondary, 32 driver hair color ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **version** | 4 | 4-bytes unsigned integer (little endian) | Format version. 0x00101014 in NFS4, 0x00101015 in Motor City Online (FCE4M) |
| 4 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **num_triangles** | 4 | 4-bytes unsigned integer (little endian) | Number of triangles in the model |
| 12 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Number of vertices in the model |
| 16 | **num_arts** | 4 | 4-bytes unsigned integer (little endian) | Number of "arts" (texture pages?). 1, unless triangles use non-zero `tex_page` |
| 20 | **vertices_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of vertices table, relative to header end (0x2038). Tables go one after another in order: vertices, normals, triangles, reserved areas 1-3, undamaged vertices, undamaged normals, damaged vertices, damaged normals, reserved area 4, animation flags, reserved areas 5-6 |
| 24 | **normals_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of normals table, relative to header end |
| 28 | **triangles_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of triangles table, relative to header end |
| 32 | **reserve1_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 1, relative to header end |
| 36 | **reserve2_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 2, relative to header end |
| 40 | **reserve3_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 3, relative to header end |
| 44 | **undamaged_vertices_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of undamaged vertices table, relative to header end |
| 48 | **undamaged_normals_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of undamaged normals table, relative to header end |
| 52 | **damaged_vertices_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of damaged vertices table, relative to header end |
| 56 | **damaged_normals_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of damaged normals table, relative to header end |
| 60 | **reserve4_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 4, relative to header end |
| 64 | **animation_flags_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of vertex animation flags table, relative to header end |
| 68 | **reserve5_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 5, relative to header end |
| 72 | **reserve6_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 6, relative to header end |
| 76 | **half_size** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Half-size of the whole model (bounding box, used for collisions) |
| 88 | **num_dummies** | 4 | 4-bytes unsigned integer (little endian) | Number of used dummies, 0..16 |
| 92 | **dummy_positions** | 192 | Array of `16` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Positions of dummies. Only first `num_dummies` are used |
| 284 | **num_parts** | 4 | 4-bytes unsigned integer (little endian) | Number of used parts, 0..64 |
| 288 | **part_positions** | 768 | Array of `64` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Positions of parts. Vertices of the part are relative to it. Only first `num_parts` are used |
| 1056 | **part_first_vertex** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Index of first vertex of each part |
| 1312 | **part_num_vertices** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Number of vertices in each part |
| 1568 | **part_first_triangle** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Index of first triangle of each part |
| 1824 | **part_num_triangles** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Number of triangles in each part |
| 2080 | **num_colors** | 4 | 4-bytes unsigned integer (little endian) | Number of car colors, 0..16. Every color is a set of 4 colors with the same index in tables below |
| 2084 | **primary_colors** | 64 | Array of `16` items<br/>Item size: 4 bytes<br/>Item type: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 | Primary car colors (car body). Only first `num_colors` are used |
| 2148 | **interior_colors** | 64 | Array of `16` items<br/>Item size: 4 bytes<br/>Item type: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 | Interior colors. Only first `num_colors` are used |
| 2212 | **secondary_colors** | 64 | Array of `16` items<br/>Item size: 4 bytes<br/>Item type: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 | Secondary car colors. Only first `num_colors` are used |
| 2276 | **driver_hair_colors** | 64 | Array of `16` items<br/>Item size: 4 bytes<br/>Item type: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 | Driver hair colors. Only first `num_colors` are used |
| 2340 | **unk1** | 260 | Bytes | Unknown purpose |
| 2600 | **dummy_names** | 1024 | Array of `16` items<br/>Item size: 64 bytes<br/>Item type: UTF-8 string | Names of dummies. The name defines what the dummy is. Special names: ":LICENSE", ":LICMED", ":LICLOW" (license plate in high/medium/low LOD), ":LICENSE_EURO" (long license plate), ":SMOKE" (smoke when shifting gears), ":WATER" (water generator). Other dummies are lights, where every letter is a property: 1st is kind ("H": headlight, "T": taillight, "B": brake light, "R": reverse light, "P": direction indicator, "S": siren), 2nd is color ("W": white, "R": red, "B": blue, "O": orange, "Y": yellow), 3rd is "Y"/"N" for breakable or not, 4th is flashing mode ("O"/"E" for odd/even flashing, "N" for no flashing), 5th is intensity 0..9, 6th and 7th are flashing time and delay 0..9 |
| 3624 | **part_names** | 4096 | Array of `64` items<br/>Item size: 64 bytes<br/>Item type: UTF-8 string | Names of parts. For car models, the role of the part is defined by its name: ":HB": high body, ":MB": medium body, ":LB": low body, ":TB": tiny body, ":OT": top of convertible, ":OL": pop-up headlights, ":OS": optional spoiler, ":OLB": left front brake, ":ORB": right front brake, ":OLM": left mirror, ":ORM": right mirror, ":OC": interior, ":ODL": dashboard when lit, ":OH": driver head, ":OD": driver holding steering wheel, ":OND": chair and steering wheel without driver, ":HLFW": high left front wheel ("M" instead of "H" for medium wheels, "R" instead of "L" for right, "M"/"R" instead of "F" for middle/rear) |
| 7720 | **unk2** | 528 | Bytes | Unknown purpose |
| 8248 | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex positions, relative to position of their part |
| 8248 + num_vertices\*12 | **normals** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex normals |
| 8248 + num_vertices\*12 + num_vertices\*12 | **triangles** | num_triangles\*56 | Array of `num_triangles` items<br/>Item type: [Fce4Triangle](#fce4triangle) | Triangles |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 | **reserve1** | 32 \* num_vertices | Bytes | Unknown purpose |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices | **reserve2** | 12 \* num_vertices | Bytes | Unknown purpose |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices | **reserve3** | 12 \* num_vertices | Bytes | Unknown purpose |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices | **undamaged_vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Undamaged vertex positions, a copy of `vertices` |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 | **undamaged_normals** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Undamaged vertex normals, a copy of `normals` |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 + num_vertices\*12 | **damaged_vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex positions of crashed car, relative to position of their part |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 | **damaged_normals** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex normals of crashed car |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 | **reserve4** | 4 \* num_vertices | Bytes | Unknown purpose |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + 4 \* num_vertices | **animation_flags** | num_vertices\*4 | Array of `num_vertices` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Vertex animation flags. Used by driver part ":OD": vertex with value 4 does not move, vertex with value 0 rotates together with steering wheel |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + 4 \* num_vertices + num_vertices\*4 | **reserve5** | 4 \* num_vertices | Bytes | Unknown purpose |
| 8248 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices + 12 \* num_vertices + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + num_vertices\*12 + 4 \* num_vertices + num_vertices\*4 + 4 \* num_vertices | **reserve6** | 12 \* num_triangles (+ num_vertices in FCE4M) | Bytes | Unknown purpose |
### **Fce4Triangle** ###
#### **Size**: 56 bytes ####
#### **Description**: A single triangle of FCE4 mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **tex_page** | 4 | 4-bytes unsigned integer (little endian) | Texture page index. 0 for car models (texture car00.tga), other values are used by multi-texture models like police officers and pursuit road objects |
| 4 | **vertex_indices** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Vertex indices, local to the part: add `part_first_vertex` of the part to get index in `vertices` |
| 16 | **unk0** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **flags** | 4 | 32 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: matte<br/>1: high_chrome<br/>2: no_cull<br/>3: semi_transparent<br/>5: window<br/>6: front_window<br/>7: left_window<br/>8: back_window<br/>9: right_window<br/>10: broken_window</details> | Triangle flags. "matte": no environment reflection (underbody), "high_chrome": strong reflection (windows), "no_cull": triangle is visible from both sides, "semi_transparent": translucent triangle (windows). Triangle is visible behind a semi-transparent triangle only if it has smaller index. "window" is set for all car windows, together with one of "front_window", "left_window", "back_window", "right_window". "broken_window" marks a texture of broken glass, which replaces the window after crash |
| 32 | **u** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Texture U coordinates of 3 vertices, 0..1 |
| 44 | **v** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Texture V coordinates of 3 vertices, 0..1, from top to bottom |
### **Fce4Color** ###
#### **Size**: 4 bytes ####
#### **Description**: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **hue** | 1 | 1-byte unsigned integer | Hue |
| 1 | **saturation** | 1 | 1-byte unsigned integer | Saturation |
| 2 | **brightness** | 1 | 1-byte unsigned integer | Brightness |
| 3 | **transparency** | 1 | 1-byte unsigned integer | Transparency |
## **Maps** ##
### **Nfs4FrdMap** ###
#### **Size**: 44..? bytes ####
#### **Description**: Main track file (NFS4 High Stakes). The track is split into blocks (segments): block headers with all counts come first, then block bodies with vertices, polygons at 3 levels of detail and objects. Polygon textures index the track QFS archive (<track>0.QFS), skipping its mirrored texture copies; UV-s are not stored, texture orientation is defined by polygon flags ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk** | 28 | Bytes | Unknown header |
| 28 | **num_blocks** | 4 | 4-bytes unsigned integer (little endian) | Number of track blocks |
| 32 | **num_vroad** | 4 | 4-bytes unsigned integer (little endian) | Number of virtual road entries |
| 36 | **vroad** | num_vroad\*84 | Array of `num_vroad` items<br/>Item type: [Nfs4VRoadBlock](#nfs4vroadblock) | Virtual road (spline) data for the whole track, referenced by index from `blocks[].polygon_vroad_data` |
| 36 + num_vroad\*84 | **blocks_headers** | (num_blocks+1)\*1512 | Array of `num_blocks+1` items<br/>Item type: [Nfs4TrkBlockHeader](#nfs4trkblockheader) | Metadata for every track block, incl. the counts used to size the corresponding entry of `blocks` |
| 36 + num_vroad\*84 + (num_blocks+1)\*1512 | **blocks** | (num_blocks+1)\*0..? | Array of `num_blocks+1` items<br/>Item type: [Nfs4TrkBlock](#nfs4trkblock) | Track block geometry and extra data |
| 36 + num_vroad\*84 + (num_blocks+1)\*1512 + (num_blocks+1)\*0..? | **num_global_objects_0** | 4 | 4-bytes unsigned integer (little endian) | Amount of objects in `global_objects_0` |
| 40 + num_vroad\*84 + (num_blocks+1)\*1512 + (num_blocks+1)\*0..? | **global_objects_0** | 0..? | A group of extra (out-of-terrain) objects: e.g. billboards, animated objects, physics props | Extra objects not attached to any track block |
| 40 + num_vroad\*84 + (num_blocks+1)\*1512 + (num_blocks+1)\*0..? | **num_global_objects_1** | 4 | 4-bytes unsigned integer (little endian) | Amount of objects in `global_objects_1` |
| 44 + num_vroad\*84 + (num_blocks+1)\*1512 + (num_blocks+1)\*0..? | **global_objects_1** | 0..? | A group of extra (out-of-terrain) objects: e.g. billboards, animated objects, physics props | Extra objects not attached to any track block. Special/physics props (type 6) live here |
### **Nfs4VRoadBlock** ###
#### **Size**: 84 bytes ####
#### **Description**: Virtual road entry: a point on the road centre line with orientation vectors of the road surface and distances to the road edges. Referenced by index from polygons of track blocks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **ref_point** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | A point on the track surface this virtual road entry describes |
| 12 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | A normal vector of the road surface |
| 24 | **forward** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | A forward vector, along the road direction |
| 36 | **right** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | A right vector, across the road |
| 48 | **left_wall** | 4 | Float number (little-endian) | Distance to the left wall/edge |
| 52 | **right_wall** | 4 | Float number (little-endian) | Distance to the right wall/edge |
| 56 | **unk0** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Unknown purpose |
| 64 | **unk1** | 20 | Array of `5` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
### **Nfs4BlockCount** ###
#### **Size**: 8 bytes ####
#### **Description**: Amount of items in some array of the track block, paired with an unknown value ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **num** | 4 | 4-bytes unsigned integer (little endian) | Amount of items |
| 4 | **unk** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **Nfs4NeighbourData** ###
#### **Size**: 4 bytes ####
#### **Description**: Reference to a neighbouring track block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block** | 2 | 2-bytes signed integer (little endian) | Neighbouring block index, or -1 |
| 2 | **unk** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
### **Nfs4TrkBlockHeader** ###
#### **Size**: 1512 bytes ####
#### **Description**: Metadata of a track block (segment of the track): position, bounds, neighbours and the counts which define sizes of all arrays in the [Nfs4TrkBlock](#nfs4trkblock) with the same index ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_chunk_sizes** | 44 | Array of `11` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Amount of polygons in each of the 11 polygon chunks (see Nfs4TrkBlock) of this block |
| 44 | **polygon_chunk_sizes_dup** | 44 | Array of `11` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 88 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Total amount of vertices stored for this block |
| 92 | **num_vertices_high** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices used by high-res terrain polygons |
| 96 | **num_vertices_low** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices used by low-res terrain polygons |
| 100 | **num_vertices_med** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices used by medium-res terrain polygons |
| 104 | **num_vertices_dup** | 4 | 4-bytes unsigned integer (little endian) | Equals to `num_vertices` |
| 108 | **num_vertices_obj** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices used by per-block objects? |
| 112 | **unk0** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 120 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position of the block in the world: a point on the road at the block start. Positions of all blocks form the track path |
| 132 | **bounds** | 48 | Array of `4` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Block bounding rectangle |
| 180 | **neighbour_data** | 1200 | Array of `300` items<br/>Item type: [Nfs4NeighbourData](#nfs4neighbourdata) | Neighbouring blocks. Unused items have block index -1 |
| 1380 | **object_chunk_counts** | 32 | Array of `4` items<br/>Item type: [Nfs4BlockCount](#nfs4blockcount) | Amount of extra objects in each of the 4 per-block extra object chunks (see Nfs4TrkBlock) |
| 1412 | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `polygon_vroad_data` |
| 1416 | **bounds_min** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Minimum corner of the axis-aligned bounding box of the block |
| 1428 | **bounds_max** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Maximum corner of the axis-aligned bounding box of the block |
| 1440 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 1444 | **num_positions** | 4 | 4-bytes unsigned integer (little endian) | Amount of position entries (groups of road polygons), usually 8 |
| 1448 | **num_xobj** | 8 | [Nfs4BlockCount](#nfs4blockcount) | Amount of items in `xobj` |
| 1456 | **num_polyobj** | 8 | [Nfs4BlockCount](#nfs4blockcount) | Amount of items in `xobj2` |
| 1464 | **num_soundsrc** | 8 | [Nfs4BlockCount](#nfs4blockcount) | Amount of items in `soundsrc` |
| 1472 | **num_lightsrc** | 8 | [Nfs4BlockCount](#nfs4blockcount) | Amount of items in `lightsrc` |
| 1480 | **neighbors** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
### **Nfs4PolygonVroadData** ###
#### **Size**: 24 bytes ####
#### **Description**: Per-polygon road data of a track block: reference to the global virtual road entry plus orientation vectors of the surface at this polygon ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **hs_minmax** | 4 | Array of `4` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 4 | **flags** | 5 | Array of `5` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 9 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 10 | **vroad_idx** | 2 | 2-bytes unsigned integer (little endian) | Index of the corresponding entry in the top-level `vroad` array |
| 12 | **normal** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part, normalized | A normal vector of the surface |
| 18 | **forward** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part, normalized | A forward vector of the surface |
### **Nfs4RefExtraObject** ###
#### **Size**: 20 bytes ####
#### **Description**: Reference to an extra object (XOBJ) placed in the track block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **pt** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | Position of the object |
| 12 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 14 | **global_index** | 2 | 2-bytes unsigned integer (little endian) | Sequence number of this object among all extra objects of the track |
| 16 | **unk1** | 3 | Bytes | Unknown purpose |
| 19 | **collision** | 1 | 1-byte unsigned integer | Unknown purpose |
### **Nfs4RefExtraObject2** ###
#### **Size**: 20 bytes ####
#### **Description**: Reference to a per-block object (POLYOBJ) placed in the track block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 2 | **type** | 1 | 1-byte unsigned integer | Unknown purpose |
| 3 | **id** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **pt** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | Position of the object |
| 16 | **crossindex** | 1 | 1-byte unsigned integer | Unknown purpose |
| 17 | **unk1** | 3 | Bytes | Unknown purpose |
### **Nfs4XObjHeader** ###
#### **Size**: 52 bytes ####
#### **Description**: Header of an extra object: type, position and the counts which define the sizes of the corresponding [Nfs4ExtraObject](#nfs4extraobject) arrays ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 4 | 4-bytes unsigned integer (little endian) | Object type. One of: 2, 4 (normal static object), 3 (animated object, has `anim_data`), 6 (special/physics prop, has `special_data`). Objects of type 6 are placed in global chunks of the track file, not in track blocks |
| 4 | **index** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **pt** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Object position |
| 24 | **size** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 32 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices of the corresponding entry in `objects` |
| 36 | **unk2** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 44 | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Amount of polygons of the corresponding entry in `objects` |
| 48 | **unk3** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **Nfs4AnimKeyframe** ###
#### **Size**: 20 bytes ####
#### **Description**: Animation keyframe of an extra object ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **pt** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 24 bits is a fractional part | Object position at this keyframe |
| 12 | **unk** | 8 | Array of `4` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes signed integer (little endian) | Object orientation at this keyframe, presumably a quaternion (x, y, z, w), where each component is 16-bit fixed point with 14 fraction bits |
### **Nfs4AnimExtra** ###
#### **Size**: 8..? bytes ####
#### **Description**: Animation of an extra object: a sequence of keyframes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 2 | **anim_type** | 1 | 1-byte unsigned integer | Unknown purpose |
| 3 | **anim_id** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **num_keyframes** | 2 | 2-bytes unsigned integer (little endian) | Amount of keyframes |
| 6 | **delay** | 2 | 2-bytes unsigned integer (little endian) | Animation delay/period |
| 8 | **keyframes** | num_keyframes\*20 | Array of `num_keyframes` items<br/>Item type: [Nfs4AnimKeyframe](#nfs4animkeyframe) | Animation keyframes |
### **Nfs4SpecialExtra** ###
#### **Size**: 72 bytes ####
#### **Description**: Physics properties of a special extra object (movable prop, e.g. a barrel or a cone) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **location** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position of the object. Equals to `pt` of the object header |
| 12 | **mass** | 4 | Float number (little-endian) | Mass of the object |
| 16 | **transform** | 36 | Array of `9` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | 3x3 rotation/transform matrix |
| 52 | **collision_dimensions** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Dimensions of the collision box of the object |
| 64 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 68 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 70 | **unk2** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
### **Nfs4Polygon** ###
#### **Size**: 13 bytes ####
#### **Description**: A single quad polygon of terrain or extra object. UV coordinates are not stored: the texture is mapped to the whole polygon, oriented according to `tex_flags` ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vertices** | 8 | Array of `4` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Indexes of the 4 vertices in the vertex table of the enclosing track block (terrain polygons) or extra object (object polygons) |
| 8 | **texture** | 2 | 2-bytes unsigned integer (little endian) | Bits 0-10: index of the texture in the track QFS archive (<file>0.QFS), not counting the archive's mirrored texture copies (images with a "<mirrored>" text attachment). Other bits: rendering flags |
| 10 | **tex_flags** | 2 | 2-bytes unsigned integer (little endian) | UV orientation of the texture on this polygon. Base UV-s of the 4 vertices are (0,1), (1,1), (1,0), (0,0); bit 4 mirrors them horizontally, bits 7-8 rotate them by 90 degrees x value. Other bits unknown. |
| 12 | **anim_flags** | 1 | 1-byte unsigned integer | Used for animated textures: length/period |
### **Nfs4ExtraObject** ###
#### **Size**: 0..? bytes ####
#### **Description**: Extra object mesh: a standalone object placed on the track (billboard, animated object, physics prop). Type, position and array sizes are defined by the [Nfs4XObjHeader](#nfs4xobjheader) with the same index in the enclosing chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **anim_data** | 0..? | Optional (if object_headers//type == 3): [Nfs4AnimExtra](#nfs4animextra) | Present when the corresponding `object_headers` entry has type == 3 (animated) |
| 0..? | **special_data** | 0..72 | Optional (if object_headers//type == 6): [Nfs4SpecialExtra](#nfs4specialextra) | Present when the corresponding `object_headers` entry has type == 6 (special) |
| 0..? | **vertices** | (object_headers//num_vertices)\*12 | Array of `object_headers//num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertices, global coordinates |
| (object_headers//num_vertices)\*12..? | **vertex_shading** | custom_func\*4 | Array of `custom_func` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex |
| (object_headers//num_vertices)\*12 + custom_func\*4..? | **polygons** | (object_headers//num_polygons)\*13 | Array of `object_headers//num_polygons` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Polygons of this object |
### **Nfs4TrkBlock** ###
#### **Size**: 0..? bytes ####
#### **Description**: Track block body: terrain vertices and polygons at 3 levels of detail, plus objects placed in this segment of the track. All array sizes come from the [Nfs4TrkBlockHeader](#nfs4trkblockheader) with the same index ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vertices** | (blocks_headers//num_vertices)\*12 | Array of `blocks_headers//num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertices, global coordinates |
| (blocks_headers//num_vertices)\*12 | **vertex_shading** | custom_func\*4 | Array of `custom_func` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 | **polygon_vroad_data** | (blocks_headers//num_polygons)\*24 | Array of `blocks_headers//num_polygons` items<br/>Item type: [Nfs4PolygonVroadData](#nfs4polygonvroaddata) | Per-polygon reference into the global `vroad` array, plus flags |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 | **xobj** | (blocks_headers//num_xobj/num)\*20 | Array of `blocks_headers//num_xobj/num` items<br/>Item type: [Nfs4RefExtraObject](#nfs4refextraobject) | References to extra objects placed in this block |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 | **xobj2** | (blocks_headers//num_polyobj/num)\*20 | Array of `blocks_headers//num_polyobj/num` items<br/>Item type: [Nfs4RefExtraObject2](#nfs4refextraobject2) | References to per-block objects placed in this block |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 | **soundsrc** | (blocks_headers//num_soundsrc/num)\*16 | Array of `blocks_headers//num_soundsrc/num` items<br/>Item size: 16 bytes<br/>Item type: Bytes | Sound sources. Each 16-byte item: position (3 x 32-bit fixed point with 24 fraction bits) + 32-bit sound type |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 | **lightsrc** | (blocks_headers//num_lightsrc/num)\*16 | Array of `blocks_headers//num_lightsrc/num` items<br/>Item size: 16 bytes<br/>Item type: Bytes | Light sources. Each 16-byte item: position (3 x 32-bit fixed point with 24 fraction bits) + 32-bit light type |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 | **polygons_low_res_track** | (blocks_headers//polygon_chunk_sizes/0)\*13 | Array of `blocks_headers//polygon_chunk_sizes/0` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Low-res track polygons |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 | **polygons_low_res_misc** | (blocks_headers//polygon_chunk_sizes/1)\*13 | Array of `blocks_headers//polygon_chunk_sizes/1` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Low-res misc (non-track) polygons |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 | **polygons_med_res_track** | (blocks_headers//polygon_chunk_sizes/2)\*13 | Array of `blocks_headers//polygon_chunk_sizes/2` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Medium-res track polygons |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 | **polygons_med_res_misc** | (blocks_headers//polygon_chunk_sizes/3)\*13 | Array of `blocks_headers//polygon_chunk_sizes/3` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Medium-res misc (non-track) polygons |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 | **polygons_high_res_track** | (blocks_headers//polygon_chunk_sizes/4)\*13 | Array of `blocks_headers//polygon_chunk_sizes/4` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | High-res track polygons |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 | **polygons_high_res_misc** | (blocks_headers//polygon_chunk_sizes/5)\*13 | Array of `blocks_headers//polygon_chunk_sizes/5` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | High-res misc (non-track) polygons |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 | **lanes** | (blocks_headers//polygon_chunk_sizes/6)\*13 | Array of `blocks_headers//polygon_chunk_sizes/6` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Lane helper polygons, not meant to be rendered |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 | **polygons_high_res_misc_1** | (blocks_headers//polygon_chunk_sizes/7)\*13 | Array of `blocks_headers//polygon_chunk_sizes/7` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Additional polygon chunk, purpose unknown. Not rendered by the converter |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 | **polygons_high_res_misc_2** | (blocks_headers//polygon_chunk_sizes/8)\*13 | Array of `blocks_headers//polygon_chunk_sizes/8` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Additional polygon chunk, purpose unknown. Not rendered by the converter |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 + (blocks_headers//polygon_chunk_sizes/8)\*13 | **polygons_high_res_misc_3** | (blocks_headers//polygon_chunk_sizes/9)\*13 | Array of `blocks_headers//polygon_chunk_sizes/9` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Additional polygon chunk, purpose unknown. Not rendered by the converter |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 + (blocks_headers//polygon_chunk_sizes/8)\*13 + (blocks_headers//polygon_chunk_sizes/9)\*13 | **polygons_high_res_misc_4** | (blocks_headers//polygon_chunk_sizes/10)\*13 | Array of `blocks_headers//polygon_chunk_sizes/10` items<br/>Item type: [Nfs4Polygon](#nfs4polygon) | Additional polygon chunk, purpose unknown. Not rendered by the converter |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 + (blocks_headers//polygon_chunk_sizes/8)\*13 + (blocks_headers//polygon_chunk_sizes/9)\*13 + (blocks_headers//polygon_chunk_sizes/10)\*13 | **extra_objects_0** | 0..? | A group of extra (out-of-terrain) objects: e.g. billboards, animated objects, physics props | Extra objects chunk #0 of this block. Amount of objects is `object_chunk_counts[0].num` of the block header |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 + (blocks_headers//polygon_chunk_sizes/8)\*13 + (blocks_headers//polygon_chunk_sizes/9)\*13 + (blocks_headers//polygon_chunk_sizes/10)\*13..? | **extra_objects_1** | 0..? | A group of extra (out-of-terrain) objects: e.g. billboards, animated objects, physics props | Extra objects chunk #1 of this block. Amount of objects is `object_chunk_counts[1].num` of the block header |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 + (blocks_headers//polygon_chunk_sizes/8)\*13 + (blocks_headers//polygon_chunk_sizes/9)\*13 + (blocks_headers//polygon_chunk_sizes/10)\*13..? | **extra_objects_2** | 0..? | A group of extra (out-of-terrain) objects: e.g. billboards, animated objects, physics props | Extra objects chunk #2 of this block. Amount of objects is `object_chunk_counts[2].num` of the block header |
| (blocks_headers//num_vertices)\*12 + custom_func\*4 + (blocks_headers//num_polygons)\*24 + (blocks_headers//num_xobj/num)\*20 + (blocks_headers//num_polyobj/num)\*20 + (blocks_headers//num_soundsrc/num)\*16 + (blocks_headers//num_lightsrc/num)\*16 + (blocks_headers//polygon_chunk_sizes/0)\*13 + (blocks_headers//polygon_chunk_sizes/1)\*13 + (blocks_headers//polygon_chunk_sizes/2)\*13 + (blocks_headers//polygon_chunk_sizes/3)\*13 + (blocks_headers//polygon_chunk_sizes/4)\*13 + (blocks_headers//polygon_chunk_sizes/5)\*13 + (blocks_headers//polygon_chunk_sizes/6)\*13 + (blocks_headers//polygon_chunk_sizes/7)\*13 + (blocks_headers//polygon_chunk_sizes/8)\*13 + (blocks_headers//polygon_chunk_sizes/9)\*13 + (blocks_headers//polygon_chunk_sizes/10)\*13..? | **extra_objects_3** | 0..? | A group of extra (out-of-terrain) objects: e.g. billboards, animated objects, physics props | Extra objects chunk #3 of this block. Amount of objects is `object_chunk_counts[3].num` of the block header |
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
