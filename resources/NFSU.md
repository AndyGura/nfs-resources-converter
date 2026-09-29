# **NFS Underground file specs** #

*Last time updated: 2026-09-29 06:59:16.901046+00:00*


# **Info by file extensions** #

Cars\**\GEOMETRY.BIN** car geometry. [NfsuBinGeometry](#nfsubingeometry)

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #
## **Geometries** ##
### **NfsuBinGeometry** ###
#### **Size**: 8..? bytes ####
#### **Description**: Car geometry file (GEOMETRY.BIN). A sequence of chunks, each having 32-bit id and 32-bit payload length; chunks with id starting with 0x80 are containers of other chunks. The file starts with a file info container, followed by a mesh descriptor per car part, interleaved with zero-id padding chunks ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **header** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134000 | Resource ID (chunk id of the whole file) |
| 4 | **data_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the rest of the file in bytes |
| 8 | **chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuMeshDescriptorChunk](#nfsumeshdescriptorchunk)<br/>- [Chunk80134001](#chunk80134001)<br/>- [Chunk80034020](#chunk80034020) | Top-level chunks, read until the end of file. Block class picked according to the chunk id |
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
#### **Description**: Fallback for a chunk with an id not known to the parser: header + raw payload. Currently not used, every chunk met in the files has a dedicated block ####
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
| 8 | **payload** | chunk_length-28 | Bytes | Unknown data, starts with 0x11 alignment filler bytes |
| 8 + chunk_length-28 | **faces_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of faces (triangles) of the mesh |
| 12 + chunk_length-28 | **unk_v** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 16 + chunk_length-28 | **unk_w** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 20 + chunk_length-28 | **unk_x** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 24 + chunk_length-28 | **vertex_amount** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices of the mesh |
| 28 + chunk_length-28 | **unk_y** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 32 + chunk_length-28 | **unk_z** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
### **NfsuMeshFacesChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh faces: a triangle list. Amount of faces is defined by the mesh info chunk (the first chunk of the same mesh data container) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b03 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | custom_func | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + custom_func | **faces** | (^0/data/faces_amount)\*6 | Array of `^0/data/faces_amount` items<br/>Item size: 6 bytes<br/>Item type: Array of `3` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | Triangles: 3 vertex indexes each, pointing to the vertices chunk of the same mesh |
| 8 + custom_func + (^0/data/faces_amount)\*6 | **padding** | custom_func | Bytes | Padding to the end of the chunk |
### **MeshVerticesChunk** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh vertices. Amount of vertices is defined by the mesh info chunk (the first chunk of the same mesh data container) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b01 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | chunk_length-(^0/data/vertex_amount)\*36 | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + chunk_length-(^0/data/vertex_amount)\*36 | **vertices** | (^0/data/vertex_amount)\*36 | Array of `^0/data/vertex_amount` items<br/>Item type: [NfsuVertex](#nfsuvertex) | Vertices |
### **Chunk00134BXX** ###
#### **Size**: 8..? bytes ####
#### **Description**: Unknown chunk of the mesh data container (id 0x00134B02). Observed payload looks like 16-byte records: 3 floats + 32-bit integer ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **index** | 1 | 1-byte unsigned integer. One of ['0x2', '0x3'] | Lowest byte of the chunk id |
| 1 | **chunk_id** | 3 | 3-bytes unsigned integer (little endian). Always == 0x134b | Upper 3 bytes of the chunk id |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **elevens** | custom_func | Bytes | Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset |
| 8 + custom_func | **payload** | custom_func | Bytes | Unknown purpose |
### **Chunk80134100** ###
#### **Size**: 8..? bytes ####
#### **Description**: Mesh data container: holds the mesh info chunk (always first), vertices chunk and faces chunk of a single mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134100 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuMeshChunk](#nfsumeshchunk)<br/>- [NfsuMeshFacesChunk](#nfsumeshfaceschunk)<br/>- [MeshVerticesChunk](#meshverticeschunk)<br/>- [Chunk00134BXX](#chunk00134bxx) | Child chunks, read until the payload is exhausted. Block class picked according to the chunk id |
### **Chunk00134002** ###
#### **Size**: 136 bytes ####
#### **Description**: File info: original path of the file and unknown values ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134002 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80 | Length of the chunk payload in bytes (everything after this field) |
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
### **Chunk00134003** ###
#### **Size**: 8..? bytes ####
#### **Description**: List of mesh ids contained in the file, one item per mesh descriptor chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134003 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | Length of the chunk payload in bytes (everything after this field) |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item size: 8 bytes<br/>Item type: Two 32-bit unsigned integers (little-endian): value, then unk (always 0) | Mesh ids: `value` equals to `mesh_id` of the corresponding mesh header chunk |
### **Chunk00134011** ###
#### **Size**: 184 bytes ####
#### **Description**: Mesh header: id, name, bounding volume and flags of a single mesh ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134011 | Chunk ID |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb0 | Length of the chunk payload in bytes (everything after this field) |
| 8 | **unk2** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 12 | **unk3** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 16 | **unk4** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 20 | **unk5** | 2 | 2-bytes unsigned integer (little endian). Always == 0x13 | Unknown purpose |
| 22 | **unk6** | 2 | 2-bytes unsigned integer (little endian). One of ['0x40', '0x0'] | Unknown purpose |
| 24 | **mesh_id** | 4 | 4-bytes unsigned integer (little endian) | Mesh id (hash), listed in the mesh ids chunk of the file |
| 28 | **unk7** | 4 | 4-bytes unsigned integer (little endian) | Amount of faces? Equals to `faces_amount` of the mesh info chunk |
| 32 | **mesh_flags** | 4 | 4-bytes unsigned integer (little endian) | Mesh flags. Maybe contains stream count / LOD / material count |
| 36 | **unk10** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 40 | **bounding_box_min** | 16 | [NfsuVec3](#nfsuvec3) | Minimum corner of the axis-aligned bounding box of the mesh |
| 56 | **bounding_box_max** | 16 | [NfsuVec3](#nfsuvec3) | Maximum corner of the axis-aligned bounding box of the mesh |
| 72 | **obb_axis0** | 16 | [NfsuVec3](#nfsuvec3) | First axis of the oriented bounding box |
| 88 | **obb_axis1** | 16 | [NfsuVec3](#nfsuvec3) | Second axis of the oriented bounding box |
| 104 | **obb_axis2** | 16 | [NfsuVec3](#nfsuvec3) | Third axis of the oriented bounding box |
| 120 | **unk_float0** | 4 | Float number (little-endian) | Is it a quaternion (with the next 3 floats)? |
| 124 | **unk_float1** | 4 | Float number (little-endian) | Unknown purpose |
| 128 | **unk_float2** | 4 | Float number (little-endian) | Unknown purpose |
| 132 | **unk_U** | 4 | Float number (little-endian). Always == 1.0 | Unknown purpose |
| 136 | **unk_V** | 4 | Float number (little-endian). Always == 0.0 | Unknown purpose |
| 140 | **unk_W** | 4 | Float number (little-endian). Always == 0.0 | Unknown purpose |
| 144 | **unk_X** | 4 | 4-bytes unsigned integer (little endian). Always == 0x12f800 | Unknown purpose |
| 148 | **unk_Y** | 4 | 4-bytes unsigned integer (little endian). Always == 0x12f800 | Unknown purpose |
| 152 | **unk_Z** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 156 | **mesh_name** | 28 | UTF-8 string | Mesh name, e.g. "S2000_KIT08_FRONT_BUMPER_A". Used as the name of exported mesh |
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
#### **Description**: A single mesh vertex ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | Vertex position |
| 12 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Presumably X component of the vertex normal, stored as 32-bit float |
| 16 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Presumably Y component of the vertex normal, stored as 32-bit float |
| 20 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Presumably Z component of the vertex normal, stored as 32-bit float |
| 24 | **unk3** | 4 | 4-bytes unsigned integer (little endian) | Presumably vertex color, 32-bit ARGB |
| 28 | **u** | 4 | Float number (little-endian) | U texture coordinate |
| 32 | **v** | 4 | Float number (little-endian) | V texture coordinate |
