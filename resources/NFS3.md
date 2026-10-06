# **NFS 3 Hot Pursuit file specs** #

*Last time updated: 2026-10-06 13:28:56.081873+00:00*


# **Info by file extensions** #

**\*.COL** track additional data. [MapColFile](#mapcolfile)
        
**\*.FCE** 3D model (car.fce in car.viv: car model). [Fce3Geometry](#fce3geometry)

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
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | The length of this BIGF block in bytes. NFS6 stores the length without padding between items: header plus item lengths |
| 8 | **num_items** | 4 | 4-bytes unsigned integer (big endian) | An amount of items |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **items_descr** | num_items\*9..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | Descriptions of items: offset, length and name of each of them |
| 16 + num_items\*9..? | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets and lengths are defined in previous block. Possible item types:<br/>- [Fce3Geometry](#fce3geometry)<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file<br/>- [BigfBlock](#bigfblock)<br/>- pure TGA image |
### **BigfItemDescriptionBlock** ###
#### **Size**: 9..? bytes ####
#### **Description**: Description of a single item of BIGF archive ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | Offset of item data, relative to BIGF block start |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | Length of item data in bytes |
| 8 | **name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | Item name (file name). Used as file name when the archive is unpacked |
## **Geometries** ##
### **Fce3Geometry** ###
#### **Size**: 7940..? bytes ####
#### **Description**: FCE 3D model, version 3 (NFS3: Hot Pursuit). Used for cars (car.fce in car.viv), police officers, menu models. Consists of up to 64 parts, each of them is a separate mesh with own position, and up to 16 "dummies": named points, which are used for lights. Coordinate system: X points right, Y up, Z forward. The unit is meter. Texture is a TGA image car00.tga, which is located next to car.fce in car.viv ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **num_triangles** | 4 | 4-bytes unsigned integer (little endian) | Number of triangles in the model |
| 8 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Number of vertices in the model |
| 12 | **num_arts** | 4 | 4-bytes unsigned integer (little endian) | Number of "arts" (texture pages?). 1, unless triangles use non-zero `tex_page` |
| 16 | **vertices_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of vertices table, relative to header end (0x1F04). Tables go one after another in order: vertices, normals, triangles, reserved areas 1-3 |
| 20 | **normals_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of normals table, relative to header end |
| 24 | **triangles_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of triangles table, relative to header end |
| 28 | **reserve1_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 1, relative to header end |
| 32 | **reserve2_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 2, relative to header end |
| 36 | **reserve3_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of reserved area 3, relative to header end |
| 40 | **half_size** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Half-size of the whole model (bounding box, used for collisions) |
| 52 | **num_dummies** | 4 | 4-bytes unsigned integer (little endian) | Number of used dummies, 0..16 |
| 56 | **dummy_positions** | 192 | Array of `16` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Positions of dummies. Only first `num_dummies` are used |
| 248 | **num_parts** | 4 | 4-bytes unsigned integer (little endian) | Number of used parts, 0..64 |
| 252 | **part_positions** | 768 | Array of `64` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Positions of parts. Vertices of the part are relative to it. Only first `num_parts` are used |
| 1020 | **part_first_vertex** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Index of first vertex of each part |
| 1276 | **part_num_vertices** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Number of vertices in each part |
| 1532 | **part_first_triangle** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Index of first triangle of each part |
| 1788 | **part_num_triangles** | 256 | Array of `64` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Number of triangles in each part |
| 2044 | **num_primary_colors** | 4 | 4-bytes unsigned integer (little endian) | Number of primary car colors, 0..16 |
| 2048 | **primary_colors** | 256 | Array of `16` items<br/>Item size: 16 bytes<br/>Item type: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 | Primary car colors. Only first `num_primary_colors` are used |
| 2304 | **num_secondary_colors** | 4 | 4-bytes unsigned integer (little endian) | Number of secondary car colors, 0..16 |
| 2308 | **secondary_colors** | 256 | Array of `16` items<br/>Item size: 16 bytes<br/>Item type: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 | Secondary car colors. Only first `num_secondary_colors` are used |
| 2564 | **dummy_names** | 1024 | Array of `16` items<br/>Item size: 64 bytes<br/>Item type: UTF-8 string | Names of dummies. The name defines what the dummy is: first letter is the kind ("H": headlight, "T": taillight, "M": siren), third letter is the side ("L"/"R"), fourth letter is a flashing mode ("O"/"E" for odd/even flashing, "N" for no flashing) |
| 3588 | **part_names** | 4096 | Array of `64` items<br/>Item size: 64 bytes<br/>Item type: UTF-8 string | Names of parts. For car models, the role of the part is defined by its index, not by name: 0: High body, 1: Left front wheel, 2: Right front wheel, 3: Left rear wheel, 4: Right rear wheel, 5: Medium body, 6: Medium right front wheel, 7: Medium left front wheel, 8: Medium right rear wheel, 9: Medium left rear wheel, 10: Low body, 11: Tiny body, 12: High headlights |
| 7684 | **unk1** | 256 | Bytes | Unknown purpose |
| 7940 | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex positions, relative to position of their part |
| 7940 + num_vertices\*12 | **normals** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex normals |
| 7940 + num_vertices\*12 + num_vertices\*12 | **triangles** | num_triangles\*56 | Array of `num_triangles` items<br/>Item type: [Fce3Triangle](#fce3triangle) | Triangles |
| 7940 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 | **reserve1** | 32 \* num_vertices | Bytes | Unknown purpose |
| 7940 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices | **reserve2** | 12 \* num_vertices | Bytes | Unknown purpose |
| 7940 + num_vertices\*12 + num_vertices\*12 + num_triangles\*56 + 32 \* num_vertices + 12 \* num_vertices | **reserve3** | 12 \* num_vertices | Bytes | Unknown purpose |
### **Fce3Triangle** ###
#### **Size**: 56 bytes ####
#### **Description**: A single triangle of FCE mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **tex_page** | 4 | 4-bytes unsigned integer (little endian) | Texture page index. 0 for car models (texture car00.tga), other values are used by multi-texture models like police officers |
| 4 | **vertex_indices** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Vertex indices, local to the part: add `part_first_vertex` of the part to get index in `vertices` |
| 16 | **unk0** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **flags** | 4 | 32 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: matte<br/>1: high_chrome<br/>2: no_cull<br/>3: semi_transparent</details> | Triangle flags. "matte": no environment reflection (underbody), "high_chrome": strong reflection (windows), "no_cull": triangle is visible from both sides, "semi_transparent": translucent triangle (windows). Triangle is visible behind a semi-transparent triangle only if it has smaller index |
| 32 | **u** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Texture U coordinates of 3 vertices, 0..1 |
| 44 | **v** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Texture V coordinates of 3 vertices, 0..1, from bottom to top |
### **FceColor** ###
#### **Size**: 16 bytes ####
#### **Description**: Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, saturation = percent / 100 * 255, brightness = percent / 100 * 255 ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **hue** | 4 | 4-bytes unsigned integer (little endian) | Hue |
| 4 | **saturation** | 4 | 4-bytes unsigned integer (little endian) | Saturation |
| 8 | **brightness** | 4 | 4-bytes unsigned integer (little endian) | Brightness |
| 12 | **transparency** | 4 | 4-bytes unsigned integer (little endian) | Transparency |
## **Maps** ##
### **FrdMap** ###
#### **Size**: 36..? bytes ####
#### **Description**: Main track file. The track is split into blocks (segments). Each block has its own vertex table ([FrdBlock](#frdblock)) and polygons at 3 levels of detail ([FrdPolyBlock](#frdpolyblock)). Standalone objects (billboards, animated objects) are stored as extra objects. Polygon textures are referenced through the `texture_blocks` table, which points to images in <track>0.QFS ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk** | 28 | Bytes | Unknown header |
| 28 | **num_blocks** | 4 | 4-bytes unsigned integer (little endian) | Number of blocks. Block arrays below have `num_blocks + 1` items |
| 32 | **blocks** | (num_blocks+1)\*1316..? | Array of `num_blocks+1` items<br/>Item type: [FrdBlock](#frdblock) | Track blocks: vertices, road data and object references of each track segment |
| 32 + (num_blocks+1)\*1316..? | **polygon_blocks** | (num_blocks+1)\*44..? | Array of `num_blocks+1` items<br/>Item type: [FrdPolyBlock](#frdpolyblock) | Polygons of the track blocks, same index as in `blocks` |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44..? | **extraobject_blocks** | (4\*(num_blocks+1)+1)\*4..? | Array of `4*(num_blocks+1)+1` items<br/>Item size: 4..? bytes<br/>Item type: Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [ExtraObjectBlock](#extraobjectblock) | Chunks of extra objects (XOBJ): 4 chunks per track block (matching the 4 `polyobj` chunks of the block), followed by one global chunk with objects not attached to any block. Each chunk is prefixed with the amount of objects in it |
| 32 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1)+1)\*4..? | **num_texture_blocks** | 4 | 4-bytes unsigned integer (little endian) | Length of texture_blocks array |
| 36 + (num_blocks+1)\*1316 + (num_blocks+1)\*44 + (4\*(num_blocks+1)+1)\*4..? | **texture_blocks** | num_texture_blocks\*47 | Array of `num_texture_blocks` items<br/>Item type: [TextureBlock](#textureblock) | Texture references table, used by all polygons of the track. Texture images are in <track>0.QFS |
### **FrdBlock** ###
#### **Size**: 1316..? bytes ####
#### **Description**: Track block: a segment of the track. Contains terrain vertices with shading, road orientation data and references to objects placed in this segment. Polygons of the block are stored separately, in the [FrdPolyBlock](#frdpolyblock) with the same index ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position of the block in the world: a point on the road at the block start. Positions of all blocks form the track path |
| 12 | **bounds** | 48 | Array of `4` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Block bounding rectangle |
| 60 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Total amount of vertices |
| 64 | **num_vertices_high** | 4 | 4-bytes unsigned integer (little endian) | End of the vertices used by high-res terrain polygons. `vertices` are ordered: POLYOBJ object vertices (up to `num_vertices_obj`), terrain vertices of low-res, then medium-res, then high-res polygons (up to `num_vertices_low`, `num_vertices_med`, `num_vertices_high`), then vertices of the lanes polygons |
| 68 | **num_vertices_low** | 4 | 4-bytes unsigned integer (little endian) | End of the vertices used by low-res terrain polygons |
| 72 | **num_vertices_med** | 4 | 4-bytes unsigned integer (little endian) | End of the vertices used by medium-res terrain polygons |
| 76 | **num_vertices_dup** | 4 | 4-bytes unsigned integer (little endian) | Equals to `num_vertices` |
| 80 | **num_vertices_obj** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices used by POLYOBJ objects of the block, they go first in `vertices` |
| 84 | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertices. Coordinates are global (not relative to block position) |
| 84 + num_vertices\*12 | **vertex_shading** | num_vertices\*4 | Array of `num_vertices` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex |
| 84 + num_vertices\*12 + num_vertices\*4 | **neighbour_data** | 1200 | Array of `600` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | 300 pairs of 16-bit values: (neighbouring block index, unknown). Unused pairs have index 0xFFFF |
| 1284 + num_vertices\*12 + num_vertices\*4 | **num_start_pos** | 4 | 4-bytes unsigned integer (little endian) | Index of the first `positions` entry of this block among all blocks of the track (sum of `num_positions` of all previous blocks) |
| 1288 + num_vertices\*12 + num_vertices\*4 | **num_positions** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `positions` |
| 1292 + num_vertices\*12 + num_vertices\*4 | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `polygons`. Equals to the amount of high-res track polygons (`polygons[4]` chunk of the [FrdPolyBlock](#frdpolyblock)) |
| 1296 + num_vertices\*12 + num_vertices\*4 | **num_vroad** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `vroad` |
| 1300 + num_vertices\*12 + num_vertices\*4 | **num_xobj** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `xobj` |
| 1304 + num_vertices\*12 + num_vertices\*4 | **num_polyobj** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `polyobj` |
| 1308 + num_vertices\*12 + num_vertices\*4 | **num_soundsrc** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `soundsrc` |
| 1312 + num_vertices\*12 + num_vertices\*4 | **num_lightsrc** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in `lightsrc` |
| 1316 + num_vertices\*12 + num_vertices\*4 | **positions** | num_positions\*8 | Array of `num_positions` items<br/>Item type: [FrdPositionBlock](#frdpositionblock) | Groups of high-res track polygons ("rows" across the road) |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 | **polygons** | num_polygons\*8 | Array of `num_polygons` items<br/>Item type: [FrdBlockPolygonData](#frdblockpolygondata) | Per-polygon data (road orientation reference + flags) for the high-res track polygons |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 | **vroad** | num_vroad\*12 | Array of `num_vroad` items<br/>Item type: [FrdBlockVroadData](#frdblockvroaddata) | Virtual road: orientation vectors of the road surface, referenced from `polygons` |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 | **xobj** | num_xobj\*20 | Array of `num_xobj` items<br/>Item type: [FrdXobjRef](#frdxobjref) | References to extra objects (XOBJ) placed in this block |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 | **polyobj** | num_polyobj\*16..num_polyobj\*20 | Array of `num_polyobj` items<br/>Item type: [FrdPolyObjRef](#frdpolyobjref) | References to the objects of the first POLYOBJ chunk of the block |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*16..1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*20 | **polyobj_unused** | 4 \* (amount of `polyobj` items with type != 4) | Bytes | Unused space: `polyobj` area is 20 * `num_polyobj` bytes long, 16-byte records leave 4 bytes each at the end |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*16 + 4 \* (amount of `polyobj` items with type != 4)..1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*20 + 4 \* (amount of `polyobj` items with type != 4) | **soundsrc** | num_soundsrc\*16 | Array of `num_soundsrc` items<br/>Item type: [FrdSoundSource](#frdsoundsource) | Sound sources |
| 1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*16 + 4 \* (amount of `polyobj` items with type != 4) + num_soundsrc\*16..1316 + num_vertices\*12 + num_vertices\*4 + num_positions\*8 + num_polygons\*8 + num_vroad\*12 + num_xobj\*20 + num_polyobj\*20 + 4 \* (amount of `polyobj` items with type != 4) + num_soundsrc\*16 | **lightsrc** | num_lightsrc\*16 | Array of `num_lightsrc` items<br/>Item type: [FrdLightSource](#frdlightsource) | Light sources |
### **FrdPositionBlock** ###
#### **Size**: 8 bytes ####
#### **Description**: A group of consecutive high-res track polygons: a "row" of polygons across the road. A track block usually has 8 of them, together covering all polygons of the high-res track chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon** | 2 | 2-bytes unsigned integer (little endian) | Index of the first polygon of this group in the high-res track polygon chunk (`polygons[4]` of the corresponding [FrdPolyBlock](#frdpolyblock)) |
| 2 | **num_polygons** | 1 | 1-byte unsigned integer | Amount of polygons in this group |
| 3 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **extra_neighbor1** | 2 | 2-bytes unsigned integer (little endian) | Extra neighbouring block index? 0xFFFF if none |
| 6 | **extra_neighbor2** | 2 | 2-bytes unsigned integer (little endian) | Extra neighbouring block index? 0xFFFF if none |
### **FrdBlockPolygonData** ###
#### **Size**: 8 bytes ####
#### **Description**: Per-polygon data of the high-res track polygons: one record per polygon of `polygons[4]` chunk of the corresponding [FrdPolyBlock](#frdpolyblock) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vroad_idx** | 1 | 1-byte unsigned integer | Index of entry in `vroad` array of the block: orientation of the road surface at this polygon |
| 1 | **flags** | 1 | 1-byte unsigned integer | Polygon flags (road surface type, driveable etc.?) |
| 2 | **unk** | 6 | Bytes | Unknown purpose |
### **FrdBlockVroadData** ###
#### **Size**: 12 bytes ####
#### **Description**: Virtual road entry: orientation of the road surface, referenced by index from `polygons[].vroad_idx` of the block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part | A normal vector of the surface, unit length (or zero) |
| 6 | **forward** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part | A forward vector of the surface, unit length (or zero) |
### **FrdXobjRef** ###
#### **Size**: 20 bytes ####
#### **Description**: Reference to an extra object (XOBJ) placed in the block. Animated extra objects are not always listed ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Position of the object, equals to its reference point (`pt_ref`) |
| 12 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 14 | **global_no** | 2 | 2-bytes unsigned integer (little endian) | Sequence number of the object among all extra objects of the track |
| 16 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 18 | **cross_index** | 1 | 1-byte unsigned integer | Index of the object in `polyobj` of the block (the first POLYOBJ chunk), 0 if the object is in another chunk |
| 19 | **unk2** | 1 | 1-byte unsigned integer | Values 1, 2 |
### **FrdPolyObjRef** ###
#### **Size**: 16..20 bytes ####
#### **Description**: Reference to an object of the first POLYOBJ chunk of the block (`polyobj[0]` of the corresponding [FrdPolyBlock](#frdpolyblock)), same order. Variable size: 16 bytes, or 20 for an extra object (XOBJ) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **size** | 2 | 2-bytes unsigned integer (little endian) | Record size in bytes |
| 2 | **type** | 1 | 1-byte unsigned integer | Object type: 1 - polygons of the block, 4 - extra object (XOBJ) |
| 3 | **objno** | 1 | 1-byte unsigned integer | Object number |
| 4 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Reference point of the object |
| 16 | **xobj_idx** | 0..4 | Optional (if type == 4): 4-bytes unsigned integer (little endian) | Index of the extra object in its chunk (`extraobject_blocks[4 * block_index]` of the track file) |
### **FrdSoundSource** ###
#### **Size**: 16 bytes ####
#### **Description**: A sound source placed in the block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Position of the sound source |
| 12 | **type** | 4 | 4-bytes unsigned integer (little endian) | Sound type |
### **FrdLightSource** ###
#### **Size**: 16 bytes ####
#### **Description**: A light source placed in the block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Position of the light source |
| 12 | **type** | 4 | 4-bytes unsigned integer (little endian) | Light type |
### **FrdPolyBlock** ###
#### **Size**: 44..? bytes ####
#### **Description**: Polygons of a track block (the [FrdBlock](#frdblock) with the same index): 7 chunks of terrain polygons + 4 chunks of per-block objects ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygons** | 28..? | Array of `7` items<br/>Item type: [FrdPolygonsBlock](#frdpolygonsblock) | Terrain polygon chunks: 0 - low-res track, 1 - low-res misc (non-track), 2 - medium-res track, 3 - medium-res misc, 4 - high-res track, 5 - high-res misc, 6 - lanes (helper polygons, not rendered). Low/medium/high-res chunks are alternative levels of detail of the same terrain (roughly 1/4, 1/2 and full amount of polygons) |
| 28..? | **polyobj** | 16..? | Array of `4` items<br/>Item type: [FrdPolyObjBlock](#frdpolyobjblock) | 4 chunks of per-block objects. Extra objects (XOBJ) referenced from chunk N are stored in `extraobject_blocks[4 * block_index + N]` of the track file |
### **FrdPolygonsBlock** ###
#### **Size**: 4..? bytes ####
#### **Description**: A chunk of terrain polygons of a track block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **sz** | 4 | 4-bytes unsigned integer (little endian) | Amount of polygons in this chunk. 0 means the chunk is absent and no data follows |
| 4 | **data** | ? | One of types:<br/>- Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [FrdPolygonRecord](#frdpolygonrecord)<br/>- Bytes | Polygons. This data is presented only if sz != 0. The array length prefix duplicates `sz` |
### **FrdPolygonRecord** ###
#### **Size**: 14 bytes ####
#### **Description**: A single quad polygon of terrain or object ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vertices** | 8 | Array of `4` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Indexes of the 4 vertices in the vertex table of the enclosing track block (terrain polygons) or extra object (object polygons) |
| 8 | **tex_id** | 2 | 2-bytes unsigned integer (little endian) | Index of entry in `texture_blocks` table of the track file, which defines the real texture index in the QFS archive and UV coordinates of polygon corners |
| 10 | **tex_flags** | 2 | 2-bytes unsigned integer (little endian) | Texture flags. Zero for terrain polygons, non-zero only in the lanes chunk |
| 12 | **flags** | 1 | 1-byte unsigned integer | Usually 0, observed values 0x20, 0x30, 0x40 |
| 13 | **unk** | 1 | 1-byte unsigned integer | Always 0xF9? |
### **FrdPolyObjBlock** ###
#### **Size**: 4..? bytes ####
#### **Description**: A chunk of per-block objects (POLYOBJ) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **sz** | 4 | 4-bytes unsigned integer (little endian) | Total amount of polygons of all objects in this chunk. 0 means the chunk is absent and no data follows |
| 4 | **data** | ? | One of types:<br/>- Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [FrdPolyObjPolygonsBlock](#frdpolyobjpolygonsblock)<br/>- Bytes | Objects. This data is presented only if sz > 0. The array length prefix is the amount of objects, including the XOBJ references (type == 4) |
### **FrdPolyObjPolygonsBlock** ###
#### **Size**: 4..? bytes ####
#### **Description**: Polygons of a single per-block object (POLYOBJ) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 4 | 4-bytes unsigned integer (little endian) | Object type: 1 - polygons follow; 4 - the object is an extra object (XOBJ), its geometry is stored in the corresponding chunk of `extraobject_blocks` and nothing follows here |
| 4 | **data** | ? | One of types:<br/>- Array, prefixed with length field<br/>Length field type: 4-bytes unsigned integer (little endian)<br/>Item type: [FrdPolygonRecord](#frdpolygonrecord)<br/>- Bytes | Polygons of the object. This data is presented only if type == 1 |
### **ExtraObjectBlock** ###
#### **Size**: 36..? bytes ####
#### **Description**: Extra object (XOBJ): a standalone mesh placed on the track, e.g. a billboard, a building or an animated object ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **cross_type** | 4 | 4-bytes unsigned integer (little endian) | Object type: 4 - static object, 3 - animated object |
| 4 | **cross_no** | 4 | 4-bytes unsigned integer (little endian) | Object number |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **data** | 16..? | One of types:<br/>- [ExtraObjectDataCrossType4](#extraobjectdatacrosstype4)<br/>- [ExtraObjectDataCrossType3](#extraobjectdatacrosstype3) | Type-specific data (position or animation), block class picked according to `cross_type` |
| 28..? | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices |
| 32..? | **vertices** | num_vertices\*12 | Array of `num_vertices` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertices, relative to the object position (reference point for static objects, current keyframe for animated ones) |
| 32 + num_vertices\*12..? | **vertex_shading** | num_vertices\*4 | Array of `num_vertices` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Per-vertex shading color, 32-bit ARGB (0xFFRRGGBB), one item per vertex |
| 32 + num_vertices\*12 + num_vertices\*4..? | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Length of polygons array |
| 36 + num_vertices\*12 + num_vertices\*4..? | **polygons** | num_polygons\*14 | Array of `num_polygons` items<br/>Item type: [FrdPolygonRecord](#frdpolygonrecord) | Polygons of the object. Vertex indexes point to `vertices` of this object |
### **ExtraObjectDataCrossType3** ###
#### **Size**: 24..? bytes ####
#### **Description**: Extra data of an animated extra object (cross_type == 3) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk** | 18 | Bytes | Unknown purpose |
| 18 | **type** | 1 | 1-byte unsigned integer. Always == 0x3 | Animation type, always 3 |
| 19 | **objno** | 1 | 1-byte unsigned integer | Object number |
| 20 | **num_animdata** | 2 | 2-bytes unsigned integer (little endian) | Amount of keyframes |
| 22 | **anim_delay** | 2 | 2-bytes unsigned integer (little endian) | Delay between keyframes (animation speed). Unit is not confirmed, the converter assumes 1/64 of a second |
| 24 | **animdata** | num_animdata\*20 | Array of `num_animdata` items<br/>Item type: [AnimData](#animdata) | Animation keyframes, played in a loop. Object vertices are relative to the position and orientation of the current keyframe |
### **AnimData** ###
#### **Size**: 20 bytes ####
#### **Description**: Animation keyframe of an extra object ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **pt** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Object position at this keyframe |
| 12 | **orientation** | 8 | Rotation quaternion (x,y,z,w), in the same axes as the positions next to it, where each component is: 16-bit real number (little-endian, signed), where last 14 bits is a fractional part | Object orientation at this keyframe. Object vertices are rotated by it (v' = q v q^-1), then moved to `pt` |
### **ExtraObjectDataCrossType4** ###
#### **Size**: 16 bytes ####
#### **Description**: Extra data of a static extra object (cross_type == 4) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **pt_ref** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Reference point: position of the object in the world. Object vertices are relative to it |
| 12 | **anim_memory** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **TextureBlock** ###
#### **Size**: 47 bytes ####
#### **Description**: Texture reference. Polygons refer to items of this table by `tex_id`, the item defines the actual texture in the QFS archive and UV coordinates of the polygon corners ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **width** | 2 | 2-bytes unsigned integer (little endian) | Texture width |
| 2 | **height** | 2 | 2-bytes unsigned integer (little endian) | Texture height |
| 4 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Blending related, hometown covered bridges godrays |
| 8 | **corners** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | UV coordinates of the 4 polygon corners (u0, v0, u1, v1, u2, v2, u3, v3), in the same order as polygon vertices |
| 40 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 44 | **is_lane** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): default<br/>1 (0x1): lane</details> | 1 if not a real texture (lane), 0 usually |
| 45 | **texture_id** | 2 | 2-bytes unsigned integer (little endian) | Index of the texture in the track QFS archive (<track>0.QFS) |
### **MapColFile** ###
#### **Size**: 16..? bytes ####
#### **Description**: Track additional data (COL file), a list of extrablocks: textures map (used by polygons of the TRK file), track-wide props with their 3D models and collision data (road centre line for the physics engine) ####
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
#### **Description**: A typed container of data records. The same structure is used for extrablocks inside TRK blocks and in the COL file; record type is defined by `type` ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes |
| 4 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>2 (0x2): textures_map<br/>4 (0x4): block_numbers<br/>5 (0x5): polygon_map<br/>6 (0x6): median_polygons<br/>7 (0x7): props_7<br/>8 (0x8): prop_descriptions<br/>9 (0x9): lanes<br/>13 (0xd): road_vectors<br/>15 (0xf): collision_data<br/>18 (0x12): props_18<br/>19 (0x13): props_19</details> | Type of the data records. textures_map, props_7, prop_descriptions and collision_data are found in COL file; polygon_map, block_numbers, median_polygons, props_18, prop_descriptions, lanes and road_vectors in TRK blocks |
| 5 | **unk** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 6 | **num_data_records** | 2 | 2-bytes unsigned integer (little endian) | Amount of data records |
| 8 | **data_records** | ? | Type according to enum `type`:<br/>- Array of `num_data_records` items<br/>Item type: [TexturesMapExtraDataRecord](#texturesmapextradatarecord)<br/>- Array of `num_data_records` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `num_data_records` items<br/>Item type: [PolygonMapExtraDataRecord](#polygonmapextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [MedianExtraDataRecord](#medianextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropDescriptionExtraDataRecord](#propdescriptionextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [LanesExtraDataRecord](#lanesextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [RoadVectorsExtraDataRecord](#roadvectorsextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [CollisionExtraDataRecord](#collisionextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Array of `num_data_records` items<br/>Item type: [PropExtraDataRecord](#propextradatarecord)<br/>- Bytes | Data records, block class picked according to `type`. Records of unknown types are kept as raw bytes |
### **TexturesMapExtraDataRecord** ###
#### **Size**: 10 bytes ####
#### **Description**: Texture reference. Polygons of the track (TRK) and of props refer to items of this table by index, the item defines the actual texture in the QFS archive and its orientation on the polygon ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **texture_number** | 2 | 2-bytes unsigned integer (little endian) | Index of the texture in the track QFS file (<track>0.QFS) |
| 2 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 3 | **alignment** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1 (0x1): rotate_180<br/>3 (0x3): rotate_270<br/>5 (0x5): normal<br/>9 (0x9): rotate_90<br/>16 (0x10): flip_v<br/>18 (0x12): rotate_270_2<br/>20 (0x14): flip_h<br/>24 (0x18): rotate_90_2</details> | Orientation of the texture on the polygon, which game uses instead of UV-s. The converter uses base UV-s (0,1), (1,1), (1,0), (0,0) for the 4 polygon vertices and modifies them according to the enum value: rotate_* shift them by 1, 2 or 3 vertices, flip_h/flip_v mirror them |
| 4 | **luminosity** | 3 | Color RGB values | Luminosity color |
| 7 | **black** | 3 | Color RGB values | Unknown, usually black |
### **PolygonMapExtraDataRecord** ###
#### **Size**: 2 bytes ####
#### **Description**: Polygon extra data: road surface orientation for a polygon of the block. Number of items here == np1 * 2, but sometimes less. Why? ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vectors_idx** | 1 | 1-byte unsigned integer | An index of entry in road_vectors extrablock |
| 1 | **car_behavior** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): unk0<br/>1 (0x1): unk1</details> | Unknown purpose |
### **MedianExtraDataRecord** ###
#### **Size**: 8 bytes ####
#### **Description**: A record of median_polygons extrablock: references a polygon of the block, presumably marking it as a road median. Purpose is not confirmed ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_idx** | 1 | 1-byte unsigned integer | Polygon index |
| 1 | **unk** | 7 | Bytes | Unknown purpose |
### **AnimatedPropPosition** ###
#### **Size**: 4..? bytes ####
#### **Description**: Animation of prop position: a sequence of keyframes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **num_frames** | 2 | 2-bytes unsigned integer (little endian) | An amount of frames |
| 2 | **anim_delay** | 2 | 2-bytes unsigned integer (little endian) | Delay between frames (animation speed). Unit is not confirmed, the converter assumes 1/64 of a second |
| 4 | **frames** | num_frames\*20 | Array of `num_frames` items<br/>Item type: [AnimatedPropPositionFrame](#animatedproppositionframe) | Animation frames, played in a loop |
### **AnimatedPropPositionFrame** ###
#### **Size**: 20 bytes ####
#### **Description**: A single keyframe of animated prop movement ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Object position in 3D space |
| 12 | **orientation** | 8 | Rotation quaternion (x,y,z,w), in the same axes as the positions next to it, where each component is: 16-bit real number (little-endian, signed), where last 14 bits is a fractional part | Object orientation at this keyframe. Prop vertices are rotated by it (v' = q v q^-1), then moved to `position` |
### **SpecialPropPosition** ###
#### **Size**: 16 bytes ####
#### **Description**: Positioning of a special prop ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Object position in 3D space |
| 12 | **special_idx** | 4 | 4-bytes unsigned integer (little endian) | Index of a record in the extrablock of type 11 of the same TRK block. The record repeats the prop position, followed by 8 unknown bytes |
### **PropExtraDataRecord** ###
#### **Size**: 4..? bytes ####
#### **Description**: 3D model placement (prop). Same 3D model can be used few times on the track. Records of props_7 (in TRK blocks and COL file) and props_18 (in TRK blocks) extrablocks have this structure; the 3D model itself is in the prop_descriptions extrablock of the same block/file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 2 | 2-bytes unsigned integer (little endian) | Block size in bytes |
| 2 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1 (0x1): static_prop<br/>3 (0x3): animated_prop<br/>4 (0x4): special_prop</details> | Object type. special_prop is a static prop with a reference to extrablock 11 |
| 3 | **prop_descr_idx** | 1 | 1-byte unsigned integer | An index of 3D model in "prop_descriptions" extrablock |
| 4 | **position** | ? | Type according to enum `type`:<br/>- Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part<br/>- [AnimatedPropPosition](#animatedpropposition)<br/>- [SpecialPropPosition](#specialpropposition)<br/>- Bytes | Object positioning in 3D space: a single point for static_prop, a sequence of keyframes for animated_prop. Block class picked according to `type` |
### **PropDescriptionExtraDataRecord** ###
#### **Size**: 8..? bytes ####
#### **Description**: 3D model of a prop. Placed on the track by records of props_* extrablocks, which reference this model by index ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Block size in bytes |
| 4 | **num_vertices** | 2 | 2-bytes unsigned integer (little endian) | Amount of vertices |
| 6 | **num_polygons** | 2 | 2-bytes unsigned integer (little endian) | Amount of polygons |
| 8 | **vertices** | num_vertices\*6 | Array of `num_vertices` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Vertices, relative to the prop position |
| 8 + num_vertices\*6 | **polygons** | num_polygons\*8 | Array of `num_polygons` items<br/>Item type: [ColPolygon](#colpolygon) | Polygons. Textures are referenced through the textures_map of the COL file, the same way as for terrain polygons |
| 8 + num_vertices\*6 + num_polygons\*8 | **padding** | block_size-local_offset | Bytes | Unused space |
### **LanesExtraDataRecord** ###
#### **Size**: 4 bytes ####
#### **Description**: A lane marker: ties a vertex and a polygon of the block terrain to a position on a lane ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vertex_idx** | 1 | 1-byte unsigned integer | Vertex number (inside background 3D structure : 0 to nv1+nv8) |
| 1 | **track_pos** | 1 | 1-byte unsigned integer | Position along track inside block (0 to 7) |
| 2 | **lat_pos** | 1 | 1-byte unsigned integer | Lateral position ? (constant in each lane), -1 at the end) |
| 3 | **polygon_idx** | 1 | 1-byte unsigned integer | Polygon number (inside full-res background 3D structure : 0 to np1) |
### **RoadVectorsExtraDataRecord** ###
#### **Size**: 12 bytes ####
#### **Description**: Orientation of the road surface: normal + forward vectors pair. Referenced by index from polygon_map records ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part, normalized | A normal vector of the road surface |
| 6 | **forward** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 15 bits is a fractional part, normalized | A forward vector of the road (direction of the track) |
### **CollisionExtraDataRecord** ###
#### **Size**: 36 bytes ####
#### **Description**: A point of the track collision spline (road centre line) with road orientation vectors and distances to the road borders. Used by the physics engine; there are 8 points per track block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | A global position of track collision spline point. The unit is meter |
| 12 | **normal** | 3 | Point in 3D space (x,y,z), where each coordinate is: 8-bit real number (little-endian, signed), where last 7 bits is a fractional part, normalized | A normal vector of road surface |
| 15 | **forward** | 3 | Point in 3D space (x,y,z), where each coordinate is: 8-bit real number (little-endian, signed), where last 7 bits is a fractional part, normalized | A forward vector |
| 18 | **right** | 3 | Point in 3D space (x,y,z), where each coordinate is: 8-bit real number (little-endian, signed), where last 7 bits is a fractional part, normalized | A right vector |
| 21 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 22 | **block_idx** | 2 | 2-bytes unsigned integer (little endian) | Index of the TRK block this point belongs to |
| 24 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 26 | **left_border** | 2 | 16-bit real number (little-endian, not signed), where last 8 bits is a fractional part | Distance to left track border in meters |
| 28 | **right_border** | 2 | 16-bit real number (little-endian, not signed), where last 8 bits is a fractional part | Distance to right track border in meters |
| 30 | **respawn_lat_pos** | 2 | 2-bytes unsigned integer (little endian) | Named by assumption (lateral position of car respawn). Values look like four packed 4-bit numbers, e.g. 0x1111, 0x1144, 0x1244 |
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
