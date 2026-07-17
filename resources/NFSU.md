# **NFS Underground file specs** #

*Last time updated: 2026-07-17 21:15:20.812838+00:00*


# **Info by file extensions** #

Cars\**\GEOMETRY.BIN** car geometry. [NfsuBinGeometry](#nfsubingeometry)

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #
## **Geometries** ##
### **NfsuBinGeometry** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **header** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134000 | - |
| 4 | **data_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [ZeroChunk](#zerochunk)<br/>- [NfsuMeshDescriptorChunk](#nfsumeshdescriptorchunk)<br/>- [Chunk80134001](#chunk80134001)<br/>- [Chunk80034020](#chunk80034020) | - |
### **ZeroChunk** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **UnknownChunk** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian) | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **Chunk80034020** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80034020 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **NfsuMeshChunk** ###
#### **Size**: 28..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134900 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length-20 | Bytes | - |
| 8 + chunk_length-20 | **unk_w** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 12 + chunk_length-20 | **unk_x** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 16 + chunk_length-20 | **vertex_amount** | 4 | 4-bytes unsigned integer (little endian) | - |
| 20 + chunk_length-20 | **unk_y** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 24 + chunk_length-20 | **unk_z** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
### **NfsuMeshFacesChunk** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134b03 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **index_table** | custom_func\*2 | Array of `custom_func` items<br/>Item size: 2 bytes<br/>Item type: 2-bytes unsigned integer (little endian) | - |
### **Chunk00134BXX** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **index** | 1 | 1-byte unsigned integer. One of ['0x1', '0x2', '0x3'] | - |
| 1 | **chunk_id** | 3 | 3-bytes unsigned integer (little endian). Always == 0x134b | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **Chunk80134100** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134100 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [NfsuMeshChunk](#nfsumeshchunk)<br/>- [NfsuMeshFacesChunk](#nfsumeshfaceschunk)<br/>- [Chunk00134BXX](#chunk00134bxx) | - |
### **Chunk00134002** ###
#### **Size**: 136 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134002 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80 | - |
| 8 | **unk_0** | 4 | 4-bytes unsigned integer (little endian) | - |
| 12 | **unk_1** | 4 | 4-bytes unsigned integer (little endian) | - |
| 16 | **unk_2** | 4 | 4-bytes unsigned integer (little endian) | - |
| 20 | **unk_3** | 4 | 4-bytes unsigned integer (little endian) | - |
| 24 | **file_path** | 56 | UTF-8 string | - |
| 80 | **unk** | 32 | UTF-8 string | - |
| 112 | **unk_4** | 4 | 4-bytes unsigned integer (little endian) | - |
| 116 | **unk_5** | 4 | 4-bytes unsigned integer (little endian) | - |
| 120 | **unk_6** | 4 | 4-bytes unsigned integer (little endian) | - |
| 124 | **unk_7** | 4 | 4-bytes unsigned integer (little endian) | - |
| 128 | **unk_8** | 4 | 4-bytes unsigned integer (little endian) | - |
| 132 | **unk_9** | 4 | 4-bytes unsigned integer (little endian) | - |
### **Chunk00134003** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134003 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item type: [CompoundBlock](#compoundblock) | - |
### **Chunk00134011** ###
#### **Size**: 184 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134011 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian). Always == 0xb0 | - |
| 8 | **unk2** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 12 | **unk3** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 16 | **unk4** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 20 | **unk5** | 2 | 2-bytes unsigned integer (little endian). Always == 0x13 | - |
| 22 | **unk6** | 2 | 2-bytes unsigned integer (little endian). One of ['0x40', '0x0'] | - |
| 24 | **mesh_id** | 4 | 4-bytes unsigned integer (little endian) | - |
| 28 | **unk7** | 4 | 4-bytes unsigned integer (little endian) | - |
| 32 | **mesh_flags** | 4 | 4-bytes unsigned integer (little endian) | - |
| 36 | **unk10** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 40 | **bounding_box_min** | 16 | [NfsuVec3](#nfsuvec3) | - |
| 56 | **bounding_box_max** | 16 | [NfsuVec3](#nfsuvec3) | - |
| 72 | **obb_axis0** | 16 | [NfsuVec3](#nfsuvec3) | - |
| 88 | **obb_axis1** | 16 | [NfsuVec3](#nfsuvec3) | - |
| 104 | **obb_axis2** | 16 | [NfsuVec3](#nfsuvec3) | - |
| 120 | **unk_float0** | 4 | Float number (little-endian) | - |
| 124 | **unk_float1** | 4 | Float number (little-endian) | - |
| 128 | **unk_float2** | 4 | Float number (little-endian) | - |
| 132 | **unk_U** | 4 | Float number (little-endian). Always == 1.0 | - |
| 136 | **unk_V** | 4 | Float number (little-endian). Always == 0.0 | - |
| 140 | **unk_W** | 4 | Float number (little-endian). Always == 0.0 | - |
| 144 | **unk_X** | 4 | 4-bytes unsigned integer (little endian). Always == 0x12f800 | - |
| 148 | **unk_Y** | 4 | 4-bytes unsigned integer (little endian). Always == 0x12f800 | - |
| 152 | **unk_Z** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | - |
| 156 | **mesh_name** | 28 | UTF-8 string | - |
### **Chunk00134012** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134012 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item type: [CompoundBlock](#compoundblock) | - |
### **Chunk00134013** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x134013 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **items** | custom_func\*8 | Array of `custom_func` items<br/>Item type: [CompoundBlock](#compoundblock) | - |
### **Chunk001340XX** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **index** | 1 | 1-byte unsigned integer. One of ['0x4', '0x17', '0x18', '0x19', '0x1a'] | - |
| 1 | **chunk_id** | 3 | 3-bytes unsigned integer (little endian). Always == 0x1340 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **Chunk80134008** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134008 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **NfsuMeshDescriptorChunk** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134010 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [Chunk00134011](#chunk00134011)<br/>- [Chunk00134012](#chunk00134012)<br/>- [Chunk00134013](#chunk00134013)<br/>- [Chunk80134100](#chunk80134100)<br/>- [Chunk001340XX](#chunk001340xx) | - |
### **Chunk80134001** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134001 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **sub_chunks** | custom_func\*8..? | Array of `custom_func` items<br/>Item size: 8..? bytes<br/>Item type: One of types:<br/>- [Chunk00134002](#chunk00134002)<br/>- [Chunk00134003](#chunk00134003)<br/>- [Chunk001340XX](#chunk001340xx)<br/>- [Chunk80134008](#chunk80134008) | - |
### **Chunk80134020** ###
#### **Size**: 8..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **chunk_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x80134020 | - |
| 4 | **chunk_length** | 4 | 4-bytes unsigned integer (little endian) | - |
| 8 | **payload** | chunk_length | Bytes | - |
### **NfsuVec3** ###
#### **Size**: 16 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **vector** | 12 | Point in 3D space (x,y,z), where each coordinate is: Float number (little-endian) | - |
| 12 | **pad** | 4 | Float number (little-endian). Always == 0.0 | - |
