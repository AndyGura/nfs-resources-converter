# **NFS Underground file specs** #

*Last time updated: 2026-10-06 23:43:20.495327+00:00*


# **Info by file extensions** #

**CARS/\*/GEOMETRY.BIN** car geometry. [NfsuBinGeometry](#nfsubingeometry)

**TRACKS/TRACKBnnnn.lzc** race bundle (JDLZ-compressed): streaming sections table and race data. Opened in the track viewer together with the city sections from **TRACKS/STREAM\*.BUN** next to it. [NfsuTrackBundle](#nfsutrackbundle)

**TRACKS/STREAM\*.BUN** streamed city sections (scenery, geometry, textures), each 0x800-aligned. [NfsuChunkBundle](#nfsuchunkbundle)

**TRACKS/TEXnnnnTRACK.BIN**, **GLOBAL/\*.BIN** texture packs and other chunk bundles. [NfsuChunkBundle](#nfsuchunkbundle)

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #
## **Maps** ##
### **NfsuTrackBundle** ###
#### **Size**: 0..? bytes ####
#### **Description**: Race bundle (NFSU TRACKS/TRACKBnnnn.lzc, uncompressed) or location bundle (NFSU2 TRACKS/L4RA.BUN): a chunk bundle with the streaming sections table of the world, which is stored in TRACKS/STREAM*.BUN. Chunk bundle (*.BUN, *.BIN, uncompressed *.lzc): a sequence of chunks, each having 32-bit id, 32-bit payload length and payload; chunks with the highest bit of id set are containers of other chunks. Geometry packs, texture packs, scenery and streaming sections table are decoded, other chunks are kept as raw bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunks** | until the end of file\*8..? | Array of `until the end of file` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuBinGeometry](#nfsubingeometry)<br/>- [NfsuTexturePack](#nfsutexturepack)<br/>- [NfsuScenery](#nfsuscenery)<br/>- [NfsuStreamingSections](#nfsustreamingsections)<br/>- [UnknownChunk](#unknownchunk) | Chunks |
### **NfsuChunkBundle** ###
#### **Size**: 0..? bytes ####
#### **Description**: Chunk bundle (*.BUN, *.BIN, uncompressed *.lzc): a sequence of chunks, each having 32-bit id, 32-bit payload length and payload; chunks with the highest bit of id set are containers of other chunks. Geometry packs, texture packs, scenery and streaming sections table are decoded, other chunks are kept as raw bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunks** | until the end of file\*8..? | Array of `until the end of file` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuBinGeometry](#nfsubingeometry)<br/>- [NfsuTexturePack](#nfsutexturepack)<br/>- [NfsuScenery](#nfsuscenery)<br/>- [NfsuStreamingSections](#nfsustreamingsections)<br/>- [UnknownChunk](#unknownchunk) | Chunks |
### **NfsuStreamingSections** ###
#### **Size**: 8..? bytes ####
#### **Description**: Table of streamed sections: where the world sections of the race lie in the STREAM*.BUN file. NFSU2 has another chunk with this id ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34107 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sections** | (chunk_length/56)\*56 | Array of `chunk_length/56` items<br/>Item type: [NfsuStreamingSection](#nfsustreamingsection) | Sections |
### **NfsuStreamingSection** ###
#### **Size**: 56 bytes ####
#### **Description**: Location of a streamed section in the STREAM*.BUN file ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 8 | UTF-8 string | Section name, e.g. "A37" |
| 8 | **number** | 4 | 4-bytes unsigned integer (little endian) | Section number: letter index (A = 1) * 100 + number. Some have flag 0x10000 set |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 20 | **offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of the section in the stream file |
| 24 | **size** | 4 | 4-bytes unsigned integer (little endian) | Size of the section in the stream file |
| 28 | **size2** | 4 | 4-bytes unsigned integer (little endian) | Equals to `size` unless the section has textures, then a bit smaller |
| 32 | **hash** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 36 | **unk2** | 20 | Bytes | Unknown purpose |
### **NfsuScenery** ###
#### **Size**: 8..? bytes ####
#### **Description**: Scenery of a section: object definitions referencing meshes by id, and their placements in the world ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80034100 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | until the end of chunk\*8..? | Array of `until the end of chunk` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuScenerySectionHeader](#nfsuscenerysectionheader)<br/>- [NfsuSceneryInfos](#nfsusceneryinfos)<br/>- [NfsuSceneryInstances](#nfsusceneryinstances)<br/>- [ZeroChunk](#zerochunk)<br/>- [UnknownChunk](#unknownchunk) | Header, definitions, instances and an unknown chunk 0x00034104 |
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
### **NfsuSceneryInfos** ###
#### **Size**: 8..? bytes ####
#### **Description**: Scenery object definitions ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34102 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **infos** | (chunk_length/72)\*72 | Array of `chunk_length/72` items<br/>Item type: [NfsuSceneryInfo](#nfsusceneryinfo) | Definitions |
### **NfsuSceneryInfo** ###
#### **Size**: 72 bytes ####
#### **Description**: Scenery object definition: which mesh to draw ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **mesh_ids** | 24 | Array of `6` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Mesh ids (hashes of mesh names, `mesh_id` of mesh header chunks). The first one is the main mesh, others are probably levels of detail |
| 24 | **far_clip_sizes** | 8 | Array of `4` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes signed integer (little endian) | Unknown purpose |
| 32 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 36 | **model_pointers** | 24 | Array of `6` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Filled by the game in runtime |
| 60 | **facade_flags** | 6 | Bytes | Unknown purpose |
| 66 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 68 | **radius** | 4 | Float number (little-endian) | Bounding sphere radius |
### **NfsuSceneryInstances** ###
#### **Size**: 8..? bytes ####
#### **Description**: Placed scenery objects ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x34103 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **instances** | custom_func\*48 | Array of `custom_func` items<br/>Item type: [NfsuSceneryInstance](#nfsusceneryinstance) | Instances |
### **NfsuSceneryInstance** ###
#### **Size**: 48 bytes ####
#### **Description**: Placed scenery object ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **bounding_box_min** | 6 | Point in 3D space (x,y,z), where each coordinate is: 2-bytes signed integer (little endian) | Minimum corner of the bounding box in world coordinates |
| 6 | **bounding_box_max** | 6 | Point in 3D space (x,y,z), where each coordinate is: 2-bytes signed integer (little endian) | Maximum corner of the bounding box in world coordinates |
| 12 | **info_index** | 2 | 2-bytes unsigned integer (little endian) | Index of the object definition in this scenery |
| 14 | **exclude_flags** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 16 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Position in world coordinates |
| 28 | **rotation** | 18 | Array of `9` items<br/>Item size: 2 bytes<br/>Item type: 16-bit real number (little-endian, signed), where last 13 bits is a fractional part | Rotation and scale matrix 3x3, row by row. World position of a mesh vertex v is v.x * row0 + v.y * row1 + v.z * row2 + position |
| 46 | **padding** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
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
| 8 | **sub_chunks** | until the end of chunk\*8..? | Array of `until the end of chunk` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuTexturePackHeader](#nfsutexturepackheader)<br/>- [NfsuTextureHashes](#nfsutexturehashes)<br/>- [NfsuTextureInfos](#nfsutextureinfos)<br/>- [NfsuTextureFormats](#nfsutextureformats)<br/>- [ZeroChunk](#zerochunk)<br/>- [UnknownChunk](#unknownchunk) | Child chunks |
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
### **NfsuMeshChunk** ###
#### **Size**: 36..? bytes ####
#### **Description**: Mesh info chunk: amounts of faces and vertices of the mesh, used to read the faces and vertices chunks of the same mesh data container ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134900 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **payload** | 0x11 alignment filler + 36 | Bytes | Unknown data, starts with 0x11 alignment filler bytes |
| 0x11 alignment filler + 44 | **faces_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of faces (triangles) of the mesh |
| 0x11 alignment filler + 48 | **unk_v** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 0x11 alignment filler + 52 | **unk_w** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 0x11 alignment filler + 56 | **unk_x** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 0x11 alignment filler + 60 | **vertex_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices of the mesh |
| 0x11 alignment filler + 64 | **unk_y** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 0x11 alignment filler + 68 | **unk_z** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 0x11 alignment filler + 72 | **unk_tail** | 0 in NFSU, 1 in NFSU2\*4 | Array of `0 in NFSU, 1 in NFSU2` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian). Always == 0x0 | NFSU2 only: one more zero value |
### **NfsuMeshFacesChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh faces: a triangle list. Amount of faces is defined by the mesh info chunk (the first chunk of the same mesh data container) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b03 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **faces** | (^0/data/faces_amount)\*6 | Array of `^0/data/faces_amount` items<br/>Item size: 6 bytes<br/>Item type: Array of `3` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Triangles: 3 vertex indexes each, pointing to the vertices chunk of the same mesh |
| 8 + up to 16-bytes alignment + (^0/data/faces_amount)\*6 | **padding** | custom_func | Bytes | Padding to the end of the chunk |
### **MeshVerticesChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh vertices. Amount of vertices is defined by the mesh info chunk (the first chunk of the same mesh data container). Vertex size (36, 24 or 60 bytes) is determined by the chunk length ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b01 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 128-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 128-bytes alignment | **vertices** | ? | One of types:<br/>- Array of `^0/data/vertex_amount` items<br/>Item type: [NfsuVertex](#nfsuvertex)<br/>- Array of `^0/data/vertex_amount` items<br/>Item type: [NfsuVertexNoNormal](#nfsuvertexnonormal)<br/>- Array of `^0/data/vertex_amount` items<br/>Item type: [NfsuVertexSkinned](#nfsuvertexskinned)<br/>- Bytes | Vertices: 36-byte vertices with normal, 24-byte vertices without normal or 60-byte vertices with normal and skinning data, whichever fills the chunk. Raw bytes if the mesh has no vertices |
### **NfsuMeshMaterialsChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh materials: the triangle list of the mesh split into ranges with their own texture ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b02 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **materials** | custom_func\*60 | Array of `custom_func` items<br/>Item type: [NfsuMeshMaterial](#nfsumeshmaterial) | Materials, in the order of their ranges in the faces chunk |
### **NfsuMeshMaterial** ###
#### **Size**: 60 bytes ####
#### **Description**: A part of the mesh drawn with one texture: a range of the triangle list ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **bounding_box_min** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Bounding box minimum corner |
| 12 | **indices_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex indexes (3 per triangle) |
| 16 | **bounding_box_max** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Bounding box maximum corner |
| 28 | **texture_index** | 4 | 4-bytes unsigned integer (little endian) | Index of texture id in the texture ids chunk (0x00134012) of the mesh |
| 32 | **light_material_index** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 36 | **unk** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 52 | **indices_offset** | 4 | 4-bytes unsigned integer (little endian) | Index of the first vertex index in the faces chunk: sum of previous `indices_amount` |
| 56 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **Chunk80134100** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh data container: holds the mesh info chunk (always first), vertices chunk and faces chunk of a single mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134100 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuMeshChunk](#nfsumeshchunk)<br/>- [NfsuMeshFacesChunk](#nfsumeshfaceschunk)<br/>- [MeshVerticesChunk](#meshverticeschunk)<br/>- [NfsuMeshMaterialsChunk](#nfsumeshmaterialschunk) | Child chunks, read until the payload is exhausted. Block class picked according to the chunk id |
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
### **Chunk00134011** ###
#### **Size**: 184..? bytes ####
#### **Description**: Mesh header: id, name, bounding volume and flags of a single mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134011 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field): 176 (NFSU) or 192 (NFSU2) + length of alignment filler |
| 8 | **elevens** | up to 16-bytes alignment | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + up to 16-bytes alignment | **unk2** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 12 + up to 16-bytes alignment | **unk3** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 16 + up to 16-bytes alignment | **unk4** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 20 + up to 16-bytes alignment | **version** | 2 | 2-bytes unsigned integer (little endian). One of ['0x13', '0x16'] | Version of the mesh header: 0x13 in NFSU, 0x16 in NFSU2 |
| 22 + up to 16-bytes alignment | **unk6** | 2 | 2-bytes unsigned integer (little endian) | Flags? 0x40 or 0 in NFSU, also 0x80 in NFSU2 |
| 24 + up to 16-bytes alignment | **mesh_id** | 4 | 4-bytes unsigned integer (little endian) | Mesh id (hash), listed in the mesh ids chunk of the file |
| 28 + up to 16-bytes alignment | **unk7** | 4 | 4-bytes unsigned integer (little endian) | Amount of faces? Equals to `faces_amount` of the mesh info chunk |
| 32 + up to 16-bytes alignment | **mesh_flags** | 4 | 4-bytes unsigned integer (little endian) | Mesh flags. Maybe contains stream count / LOD / material count |
| 36 + up to 16-bytes alignment | **unk10** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 40 + up to 16-bytes alignment | **bounding_box_min** | 16 | [NfsuVec3](#nfsuvec3) | Minimum corner of the axis-aligned bounding box of the mesh |
| 56 + up to 16-bytes alignment | **bounding_box_max** | 16 | [NfsuVec3](#nfsuvec3) | Maximum corner of the axis-aligned bounding box of the mesh |
| 72 + up to 16-bytes alignment | **obb_axis0** | 16 | [NfsuVec3](#nfsuvec3) | First axis of the oriented bounding box |
| 88 + up to 16-bytes alignment | **obb_axis1** | 16 | [NfsuVec3](#nfsuvec3) | Second axis of the oriented bounding box |
| 104 + up to 16-bytes alignment | **obb_axis2** | 16 | [NfsuVec3](#nfsuvec3) | Third axis of the oriented bounding box |
| 120 + up to 16-bytes alignment | **unk_float0** | 4 | Float number (little-endian) | Is it a quaternion (with the next 3 floats)? |
| 124 + up to 16-bytes alignment | **unk_float1** | 4 | Float number (little-endian) | Unknown purpose |
| 128 + up to 16-bytes alignment | **unk_float2** | 4 | Float number (little-endian) | Unknown purpose |
| 132 + up to 16-bytes alignment | **unk_U** | 4 | Float number (little-endian). Always == 1.0 | Unknown purpose |
| 136 + up to 16-bytes alignment | **unk_V** | 4 | Float number (little-endian). Always == 0.0 | Unknown purpose |
| 140 + up to 16-bytes alignment | **unk_W** | 4 | Float number (little-endian). Always == 0.0 | Unknown purpose |
| 144 + up to 16-bytes alignment | **unk_X** | 4 | 4-bytes unsigned integer (little endian) | Always 0x0012F800 in NFSU |
| 148 + up to 16-bytes alignment | **unk_Y** | 4 | 4-bytes unsigned integer (little endian) | Always equals to `unk_X` |
| 152 + up to 16-bytes alignment | **unk_Z** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 156 + up to 16-bytes alignment | **nfsu2_unk_floats** | 0 in NFSU, 2 in NFSU2\*4 | Array of `0 in NFSU, 2 in NFSU2` items<br/>Item size: 4 bytes<br/>Item type: Float number (little-endian) | NFSU2 only |
| 156 + up to 16-bytes alignment + 0 in NFSU, 2 in NFSU2\*4 | **nfsu2_unk_ints** | 0 in NFSU, 2 in NFSU2\*4 | Array of `0 in NFSU, 2 in NFSU2` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | NFSU2 only |
| 156 + up to 16-bytes alignment + 0 in NFSU, 2 in NFSU2\*4 + 0 in NFSU, 2 in NFSU2\*4 | **mesh_name** | 28 | UTF-8 string | Mesh name, e.g. "S2000_KIT08_FRONT_BUMPER_A". Used as the name of exported mesh |
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
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [Chunk00134011](#chunk00134011)<br/>- [Chunk00134012](#chunk00134012)<br/>- [Chunk00134013](#chunk00134013)<br/>- [Chunk80134100](#chunk80134100)<br/>- [Chunk001340XX](#chunk001340xx) | Child chunks, read until the payload is exhausted. Block class picked according to the chunk id |
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
### **NfsuVertexNoNormal** ###
#### **Size**: 24 bytes ####
#### **Description**: A single mesh vertex without normal (24 bytes). Used by a few meshes, e.g. SUPRA_STYLE02_HEADLIGHT_C. Same layout as the 36-byte vertex with the normal omitted (Direct3D FVF order: position, diffuse color, texture coordinates) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex position |
| 12 | **unk3** | 4 | 4-bytes unsigned integer (little endian) | Presumably vertex color, 32-bit ARGB |
| 16 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 20 | **v** | 4 | Float number (little-endian) | V texture coordinate |
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
