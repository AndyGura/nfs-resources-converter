# **TNFSSE (PC) file specs** #

*Last time updated: 2026-10-10 06:18:34.021872+00:00*


# **Info by file extensions** #

**\*INFO** track settings with unknown purpose. That's a plain text file with some values, no problem to edit manually

**\*.AS4**, **\*.ASF**, **\*.EAS** audio + loop settings. [AsfAudio](#asfaudio)

**\*.BNK** sound bank. [SoundBank](#soundbank)

**\*.CFM** car 3D model. [WwwwBlock](#wwwwblock) with 4 entries:
- [OripGeometry](#oripgeometry) high-poly 3D model
- [ShpiBlock](#shpiblock) textures for high-poly model
- [OripGeometry](#oripgeometry) low-poly 3D model
- [ShpiBlock](#shpiblock) textures for low-poly model

**\*.FAM** track textures, props, skybox. [WwwwBlock](#wwwwblock) with 4 entries:
- [WwwwBlock](#wwwwblock) (background) contains few [ShpiBlock](#shpiblock) items, terrain textures
- [WwwwBlock](#wwwwblock) (foreground) contains few [ShpiBlock](#shpiblock) items, prop textures
- [ShpiBlock](#shpiblock) (skybox) contains horizon texture
- [WwwwBlock](#wwwwblock) (props) contains a series of consecutive [OripGeometry](#oripgeometry) + [ShpiBlock](#shpiblock) items, 3D props

**\*.FFN** bitmap font. [FfnFont](#ffnfont)

**\*.FSH** image archive. [ShpiBlock](#shpiblock)

**\*.PBS** player car physics. [PlayerCarPhysics](#playercarphysics), [compressed](eac_compressions.md)

**\*.PDN** car AI and crash body. [CarAiAndCrashBody](#caraiandcrashbody), [compressed](eac_compressions.md)

**\*.QFS** image archive. [ShpiBlock](#shpiblock), [compressed](eac_compressions.md)

**\*.RPL** race replay, car states and controls. [TnfsReplay](#tnfsreplay)

**\*.TGV** video, I just use ffmpeg to convert it

**\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. [TriMap](#trimap)

**GAMEDATA\CONFIG\CONFIG.DAT** Player name, best times, whether warrior car unlocked etc. [TnfsConfigDat](#tnfsconfigdat)

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
### **WwwwBlock** ###
#### **Size**: 8..? bytes ####
#### **Description**: A block-container with various data: image archives, geometries, other wwww blocks. If has ORIP 3D model, next item is always SHPI block with textures to this 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "wwww" | Resource ID |
| 4 | **num_items** | 4 | 4-bytes unsigned integer (little endian) | An amount of items |
| 8 | **items_descr** | num_items\*4 | Array of `num_items` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | An array of offsets to items data in file, relatively to wwww block start (where resource id string is presented) |
| 8 + num_items\*4 | **data_bytes** | up to end of block | Bytes | A part of block, where items data is located. Offsets are defined in previous block, lengths are calculated: either up to next item offset, or up to the end of this block. Possible item types:<br/>- [ShpiBlock](#shpiblock)<br/>- [OripGeometry](#oripgeometry)<br/>- [WwwwBlock](#wwwwblock) |
### **SoundBank** ###
#### **Size**: 512..? bytes ####
#### **Description**: A pack of SFX samples (short audios). Used mostly for car engine sounds, crash sounds etc. In TNFS all banks of a race share one 128-entry sample id table: the game loads the car bank, the opponent banks, the collision bank (`COLL*`), then `NFS_FMMB`, and a bank loaded later replaces the ids it has ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **items_descr** | 512 | Array of `128` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Offsets of `items` in the file, the array index being the sample index used by the game. Zero values ignored. Entries are not always stored in index order (in TNFS collision banks entry 0x50 precedes 0x3d-0x40) |
| 512 | **items** | (amount of non-zero elements in items_descr)\*72 | Array of `amount of non-zero elements in items_descr` items<br/>Item type: [SoundBankHeaderEntry](#soundbankheaderentry) | Sound bank entries in file order (see `items_descr` for their indices). EACS audio headers in them can be read easily because it contains file-wide offset to wave data, so it does not care wave data located, right after EACS header, or somewhere else like it is here in sound bank file |
| 512 + (amount of non-zero elements in items_descr)\*72 | **wave_data** | up to end of block | Bytes | Raw byte data, which is sliced according to provided offsets and used as wave data |
## **Geometries** ##
### **OripGeometry** ###
#### **Size**: 112..? bytes ####
#### **Description**: Geometry block for 3D model with few materials ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "ORIP" | Resource ID |
| 4 | **block_size** | 4 | 4-bytes unsigned integer (little endian) | Total ORIP block size in bytes |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian). Always == 0x2bc | Looks like always 0x01F4 in 3DO version and 0x02BC in PC TNFSSE. ORIP type? |
| 12 | **unk1** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 16 | **num_vrtx** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertices |
| 20 | **unk2** | 4 | Bytes | Unknown purpose |
| 24 | **vrtx_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertices |
| 28 | **num_uvs** | 4 | 4-bytes unsigned integer (little endian) | Amount of vertex UV-s (texture coordinates) |
| 32 | **uvs_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to vertex_uvs. Always equals to `112 + num_polygons*12` |
| 36 | **num_polygons** | 4 | 4-bytes unsigned integer (little endian) | Amount of polygons |
| 40 | **polygons_ptr** | 4 | 4-bytes unsigned integer (little endian). Always == 0x70 | An offset to polygons block |
| 44 | **identifier** | 12 | UTF-8 string | Some ID of geometry, don't know the purpose |
| 56 | **num_tex_ids** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture names |
| 60 | **tex_ids_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture names block. Always equals to `112 + num_polygons*12 + num_uvs*8` |
| 64 | **num_tex_nmb** | 4 | 4-bytes unsigned integer (little endian) | Amount of texture numbers |
| 68 | **tex_nmb_ptr** | 4 | 4-bytes unsigned integer (little endian) | An offset to texture numbers block |
| 72 | **num_ren_ord** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in render_order block |
| 76 | **ren_ord_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of render_order block. Always equals to `tex_nmb_ptr + num_tex_nmb*20` |
| 80 | **vmap_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of polygon_vertex_map block |
| 84 | **num_fxp** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in fx_polys block |
| 88 | **fxp_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of fx_polys block. Always equals to `tex_nmb_ptr + num_tex_nmb*20 + num_ren_ord*28` |
| 92 | **num_lbl** | 4 | 4-bytes unsigned integer (little endian) | Amount of items in labels block |
| 96 | **lbl_ptr** | 4 | 4-bytes unsigned integer (little endian) | Offset of labels block. Always equals to `tex_nmb_ptr + num_tex_nmb*20 + num_ren_ord*28 + num_fxp*12` |
| 100 | **unknowns1** | 12 | Bytes | Unknown purpose |
| 112 | **polygons** | num_polygons\*12 | Array of `num_polygons` items<br/>Item type: [OripPolygon](#orippolygon) | A block with polygons of the geometry. Probably should be a start point when building model from this file |
| 112 + num_polygons\*12 | **unk_uvs** | up to offset uvs_ptr | Padding bytes | Padding up to `uvs_ptr`, normally empty |
| uvs_ptr | **vertex_uvs** | num_uvs\*8 | Array of `num_uvs` items<br/>Item size: 8 bytes<br/>Item type: Texture coordinates for vertex, where each coordinate is: 4-bytes unsigned integer (little endian). The unit is a pixels amount of assigned texture. So it should be changed when selecting texture with different size | A table of texture coordinates. Items are retrieved by index, located in vmap |
| uvs_ptr + num_uvs\*8 | **unk_tex_ids** | up to offset tex_ids_ptr | Padding bytes | Padding up to `tex_ids_ptr`, normally empty |
| tex_ids_ptr | **tex_ids** | num_tex_ids\*20 | Array of `num_tex_ids` items<br/>Item type: [OripTextureName](#oriptexturename) | A table of texture references. Items are retrieved by index, located in polygon item |
| tex_ids_ptr + num_tex_ids\*20 | **offset** | up to offset tex_nmb_ptr | Padding bytes | In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in case of DIABLO.CFM it's length is equal to -3, meaning that last 3 bytes from texture names block are reused by next block |
| tex_nmb_ptr | **tex_nmb** | num_tex_nmb\*20 | Array of `num_tex_nmb` items<br/>Item size: 20 bytes<br/>Item type: Array of `20` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| tex_nmb_ptr + num_tex_nmb\*20 | **unk_ren_ord** | up to offset ren_ord_ptr | Padding bytes | Padding up to `ren_ord_ptr`, normally empty |
| ren_ord_ptr | **render_order** | num_ren_ord\*28 | Array of `num_ren_ord` items<br/>Item type: [RenderOrderBlock](#renderorderblock) | Render order. The exact mechanism how it works is unknown |
| ren_ord_ptr + num_ren_ord\*28 | **unk_fxp** | up to offset fxp_ptr | Padding bytes | Padding up to `fxp_ptr`, normally empty |
| fxp_ptr | **fx_polys** | num_fxp\*12 | Array of `num_fxp` items<br/>Item size: 12 bytes<br/>Item type: 12-bytes record, first 8 bytes is null-terminated UTF-8 string, last 4 bytes is an unsigned integer (little-endian). Used by ORIP `fx_polys` (index is a vertex index) and `labels` (index is a polygon index) | Named points of the model for visual effects, in high-poly car models (CFM). Despite the name, `index` is the index of an item of `vertices`, not of a polygon. Names (the case differs between cars: F512M, F512TR, TRAFFC and WARRIOR use lower case): `FL0`, `FL1`, `FR0`, `FR1`, `RL0`, `RL1`, `RR0`, `RR1` are the ground contact points of the wheels (front/rear, left/right), 0 at the front edge of the wheel, 1 at the rear edge (the bottom corners of the wheel polygon labelled `lt_frnt`, `rt_rear`...); guess: sources of tyre smoke, dust and skid marks. `smok` is a point at the engine: on the hood of front-engined cars (DVIPER, CZR1, MRX7, TSUPRA), at the exhaust or the engine lid of the others; guess: source of engine smoke and fire of a wrecked car. `d` (only in the M*.CFM models) is a point near the bottom of the front left wheel, unknown purpose. DVIPER has one more entry with garbage name "\x02" (the top of a wheel polygon). The gg-web-engine export writes every entry as a dummy "fx_<name>" at the vertex, with properties `fx` (the name) and `vertex` (the index), skipping entries with a non-printable name like "\x02" |
| fxp_ptr + num_fxp\*12 | **unk_lbl** | up to offset lbl_ptr | Padding bytes | Padding up to `lbl_ptr`, normally empty |
| lbl_ptr | **labels** | num_lbl\*12 | Array of `num_lbl` items<br/>Item size: 12 bytes<br/>Item type: 12-bytes record, first 8 bytes is null-terminated UTF-8 string, last 4 bytes is an unsigned integer (little-endian). Used by ORIP `fx_polys` (index is a vertex index) and `labels` (index is a polygon index) | Named polygons of high-poly car models (CFM), `index` is the index of an item of `polygons`. Names: `lt_frnt`, `rt_frnt`, `lt_rear`, `rt_rear`: the outer side of the wheels (left/right, front/rear), mostly untextured (guess: the game draws the tyre textures `tyr*` there); `bkll` / `bklr`: left / right rear light (guess: lit when braking); `bott`: a horizontal quad over the whole underside of the body of the simple traffic car models (texture `bott`), purpose unknown. Guesses: `bacr` (P911) the centre part of the rear light bar; `mm` (LDIABLO; garbage name "\x01" on the same polygon of LDIABL) a two-sided quad at the inner side of the front right wheel (texture `circ`); `W` (TRAFFC, WARRIOR) a triangle at the top rear left corner of the body (texture `abox`); COPMUST: `hll0` / `hlr0` headlights, `bkl0` / `bkr0` rear lights, `lfl0` / `lfr0` and `lrl0` / `lrr0` the front and rear left / right parts of the siren light bar on the roof, flashed by the game |
| lbl_ptr + num_lbl\*12 | **unk_vrtx** | up to offset vrtx_ptr | Padding bytes | Padding up to `vrtx_ptr`, normally empty |
| vrtx_ptr | **vertices** | num_vrtx\*12 | One of types:<br/>- Array of `num_vrtx` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 7 bits is a fractional part<br/>- Array of `num_vrtx` items<br/>Item size: 12 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 4 bits is a fractional part | A table of mesh vertices 3D coordinates. For cars uses 32:7 points, else 32:4. The unit is meter |
| vrtx_ptr + num_vrtx\*12 | **unk_vmap** | up to offset vmap_ptr | Padding bytes | Padding up to `vmap_ptr`, normally empty |
| vmap_ptr | **vmap** | ? | Array of `?` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | A LUT for both 3D and 2D vertices. Every item is an index of either item in vertices or vertex_uvs. When building 3D vertex, polygon defines offset_3d, a lookup to this table, and value from here is an index of item in vertices. When building UV-s, polygon defines offset_2d, a lookup to this table, and value from here is an index of item in vertex_uvs |
### **OripPolygon** ###
#### **Size**: 12 bytes ####
#### **Description**: A geometry polygon ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **polygon_type** | 1 | 1-byte unsigned integer | Huh, that's a srange field. From my tests, if it is xxx0_0011, the polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only one polygon for entire TNFS with type == 2 in burnt sienna props. If ignore this polygon everything still looks great |
| 1 | **mapping** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: two_sided<br/>1: flip_normal<br/>4: use_uv</details> | Rendering properties of the polygon |
| 2 | **texture_index** | 1 | 1-byte unsigned integer | The index of item in ORIP's tex_ids block |
| 3 | **unk** | 1 | 1-byte unsigned integer | Unknown purpose |
| 4 | **offset_3d** | 4 | 4-bytes unsigned integer (little endian) | The index in vmap ORIP's table. This index represents first vertex of this polygon, so in order to determine all vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. Look at vmap description for more info |
| 8 | **offset_2d** | 4 | 4-bytes unsigned integer (little endian) | The same as offset_3d, also points to vmap, but used for texture coordinates. Look at vmap description for more info |
### **OripTextureName** ###
#### **Size**: 20 bytes ####
#### **Description**: A settings of the texture. From what is known, contains name of bitmap (not always a correct UTF-8) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **type** | 8 | Bytes | Unknown purpose |
| 8 | **file_name** | 4 | UTF-8 string | Name of bitmap in SHPI block |
| 12 | **unknown** | 8 | Bytes | Unknown purpose |
### **RenderOrderBlock** ###
#### **Size**: 28 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **identifier** | 8 | UTF-8 string | identifier ('NON-SORT', 'inside', 'surface', 'outside') |
| 8 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | 0x8 for 'NON-SORT' or 0x1 for the others |
| 12 | **polygons_amount** | 4 | 4-bytes unsigned integer (little endian) | Polygons amount (3DO). For TNFSSE sometimes too big value |
| 16 | **polygon_sum** | 4 | 4-bytes unsigned integer (little endian) | 0 for 'NON-SORT'; block’s 10 size for 'inside'; equals block’s 10 size + number of polygons from ‘inside’ = XXX for 'surface'; equals XXX + number of polygons from 'surface' for 'outside'; (Description for 3DO orip file, TNFSSE version has only 9 blocks!) |
| 20 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 24 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
## **Maps** ##
### **TriMap** ###
#### **Size**: 90664..? bytes ####
#### **Description**: Map TRI file, represents terrain mesh, road itself, props locations etc. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | 4-bytes unsigned integer (little endian). Always == 0x11 | Resource ID |
| 4 | **loop_chunk** | 2 | 2-bytes unsigned integer (little endian) | Index of chunk, on which game should use chunk #0 again. So for closed tracks this value should be equal to `num_chunks`, for open tracks it is 0 |
| 6 | **num_chunks** | 4 | 4-bytes unsigned integer (little endian) | number of terrain chunks (max 600) |
| 10 | **unk0** | 2 | 2-bytes unsigned integer (little endian). Always == 0x6 | Unknown purpose |
| 12 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Unknown purpose |
| 24 | **unknowns0** | 12 | Array of `12` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 36 | **chunks_size** | 4 | 4-bytes unsigned integer (little endian) | Size of terrain array in bytes (num_chunks * 0x120) |
| 40 | **fence_texture_id** | 4 | 4-bytes unsigned integer (little endian) | The texture id of the track's fence (`fence.texture_id` + 32 of the terrain chunks with a fence, or of most of them). The texture loader (Win95 SE `tnfs_render_load_track_textures` 0x44c36c, reading the low 16 bits) uses it on closed tracks only: it gives the ids (value // 3) * 3 + 0, 1 and 2 the FAM bitmaps `ga00`, `ga10` and `ga20` instead of `%02d%c0` |
| 44 | **lookup_table** | 2400 | Array of `600` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | 600 consequent numbers, each value is previous + 288. Looks like a space needed by the original NFS engine |
| 2444 | **road_spline** | 86400 | Array of `2400` items<br/>Item type: [RoadSplinePoint](#roadsplinepoint) | Road spline is a series of points in 3D space, located at the center of road. Around this spline the track terrain mesh is built. TRI always has 2400 elements, however it uses only amount of vertices, equals to (num_chunks * 4), after them records filled with zeros. For opened tracks, finish line will be always located at spline point (num_chunks * 4 - 179) |
| 88844 | **ai_info** | 1800 | Array of `600` items<br/>Item type: [AIEntry](#aientry) | AI behaviour settings per terrain chunk. Always has 600 items, only the first `num_chunks` are used |
| 90644 | **num_prop_descr** | 4 | 4-bytes unsigned integer (little endian) | Amount of prop descriptions |
| 90648 | **num_props** | 4 | 4-bytes unsigned integer (little endian) | Amount of props |
| 90652 | **objs_hdr** | 4 | UTF-8 string. Always == "SJBO" | Header of the props section |
| 90656 | **unk1** | 4 | 4-bytes unsigned integer (little endian). Always == 0x428c | Unknown purpose |
| 90660 | **unk2** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
| 90664 | **prop_descr** | num_prop_descr\*16 | Array of `num_prop_descr` items<br/>Item type: [PropDescr](#propdescr) | Prop descriptions: 3D models, bitmaps and two-sided bitmaps, which can be placed on the map |
| 90664 + num_prop_descr\*16 | **props** | num_props\*16 | Array of `num_props` items<br/>Item type: [MapProp](#mapprop) | Props placed on the map. Unused trailing items have `road_point_idx` == -1 |
| 90664 + num_prop_descr\*16 + num_props\*16 | **terrain** | num_chunks\*288 | Array of `num_chunks` items<br/>Item type: [TerrainEntry](#terrainentry) | Terrain chunks, one per 4 road spline points |
### **RoadSplinePoint** ###
#### **Size**: 36 bytes ####
#### **Description**: The description of one single point of road spline. Thank you jeff-1amstudios for your [OpenNFS1](https://github.com/jeff-1amstudios/OpenNFS1) project ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **left_verge** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to the left edge of road. After this point the grip decreases |
| 1 | **right_verge** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to the right edge of road. After this point the grip decreases |
| 2 | **left_barrier** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to invisible wall on the left |
| 3 | **right_barrier** | 1 | 8-bit real number (little-endian, not signed), where last 3 bits is a fractional part | The distance to invisible wall on the right |
| 4 | **num_lanes** | 1 | Array of `2` sub-byte numbers. Each number consists of 4 bits | Amount of lanes. First number is amount of oncoming lanes, second number is amount of ongoing ones |
| 5 | **fence_flag** | 1 | Array of `2` sub-byte numbers. Each number consists of 4 bits | Flags whether there is fence or not. First number is fence on left side, second number is fence on right side. Used for physics simulation: only the fence collision (Win95 SE 0x430600) and `tnfs_collision_main` read it. Rendering ignores it: fences are drawn from the `fence` byte of the terrain chunks |
| 6 | **shoulder_surface_type** | 1 | Array of `2` sub-byte numbers. Each number consists of 4 bits | Surface type of the road shoulders, the areas between the verge distance and the barrier: first number for the left shoulder, second number for the right one (the game takes `>> 4` and `& 0xf` of this byte). The car gets this surface while it is between `left_verge` / `right_verge` and the barrier, 0 elsewhere. It is an index into the game's road surface table (grip, drag, is_unpaved): 0 is tarmac like the road, 1 and 2 are unpaved shoulders with 20 times the velocity drag. Higher values read past the table: values above 3 cause unbearable slide in the game and make it impossible to return back to road, values around the maximum (15) cause lags and even crashes. Also used for sound: a non-zero value turns the player's wind loop into a gravel rumble (pitch value 0x18, volume +25%), an unpaved surface picks the gravel tyre squeal and dust. Decoded by [tnfs-1995](https://github.com/marcos2250/tnfs-1995) (`shoulder_surface_type`; DOS sound code 0x668ab) |
| 7 | **item_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): lane_split<br/>1 (0x1): default_0<br/>2 (0x2): lane_merge<br/>3 (0x3): default_1<br/>4 (0x4): tunnel<br/>5 (0x5): cobbled_road<br/>7 (0x7): right_tunnel_A9_A2<br/>8 (0x8): no_sky<br/>9 (0x9): left_tunnel_A4_A7<br/>11 (0xb): unk_autumn_valley_tribunes<br/>12 (0xc): left_tunnel_A4_A8<br/>13 (0xd): left_tunnel_A5_A8<br/>14 (0xe): waterfall_audio_left_channel<br/>15 (0xf): waterfall_audio_right_channel<br/>16 (0x10): unk_al1_uphill<br/>17 (0x11): transtropolis_noise_audio<br/>18 (0x12): water_audio</details> | Modifier of this point. Affects terrain geometry and/or some gameplay features. Effects found in the game code ([tnfs-1995](https://github.com/marcos2250/tnfs-1995) `tnfs_track_item_mode_flags`, PSX 0x80030fe8, DOS 0x5b2b9): 4, 7, 9, 12 and 13 set the car's in-tunnel flag (wind loop +20 volume and pitch value 0x5e; on PSX the voices whose patch has the reverb flag get the SPU reverb; the police siren plays `NFS_FMMB.BNK` sample 0x64 along with 0x62; the DOS camera 0x6b5a5 skips the horizon for 4, 7, 9 and 8). 5 is cobbles: the wind loop pitch wobbles between 0x40 and 0x5e with speed; a side with a fence (`fence_flag`) also gets a different fence offset in 3D crash collisions unless the mode is 5. 14 / 15 are a waterfall to the left / right: they play the waterfall loop (collision bank sample 0x3e on mixer channel 0xb), panned hard left / right and fading in and out by 5 per tick. 8 only means "no sky": the DOS camera skips the horizon, the PSX sky drawing (0x800357ec) hides the sky when the slices -0xe and -9 from the camera are both mode 8; the road renders like plain road, and the second engine flag 8 sets next to the in-tunnel one is never read. Values in the game tracks besides 1 and 3: 0 / 2 at single points, 4 in most tracks, 5 in AL2, TR4, TR7, 7 in CL2, 8 in CL3, 9 in AL3, 11 in TR2, 12 and 13 in TR3, 14 in TR2 and TR3, 15 in TR3, 16 in AL1 and TR3, 17 in TR7, 18 in TR6 |
| 8 | **position** | 12 | Point in 3D space (x,y,z), where each coordinate is: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Coordinates of this point in 3D space. The unit is meter |
| 20 | **slope** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Slope of the road at this point (angle if road goes up or down) |
| 22 | **slant** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Perpendicular angle of road |
| 24 | **orientation** | 2 | EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees | Rotation of road path, if view from the top. Equals to atan2(next_x - x, next_z - z) |
| 26 | **unk1** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 28 | **side_normal** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 16 bits is a fractional part | Side normal vector |
| 34 | **unk2** | 2 | 2-bytes unsigned integer (little endian). Always == 0x0 | Unknown purpose |
### **PropDescr** ###
#### **Size**: 16 bytes ####
#### **Description**: The description of map prop: everything except terrain (road signs, buildings etc.) Thanks to jeff-1amstudios and his [OpenNFS1](https://github.com/jeff-1amstudios/OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202) project ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **flags** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>2: is_animated</details> | Different modes of prop |
| 1 | **type** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>1 (0x1): model<br/>4 (0x4): bitmap<br/>6 (0x6): two_sided_bitmap</details> | Type of prop |
| 2 | **data** | 14 | Type according to enum `type`:<br/>- [ModelPropDescrData](#modelpropdescrdata)<br/>- [BitmapPropDescrData](#bitmappropdescrdata)<br/>- [TwoSidedBitmapPropDescrData](#twosidedbitmappropdescrdata)<br/>- Bytes | Settings of the prop. Block class picked according to `type` |
### **MapProp** ###
#### **Size**: 16 bytes ####
#### **Description**: The prop on the map. For instance: exactly the same road sign used 5 times on the map. In this case file will have 1 PropDescr for this road sign and 5 MapProps ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **road_point_idx** | 4 | 4-bytes signed integer (little endian) | Index of point of the road path spline, where prop is located. Sometimes has too big value, I skip those instances for now and it seems to look good. Probably should consider this value to be 16-bit integer, having some unknown 16-integer as next field. Also, why it is signed? |
| 4 | **prop_descr_idx** | 1 | 1-byte unsigned integer | Index of prop description, which should be used for this prop. Sometimes has too big value, I use object index % amount of prop descriptions for now and it seems to look good |
| 5 | **rotation** | 1 | EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees | Y-rotation, relative to rotation of referenced road spline vertex |
| 6 | **flags** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 10 | **position** | 6 | Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 8 bits is a fractional part | Position in 3D space, relative to position of referenced road spline vertex. The unit is meter |
### **TerrainEntry** ###
#### **Size**: 288 bytes ####
#### **Description**: The terrain model around 4 spline points. It has good explanation in original [Denis Auroux NFS file specs](http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "TRKD" | Resource ID |
| 4 | **block_length** | 4 | 4-bytes unsigned integer (little endian) | Block length in bytes |
| 8 | **block_number** | 4 | 4-bytes unsigned integer (little endian). Always == 0x0 | Block number, always 0 |
| 12 | **unknown** | 1 | 1-byte unsigned integer. Always == 0x0 | Unknown purpose |
| 13 | **fence** | 1 | Sub-byte compound block:<br/>1-bit flag "has_left_fence"<br/>1-bit flag "has_right_fence"<br/>1-bit flag "is_low"<br/>5-bits int "texture_id" | Fence of this chunk, as the game draws it (`tnfs_render_track_fence`: Win95 SE 0x44a2b4, DOS 0x69719, PSX 0x80046484). It is the only thing that decides fence drawing: the road spline points' `fence_flag` is for collisions. One vertical quad per node to the next node (the last one to the next chunk's first node) on each side with a flag, from terrain vertices up by 2 m, or by 0.9 m (0xe666 in 16.16) for a low fence. The bottom vertex is picked by the `item_mode` of the chunk's first node: the right fence stands on A2; the left one on A7 for item modes 3, 4, 5, 6, 8, 10 and 11, on A8 for 1 and 14..18, on A7 at the first node and A8 after it for 0 (lane split), on A8 and at the next chunk's first node on A7 for 2 (lane merge). Tunnel modes 7, 9, 12 and 13 draw no fence near the camera (SE draws A2 / A8 at mid and far distance only). The texture id is `texture_id` + 32 (same id space as `texture_ids`; on closed tracks the ids of `fence_texture_id` // 3 are replaced by the `ga00` / `ga10` / `ga20` bitmaps); SE draws no fence when the track's FAM has no bitmap for it (TR4's 0xb7 chunks, id 55 = `18B0`). The fence maps the texture like the road polygon of its node: half the texture width per node, full height |
| 14 | **texture_ids** | 10 | Array of `10` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Texture ids to be used for terrain |
| 24 | **rows** | 264 | Array of `4` items<br/>Item size: 66 bytes<br/>Item type: Array of `11` items<br/>Item size: 6 bytes<br/>Item type: Point in 3D space (x,y,z), where each coordinate is: 16-bit real number (little-endian, signed), where last 7 bits is a fractional part | Terrain vertex positions. The unit is meter |
### **AIEntry** ###
#### **Size**: 3 bytes ####
#### **Description**: The record describing AI behavior at given terrain chunk ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **top_speed** | 1 | 1-byte unsigned integer | Max speed among all AI drivers in m/s |
| 1 | **legal_speed** | 1 | 1-byte unsigned integer | Minimum speed in m/s that makes cops start pursuit |
| 2 | **safe_speed** | 1 | 1-byte unsigned integer | Max traffic speed in m/s. Oncoming traffic does not obey it |
### **ModelPropDescrData** ###
#### **Size**: 14 bytes ####
#### **Description**: Map prop settings if it is a 3D model ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | An index of prop in the track FAM file |
| 1 | **resource_id_2** | 1 | 1-byte unsigned integer | Seems to always be equal to `resource_id`, except for one prop on map CL1, which is not used on map |
| 2 | **unk0** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part. Always == 1.5 | Unknown purpose |
| 6 | **unk1** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | The purpose is unknown. Every single entry in TNFS files equals to 1.5 (0x00_80_01_00) just like `unk0`, except for one prop on CL1, which has broken texture palette and which is not used on the map anyways |
| 10 | **unk2** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part. Always == 0x3 | Unknown purpose |
### **BitmapPropDescrData** ###
#### **Size**: 14 bytes ####
#### **Description**: Map prop settings if it is a bitmap ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | Represents texture id. How to get texture name from this value [explained](http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) well by Denis Auroux |
| 1 | **resource_id_2** | 1 | 1-byte unsigned integer | Oftenly equals to `resource_id`, but can be different |
| 2 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 6 | **frame_count** | 1 | 1-byte unsigned integer | Frame amount for animated object. Ignored if flag `is_animated` not set |
| 7 | **animation_interval** | 1 | TNFS time field. 1-byte unsigned integer, equals to amount of ticks (amount of seconds * 60) | Interval between animation frames in seconds |
| 8 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 9 | **unk1** | 1 | 1-byte unsigned integer | Unknown purpose |
| 10 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters |
### **TwoSidedBitmapPropDescrData** ###
#### **Size**: 14 bytes ####
#### **Description**: Map prop settings if it is a two-sided bitmap (fake 3D model) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer | Represents texture id. How to get texture name from this value [explained](http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) well by Denis Auroux |
| 1 | **resource_id_2** | 1 | 1-byte unsigned integer | Texture id of second sprite, rotated 90 degrees. Logic to determine texture name is the same as for resource_id |
| 2 | **width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters |
| 6 | **width_2** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Width in meters of second bitmap |
| 10 | **height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height in meters |
## **Physics** ##
### **PlayerCarPhysics** ###
#### **Size**: 1912 bytes ####
#### **Description**: Player car physics: the full physics specification of a car the player can drive (`SIMDATA/CARSPECS/*.PBS`, QFS-compressed, 1912 bytes uncompressed). Loaded by `Fiziks_PreInitCar` (SE 0x4400f4, DOS 0x63e72, PSX 0x80038ea4); the game keeps the same layout in memory (DOS, SE, PSX). Readers are named as in [tnfs-1995](https://github.com/marcos2250/tnfs-1995) with Win95 SE addresses; "not read" = no reader in the DOS, SE and PSX executables. Physics ticks are 1/30 s, angles are 24-bit (0x1000000 = full turn). Rally mode changes some fields in memory after loading (DOS, SE): rear grip table := front, `unknown_0x320` and `thrust_scale` halved and their inverses recomputed, `friction_f/r` and `max_brake_force_1/2` halved, `cog_height` x 1.5, `efficiency` x 0x14c/256 on track 3, else x 0x133/256. PSX rally: `lat_acc_cutoff` x 0.625, `cog_height` x 7/4, `efficiency` x a per-track value, `drive_bias` = 0.5. Thanks to [Five-Damned-Dollarz](https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e) and [marcos2250](https://github.com/marcos2250/tnfs-1995/blob/main/tnfs_files.c) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **mass_front** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Mass on the front axle (kg). Front weight fraction = `mass_front * inv_mass` (`Fiziks_InitCar`, SE 0x42ff60). Equals `mass_rear` in all files |
| 4 | **mass_rear** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Mass on the rear axle (kg) |
| 8 | **mass** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Total car mass (kg), `mass_front + mass_rear`. Only feeds car fields that nothing reads (`Fiziks_InitCar`): the game uses `inv_mass` |
| 12 | **inv_mass_f** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | `1 / mass_front`, rounded down. Only feeds a car field that nothing reads |
| 16 | **inv_mass_r** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | `1 / mass_rear`, rounded down. Only feeds a car field that nothing reads |
| 20 | **inv_mass** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | `1 / mass`, rounded down. Used for the weight distribution, drag / mass (`Fiziks_InitCar`) and the torque table (`tnfs_load_torque_table`, SE 0x409990) |
| 24 | **drive_bias** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Front share of the drive force, 0.0 = RWD, 1.0 = FWD (`tnfs_physics_update`, SE 0x430cb0). 0 also enables the burnout rule of `tnfs_engine_thrust` (SE 0x42f138). 0 in all files but LDIABL (0.35) and TRAFFC (0.4) |
| 28 | **brake_bias_f** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Front share of the pedal brake force, 0.0-1.0 (`tnfs_physics_update`); the rear gets the rest |
| 32 | **brake_bias_r** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Rear share of the brake force, `1 - brake_bias_f` (raw 65536 - `brake_bias_f` in all files). Not read: the game uses total - front |
| 36 | **cog_height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Height of the centre of gravity (m). Weight transfer factor = `cog_height * wheel_base_inv` (`Fiziks_InitCar`): moves grip between front and rear under longitudinal force. Rally mode x 1.5 (PSX x 7/4) |
| 40 | **max_brake_force_1** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Cap of the absolute longitudinal tire force while braking (brake > 100 or handbrake) below 26.8 m/s (60 mph); also the brake force when the car rolls against the selected gear (`tnfs_physics_update`). Deceleration (m/s²) = this * `force_to_accel` (~10 for ANSX). Rally mode halves it |
| 44 | **max_brake_force_2** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Same cap from 26.8 to 40 m/s; above 40 m/s the larger of `max_brake_force_1` and this. Differs from `max_brake_force_1` in 6 of 9 files (ANSX 25.5 / 37.5). Rally mode halves it |
| 48 | **max_tire_coeff** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Maximal tire coefficient (0.84-1.35). Not read |
| 52 | **drag** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Air drag (kg/m, ½ * air density * drag coefficient * frontal area). `Fiziks_InitCar` replaces it in memory with `drag * inv_mass`; deceleration = that * surface factor * speed² (`tnfs_drag_force`, SE 0x42f630) |
| 56 | **top_speed** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Top speed (m/s). Above it `tnfs_physics_update` raises the drag so that it cancels the thrust, except on track id 6 |
| 60 | **efficiency** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Drivetrain efficiency (0.5-2.0), multiplies the torque table (`tnfs_load_torque_table`); x 0xf8/256 with the automatic gearbox. `Fiziks_PreInitCar` sets it to 0 on a `checksum` mismatch, and when the file `By_R&T` can be created in the CARSPECS folder (DOS flag 0xf7bbe, SE 0x4c5ccc; probably an anti-copy trap, the folder being read-only on the CD). Rally mode: x 0x14c/256 on track 3, else x 0x133/256 |
| 64 | **wheel_base** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Distance between the front and rear axles (m): car wheelbase and yaw factors |
| 68 | **wheel_base_inv** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | `1 / wheel_base`, rounded down. Weight transfer factor (`Fiziks_InitCar`) |
| 72 | **wheel_track** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Distance between the left and right wheels (m). Not read |
| 76 | **wheel_track_inv** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | `1 / wheel_track`, rounded down. Not read |
| 80 | **rear_weight_fraction** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Rear weight fraction, `mass_rear / mass` (0.5 in all files). Not read |
| 84 | **mps_to_rpm** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Engine rpm = speed (m/s) * this * gear ratio (`tnfs_engine_rev_limiter` SE 0x42ee68, `tnfs_engine_auto_shift_change` SE 0x4098a0, `tnfs_engine_thrust`) |
| 88 | **num_gears** | 4 | 4-bytes unsigned integer (little endian) | Number of used `gear_ratios` entries: reverse, neutral and `num_gears - 2` forward gears. Upshifts stop at gear index `num_gears - 3` (`tnfs_control_shift_gears` SE 0x438c84, `tnfs_engine_auto_shift_change`) |
| 92 | **final_drive** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Final drive ratio. Only read by `tnfs_load_torque_table` |
| 96 | **wheel_radius** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Wheel radius (m). Not read, the game uses `inv_wheel_rad` |
| 100 | **inv_wheel_rad** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | `1 / wheel_radius`, rounded down. Only read by `tnfs_load_torque_table` |
| 104 | **gear_ratios** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Gear ratios, index = selected gear + 2: [0] reverse (negative), [1] neutral, [2] first gear and up (`tnfs_engine_rev_limiter`, `tnfs_engine_auto_shift_change`, `tnfs_engine_thrust`). The neutral ratio only gives the wheel rpm in neutral. The first `num_gears` entries are used, the rest is garbage |
| 136 | **num_torques** | 4 | 4-bytes unsigned integer (little endian). Always <= 60 | Number of used `torques` entries (51; 41 in P911), at most 60, the length of `torques`. The game loads that many entries and uses the last one for any higher rpm (`tnfs_load_torque_table`, `tnfs_engine_get_torque`) |
| 140 | **roll_stiff_f** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Front roll stiffness (10000.0 in all files). Not read |
| 144 | **roll_stiff_r** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Rear roll stiffness (10000.0 in all files). Not read |
| 148 | **roll_axis_y** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Roll axis height (m). Not read |
| 152 | **front_roll_stiffness_2** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | 0.5 in all files. Not read |
| 156 | **rear_roll_stiffness_2** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | 0.5 in all files. Not read |
| 160 | **weight_transfer_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | 0.001-0.27. Not read: the weight transfer factor of the game is `cog_height * wheel_base_inv` |
| 164 | **slip_cutoff** | 4 | 4-bytes signed integer (little endian), angle: 0x1000000 means 360 degrees | Max tire slip angle, 24-bit angle: 0x1FE667 = 44.9° in all files. Larger slip angles are clamped to it and set skid bit 1 (`tnfs_tire_forces`, SE 0x42fb88) |
| 168 | **normal_loss** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Normal coefficient loss. Not read |
| 172 | **max_rpm** | 4 | 4-bytes unsigned integer (little endian) | Engine redline rpm (`rpm_redline` in the game engine). Rpm limit with the throttle = this * throttle / 256 (`tnfs_engine_rev_limiter`, `tnfs_engine_thrust`). Engine sound pitch value = rpm * 127 / (max_rpm + 2000), at most 127 (`tnfs_sfx_engine_player`, SE 0x4444b8, DOS 0x668ab). Tachometer needle: min(rpm, max_rpm + 980) * 600 / max_rpm (SE 0x42221c, 0x420d0c) |
| 176 | **min_rpm** | 4 | 4-bytes unsigned integer (little endian) | Engine idle rpm (`rpm_idle`), engine rpm floor (`tnfs_engine_rev_limiter`) |
| 180 | **torques** | 480 | Array of `60` items<br/>Item size: 8 bytes<br/>Item type: Two 32bit unsigned integers (little-endian): rpm and torque (N*m) | Engine torque by rpm, the first `num_torques` entries are used, the rest is garbage. The game reads only the first rpm and assumes 200 rpm steps (true in all files): entry = (rpm rounded to 200 - rpm[0]) / 200 (`tnfs_engine_get_torque`, SE 0x409a04). `tnfs_load_torque_table` turns each torque in memory into the 16.16 acceleration per unit of gear ratio, `torque * final_drive * efficiency * inv_wheel_rad * inv_mass` |
| 660 | **upshifts** | 28 | Array of `7` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Automatic gearbox rpm: [g] = upshift from gear index g to g + 1; it shifts down when the rpm in the lower gear would be below 15/16 of [g - 1] (`tnfs_engine_auto_shift_change`). `tnfs_engine_thrust` uses [1] - 500 as the burnout rpm limit. The first `num_gears - 3` entries are used, the rest is garbage |
| 688 | **gear_efficiency** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 8 bits is a fractional part | Per-gear multiplier of the wheel torque, index = selected gear + 2 like `gear_ratios` (`tnfs_engine_thrust`). The first `num_gears` entries are used, the rest is garbage |
| 720 | **inertia_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | 0.5 in all files. Only feeds the car moment of inertia (`Fiziks_InitCar`), which nothing reads |
| 724 | **roll_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Visual body roll from the lateral acceleration (`tnfs_physics_update`), no unit |
| 728 | **pitch_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Visual body pitch from the longitudinal acceleration (`tnfs_physics_update`), no unit |
| 732 | **friction_f** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Front tire friction coefficient: front grip = this * front weight fraction * 9.81 (`Fiziks_InitCar`). Rally mode halves it |
| 736 | **friction_r** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Rear tire friction coefficient, like `friction_f`. Rally mode halves it |
| 740 | **body_len** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Body length (m). Copied to the car length, then overwritten by `half_length * 2` of the car PDN in `tnfs_ai_init_car` (SE 0x4407b8): no effect, all 9 cars have PDN sizes |
| 744 | **body_width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Body width (m). Overwritten by `half_width * 2` of the car PDN, like `body_len` |
| 748 | **auto_steer** | 4 | 4-bytes signed integer (little endian) | 24-bit angle per m/s (983 in all files). Digital steering, wheel centred, moving forward: the auto-steer target (road heading) is taken only if its absolute value < this * speed (`tnfs_control_steering_a`, SE 0x438954) |
| 752 | **steer_mult** | 4 | 4-bytes unsigned integer (little endian) | Auto-steer ramp multiplier shift (1). Not read |
| 756 | **steer_div** | 4 | 4-bytes unsigned integer (little endian) | Auto-steer ramp divider shift (1). Not read |
| 760 | **steer_model** | 4 | 4-bytes unsigned integer (little endian) | Steering model (2). Not read |
| 764 | **steer_vel** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Auto-steer velocities (2, 4, 8, 16). Only [1] is read: steering rate per tick = min(`steer_vel_ramp` - min(speed * `steer_vel_att`, 1.5), 1.6) * [1] (`tnfs_control_steering_a`) |
| 780 | **steer_vel_ramp** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Base steering rate (2.2-2.5), see `steer_vel` (`tnfs_control_steering_a`) |
| 784 | **steer_vel_att** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Steering rate reduction per m/s, at most 1.5 in total (`tnfs_control_steering_a`) |
| 788 | **steer_ramp_mult** | 4 | 4-bytes unsigned integer (little endian) | Shift count: steering rate << this when the target and the auto-steer angle are on the same side of the current angle (`tnfs_control_steering_a`) |
| 792 | **steer_ramp_div** | 4 | 4-bytes unsigned integer (little endian) | Shift count: steering rate >> this otherwise (`tnfs_control_steering_a`; SE and PSX only, DOS has no such branch) |
| 796 | **lat_acc_cutoff** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Max absolute lateral acceleration (m/s², 17.5-40), also the road grip increment (`tnfs_physics_update`). PSX rally mode x 0.625 |
| 800 | **unknown_0x320** | 4 | 32-bit real number (little-endian, signed), where last 8 bits is a fractional part | Equals `thrust_scale` in all files (2.5; TRAFFC 5.5, TSUPRA 2.7). Not read; rally mode (DOS, SE) halves it and recomputes `unknown_0x320_inv` |
| 804 | **unknown_0x320_inv** | 4 | 32-bit real number (little-endian, signed), where last 8 bits is a fractional part | `1 / unknown_0x320`, rounded down (raw 65536 / raw). Not read |
| 808 | **thrust_scale** | 4 | 32-bit real number (little-endian, signed), where last 8 bits is a fractional part | Thrust multiplier (`tnfs_engine_thrust`): 2.5, TRAFFC 5.5, TSUPRA 2.7. Rally mode halves it and recomputes `force_to_accel` |
| 812 | **force_to_accel** | 4 | 32-bit real number (little-endian, signed), where last 8 bits is a fractional part | `1 / thrust_scale`, rounded down (raw 65536 / raw): summed longitudinal tire force * this = acceleration (m/s²) (`tnfs_physics_update`) |
| 816 | **unknown_0x330** | 4 | 4-bytes unsigned integer (little endian) | 102 in all files. Not read |
| 820 | **has_abs** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Car has ABS if > 0 (1.0); ABS is on if this and the player option are both set (`Fiziks_PreInitCar`) |
| 824 | **has_tcs** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Car has traction control if > 0 (1.0), like `has_abs` |
| 828 | **throttle_on_ramp** | 4 | 4-bytes unsigned integer (little endian) | Throttle (0-255) rise per tick (`tnfs_control_throttle`, SE 0x438b70) |
| 832 | **throttle_off_ramp** | 4 | 4-bytes unsigned integer (little endian) | Throttle (0-255) fall per tick (`tnfs_control_throttle`) |
| 836 | **brake_on_ramp_1** | 4 | 4-bytes unsigned integer (little endian) | Brake (0-255) rise per tick, x 1.25, while the brake is below 144 (`tnfs_control_brake`, SE 0x438bc8) |
| 840 | **brake_on_ramp_2** | 4 | 4-bytes unsigned integer (little endian) | Brake rise per tick, x 1.25, from 144 up (`tnfs_control_brake`) |
| 844 | **brake_off_ramp_1** | 4 | 4-bytes unsigned integer (little endian) | Brake fall per tick while the brake is below 144 (`tnfs_control_brake`) |
| 848 | **brake_off_ramp_2** | 4 | 4-bytes unsigned integer (little endian) | Brake fall per tick from 144 up (`tnfs_control_brake`) |
| 852 | **shift_timer** | 4 | 4-bytes unsigned integer (little endian) | Ticks with the gear disengaged while shifting (`tnfs_control_shift_gears`, `tnfs_engine_auto_shift_control` SE 0x42ed94). Manual downshift: half of it; automatic N -> D: +1; F512TR (car model 4): +3 when (time & 0x31) == 0x10 |
| 856 | **rpm_dec** | 4 | 4-bytes unsigned integer (little endian) | Rpm fall per tick towards idle without throttle while the gear is disengaged, half in neutral (`tnfs_engine_rev_limiter`) |
| 860 | **rpm_acc** | 4 | 4-bytes unsigned integer (little endian) | Rpm rise per tick, x throttle / 256, while the gear is disengaged, half in neutral (`tnfs_engine_rev_limiter`) |
| 864 | **drop_rpm_dec** | 4 | 4-bytes unsigned integer (little endian) | In gear: engine rpm fall per tick towards the wheel rpm; / 8 while the rear wheels spin with throttle > 220 (`tnfs_engine_rev_limiter`) |
| 868 | **drop_rpm_inc** | 4 | 4-bytes unsigned integer (little endian) | In gear: engine rpm rise per tick towards the wheel rpm (`tnfs_engine_rev_limiter`; its branch multiplying this by a per-gear table is unreachable) |
| 872 | **neg_torque** | 4 | 4-bytes unsigned integer (little endian) | Engine braking: force = rpm difference * this / 256 * gear ratio, x 8 when the wheels drive the engine (`tnfs_engine_thrust`) |
| 876 | **incar_camera_height** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | In-car camera height (m, ~1.0) (in-car camera setup, SE 0x405630). Not read by PSX |
| 880 | **center_y** | 4 | 4-bytes unsigned integer (little endian) | In-car view vertical centre (pixels of 320x200): the in-car view windows get the y offset (center_y - 108) * screen height / 200 (in-car camera setup, SE 0x405630). Not read by PSX. The formula is certain, its meaning (projection centre) is an interpretation |
| 884 | **grip_table_f** | 512 | Array of `512` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Front tire grip by slip angle, grip = value / 128 (the game: value << 9 as 16.16). Index = slip angle (24-bit) >> 12: 0.088° steps over 0-45° (`tnfs_tire_slide_table`, read in `tnfs_tire_forces`; DOS 0x593d5). Index 511 is unreachable with the 44.9° `slip_cutoff` and holds garbage |
| 1396 | **grip_table_r** | 512 | Array of `512` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Rear tire grip by slip angle, like `grip_table_f`. Rally mode (DOS, SE) replaces it with the front table in memory |
| 1908 | **checksum** | 4 | 4-bytes unsigned integer (little endian) | Byte sum of the first 1880 bytes (0x758: all but the last 28 bytes of `grip_table_r`). On a mismatch `Fiziks_PreInitCar` sets `efficiency` to 0 |
### **CarAiAndCrashBody** ###
#### **Size**: 460 bytes ####
#### **Description**: Car AI and crash body: the AI driving model and the collision body of a car (`SIMDATA/CARFAMS/*.PDN`, QFS-compressed, 460 bytes uncompressed), one per car slot, player included. Loaded by `tnfs_ai_pdn_file` (SE 0x40fa3c, DOS 0x47425, PSX 0x8001eaa8), applied by `tnfs_ai_init_car` (SE 0x4407b8). Angles are 24-bit (0x1000000 = full turn) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **half_width** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Half width (x) of the collision body (m); car width = 2 * this, it overrides PBS `body_width` (`tnfs_ai_init_car`). Zero in all traffic and cop PDNs: if any of the three half sizes is 0, the sizes come from the car 3D model |
| 4 | **half_height** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Half height (y) of the collision body (m), also the collision height offset |
| 8 | **half_length** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Half length (z) of the collision body (m); car length = 2 * this, it overrides PBS `body_len` |
| 12 | **moment_of_inertia** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Crash-body moment of inertia (1.4-2.25), no physical unit; angular acceleration factor = 1 / this (`tnfs_collision_data_reset` and the rebound functions) |
| 16 | **mass** | 4 | 32-bit real number (little-endian, not signed), where last 16 bits is a fractional part | Relative crash-body mass (1.0 typical, 0.5-1.5), no physical unit; linear acceleration factor = 1 / this. Car to car impulses are split by the mass ratio |
| 20 | **handling_factor** | 4 | 4-bytes signed integer (little endian), angle: 0x1000000 means 360 degrees | Racers only (`tnfs_ai_racer_speed`, SE 0x470a9c, DOS 0x80c50, PSX 0x8005bcc8), 24-bit angle (0xA0000 = 14.1°): target speed * (0.8 + 0.203 * (1 - turn / this)), turn = road heading change per track node. 0xFF0000 (TSUPRA, TRAFFC, traffic, cops) = no corner slowdown. Copied to car+0x168, its inverse to car+0x16c |
| 24 | **speed_factor** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Racers only: target speed multiplier (0.92-1.0) (`tnfs_ai_racer_speed`, car+0x170). 1.0 in traffic and cop PDNs |
| 28 | **power_curve** | 400 | Array of `100` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | AI acceleration by speed (`tnfs_ai_drive_car`, SE 0x46f3e8, DOS 0x7e961, PSX 0x80059d68): speed gain per AI update at index abs(speed in m/s) + 1, x 8 (traffic), x 4 (racers), x 6 (cops), minus the drive argument of the function. The car slows down when [index - 1] is 0. In racer PDNs the first 0 is at the top gear speed rounded up; traffic PDNs have a linear 0.2 -> 0 curve, COPMUST the P911 curve. Uncertain: the exact time scale and the drive argument |
| 428 | **top_speeds** | 24 | Array of `6` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Top speed (m/s) per AI gear, 0 = gear skipped (leading zeros); all 0 in traffic and cop PDNs. Racers' engine rpm = 0.75 * `max_rpm` * speed / top speed of the gear, a shift timer starts at each gear change (`tnfs_ai_opp_engine_and_cornering`, SE 0x46c278, DOS 0x79af9) |
| 452 | **max_rpm** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Racers' engine rpm cap, drives the opponent engine sound. 0 in traffic and cop PDNs |
| 456 | **gear_count** | 4 | 4-bytes unsigned integer (little endian) | Read only as the traffic horn pitch index, when `tnfs_ai_lane_change` starts the horn (tnfs-1995 names it `pdn_number_of_gears`). Not the number of gears: 5 in every racer PDN, also in CZR1, DVIPER, P911 and TSUPRA with 6 `top_speeds`. The game plays the traffic horn (collision bank sample 0x3f) at pitch value `table[index] * doppler >> 8`, table at DOS 0x81aa9 = 0x40, 0x40, 0x64, 0x5a, 0x50, 0x46, 0x3c, 0x32, 0x2d, 0x28. Values: crx 2, bmw 3, jetta 3, sunbird 4, wagon 4, pickup 5, probe 5, traffc 5, axxess 6, jeep 6, lemans 6, rodeo 8, vandura 8, copmust 0 (the cop never honks); 7 and 9 unused |
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
### **AsfAudio** ###
#### **Size**: 40..? bytes ####
#### **Description**: An audio file, which is supported by FFMPEG and can be converted using only it. Has some explanation [here](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "1SNh" | Resource ID |
| 4 | **unk0** | 8 | Bytes | Unknown purpose |
| 12 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | Sampling rate of audio |
| 16 | **sound_resolution** | 1 | 1-byte unsigned integer | How many bytes in one wave data entry |
| 17 | **channels** | 1 | 1-byte unsigned integer | Channels amount. 1 is mono, 2 is stereo |
| 18 | **compression** | 1 | 1-byte unsigned integer | If equals to 2, wave data is compressed with [IMA ADPCM codec](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)#IMA_ADPCM_Decompression_Algorithm) |
| 19 | **unk1** | 1 | 1-byte unsigned integer | Unknown purpose |
| 20 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | Amount of wave data entries. Should be multiplied by sound_resolution to calculated the size of data in bytes |
| 24 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | When audio ends, it repeats in loop from here. Should be multiplied by sound_resolution to calculate offset in bytes |
| 28 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | If play audio in loop, at this point we should rewind to repeat_loop_beginning. Should be multiplied by sound_resolution to calculate offset in bytes |
| 32 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of wave data start in current file, relative to start of the file itself |
| 36 | **unk2** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 40 | **offset** | up to offset wave_data_offset + 40 | Padding bytes | Padding between the header and wave data |
| wave_data_offset + 40 | **wave_data** | min(`remaining file bytes`, `wave_data_length` \* `sound_resolution`) | Bytes | Wave data is here |
### **EacsAudioFile** ###
#### **Size**: 32..? bytes ####
#### **Description**: A file with single EACS audio entry ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **header** | 32 | [EacsAudioHeader](#eacsaudioheader) | EACS header: sampling rate, resolution, channels, loop settings |
| 32 | **offset** | up to offset header/wave_data_offset | Padding bytes | Unknown purpose |
| header/wave_data_offset | **wave_data** | min(`remaining file bytes`, `header.wave_data_length` \* `header.sound_resolution`) | Bytes | Wave data is here. If header.sound_resolution == 1, contains signed bytes, else - unsigned |
### **SoundBankHeaderEntry** ###
#### **Size**: 72 bytes ####
#### **Description**: TNFS sound bank (*.BNK) entry: the game's playback settings for a sample, followed by its EACS header. Field meanings come from the game code, as decoded by the [tnfs-1995](https://github.com/marcos2250/tnfs-1995) project ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **voice_mask** | 4 | 4-bytes unsigned integer (little endian) | Bit mask of the game's mixer channels (voices) this sample may play on (bit n = channel n), used by the DOS voice allocator `sfx_voice_alloc` (0x96760). The collision bank duplicates looped wavs under several indices, each with a different bit. Examples: collision bank wind 0x29 has bit 5 (wind channel 5), waterfall 0x3e bit 11 (channel 0xb), the hits bits 4 and 5 (one-shot channel 4), car bank engine_off bit 1 (channel 1), car bank horn bit 14 (player horn channel 0xe). The exception is car bank engine_on: bit 6, played on channel 0 |
| 4 | **eacs_header_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of `eacs_header` in the file: offset of this entry + 40. The game turns it into a pointer when it loads the bank |
| 8 | **play_time_limit** | 4 | 4-bytes unsigned integer (little endian) | Play time limit in sound driver ticks. At voice start the game stores this value - 1 in the voice (voice+4; DOS `sfx_voice_start_one` 0x96d22, demo 0x79ca2, Win95 SE 0x48eed8), the driver tick (DOS `sfx_driver_tick` 0xaada7, Win95 SE 0x4a4ac0) decrements it and stops the voice when it goes below 0. 0 = no limit, the value of every entry in the shipped banks |
| 12 | **random_range** | 4 | 4-bytes unsigned integer (little endian) | Random pitch range in cents. At every voice start (DOS 0x96d22) the pitch offset of the voice is `pitch_offset` + a random value in [-random_range, +random_range]. 300 for hits, 150-250 for gear clicks, 600 for collision bank entry 0x50, 0 for loops |
| 16 | **pitch_offset** | 4 | 4-bytes signed integer (little endian) | Base pitch offset in cents, added to every pitch the voice plays at (see `random_range`, `bend_range_semitones`). 0 in all TNFS banks |
| 20 | **priority** | 1 | 1-byte unsigned integer | Playback priority |
| 21 | **unk3** | 1 | 1-byte unsigned integer | DOS and the demo copy it to the voice (voice+0x14), no code reads it there; Win95 SE does not copy it. 0x80 in every entry of the shipped banks |
| 22 | **unk4** | 1 | 1-byte signed integer | Read by no binary (DOS, demo, Win95 SE): probably an authoring transpose the games ignore. 0 in most entries; -5, -6, -12 (e.g. collision bank 0x3d) and 2 in some collision bank entries |
| 23 | **bend_range_semitones** | 1 | 1-byte unsigned integer | Pitch bend range in semitones. The game plays a sample at pitch value 0..127 (64 = original pitch). Every pitch set computes cents = (value - 64) * bend_range_semitones * 100 / 64 + the pitch offset of the voice (`pitch_offset` + random, see `random_range`), the playback rate is the base rate * 2 ^ (cents / 1200) (DOS 0xa6fbd, table 0xa5470) |
| 24 | **pan** | 1 | 1-byte unsigned integer | Pan, 0..127, 64 is center |
| 25 | **volume** | 1 | 1-byte unsigned integer | Volume, 0..127, with a random +-`random_volume_range`. The final volume is master volume * entry volume * channel volume / 127^2 |
| 26 | **random_volume_range** | 1 | 1-byte unsigned integer | Random volume range: the volume is `volume` +- a random value up to it. 0 in all TNFS banks |
| 27 | **driver** | 1 | 1-byte unsigned integer | Sound driver of the sample, a run time field: the demo's bank loader (0x79a62) writes it when it loads the bank, so a non-zero value here and in the following bytes of a shipped bank is a leftover of the tool that saved it. 0 or 0x0a in TNFS banks (0xcc in one entry) |
| 28 | **flags** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: stereo_pair</details> | Bit 0: stereo pair, the next sample of the bank is the other channel (`*3D` / `*3` banks: collision bank 0x30-0x3a even entries and 0x3f, opponent bank 0x43 and 0x45) |
| 29 | **unk5** | 11 | Bytes | Run time voice data (see `driver`): zeros, or leftovers in the entries with a non-zero `driver` |
| 40 | **eacs_header** | 32 | [EacsAudioHeader](#eacsaudioheader) | EACS header. Its `wave_data_offset` points into the wave data region of the sound bank file |
### **EacsAudioHeader** ###
#### **Size**: 32 bytes ####
#### **Description**: A header for EACS audio. It is almost identical to AsfAudio when it is the only sound in the file (*.EAS), but also can be included in single SoundBank file (*.BNK), which has multiple EACS headers and wave data located separately ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "EACS" | Resource ID |
| 4 | **sampling_rate** | 4 | 4-bytes unsigned integer (little endian) | Sampling rate of audio |
| 8 | **sound_resolution** | 1 | 1-byte unsigned integer | How many bytes in one wave data entry |
| 9 | **channels** | 1 | 1-byte unsigned integer | Channels amount. 1 is mono, 2 is stereo |
| 10 | **compression** | 1 | 1-byte unsigned integer | If equals to 2, wave data is compressed with [IMA ADPCM](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats_(2)#IMA_ADPCM_Decompression_Algorithm) codec |
| 11 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 12 | **wave_data_length** | 4 | 4-bytes unsigned integer (little endian) | Amount of wave data entries. Should be multiplied by sound_resolution to calculated the size of data in bytes |
| 16 | **repeat_loop_beginning** | 4 | 4-bytes unsigned integer (little endian) | When audio ends, it repeats in loop from here. Should be multiplied by sound_resolution to calculate offset in bytes |
| 20 | **repeat_loop_length** | 4 | 4-bytes unsigned integer (little endian) | If play audio in loop, at this point we should rewind to repeat_loop_beginning. Should be multiplied by sound_resolution to calculate offset in bytes |
| 24 | **wave_data_offset** | 4 | 4-bytes unsigned integer (little endian) | Offset of wave data start in current file, relative to start of the file itself |
| 28 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
## **Replays** ##
### **TnfsReplay** ###
#### **Size**: 100374 bytes ####
#### **Description**: Replay of the race, saved in `GAMEDATA\REPLAY`. Reverse engineered from the decompiled game code, the cars' states are copied from its physics data structures. The 4 replays REPLAY, REPLAY1, REPLAY2 and REPLAY3 are the replays of the game that cannot be replaced. ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **setup** | 840 | [TnfsReplaySetup](#tnfsreplaysetup) | Race settings |
| 840 | **highlights** | 2468 | [TnfsReplayHighlights](#tnfsreplayhighlights) | Highlights of the race |
| 3308 | **recording** | 89600 | [TnfsReplayRecording](#tnfsreplayrecording) | Controls and car states |
| 92908 | **world_state** | 3272 | Bytes | State of the race that is not stored in the cars, every 0x708 ticks. Contains the state of the random generator, the AI tables, the police state, etc. |
| 96180 | **stats** | 4194 | Array of `9` items<br/>Item type: [TnfsReplayStats](#tnfsreplaystats) | Stats of the cars |
### **TnfsReplaySetup** ###
#### **Size**: 840 bytes ####
#### **Description**: Settings of the race the replay was recorded in, 0x348 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 2 | Bytes | Unknown purpose |
| 2 | **track_index** | 4 | 4-bytes signed integer (little endian) | Selected track in the track group. With `track_group` is used as an index of the game's track tables (`track_group * 0xa6b + track_index * 0x27`) |
| 6 | **track_group** | 4 | 4-bytes signed integer (little endian) | Selected track group, see `track_index` |
| 10 | **track_name** | 10 | UTF-8 string | Track file name without extension, e.g. `cl2` for CL2.TRI |
| 20 | **game_mode** | 4 | 4-bytes signed integer (little endian) | Same as the game mode of the best race records: 0 time trial, 1 head to head, 2 full grid race. 3 also starts a race of 8 cars |
| 24 | **is_multiplayer** | 4 | 4-bytes signed integer (little endian) | Boolean. 1 for the multiplayer game |
| 28 | **race_flags** | 4 | 4-bytes signed integer (little endian) | Bit flags of the race. The game checks bits 2, 3 and 5 |
| 32 | **unk1** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 36 | **unk2** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 40 | **extra_cars_a** | 4 | 4-bytes signed integer (little endian) | Amount of the cars in addition to the racers. Set to 1 in the single player game when the game mode is head to head, race flag 4 is not set and `track_group` is less than 3, 0 otherwise |
| 44 | **unk3** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 48 | **extra_cars_b** | 4 | 4-bytes signed integer (little endian) | Amount of the cars in addition to the racers. Set to 6 under the same conditions as `extra_cars_a`, 0 otherwise |
| 52 | **unk4** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 56 | **random_seed** | 4 | 4-bytes signed integer (little endian) | Seed of the random generator of the race. Is a unix time in seconds of the moment the race started |
| 60 | **unk5** | 2 | Bytes | Unknown purpose |
| 62 | **players** | 150 | Array of `2` items<br/>Item type: [TnfsReplayPlayer](#tnfsreplayplayer) | Settings of the players of this machine (up to 2 in the multiplayer game) |
| 212 | **unk6** | 572 | Bytes | Unknown purpose |
| 784 | **player_id** | 4 | 4-bytes signed integer (little endian) | Index of the player car of this machine (`g_player_id` in the game code) |
| 788 | **unk7** | 52 | Bytes | Unknown purpose |
### **TnfsReplayPlayer** ###
#### **Size**: 75 bytes ####
#### **Description**: Settings of one player, 0x4b bytes. The structure starts at the name, so the last field of the previous player is directly in front of it ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 8 | UTF-8 string | Player name |
| 8 | **unk0** | 1 | Bytes | Unknown purpose |
| 9 | **car_id** | 4 | 4-bytes signed integer (little endian) | Index of the car in the car list of the game |
| 13 | **transmission** | 4 | 4-bytes signed integer (little endian) | Boolean. Used as the "automatic gear" flag of the car, and selects the variant of the car physics |
| 17 | **option_a** | 4 | 4-bytes signed integer (little endian) | Boolean, traction control option. Applied only if the car PBS `has_tcs` (0x338) is set |
| 21 | **option_b** | 4 | 4-bytes signed integer (little endian) | Boolean, ABS option. Applied only if the car PBS `has_abs` (0x334) is set |
| 25 | **unk1** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 29 | **sound_value_0** | 4 | 4-bytes signed integer (little endian) | Taken from the sound configuration when the replay is saved, 0 without a sound card |
| 33 | **sound_value_1** | 4 | 4-bytes signed integer (little endian) | Taken from the sound configuration when the replay is saved, 0 without a sound card |
| 37 | **unk2** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 41 | **sound_value_2** | 4 | 4-bytes signed integer (little endian) | Taken from the sound configuration when the replay is saved, 0 without a sound card |
| 45 | **unk3** | 30 | Bytes | Unknown purpose |
### **TnfsReplayHighlights** ###
#### **Size**: 2468 bytes ####
#### **Description**: Highlights of the race, found by the game during the race, 0x9a4 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **clips** | 360 | Array of `30` items<br/>Item type: [TnfsReplayHighlightClip](#tnfsreplayhighlightclip) | Clips, selected at the end of the race from the best seconds. First `clip_count` used |
| 360 | **best_seconds** | 120 | Array of `30` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes signed integer (little endian) | Numbers of the best seconds of the race, picked by the highest `seconds` score |
| 480 | **clip_count** | 4 | 4-bytes signed integer (little endian) | Amount of used `clips` |
| 484 | **state** | 4 | 4-bytes signed integer (little endian) | Replay playback state. -2 until the replay is started |
| 488 | **unk0** | 24 | Bytes | Unknown purpose |
| 512 | **seconds** | 1920 | Array of `480` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | The score of every second of the race. The value is `second_number << 8 | score`, where score is the highest highlight score of the second (0 if nothing happened), plus 0x80 until the second is selected to be a clip |
| 2432 | **current_second** | 4 | 4-bytes signed integer (little endian) | Recording tick divided by 60, updated each time a highlight is recorded |
| 2436 | **unk1** | 32 | Bytes | Unknown purpose |
### **TnfsReplayHighlightClip** ###
#### **Size**: 12 bytes ####
#### **Description**: Interesting part of the race to be shown on the replay summary ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **start_tick** | 4 | 4-bytes signed integer (little endian) | First tick of the clip |
| 4 | **end_tick** | 4 | 4-bytes signed integer (little endian) | Last tick of the clip |
| 8 | **coolness** | 4 | 4-bytes signed integer (little endian) | Highlight score of the clip |
### **TnfsReplayRecording** ###
#### **Size**: 89600 bytes ####
#### **Description**: Replay recording buffer (0x15e00 bytes). A replay is played by restoring the state of the cars from the last keyframe and then simulating the game with the recorded controls ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **controls_low** | 14400 | Array of `2` items<br/>Item size: 7200 bytes<br/>Item type: Bytes | Low bytes of the control word of every player, one sample per 4 ticks. Bits 0-5 of the word is the steering (0x20 is the centre), bits 6-11 the throttle/brake axis (0x1e is the neutral) |
| 14400 | **controls_high** | 14400 | Array of `2` items<br/>Item size: 7200 bytes<br/>Item type: Bytes | High bytes of the control word of every player, one sample per 4 ticks. Bits 12-15 of the word are the gear change (bits 12 and 13), bit 14 is a flag, bit 15 is the handbrake. Neutral word is 0x07a0 |
| 28800 | **player_frames** | 13440 | Array of `2` items<br/>Item size: 6720 bytes<br/>Item type: Array of `16` items<br/>Item type: [TnfsReplayPlayerFrame](#tnfsreplayplayerframe) | Keyframes of the player cars, a keyframe every 0x708 ticks (30 seconds) |
| 42240 | **other_frames** | 47360 | Array of `16` items<br/>Item size: 2960 bytes<br/>Item type: Array of `8` items<br/>Item type: [TnfsReplayOtherFrame](#tnfsreplayotherframe) | Keyframes of the other cars, a keyframe every 0x708 ticks (30 seconds) |
### **TnfsReplayPlayerFrame** ###
#### **Size**: 420 bytes ####
#### **Description**: State of a car driven by a player, 0x1a4 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **car** | 360 | [TnfsReplayCarState](#tnfsreplaycarstate) | - |
| 360 | **throttle** | 1 | 1-byte unsigned integer | - |
| 361 | **throttle_previous_pos** | 1 | 1-byte unsigned integer | - |
| 362 | **brake** | 1 | 1-byte unsigned integer | - |
| 363 | **is_shifting_gears** | 1 | 1-byte unsigned integer | Game value + 100 |
| 364 | **rpm_engine** | 2 | 2-bytes unsigned integer (little endian) | - |
| 366 | **rpm_vehicle** | 2 | 2-bytes unsigned integer (little endian) | - |
| 368 | **road_grip_increment** | 4 | 4-bytes signed integer (little endian) | - |
| 372 | **tire_grip_rear** | 4 | 4-bytes signed integer (little endian) | - |
| 376 | **tire_grip_front** | 4 | 4-bytes signed integer (little endian) | - |
| 380 | **speed_drivetrain** | 4 | 4-bytes signed integer (little endian) | - |
| 384 | **tire_grip_loss** | 4 | 4-bytes signed integer (little endian) | - |
| 388 | **gear_auto_selected** | 1 | 1-byte unsigned integer | - |
| 389 | **gear_selected** | 1 | 1-byte unsigned integer | Game value + 2 |
| 390 | **flags** | 1 | 8 flags container<br/><details><summary>flag names (from least to most significant)</summary>0: wheels_on_ground<br/>1: is_engine_cutoff<br/>2: handbrake<br/>3: is_gear_engaged<br/>5: tire_skid_rear</details> | - |
| 391 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
| 392 | **time_off_ground** | 4 | 4-bytes signed integer (little endian) | - |
| 396 | **unk1** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 400 | **slope_force_lat** | 4 | 4-bytes signed integer (little endian) | - |
| 404 | **unk2** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 408 | **slope_force_lon** | 4 | 4-bytes signed integer (little endian) | - |
| 412 | **thrust** | 4 | 4-bytes signed integer (little endian) | - |
| 416 | **surface_type** | 4 | 4-bytes signed integer (little endian) | - |
### **TnfsReplayOtherFrame** ###
#### **Size**: 370 bytes ####
#### **Description**: State of a car that is not driven by a player (its index is not less than the number of players), 0x172 bytes. Slots go in the order of the car indexes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **car** | 360 | [TnfsReplayCarState](#tnfsreplaycarstate) | - |
| 360 | **speed_target** | 4 | 4-bytes signed integer (little endian) | - |
| 364 | **target_center_line** | 4 | 4-bytes signed integer (little endian) | - |
| 368 | **wheels_on_ground** | 1 | 1-byte unsigned integer | - |
| 369 | **unk0** | 1 | 1-byte unsigned integer | Unknown purpose |
### **TnfsReplayCarState** ###
#### **Size**: 360 bytes ####
#### **Description**: Physics state of a car, copied from the car data structure (0x168 bytes). Field names are the names of the car data fields in the game code ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unk0** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 4 | **unk1** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 8 | **unk2** | 1 | 1-byte unsigned integer | Unknown purpose |
| 9 | **unk3** | 2 | 2-bytes unsigned integer (little endian) | Unknown purpose |
| 11 | **car_index** | 1 | 1-byte unsigned integer | Index of the car, 0 is the first player |
| 12 | **position** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Position x, y, z |
| 24 | **angle** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes signed integer (little endian) | Angle x, y, z (24-bit angles) |
| 36 | **steer_angle** | 4 | 4-bytes signed integer (little endian) | - |
| 40 | **target_angle** | 4 | 4-bytes signed integer (little endian) | - |
| 44 | **is_crashed** | 4 | 4-bytes signed integer (little endian) | - |
| 48 | **matrix** | 36 | Array of `9` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Rotation matrix of the car |
| 84 | **track_slice** | 4 | 4-bytes signed integer (little endian) | Index of the track node |
| 88 | **lap_number** | 4 | 4-bytes signed integer (little endian) | - |
| 92 | **speed_x** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 96 | **speed_y** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 100 | **speed_z** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 104 | **speed_local_lat** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 108 | **speed_local_vert** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 112 | **speed_local_lon** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 116 | **speed** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 120 | **angular_speed** | 4 | 4-bytes signed integer (little endian) | - |
| 124 | **car_length** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 128 | **car_width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 132 | **center_line_distance** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 136 | **side_width** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 140 | **road_normals** | 36 | Array of `9` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | Road fence normal, road surface normal and road heading, 3 vectors |
| 176 | **road_position** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 188 | **ai_state** | 4 | 4-bytes signed integer (little endian) | Bit flags of the AI state of the car |
| 192 | **collision_height_offset** | 4 | 4-bytes signed integer (little endian) | - |
| 196 | **collision_data** | 148 | Bytes | Collision data of the car |
| 344 | **car_road_speed** | 4 | 4-bytes signed integer (little endian) | - |
| 348 | **field_158** | 4 | 4-bytes signed integer (little endian) | Random group index |
| 352 | **lane_slack** | 4 | 4-bytes signed integer (little endian) | - |
| 356 | **unk4** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
### **TnfsReplayStats** ###
#### **Size**: 466 bytes ####
#### **Description**: Race stats of one car, 0x1d2 bytes. Times are in ticks (1/60 of second) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **lap_times** | 68 | Array of `17` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes signed integer (little endian) | Race time at the end of each lap (0 until the lap is finished) |
| 68 | **unk0** | 340 | Bytes | Unknown purpose |
| 408 | **best_accel_time_1** | 4 | 4-bytes signed integer (little endian) | Best acceleration time, 99999 if none |
| 412 | **best_accel_time_2** | 4 | 4-bytes signed integer (little endian) | Best acceleration time, 99999 if none |
| 416 | **best_brake_time_1** | 4 | 4-bytes signed integer (little endian) | Best braking time, 999 if none |
| 420 | **best_brake_time_2** | 4 | 4-bytes signed integer (little endian) | Best braking time, 999 if none |
| 424 | **quarter_mile_speed** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 428 | **quarter_mile_time** | 4 | 4-bytes signed integer (little endian) | 99999 if none |
| 432 | **penalty_count** | 4 | 4-bytes signed integer (little endian) | - |
| 436 | **warning_count** | 4 | 4-bytes signed integer (little endian) | - |
| 440 | **unk1** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 444 | **finish_time** | 4 | 4-bytes signed integer (little endian) | Race time when the car finished the race. 0 if not finished, 999999 if timed out |
| 448 | **unk2** | 4 | 4-bytes signed integer (little endian) | Unknown purpose |
| 452 | **top_speed** | 4 | 32-bit real number (little-endian, signed), where last 16 bits is a fractional part | - |
| 456 | **unk3** | 10 | Bytes | Unknown purpose |
## **Misc** ##
### **TnfsConfigDat** ###
#### **Size**: 24402 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **player_name** | 42 | UTF-8 string | Player name, leading with zeros. Though game allows to set name with as many as 8 characters, the game seems to work fine with name up to 42 symbols, though some part of name will be cut off in the UI |
| 42 | **unk0** | 139 | Bytes | Unknown purpose |
| 181 | **city_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on City track |
| 2848 | **coastal_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Coastal track |
| 5515 | **alpine_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Alpine track |
| 8182 | **rusty_springs_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Rusty Springs track |
| 10849 | **autumn_valley_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Autumn Valley track |
| 13516 | **burnt_sienna_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Burnt Sienna track |
| 16183 | **vertigo_ridge_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Vertigo Ridge track |
| 18850 | **transtropolis_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Transtropolis track |
| 21517 | **lost_vegas_stats** | 2667 | [TrackStats](#trackstats) | Best times and top speeds on Lost Vegas track |
| 24184 | **unk1** | 39 | [BestRaceRecord](#bestracerecord) | Unknown purpose |
| 24223 | **unk2** | 177 | Bytes | Unknown purpose |
| 24400 | **unlocks_level** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): none<br/>1 (0x1): warrior_vegas_mirror<br/>2 (0x2): warrior_vegas_mirror_rally</details> | Level of unlocked features: warrior car, lost vegas track, mirror track mode, rally track mode |
| 24401 | **unk3** | 1 | Bytes | Unknown purpose |
### **TrackStats** ###
#### **Size**: 2667 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **best_lap_1** | 39 | [BestRaceRecord](#bestracerecord) | Best single lap time (closed track). Best time of first segment for open track |
| 39 | **best_lap_2** | 39 | [BestRaceRecord](#bestracerecord) | Best time of second segment (open track). Zeros for closed track |
| 78 | **best_lap_3** | 39 | [BestRaceRecord](#bestracerecord) | Best time of third segment (open track). Zeros for closed track |
| 117 | **top_speed_1** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on first segment (open track). Zeros for closed track |
| 156 | **top_speed_2** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on second segment (open track). Zeros for closed track |
| 195 | **top_speed_3** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on third segment (open track). Zeros for closed track |
| 234 | **best_race_time_table_1** | 390 | Array of `10` items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with minimum amount of laps: for open track total time of all 3 segments, for closed track time of minimum selection of laps (2 or 4 depending on track) |
| 624 | **best_race_time_table_2** | 390 | Array of `10` items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with middle amount of laps (6 or 8 depending on track). Zeros for open track |
| 1014 | **best_race_time_table_3** | 390 | Array of `10` items<br/>Item type: [BestRaceRecord](#bestracerecord) | Best 10 runs of the whole race with maximum amount of laps (12 or 16 depending on track). Zeros for open track |
| 1404 | **top_race_speed** | 39 | [BestRaceRecord](#bestracerecord) | Top speed on the whole race. Why it is not equal to max stat between top_speed_1, top_speed_2 and top_speed_3 for open track? |
| 1443 | **unk** | 1224 | Bytes | Unknown purpose |
### **BestRaceRecord** ###
#### **Size**: 39 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **name** | 11 | UTF-8 string | Racer name |
| 11 | **unk0** | 4 | Bytes | Unknown purpose |
| 15 | **car_id** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): RX-7<br/>1 (0x1): NSX<br/>2 (0x2): SUPRA<br/>3 (0x3): 911<br/>4 (0x4): CORVETTE<br/>5 (0x5): VIPER<br/>6 (0x6): 512TR<br/>7 (0x7): DIABLO<br/>8 (0x8): WAR_SLEW?<br/>9 (0x9): WAR_WATCH?<br/>10 (0xa): WAR_TOURNY?<br/>11 (0xb): WAR?</details> | A car identifier. Last 4 options are unclear, names came from decompiled NFS.EXE |
| 16 | **unk1** | 11 | Bytes | Unknown purpose |
| 27 | **time** | 4 | TNFS time field. 4-bytes unsigned integer (little endian), equals to amount of ticks (amount of seconds * 60) | Total track time in seconds |
| 31 | **unk2** | 1 | Bytes | Unknown purpose |
| 32 | **top_speed** | 3 | TNFS top speed record. Appears to be 24-bit real number (sign unknown because big values show up as N/A in the game), little-endian, where last 8 bits is a fractional part. For determining speed, ONLY INTEGER PART of this number should be multiplied by 2,240000000001 and rounded up, e.g. 0xFF will be equal to 572mph. Note: probably game multiplies number by 2,24 with some fast algorithm so it rounds up even integer result, because 0xFA (*2,24 == 560.0) shows up in game as 561mph | Top speed |
| 35 | **game_mode** | 1 | Enum of 256 possible values<br/><details><summary>Value names:</summary>0 (0x0): time_trial<br/>1 (0x1): head_to_head<br/>2 (0x2): full_grid_race</details> | Game mode. In the game shown as "t.t.", "h.h." or empty string |
| 36 | **unk3** | 3 | Bytes. Always == b'\x00\x00\x00' | Unknown purpose |
