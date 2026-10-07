# **NFS Most Wanted (2005) file specs** #

*Last time updated: 2026-10-07 00:35:04.760762+00:00*


# **Info by file extensions** #

**CARS/\*/GEOMETRY.BIN** car geometry. [NfsuBinGeometry](#nfsubingeometry)

**CARS/\*/TEXTURES.BIN**, **CARS/TEXTURES.BIN** car texture packs, every texture compressed separately (JDLZ or HUFF). [NfsuChunkBundle](#nfsuchunkbundle)

**TRACKS/L2RA.BUN** location bundle (Rockport): streaming sections table and textures shared by the city. Opened in the track viewer together with the city sections from **TRACKS/STREAML2RA.BUN** next to it. [NfsuTrackBundle](#nfsutrackbundle)

**TRACKS/STREAML2RA.BUN** streamed city sections (scenery, geometry, textures), each 0x800-aligned. [NfsuChunkBundle](#nfsuchunkbundle)

**GLOBAL/GLOBALB.BUN** global textures (chrome, grilles, ...) and other data. [NfsuChunkBundle](#nfsuchunkbundle)

**GLOBAL/\*.BUN**, **GLOBAL/\*.BIN** texture packs and other chunk bundles. [NfsuChunkBundle](#nfsuchunkbundle)

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #
## **Maps** ##
### **NfsuTrackBundle** ###
#### **Size**: 0..? bytes ####
#### **Description**: Race bundle (NFSU TRACKS/TRACKBnnnn.lzc, uncompressed) or location bundle (NFSU2 TRACKS/L4RA.BUN, NFSMW TRACKS/L2RA.BUN): a chunk bundle with the streaming sections table of the world, which is stored in TRACKS/STREAM*.BUN. Chunk bundle (*.BUN, *.BIN, uncompressed *.lzc): a sequence of chunks, each having 32-bit id, 32-bit payload length and payload; chunks with the highest bit of id set are containers of other chunks. Geometry packs, texture packs, scenery and streaming sections table are decoded, other chunks are kept as raw bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunks** | until the end of file\*8..? | Array of `until the end of file` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuBinGeometry](#nfsubingeometry)<br/>- [NfsuTexturePack](#nfsutexturepack)<br/>- [NfsmwScenery](#nfsmwscenery)<br/>- [NfsmwStreamingSections](#nfsmwstreamingsections)<br/>- [UnknownChunk](#unknownchunk) | Chunks |
### **NfsuChunkBundle** ###
#### **Size**: 0..? bytes ####
#### **Description**: Chunk bundle (*.BUN, *.BIN, uncompressed *.lzc): a sequence of chunks, each having 32-bit id, 32-bit payload length and payload; chunks with the highest bit of id set are containers of other chunks. Geometry packs, texture packs, scenery and streaming sections table are decoded, other chunks are kept as raw bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunks** | until the end of file\*8..? | Array of `until the end of file` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuBinGeometry](#nfsubingeometry)<br/>- [NfsuTexturePack](#nfsutexturepack)<br/>- [NfsmwScenery](#nfsmwscenery)<br/>- [NfsmwStreamingSections](#nfsmwstreamingsections)<br/>- [UnknownChunk](#unknownchunk) | Chunks |
### **NfsmwStreamingSections** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW table of streamed sections: where the world sections of the location lie in the STREAM*.BUN file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34110 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sections** | (chunk_length/92)\*92 | Array of `chunk_length/92` items<br/>Item type: [NfsmwStreamingSection](#nfsmwstreamingsection) | Sections |
### **NfsmwStreamingSection** ###
#### **Size**: 92 bytes ####
#### **Description**: NFSMW: location of a streamed section in the STREAM*.BUN file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 8 | UTF-8 string | Section name, e.g. "T26" |
| 8 | **number** | 4 | 4-bytes unsigned integer (little endian) | Section number: letter index (A = 1) * 100 + number |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Always 1 |
| 20 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of the section in the stream file |
| 24 | **size** | 4 | 4-bytes unsigned integer (little endian) | Size of the section in the stream file, without padding to 2048 bytes |
| 28 | **size2** | 4 | 4-bytes unsigned integer (little endian) | Always equals to `size` |
| 32 | **size3** | 4 | 4-bytes unsigned integer (little endian) | Equals to `size` unless the section has textures, then smaller |
| 36 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Section number + 2000, 4000 ... 22000 (10, 20, 30 for X0, Z0, Y0) |
| 40 | **center** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Presumably the center of the section (X, Y) in world coordinates |
| 48 | **radius** | 4 | Float number (little-endian) | Presumably radius of the section |
| 52 | **hash** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 56 | **unk3** | 36 | Bytes | Unknown purpose |
### **NfsmwScenery** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW scenery of a section: object definitions (named, 4 mesh ids) and their placements in the world. Told apart from NFSU and NFSU2 scenery by the definitions: every one starts with a 24-byte name ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80034100 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | until the end of chunk\*8..? | Array of `until the end of chunk` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuScenerySectionHeader](#nfsuscenerysectionheader)<br/>- [NfsmwSceneryInfos](#nfsmwsceneryinfos)<br/>- [NfsmwSceneryInstances](#nfsmwsceneryinstances)<br/>- [ZeroChunk](#zerochunk)<br/>- [UnknownChunk](#unknownchunk) | Header, instances, definitions and unknown chunks 0x00034105, 0x00034106, 0x00034107 |
### **NfsuScenerySectionHeader** ###
#### **Size**: 68..? bytes ####
#### **Description**: Scenery header: number of the section it belongs to ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34101 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **unk0** | 12 | Bytes | Unknown purpose |
| 20 + up to 16-bytes alignment | **section_number** | 4 | 4-bytes unsigned integer (little endian) | Number of the section: letter index (A = 1) * 100 + number, e.g. 2617 for "Z17". Matches `number` in the streaming sections table (without its 0x10000 flag) |
| 24 + up to 16-bytes alignment | **unk1** | 44 | Bytes | Unknown purpose |
### **NfsmwSceneryInfos** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW scenery object definitions ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34102 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **infos** | (chunk_length/72)\*72 | Array of `chunk_length/72` items<br/>Item type: [NfsmwSceneryInfo](#nfsmwsceneryinfo) | Definitions |
### **NfsmwSceneryInfo** ###
#### **Size**: 72 bytes ####
#### **Description**: NFSMW scenery object definition: which mesh to draw ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 24 | UTF-8 string | Object name, e.g. "XO_StreetLightCb_1b_00" |
| 24 | **mesh_ids** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Mesh ids (hashes of mesh names, `mesh_id` of mesh header chunks). The first one is the main mesh, others are probably levels of detail |
| 40 | **model_pointers** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Filled by the game in runtime |
| 56 | **radius** | 4 | Float number (little-endian) | Bounding sphere radius |
| 60 | **mesh_checksum** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 64 | **hierarchy_name_hash** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 68 | **hierarchy_pointer** | 4 | 4-bytes unsigned integer (little endian) | Filled by the game in runtime |
### **NfsmwSceneryInstances** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW placed scenery objects ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34103 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **instances** | custom_func\*64 | Array of `custom_func` items<br/>Item type: [NfsmwSceneryInstance](#nfsmwsceneryinstance) | Instances |
### **NfsmwSceneryInstance** ###
#### **Size**: 64 bytes ####
#### **Description**: NFSMW placed scenery object ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **bounding_box_min** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Minimum corner of the bounding box in world coordinates |
| 12 | **bounding_box_max** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Maximum corner of the bounding box in world coordinates |
| 24 | **exclude_flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **preculler_info_index** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 30 | **lighting_context_number** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 32 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position in world coordinates |
| 44 | **rotation** | 18 | Array of `9` items<br/>Item size: 2 bytes<br/>Item type: 16-bit real number (little-endian, signed), where last 13 bits is a fractional part | Rotation and scale matrix 3x3, row by row. World position of a mesh vertex v is v.x * row0 + v.y * row1 + v.z * row2 + position |
| 62 | **info_index** | 2 | 2-bytes unsigned integer (little endian) | Index of the object definition in this scenery |
## **Images** ##
### **NfsuTexturePack** ###
#### **Size**: 8..? bytes ####
#### **Description**: Texture pack (TPK): a container of texture infos and their pixel data. Standalone in car TEXTURES.BIN and TRACKS/TEXnnnnTRACK.BIN, embedded in track bundles ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb3300000 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | until the end of chunk\*8..? | Array of `until the end of chunk` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuTexturePackInfo](#nfsutexturepackinfo)<br/>- [NfsuTexturePackDataContainer](#nfsutexturepackdatacontainer)<br/>- [ZeroChunk](#zerochunk)<br/>- [UnknownChunk](#unknownchunk) | Child chunks |
### **NfsuTexturePackHeader** ###
#### **Size**: 132 bytes ####
#### **Description**: Texture pack header: name and original file path ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x33310001 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian). Always == 0x7c | - |
| 8 | **version** | 4 | 4-bytes unsigned integer (little endian) | Texture pack version, 4 in NFSU, 5 in NFSU2 |
| 12 | **name** | 28 | UTF-8 string | Texture pack name, e.g. "TRACK" |
| 40 | **file_path** | 64 | UTF-8 string | Path of the texture pack in the original development environment |
| 104 | **hash** | 4 | 4-bytes unsigned integer (little endian) | Hash of the texture pack name |
| 108 | **unk** | 24 | Bytes | Unknown purpose |
### **NfsuTextureHashes** ###
#### **Size**: 8..? bytes ####
#### **Description**: Hashes of texture names, one per texture ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x33310002 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **hashes** | (chunk_length/8)\*8 | Array of `chunk_length/8` items<br/>Item size: 8 bytes<br/>Item type: Array of `2` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Texture name hash and zero, per texture |
### **NfsuCompressedTextures** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSU2 compressed texture pack: locations of textures, one per texture. Every texture is compressed separately (JDLZ or HUFF) and holds its image data, followed by its texture info (124 bytes) and pixel format (32 bytes). Such a pack has no texture infos and formats chunks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x33310003 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **textures** | (chunk_length/24)\*24 | Array of `chunk_length/24` items<br/>Item type: [NfsuCompressedTexture](#nfsucompressedtexture) | Compressed textures |
### **NfsuCompressedTexture** ###
#### **Size**: 24 bytes ####
#### **Description**: Location of a compressed texture in the texture pack file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name_hash** | 4 | 4-bytes unsigned integer (little endian) | Hash of the texture name |
| 4 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of the compressed texture in the file (absolute: the first one is the start of texture data chunk payload) |
| 8 | **compressed_size** | 4 | 4-bytes unsigned integer (little endian) | Size of the compressed texture |
| 12 | **size** | 4 | 4-bytes unsigned integer (little endian) | Size of the uncompressed texture |
| 16 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 20 | **unk** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **NfsuTextureInfos** ###
#### **Size**: 8..? bytes ####
#### **Description**: Texture infos, one per texture ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x33310004 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **textures** | (chunk_length/124)\*124 | Array of `chunk_length/124` items<br/>Item type: [NfsuTextureInfo](#nfsutextureinfo) | Texture infos |
### **NfsuTextureInfo** ###
#### **Size**: 124 bytes ####
#### **Description**: Texture info: name, size, format and location of its data ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 12 | Bytes | Unknown purpose |
| 12 | **name** | 24 | UTF-8 string | Texture name |
| 36 | **name_hash** | 4 | 4-bytes unsigned integer (little endian) | Hash of the name: texture id used by meshes |
| 40 | **class_name_hash** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 44 | **image_parent_hash** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 48 | **image_placement** | 4 | 4-bytes unsigned integer (little endian) | Offset of image data in the data chunk |
| 52 | **palette_placement** | 4 | 4-bytes unsigned integer (little endian) | Offset of palette in the data chunk |
| 56 | **image_size** | 4 | 4-bytes unsigned integer (little endian) | Size of image data, including mipmaps |
| 60 | **palette_size** | 4 | 4-bytes unsigned integer (little endian) | Size of palette, 0 if there is no palette |
| 64 | **base_image_size** | 4 | 4-bytes unsigned integer (little endian) | Size of the full-size image (without mipmaps) |
| 68 | **width** | 2 | 2-bytes unsigned integer (little endian) | Image width |
| 70 | **height** | 2 | 2-bytes unsigned integer (little endian) | Image height |
| 72 | **shift_width** | 1 | 1-byte unsigned integer | Log2 of width |
| 73 | **shift_height** | 1 | 1-byte unsigned integer | Log2 of height |
| 74 | **image_compression_type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): DEFAULT<br/>4 (0x4): 4BIT<br/>8 (0x8): 8BIT<br/>16 (0x10): 16BIT<br/>24 (0x18): 24BIT<br/>32 (0x20): 32BIT<br/>33 (0x21): DXT<br/>34 (0x22): DXTC1<br/>36 (0x24): DXTC3<br/>38 (0x26): DXTC5</details> | Image format. The exact format is defined by the formats chunk |
| 75 | **palette_compression_type** | 1 | 1-byte unsigned integer | Unknown purpose |
| 76 | **num_palette_entries** | 2 | 2-bytes unsigned integer (little endian) | Amount of palette colors |
| 78 | **num_mipmap_levels** | 1 | 1-byte unsigned integer | Amount of mipmaps |
| 79 | **tilable_uv** | 1 | 1-byte unsigned integer | Unknown purpose |
| 80 | **bias_level** | 1 | 1-byte unsigned integer | Unknown purpose |
| 81 | **rendering_order** | 1 | 1-byte unsigned integer | Unknown purpose |
| 82 | **scroll_type** | 1 | 1-byte unsigned integer | Unknown purpose |
| 83 | **used_flag** | 1 | 1-byte unsigned integer | Unknown purpose |
| 84 | **apply_alpha_sorting** | 1 | 1-byte unsigned integer | Unknown purpose |
| 85 | **alpha_usage_type** | 1 | 1-byte unsigned integer | Unknown purpose |
| 86 | **alpha_blend_type** | 1 | 1-byte unsigned integer | Unknown purpose |
| 87 | **flags** | 1 | 1-byte unsigned integer | Unknown purpose |
| 88 | **scroll_time_step** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 90 | **scroll_speed_s** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 92 | **scroll_speed_t** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 94 | **offset_s** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 96 | **offset_t** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 98 | **scale_s** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 100 | **scale_t** | 2 | 2-bytes signed integer (little endian) | Unknown purpose |
| 102 | **unk1** | 22 | Bytes | Unknown purpose |
### **NfsuTextureFormats** ###
#### **Size**: 8..? bytes ####
#### **Description**: Pixel formats of textures, one per texture ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x33310005 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **formats** | (chunk_length/32)\*32 | Array of `chunk_length/32` items<br/>Item type: [NfsuTextureFormat](#nfsutextureformat) | Formats |
### **NfsuTextureFormat** ###
#### **Size**: 32 bytes ####
#### **Description**: Exact pixel format of a texture ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 20 | Bytes | Unknown purpose |
| 20 | **format** | 4 | 4-bytes unsigned integer (little endian) | Direct3D format: FourCC "DXT1" (0x31545844), "DXT3", "DXT5", 0x15 (A8R8G8B8) or 0x29 (8-bit with palette) |
| 24 | **unk1** | 8 | Bytes | Unknown purpose |
### **NfsuTexturePackInfo** ###
#### **Size**: 8..? bytes ####
#### **Description**: Texture pack info container: header, hashes, infos, formats ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb3310000 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | until the end of chunk\*8..? | Array of `until the end of chunk` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuTexturePackHeader](#nfsutexturepackheader)<br/>- [NfsuTextureHashes](#nfsutexturehashes)<br/>- [NfsuCompressedTextures](#nfsucompressedtextures)<br/>- [NfsuTextureInfos](#nfsutextureinfos)<br/>- [NfsuTextureFormats](#nfsutextureformats)<br/>- [ZeroChunk](#zerochunk)<br/>- [UnknownChunk](#unknownchunk) | Child chunks |
### **NfsuTexturePackDataContainer** ###
#### **Size**: 8..? bytes ####
#### **Description**: Texture pack data container ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb3320000 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | until the end of chunk\*8..? | Array of `until the end of chunk` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuTextureData](#nfsutexturedata)<br/>- [ZeroChunk](#zerochunk)<br/>- [UnknownChunk](#unknownchunk) | Child chunks |
### **NfsuTextureData** ###
#### **Size**: 8..? bytes ####
#### **Description**: Pixel data of all textures of the pack. Texture infos point to it ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x33320002 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 128-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 128-bytes alignment | **data** | custom_func | Bytes | Image data and palettes |
## **Geometries** ##
### **NfsuBinGeometry** ###
#### **Size**: 8..? bytes ####
#### **Description**: Geometry pack: car geometry file (GEOMETRY.BIN), also a chunk of track bundles. A sequence of chunks, each having 32-bit id and 32-bit payload length; chunks with id starting with 0x80 are containers of other chunks. The pack starts with a file info container, followed by a mesh descriptor per mesh (car part, scenery object), interleaved with zero-id padding chunks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **header** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134000 | Resource ID (chunk id of the whole file) |
| 4 | **data_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the rest of the chunk in bytes |
| 8 | **chunks** | until the end of chunk (car GEOMETRY.BIN: until the end of file)\*8..? | Array of `until the end of chunk (car GEOMETRY.BIN: until the end of file)` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuMeshDescriptorChunk](#nfsumeshdescriptorchunk)<br/>- [Chunk80134001](#chunk80134001)<br/>- [Chunk80034020](#chunk80034020) | Top-level chunks, read until the end of file. Block class picked according to the chunk id |
### **ZeroChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Padding chunk with id 0: filler between meaningful chunks, used for alignment. Payload has no meaning ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | chunk_length | Bytes | Filler bytes |
### **UnknownChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: A chunk not decoded by the parser: header + raw payload ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian) | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | chunk_length | Bytes | Raw chunk payload |
### **Chunk80034020** ###
#### **Size**: 8..? bytes ####
#### **Description**: The last chunk of the file, purpose unknown ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80034020 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | chunk_length | Bytes | Unknown purpose |
### **NfsmwMeshChunk** ###
#### **Size**: 56..? bytes ####
#### **Description**: NFSMW mesh info chunk: amounts of materials, vertex buffers and vertex indexes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134900 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **unk0** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 + up to 16-bytes alignment | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Usually 0x12 |
| 20 + up to 16-bytes alignment | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 24 + up to 16-bytes alignment | **materials_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of materials |
| 28 + up to 16-bytes alignment | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 32 + up to 16-bytes alignment | **vertex_buffers_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices chunks |
| 36 + up to 16-bytes alignment | **unk3** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 52 + up to 16-bytes alignment | **indices_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex indexes in the faces chunk |
### **NfsmwMeshFacesChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW mesh faces: a triangle list. Amount of vertex indexes is defined by the mesh info chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b03 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **faces** | (^0/data/indices_amount/3)\*6 | Array of `^0/data/indices_amount/3` items<br/>Item size: 6 bytes<br/>Item type: Array of `3` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Triangles: 3 vertex indexes each, pointing to the vertex buffer of the material the triangle belongs to |
| 8 + up to 16-bytes alignment + (^0/data/indices_amount/3)\*6 | **padding** | custom_func | Bytes | Padding to 4 bytes |
### **NfsmwMeshVerticesChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW vertex buffer. A mesh has one per group of consecutive materials with the same effect; amount of vertices is the sum of `vertex_amount` of these materials. Vertex size (36, 44 or 60 bytes) depends on the effect ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b01 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 128-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 128-bytes alignment | **vertices** | ? | One of types:<br/>- Array of `custom_func` items<br/>Item type: [NfsuVertex](#nfsuvertex)<br/>- Array of `custom_func` items<br/>Item type: [NfsmwVertex44](#nfsmwvertex44)<br/>- Array of `custom_func` items<br/>Item type: [NfsmwVertex60](#nfsmwvertex60)<br/>- Array of `custom_func` items<br/>Item type: [NfsuVertexSkinned](#nfsuvertexskinned)<br/>- Bytes | Vertices: 36-byte vertices with normal, 44-byte vertices with two texture coordinates, 60-byte vertices with tangent or 60-byte vertices with skinning data (WorldBoneShader), whichever fills the chunk. Raw bytes if the layout is unknown |
### **NfsmwMeshMaterialsChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: NFSMW mesh materials: the triangle list split into ranges with their own texture and effect ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b02 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **materials** | custom_func\*104 | Array of `custom_func` items<br/>Item type: [NfsmwMeshMaterial](#nfsmwmeshmaterial) | Materials, in the order of their ranges in the faces chunk |
### **NfsmwMeshMaterial** ###
#### **Size**: 104 bytes ####
#### **Description**: NFSMW mesh material: a range of the triangle list drawn with one texture and effect ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **bounding_box_min** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Bounding box minimum corner |
| 12 | **bounding_box_max** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Bounding box maximum corner |
| 24 | **texture_index** | 1 | 1-byte unsigned integer | Index of diffuse texture id in the texture ids chunk (0x00134012) of the mesh |
| 25 | **normal_texture_index** | 1 | 1-byte unsigned integer | Index of normal map texture id |
| 26 | **height_texture_index** | 1 | 1-byte unsigned integer | Index of height map texture id |
| 27 | **specular_texture_index** | 1 | 1-byte unsigned integer | Index of specular map texture id |
| 28 | **opacity_texture_index** | 1 | 1-byte unsigned integer | Index of opacity map texture id |
| 29 | **light_material_index** | 1 | 1-byte unsigned integer | 0xFF if none |
| 30 | **unk0** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 32 | **unk1** | 16 | Bytes | Unknown purpose |
| 48 | **effect** | 4 | 4-bytes unsigned integer (little endian) | Effect (shader), defines vertex layout: 0: WorldShader, 1: WorldReflectShader, 2: WorldBoneShader, 3: WorldNormalMap, 4: CarShader, 5: GlossyWindow, 6: billboardshader, 7: WorldMinShader, 8: WorldNoFogShader, 9: FEShader, 10: FEMaskShader, 11: FilterShader, 12: OverbrightShader, 13: ScreenFilterShader, 14: RainDropShader, 15: RunwayLightShader, 16: VisualTreatmentShader, 17: WorldPrelitShader, 18: ParticlesShader, 19: skyshader, 20: shadow_map_mesh, 21: SkyboxCurrentGen, 22: ShadowPolyCurrentGen, 23: CarShadowMapShader, 24: WorldDepthShader, 25: WorldNormalMapDepth, 26: CarShaderDepth, 27: GlossyWindowDepth, 28: TreeDepthShader, 29: shadow_map_mesh_depth, 30: NormalMapNoFog |
| 52 | **effect_pointer** | 4 | 4-bytes unsigned integer (little endian) | Filled by the game in runtime |
| 56 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 60 | **vertex_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices of the material |
| 64 | **faces_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of triangles of the material |
| 68 | **unk2** | 24 | Bytes | Unknown purpose |
| 92 | **indices_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex indexes (3 per triangle) |
| 96 | **unk3** | 8 | Bytes | Unknown purpose |
### **NfsmwMeshMaterialName** ###
#### **Size**: 9..? bytes ####
#### **Description**: NFSMW material name, one chunk per material in the order of materials ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134c02 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | Material name, e.g. "BMWM3GTR_BADGING" |
| 9..? | **padding** | custom_func | Bytes | Zero bytes up to 4-bytes alignment |
### **Chunk80134100** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh data container: holds the mesh info chunk (always first), vertices chunk and faces chunk of a single mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134100 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsmwMeshChunk](#nfsmwmeshchunk)<br/>- [NfsmwMeshFacesChunk](#nfsmwmeshfaceschunk)<br/>- [NfsmwMeshVerticesChunk](#nfsmwmeshverticeschunk)<br/>- [NfsmwMeshMaterialsChunk](#nfsmwmeshmaterialschunk)<br/>- [NfsmwMeshMaterialName](#nfsmwmeshmaterialname) | Child chunks, read until the payload is exhausted. Block class picked according to the chunk id |
### **Chunk00134002** ###
#### **Size**: 136..? bytes ####
#### **Description**: File info: original path of the file and unknown values ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134002 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian). One of ['0x80', '0x90'] | Length of the chunk payload in bytes (everything after this field): 128 in NFSU, 144 in NFSU2 |
| 8 | **unk_0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 12 | **unk_1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **unk_2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 20 | **unk_3** | 4 | 4-bytes unsigned integer (little endian) | Amount of meshes in the file? Equals to the amount of items in the mesh ids chunk |
| 24 | **file_path** | 56 | UTF-8 string | Path of this file in the original development environment, e.g. "..\PC\CD\CARS\S2000\GEOMETRY.BIN" |
| 80 | **unk** | 32 | UTF-8 string | Some name, e.g. "DEFAULT" |
| 112 | **unk_4** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 116 | **unk_5** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 120 | **unk_6** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 124 | **unk_7** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 128 | **unk_8** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 132 | **unk_9** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 136 | **nfsu2_padding** | 0 in NFSU, 16 in NFSU2 | Bytes | NFSU2 only: zero bytes |
### **Chunk00134003** ###
#### **Size**: 8..? bytes ####
#### **Description**: List of mesh ids contained in the file, one item per mesh descriptor chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134003 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item size: 8 bytes<br/>Item type: Two 32-bit unsigned integers (little-endian): value, then unk (always 0) | Mesh ids: `value` equals to `mesh_id` of the corresponding mesh header chunk |
### **NfsmwMeshHeaderChunk** ###
#### **Size**: 169..? bytes ####
#### **Description**: NFSMW mesh header: id, name, bounding box and transformation of a single mesh. Same id as in NFSU, the name is null-terminated ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134011 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **unk0** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 20 + up to 16-bytes alignment | **version** | 2 | 2-bytes unsigned integer (little endian). Always == 0x16 | Version of the mesh header |
| 22 + up to 16-bytes alignment | **flags** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 24 + up to 16-bytes alignment | **mesh_id** | 4 | 4-bytes unsigned integer (little endian) | Mesh id (hash of the name), listed in the mesh ids chunk |
| 28 + up to 16-bytes alignment | **faces_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of faces (triangles) of the mesh |
| 30 + up to 16-bytes alignment | **vertex_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of vertices, usually 0 |
| 32 + up to 16-bytes alignment | **bones_amount** | 1 | 1-byte unsigned integer | Unknown purpose |
| 33 + up to 16-bytes alignment | **textures_amount** | 1 | 1-byte unsigned integer | Amount of items in the texture ids chunk |
| 34 + up to 16-bytes alignment | **light_materials_amount** | 1 | 1-byte unsigned integer | Amount of items in the light materials chunk |
| 35 + up to 16-bytes alignment | **position_markers_amount** | 1 | 1-byte unsigned integer | Unknown purpose |
| 36 + up to 16-bytes alignment | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 40 + up to 16-bytes alignment | **bounding_box_min** | 16 | [NfsuVec3](#nfsuvec3) | Minimum corner of the axis-aligned bounding box of the mesh |
| 56 + up to 16-bytes alignment | **bounding_box_max** | 16 | [NfsuVec3](#nfsuvec3) | Maximum corner of the axis-aligned bounding box of the mesh |
| 72 + up to 16-bytes alignment | **transform** | 64 | Array of `16` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Transformation matrix 4x4, row by row |
| 136 + up to 16-bytes alignment | **unk2** | 24 | Array of `6` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 160 + up to 16-bytes alignment | **unk3** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Unknown purpose |
| 168 + up to 16-bytes alignment | **mesh_name** | 1..? | Null-terminated UTF-8 string. Ends with first occurrence of zero byte | Mesh name, e.g. "BMWM3GTR_BASE_A". Used as the name of exported mesh |
| 169 + up to 16-bytes alignment..? | **name_padding** | custom_func | Bytes | Zero bytes up to 4-bytes alignment |
### **Chunk00134012** ###
#### **Size**: 8..? bytes ####
#### **Description**: A list of 32-bit values (hashes) of the mesh, presumably texture ids ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134012 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item size: 8 bytes<br/>Item type: Two 32-bit unsigned integers (little-endian): value, then unk (always 0) | Items |
### **Chunk00134013** ###
#### **Size**: 8..? bytes ####
#### **Description**: A list of 32-bit values (hashes) of the mesh, presumably shader/material ids ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134013 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item size: 8 bytes<br/>Item type: Two 32-bit unsigned integers (little-endian): value, then unk (always 0) | Items |
### **Chunk001340XX** ###
#### **Size**: 8..? bytes ####
#### **Description**: Unknown chunk with id 0x001340XX, kept as raw bytes. Known ids: 0x00134004 in the file info container (20-byte records per mesh, starting with mesh id); 0x00134017, 0x00134018, 0x00134019, 0x0013401A in mesh descriptors ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **index** | 1 | 1-byte unsigned integer. One of ['0x4', '0x17', '0x18', '0x19', '0x1a'] | Lowest byte of the chunk id |
| 1 | **chunk_id** | 3 | 3-bytes unsigned integer (little endian). Always == 0x1340 | Upper 3 bytes of the chunk id |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | chunk_length | Bytes | Unknown purpose |
### **Chunk80134008** ###
#### **Size**: 8..? bytes ####
#### **Description**: Unknown chunk of the file info container, usually empty ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134008 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | chunk_length | Bytes | Unknown purpose |
### **NfsuMeshDescriptorChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh descriptor: everything about a single mesh (a car part). Contains the mesh header chunk, lists of hashes and the mesh data container with vertices and faces. The converter exports every descriptor as a separate mesh, named after `mesh_name` of the header ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134010 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsmwMeshHeaderChunk](#nfsmwmeshheaderchunk)<br/>- [Chunk00134012](#chunk00134012)<br/>- [Chunk00134013](#chunk00134013)<br/>- [Chunk80134100](#chunk80134100)<br/>- [Chunk001340XX](#chunk001340xx) | Child chunks, read until the payload is exhausted. Block class picked according to the chunk id |
### **Chunk80134001** ###
#### **Size**: 8..? bytes ####
#### **Description**: File info container: the first meaningful chunk of the file. Holds file info, the list of mesh ids and a per-mesh table ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134001 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [Chunk00134002](#chunk00134002)<br/>- [Chunk00134003](#chunk00134003)<br/>- [Chunk001340XX](#chunk001340xx)<br/>- [Chunk80134008](#chunk80134008) | Child chunks (always 3 or 4), read until the payload is exhausted. Block class picked according to the chunk id |
### **Chunk80134020** ###
#### **Size**: 8..? bytes ####
#### **Description**: Unknown top-level chunk, kept as raw bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134020 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | chunk_length | Bytes | Unknown purpose |
### **NfsuVec3** ###
#### **Size**: 16 bytes ####
#### **Description**: A 3D vector padded to 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vector** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vector components |
| 12 | **pad** | 4 | Float number (little-endian). Always == 0.0 | Padding, always 0 |
### **NfsuVertex** ###
#### **Size**: 36 bytes ####
#### **Description**: A single mesh vertex with normal (36 bytes). The most common vertex layout ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex position |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Presumably X component of the vertex normal, stored as 32-bit float |
| 16 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Presumably Y component of the vertex normal, stored as 32-bit float |
| 20 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Presumably Z component of the vertex normal, stored as 32-bit float |
| 24 | **unk3** | 4 | 4-bytes unsigned integer (little endian) | Presumably vertex color, 32-bit ARGB |
| 28 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 32 | **v** | 4 | Float number (little-endian) | V texture coordinate |
### **NfsmwVertex44** ###
#### **Size**: 44 bytes ####
#### **Description**: NFSMW vertex with two texture coordinates (44 bytes), skyshader ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex position |
| 12 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex normal |
| 24 | **color** | 4 | 4-bytes unsigned integer (little endian) | Vertex color, 32-bit ARGB |
| 28 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 32 | **v** | 4 | Float number (little-endian) | V texture coordinate |
| 36 | **uv2** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Unknown purpose |
### **NfsmwVertex60** ###
#### **Size**: 60 bytes ####
#### **Description**: NFSMW vertex with tangent (60 bytes), WorldReflectShader and WorldNormalMap effects ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex position |
| 12 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex normal |
| 24 | **color** | 4 | 4-bytes unsigned integer (little endian) | Vertex color, 32-bit ARGB |
| 28 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 32 | **v** | 4 | Float number (little-endian) | V texture coordinate |
| 36 | **uv2** | 8 | Array of `2` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Unknown purpose |
| 44 | **tangent** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | Tangent (x, y, z, w) |
### **NfsuVertexSkinned** ###
#### **Size**: 60 bytes ####
#### **Description**: A single mesh vertex with normal and skinning data (60 bytes). Used by a few world meshes (flags 0x4081 in the mesh info chunk) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex position |
| 12 | **normal** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex normal |
| 24 | **unk3** | 4 | 4-bytes unsigned integer (little endian) | Presumably vertex color, 32-bit ARGB |
| 28 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 32 | **v** | 4 | Float number (little-endian) | V texture coordinate |
| 36 | **blend_weights** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Blend weights |
| 48 | **blend_indices** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Blend indices |
