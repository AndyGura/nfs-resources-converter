# **NFS 5 Porsche Unleashed file specs** #

*Last time updated: 2026-10-08 21:41:48.050767+00:00*


# **Info by file extensions** #

**\*.BNK** sound bank. [EaSoundBank](#easoundbank)

**\*.crp** geometry file. [CrpGeometry](#crpgeometry), [compressed](eac_compressions.md)
        
**\*.FFN** bitmap font. [FfnFont](#ffnfont)

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
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | The length of this BIGF block in bytes. NFS6 stores the length without padding between items: header plus item lengths |
| 8 | **num_items** | 4 | 4-bytes unsigned integer (big endian) | An amount of items |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **items_descr** | num_items\*9..? | Array of `num_items` items<br/>Item type: [BigfItemDescriptionBlock](#bigfitemdescriptionblock) | Descriptions of items: offset, length and name of each of them |
| 16 + num_items\*9..? | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets and lengths are defined in previous block. Possible item types:<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file<br/>- [BigfBlock](#bigfblock)<br/>- [EaSoundBank](#easoundbank)<br/>- pure TGA image |
### **BigfItemDescriptionBlock** ###
#### **Size**: 9..? bytes ####
#### **Description**: Description of a single item of BIGF archive ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **offset** | 4 | 4-bytes unsigned integer (big endian) | Offset of item data, relative to BIGF block start |
| 4 | **length** | 4 | 4-bytes unsigned integer (big endian) | Length of item data in bytes |
| 8 | **name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | Item name (file name). Used as file name when the archive is unpacked |
### **EaSoundBank** ###
#### **Size**: 12..? bytes ####
#### **Description**: EA sound bank "BNKl" (*.BNK of NFS2, NFS2 SE, NFS3, NFS4, NFS5, NFS6): a table of sound patches, then their wave data. Car banks (NFS2 `<car>.BNK` / `O<car>.BNK` (opponent) / `S<car>.BNK`, NFS3 `car.bnk` / `ocar.bnk` / `scar.bnk` in car.viv, NFS4 `careng.bnk` / `ocareng.bnk` / `scareng.bnk`, NFS3/NFS4 `GENCAR.BNK`, traffic `TRUCK.BNK`...) use indices 0 and 1 for the engine (looped), 2 for a one-shot with random detune range 200-250 (gear shift, like `gear` of TNFS car banks) and 3 for the horn (looped). Opponent banks have the engine and the horn only: NFS2 `O<car>.BNK` in slots 0 and 1 of a 2-slot table, NFS3 `ocar.bnk` / NFS4 `ocareng.bnk` in slots 0 and 3. NFS4 `careng.bnk` has more engine samples at higher indices (presumably one per RPM range). `W*.BNK` of NFS2 SE are car speech ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "BNKl" | Resource ID |
| 4 | **version** | 2 | 2-bytes unsigned integer (little endian) | 2 (NFS2, NFS2 SE, most of NFS3 GameData/Audio/SFX), 4 (NFS3 car.viv, NFS4, NFS5, NFS6) or 5 (NFS6) |
| 6 | **num_items** | 2 | 2-bytes unsigned integer (little endian) | Amount of slots in `items_descr` |
| 8 | **header_length** | 4 | 4-bytes unsigned integer (little endian) | Version 2 and 4: offset of the wave data, i.e. the length of the table and the patches. Version 5: file length |
| 12 | **wave_data_length** | 0..4 | Optional (if version >= 4): 4-bytes unsigned integer (little endian) | Version 4: length of the wave data. Version 5: 0 |
| 12..16 | **unk0** | 0..4 | Optional (if version >= 4): 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12..20 | **items_descr** | num_items\*4 | Array of `num_items` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offset of every patch, relative to its own position in this table, the array index being the sample index used by the game. 0 is an empty slot |
| 12 + num_items\*4..20 + num_items\*4 | **data_bytes** | up to end of block | Bytes | Sound patches ([EaSoundPatch](#easoundpatch)) at the offsets of `items_descr`, then wave data |
## **Geometries** ##
### **CrpGeometry** ###
#### **Size**: 16..? bytes ####
#### **Description**: A set of 3D meshes, used for cars and tracks. Materials are parsed only partially. Contains many part blocks, 16-bytes each, splitted into 3 sections: articles, common_parts, parts, followed by raw data. Each part, except articles, have an offset and length of it's data, located in "raw_data" byte array. The converter builds one mesh per vertex part and texture of each article, named `<article name>_LOD<lod>_ai<animation index>_<texture>`, using triangle, UV and transformation parts of the article with the same LOD. Car textures: every FSH part is composed into a texture page (images are placed by their atlas position), material references the page by index; mapping of FSH parts to pages is described in car's .tpg file. Track textures: material references the texture by 4-char name in the FSH file, which name is stored in TextPart2 "ns" ####
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
| 8 | **num_data** | 4 | 4-bytes unsigned integer (little endian) | Number of indices (size of each index table in the data) |
| 12 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Data offset (Relative from current block offset) |
### **TransformationPart** ###
#### **Size**: 16 bytes ####
#### **Description**: A part referencing to a transformation matrix. If exists, matrix should be applied to the meshes of the same article with the same LOD. Matrix is a 4x4 matrix in column-major order (elements 12, 13, 14 are the translation), where each number is stored as 4-bytes float number (little-endian). ####
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
#### **Description**: A part referencing to an array of [VertexData](#vertexdata) blocks, representing mesh vertices. Every vertex part of an article produces a separate mesh, combined with the triangle, UV and transformation parts of the same LOD. For a damaged part (damage == 8) vertex positions are offsets, which are added to vertices of the undamaged part with the same LOD and animation index ####
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
#### **Description**: A material, data structure is mostly unknown. Triangle parts reference it by index (`idx` of [MaterialPart](#materialpart)) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 16 | Bytes | Unknown purpose |
| 16 | **desc** | 16 | UTF-8 string | Description |
| 32 | **unk1** | 8 | Bytes | Unknown purpose |
| 40 | **tex_page_index** | 4 | 4-bytes unsigned integer (little endian) | Texture reference. Cars: 0-based texture page index (page N+1 in car's .tpg file, embedded FSH part with `idx` M is .tpg file M+1). Tracks: 4-char name of the texture in track's FSH file, stored as integer |
| 44 | **unk2** | 268 | Bytes | Unknown purpose |
### **CullingPartData** ###
#### **Size**: 16 bytes ####
#### **Description**: Polygon culling rule? ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Normalized direction vector (plane normal?) |
| 12 | **threshold** | 4 | Float number (little-endian) | Threshold value (plane distance?) |
### **CullingInfoRow** ###
#### **Size**: 16 bytes ####
#### **Description**: Info row referencing the culling data used by the triangle part ####
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
#### **Description**: Info row referencing the normals data used by the triangle part ####
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
#### **Description**: A description of mesh geometry (faces): a triangle list. Every 3 consecutive values of the vertex index table (starting from the offset of the first index row) form a triangle; UV index table maps the same positions to UV-s ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Info flags |
| 4 | **material_index** | 2 | 2-bytes unsigned integer (little endian) | Material index |
| 6 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **unk_floats** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Unknown purpose |
| 24 | **unk_zeros** | 16 | Bytes | Unknown purpose |
| 40 | **num_info_rows** | 4 | 4-bytes unsigned integer (little endian) | Number of info rows |
| 44 | **num_index_rows** | 4 | 4-bytes unsigned integer (little endian) | Number of index rows |
| 48 | **info_rows** | num_info_rows\*16 | Array of `num_info_rows` items<br/>Item size: 16 bytes<br/>Item type: One of types:<br/>- [CullingInfoRow](#cullinginforow)<br/>- [NormalInfoRow](#normalinforow)<br/>- [UVInfoRow](#uvinforow)<br/>- [VertexInfoRow](#vertexinforow) | Descriptors of the data streams used by this part. When there are 4 rows, they are culling, normal, UV and vertex rows; when 3 - normal, UV and vertex rows |
| 48 + num_info_rows\*16 | **index_rows** | num_index_rows\*8 | Array of `num_index_rows` items<br/>Item type: [IndexRow](#indexrow) | Descriptors of the index streams: vertex indices and UV indices |
| 48 + num_info_rows\*16 + num_index_rows\*8 | **index_table** | ^num_data | Array of `^num_data` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Vertex index table. Every 3 consecutive values form a triangle |
| 48 + num_info_rows\*16 + num_index_rows\*8 + ^num_data | **uv_index_table** | ^num_data | Array of `^num_data` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | UV index table: for every position of the vertex index table, index of UV-s in the UV part of the same LOD |
### **TriangleInfoRowBase** ###
#### **Size**: 10 bytes ####
#### **Description**: Common prefix of the info rows of [TrianglePartData](#trianglepartdata) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in data |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length used |
### **IndexRow** ###
#### **Size**: 8 bytes ####
#### **Description**: Descriptor of an index stream (vertex indices or UV indices) of the triangle part ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **idx** | 2 | 2-bytes unsigned integer (little endian) | Row index |
| 2 | **identifier** | 2 | UTF-8 string | Identifier "vI"|"Iv" – vertex index, "uI"|"Iu" - uv index |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of indices: the position of the first index of this stream in the index tables |
### **UVData** ###
#### **Size**: 8 bytes ####
#### **Description**: Texture coordinates of a vertex ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 4 | **v** | 4 | Float number (little-endian) | V texture coordinate |
### **UVInfoRow** ###
#### **Size**: 16 bytes ####
#### **Description**: Info row referencing the UV data used by the triangle part ####
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
#### **Description**: Info row referencing the vertex data used by the triangle part ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset in vertex data in bytes. offset / 16 is the index of the first vertex used by the part; it is added to all values of the vertex index table |
| 8 | **length_used** | 2 | 2-bytes unsigned integer (little endian) | Length of vertex data used |
| 10 | **unk1** | 2 | Bytes | Unknown purpose |
| 12 | **level_index** | 2 | 2-bytes unsigned integer (little endian) | Level index |
| 14 | **unk2** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
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
## **Audio** ##
### **EaSoundPatch** ###
#### **Size**: 4..? bytes ####
#### **Description**: EA sound patch ("PT" header): a sound of a BNKl sound bank as a list of tags. Tags before `info_start` are playback settings (priority, volume, pan, pitch bend range...), tags after it describe the wave data: `num_samples`, `channels` (default 1), `sampling_rate` (default 22050), loop sample indices `loop_start` and `loop_end` (inclusive; a sample loops when it has one of them, from 0 / up to the last sample when the other one is missing), `data_offset` (wave data offset from the start of the bank file) and the codec. Without the `version` tag, `codec` 7 is EA-XA ADPCM v1, 9 is EA MicroTalk 10:1 (speech), no `codec` tag is 16-bit little endian PCM. With `version` 1, `codec_2` 8 is 16-bit little endian PCM, 9 is signed 8-bit PCM, no `codec_2` tag is EA-XA ADPCM v2. Stereo samples are interleaved. A sound can have several layers, played together, separated by the `layer_end` tag, each one with its own settings and wave data (NFS3 player car engines add a short mono loop to the stereo engine sample) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **platform_magic** | 2 | UTF-8 string. Always == "PT" | Patch header magic |
| 2 | **platform** | 2 | 2-bytes unsigned integer (little endian) | Platform id, 0 is PC |
| 4 | **tags** | up to and including tag "end"..? | Array of `up to and including tag "end"` items<br/>Item type: [EaSoundPatchTag](#easoundpatchtag) | Tags |
### **EaSoundPatchTag** ###
#### **Size**: 1..? bytes ####
#### **Description**: A tag of EA sound patch: tag id, then (except for tags 0xFC-0xFF) the length of the value and the value, big endian unsigned. Tag meanings follow [vgmstream](https://github.com/vgmstream/vgmstream) (`ea_schl.c`), the ones named `unk_*` are not known ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **tag** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>6 (0x6): priority<br/>7 (0x7): unk_0x07<br/>8 (0x8): release_envelope<br/>9 (0x9): playback_envelope<br/>10 (0xa): bend_range_semitones<br/>11 (0xb): bank_channels<br/>12 (0xc): pan<br/>13 (0xd): random_pan_range<br/>14 (0xe): volume<br/>15 (0xf): random_volume_range<br/>16 (0x10): detune<br/>17 (0x11): random_detune_range<br/>18 (0x12): unk_0x12<br/>19 (0x13): effect_bus<br/>128 (0x80): version<br/>130 (0x82): channels<br/>131 (0x83): codec<br/>132 (0x84): sampling_rate<br/>133 (0x85): num_samples<br/>134 (0x86): loop_start<br/>135 (0x87): loop_end<br/>136 (0x88): data_offset<br/>137 (0x89): data_offset_channel_2<br/>138 (0x8a): unk_0x8a<br/>139 (0x8b): unk_0x8b<br/>140 (0x8c): flags<br/>145 (0x91): unk_0x91<br/>146 (0x92): unk_0x92<br/>147 (0x93): unk_0x93<br/>160 (0xa0): codec_2<br/>252 (0xfc): padding<br/>253 (0xfd): info_start<br/>254 (0xfe): layer_end<br/>255 (0xff): end</details> | Tag id |
| 1 | **value_length** | 0..1 | Optional (if tag is not padding, info_start, layer_end or end): 1-byte unsigned integer | Length of value in bytes. 0 means value 0 |
| 1..2 | **value** | 0..value_length | Optional (if tag is not padding, info_start, layer_end or end): Bytes | Value, big endian unsigned integer |
