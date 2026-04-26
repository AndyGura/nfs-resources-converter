# **NFS 5 Porsche Unleashed file specs** #

*Last time updated: 2026-04-26 11:02:35.536330+00:00*


# **Info by file extensions** #

**\*.crp** geometry file. [CrpGeometry](#crpgeometry), **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.ENV** image archive. [ShpiBlock](#shpiblock)

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
## **Geometries** ##
### **CrpGeometry** ###
#### **Size**: 16..? bytes ####
#### **Description**: A set of 3D meshes, used for cars and tracks. Currently I parsed all geometries and (possibly) UV-s, materials are not parsed yet. Contains many part blocks, 16-bytes each, splitted into 3 sections: articles, common_parts, parts, followed by raw data. Each part, except articles, have an offset and length of it's data, located in "raw_data" byte array ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. One of ['" raC"', '"karT"'] | Resource ID. " raC" ("Car ") for cars, "karT" for tracks |
| 4 | **header_info** | 4 | 4-bytes unsigned integer (little endian) | Header info: 27 higher bits: number of articles; 5 lower bits: unknown, always seems to be 0x1A |
| 8 | **num_common_parts** | 4 | 4-bytes unsigned integer (little endian) | Number of common parts |
| 12 | **articles_offset** | 4 | 4-bytes unsigned integer (little endian). Always == 0x1 | Offset to articles block / 16 |
| 16 | **articles** | (header_info >> 5)\*16 | Array of `header_info >> 5` items<br/>Item type: [ArticlePart](#articlepart) | Array of articles |
| 16 + (header_info >> 5)\*16 | **common_parts** | num_common_parts\*16 | Array of `num_common_parts` items<br/>Item size: 16 bytes<br/>Item type: One of types:<br/>- [TextPart4](#textpart4)<br/>- [MaterialPart](#materialpart)<br/>- [FSHPart](#fshpart)<br/>- [TextPart2](#textpart2)<br/>- [UnkPart4](#unkpart4)<br/>- [UnkPart2](#unkpart2) | Array of common parts. They are ordered by type (identifier). The order is:<br/>- "PdnB" - ?, cars only<br/>- "nAmC" - camera animations? tracks only<br/>- [TextPart4](#textpart4) "cseD" - seems to be a path to original development source file, tracks only<br/>- "htMR" - ?<br/>- "odnW" - ?, cars only<br/>- "DmiS" - ?, tracks only<br/>- "TmiS" - ?, tracks only<br/>- " siV" - ?, tracks only<br/>- [MaterialPart](#materialpart)<br/>- [FSHPart](#fshpart)<br/>- [TextPart2](#textpart2) "ns" - a path to fsh file with textures, tracks only |
| 16 + (header_info >> 5)\*16 + num_common_parts\*16 | **parts** | (1 + last referenced part index in articles data)\*16 | Array of `1 + last referenced part index in articles data` items<br/>Item size: 16 bytes<br/>Item type: One of types:<br/>- [TextPart4](#textpart4)<br/>- [CullingPart](#cullingpart)<br/>- [TextPart2](#textpart2)<br/>- [EffectPart](#effectpart)<br/>- [NormalPart](#normalpart)<br/>- [TrianglePart](#trianglepart)<br/>- [TransformationPart](#transformationpart)<br/>- [UVPart](#uvpart)<br/>- [VertexPart](#vertexpart)<br/>- [UnkPart4](#unkpart4)<br/>- [UnkPart2](#unkpart2) | Array of parts, ordered by article, for each article it is also ordered by type (identifier):<br/>- "minA" - animations? tracks only<br/>- "tqnA" - ?, tracks only<br/>- [CullingPart](#cullingpart) - ?, cars only<br/>- "esaB" - ?<br/>- [TextPart4](#textpart4) "emaN" - name of the mesh<br/>- "fd" - ?, tracks only<br/>- [EffectPart](#effectpart) - ?<br/>- "zd" - ?, cars only<br/>- [NormalPart](#normalpart) - ?, cars only<br/>- [TrianglePart](#trianglepart) - mesh indexes (faces)<br/>- [TransformationPart](#transformationpart) - position/rotation of the mesh<br/>- [UVPart](#uvpart) - vertex UV-s<br/>- [VertexPart](#vertexpart) - vertices |
| 16 + (header_info >> 5)\*16 + num_common_parts\*16 + (1 + last referenced part index in articles data)\*16 | **raw_data** | up to end of block | Bytes | Raw data region, where part data is stored. Part data offset and lengthes are stored in the PartBlock. |
### **ArticlePart** ###
#### **Size**: 16 bytes ####
#### **Description**: Article is a single logical part of a car or track. Contains meshes of the same entity for various levels of details, damage status, animation indexes etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "itrA" | Resource ID |
| 4 | **header_info** | 4 | 4-bytes unsigned integer (little endian). Always == 0x1a | Unknown purpose |
| 8 | **num_parts** | 4 | 4-bytes unsigned integer (little endian) | An amount of parts, linked to this article |
| 12 | **local_offset** | 4 | 4-bytes unsigned integer (little endian) | A local offset from the beginning of this article to the first linked part, divided by 16. So the first part index in parts array for this article is: local_offset + this article index - len(articles) - len(common_parts) |
### **TextPart2** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to text with index and 2-chars identifier ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **idx** | 2 | 2-bytes unsigned integer (little endian) | A part index of the same identifier (in the same article) |
| 2 | **identifier** | 2 | UTF-8 string. Always == "ns" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes, equals to `text length + 1` (0x00 terminating byte) |
| 8 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **TextPart4** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to text with 4-chars identifier ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **identifier** | 4 | UTF-8 string. One of ['"emaN"', '"cseD"'] | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes, equals to `text length + 1` (0x00 terminating byte) |
| 8 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **MaterialPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to [MaterialPartData](#materialpartdata) block ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **idx** | 2 | 2-bytes unsigned integer (little endian) | A part index of the same identifier |
| 2 | **identifier** | 2 | UTF-8 string. Always == "tm" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **FSHPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to an array of [ShpiBlock](#shpiblock) blocks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **idx** | 2 | 2-bytes unsigned integer (little endian) | A part index of the same identifier |
| 2 | **identifier** | 2 | UTF-8 string. Always == "fs" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **num_data** | 4 | 4-bytes unsigned integer (little endian) | Number of SHPI blocks |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **CullingPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to an array of [CullingPartData](#cullingpartdata) blocks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "damage"<br/>8-bits int "animation_index"<br/>4-bits int "lod" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "n$" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **num_data** | 4 | 4-bytes unsigned integer (little endian) | Number of culling part data blocks |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **EffectPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to an array of [EffectPartData](#effectpartdata) blocks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "damage"<br/>8-bits int "animation_index"<br/>4-bits int "lod" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "fe" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **NormalPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to an array of [NormalPartData](#normalpartdata) blocks, describing mesh normals ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "damage"<br/>8-bits int "animation_index"<br/>4-bits int "lod" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "mn" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **num_data** | 4 | 4-bytes unsigned integer (little endian) | Number of normals |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **TrianglePart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to [TrianglePartData](#TrianglePartData) block, describes mesh faces ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "lod"<br/>8-bits int "unk"<br/>4-bits int "part_index" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "rp" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **num_data** | 4 | 4-bytes unsigned integer (little endian) | Number of indices |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **TransformationPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to a transformation matrix. If exists, matrix should be applied to the mesh. Matrix is a 4x4 matrix in row-major order, where each number is stored as 4-bytes float number (little-endian). ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "damage"<br/>8-bits int "animation_index"<br/>4-bits int "lod" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "rt" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian). Always == 0x40 | Data length in bytes |
| 8 | **unk_1** | 4 | 4-bytes unsigned integer (little endian) | Always 1? Number of Transformation Matrices? |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **UVPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to an array of [UVData](#uvdata) blocks, representing texture coordinates ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "damage"<br/>8-bits int "animation_index"<br/>4-bits int "lod" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "vu" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **num_data** | 4 | 4-bytes unsigned integer (little endian) | Amount of UVData blocks, equals to len / 8 |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **VertexPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to an array of [VertexData](#vertexdata) blocks, representing mesh vertices ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **part_info** | 2 | Sub-byte compound block (little endian):<br/>4-bits int "damage"<br/>8-bits int "animation_index"<br/>4-bits int "lod" | Part matching info. Part should be used with others that have same values |
| 2 | **identifier** | 2 | UTF-8 string. Always == "tv" | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **num_vertices** | 4 | 4-bytes unsigned integer (little endian) | Number of vertices |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **UnkPart2** ###
#### **Size**: 16 bytes ####
#### **Description**: Unknown part with index and 2-chars identifier ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **idx** | 2 | 2-bytes unsigned integer (little endian) | A part index of the same identifier (in the same article) |
| 2 | **identifier** | 2 | UTF-8 string. One of ['"zd"', '"ns"', '"fd"'] | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **UnkPart4** ###
#### **Size**: 16 bytes ####
#### **Description**: Unknown part with 4-chars identifier ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **identifier** | 4 | UTF-8 string. One of ['"esaB"', '"PdnB"', '"htMR"', '"odnW"', '"nAmC"', '"cseD"', '"DmiS"', '"TmiS"', '" siV"', '""', '"minA"', '"tqnA"'] | Identifier |
| 4 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 5 | **len** | 3 | 3-bytes unsigned integer (little endian) | Data length in bytes |
| 8 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **MaterialPartData** ###
#### **Size**: 312 bytes ####
#### **Description**: A material, data structure is mostly unknown ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 16 | Bytes | Unknown purpose |
| 16 | **desc** | 16 | UTF-8 string | Description |
| 32 | **unk1** | 8 | Bytes | Unknown purpose |
| 40 | **tex_page_index** | 4 | 4-bytes unsigned integer (little endian) | Texture page index |
| 44 | **unk2** | 268 | Bytes | Unknown purpose |
### **CullingPartData** ###
#### **Size**: 16 bytes ####
#### **Description**: Polygon culling rule? ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | - |
| 12 | **threshold** | 4 | Float number (little-endian) | - |
### **CullingInfoRow** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in culling data |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length of culling data used |
| 10 | **identifier** | 2 | UTF-8 string | Identifier ("n$") |
| 12 | **level_index** | 2 | 2-bytes unsigned integer (little endian) | Level index |
| 14 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
### **EffectPartData** ###
#### **Size**: 88 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position |
| 20 | **unk_scale** | 4 | Float number (little-endian) | Unknown purpose |
| 24 | **width** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Width relative to position |
| 36 | **unk2** | 4 | Float number (little-endian) | Unknown purpose |
| 40 | **height** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Height relative to position |
| 52 | **unk3** | 4 | Float number (little-endian) | Unknown purpose |
| 56 | **depth** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Depth relative to position |
| 68 | **unk4** | 4 | Float number (little-endian) | Unknown purpose |
| 72 | **glow_color** | 4 | 4-bytes unsigned integer (little endian) | Color of glow (BGRA) |
| 76 | **source_color** | 4 | 4-bytes unsigned integer (little endian) | Color of source (BGRA) |
| 80 | **mirror** | 4 | 4-bytes unsigned integer (little endian) | Mirror |
| 84 | **info** | 4 | 4-bytes unsigned integer (little endian) | Information |
### **NormalPartData** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Normal vector |
| 12 | **unk** | 4 | Float number (little-endian) | Unknown purpose |
### **NormalInfoRow** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in normal data |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length of normal data used |
| 10 | **unk1** | 2 | Bytes | Unknown purpose |
| 12 | **level_index** | 2 | 2-bytes unsigned integer (little endian) | Level index |
| 14 | **unk2** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
### **TrianglePartData** ###
#### **Size**: 48..? bytes ####
#### **Description**: A description of mesh geometry (faces) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Info flags |
| 4 | **material_index** | 2 | 2-bytes unsigned integer (little endian) | Material index |
| 6 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **unk_floats** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Unknown purpose |
| 24 | **unk_zeros** | 16 | Bytes | Unknown purpose |
| 40 | **num_info_rows** | 4 | 4-bytes unsigned integer (little endian) | Number of info rows |
| 44 | **num_index_rows** | 4 | 4-bytes unsigned integer (little endian) | Number of index rows |
| 48 | **info_rows** | num_info_rows\*16 | Array of `num_info_rows` items<br/>Item size: 16 bytes<br/>Item type: One of types:<br/>- [CullingInfoRow](#cullinginforow)<br/>- [NormalInfoRow](#normalinforow)<br/>- [UVInfoRow](#uvinforow)<br/>- [VertexInfoRow](#vertexinforow) | - |
| 48 + num_info_rows\*16 | **index_rows** | num_index_rows\*8 | Array of `num_index_rows` items<br/>Item type: [IndexRow](#indexrow) | - |
| 48 + num_info_rows\*16 + num_index_rows\*8 | **index_table** | ^num_data | Array of `^num_data` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Vertex index table |
| 48 + num_info_rows\*16 + num_index_rows\*8 + ^num_data | **uv_index_table** | ^num_data | Array of `^num_data` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | UV index table |
### **TriangleInfoRowBase** ###
#### **Size**: 10 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in data |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length used |
### **IndexRow** ###
#### **Size**: 8 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **idx** | 2 | 2-bytes unsigned integer (little endian) | Row index |
| 2 | **identifier** | 2 | UTF-8 string | Identifier "vI"|"Iv" – vertex index, "uI"|"Iu" - uv index |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of indices |
### **UVData** ###
#### **Size**: 8 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **u** | 4 | Float number (little-endian) | - |
| 4 | **v** | 4 | Float number (little-endian) | - |
### **UVInfoRow** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in uv data |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length of uv data used |
| 10 | **unk1** | 2 | Bytes | Unknown purpose |
| 12 | **level_index** | 2 | 2-bytes unsigned integer (little endian) | Level index |
| 14 | **unk2** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
### **VertexData** ###
#### **Size**: 16 bytes ####
#### **Description**: Represents single vertex ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position |
| 12 | **unk** | 4 | Float number (little-endian) | Unknown purpose |
### **VertexInfoRow** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in vertex data |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length of vertex data used |
| 10 | **unk1** | 2 | Bytes | Unknown purpose |
| 12 | **level_index** | 2 | 2-bytes unsigned integer (little endian) | Level index |
| 14 | **unk2** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
## **Images** ##
### **EacImage** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>109 (0x6d): 16Bit_4444 color format bitmap<br/>120 (0x78): 16Bit_0565 color format bitmap<br/>121 (0x79): 4Bit (swapped)<br/>122 (0x7a): 4Bit<br/>123 (0x7b): 8Bit<br/>125 (0x7d): 32Bit color format bitmap<br/>126 (0x7e): 16Bit_1555 color format bitmap<br/>127 (0x7f): 24Bit color format bitmap</details> | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+<color_bytes_amount>\*width\*height + trailing bytes length |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unk** | 2 | Bytes | Unknown purpose |
| 10 | **pivot_y** | 2 | 2-bytes unsigned integer (little endian) | For "horz" bitmap in TNFS FAM files: Y coordinate of the horizon line on the image. Higher value = image as horizon will be put higher on the screen. Seems to affect only open tracks |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | ? | Type according to enum `resource_id`:<br/>- Array of `width*height` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `width*height` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `height` items<br/>Item size: ceil((^width)\*4/8) bytes<br/>Item type: Array of `^width` sub-byte numbers. Each number consists of 4 bits<br/>- Array of `height` items<br/>Item size: ceil((^width)\*4/8) bytes<br/>Item type: Array of `^width` sub-byte numbers. Each number consists of 4 bits<br/>- Array of `width*height` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer<br/>- Array of `width*height` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `width*height` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (little endian)<br/>- Array of `width*height` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Pixel color table. For 8Bit bitmap each value represents an index of color in the attached palette. Palette can be stored: <br/>- right after 8Bit image<br/>- as !pal/!PAL in the same SHPI<br/>- in a different SHPI before this one (if it is WWWW archive)<br/>- even in different QFS file (TNFS, CONTROL directory).<br/>Color model is selected according to `resource_id` field. Color models are described [here](eac_colors.md) |
### **EacPalette** ###
#### **Size**: 16..? bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette. Has special colors: 255th in most cases means transparent color, 254th in car textures is replaced by tail light color, 250th - 253th in car textures are rendered black: thy are reserved for cop car siren ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>34 (0x22): 24BitDos color format palette<br/>36 (0x24): 24Bit color format palette<br/>41 (0x29): 16BitUnk color format palette<br/>42 (0x2a): 32Bit color format palette<br/>45 (0x2d): 16Bit_0565 color format palette</details> | Resource ID |
| 1 | **unk0** | 3 | Bytes | Unknown purpose |
| 4 | **num_colors** | 2 | 2-bytes unsigned integer (little endian) | Amount of colors |
| 6 | **unk1** | 2 | Bytes | Unknown purpose |
| 8 | **num_colors1** | 2 | 2-bytes unsigned integer (little endian) | Always equals to num_colors? |
| 10 | **unk2** | 6 | Bytes | Unknown purpose |
| 16 | **colors** | ? | Type according to enum `resource_id`:<br/>- Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (big endian)<br/>- Array of `num_colors` items<br/>Item size: 3 bytes<br/>Item type: 3-bytes unsigned integer (big endian)<br/>- Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian)<br/>- Array of `num_colors` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian)<br/>- Array of `num_colors` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Colors LUT. Color model is selected according to `resource_id` field. Color models are described [here](eac_colors.md) |
