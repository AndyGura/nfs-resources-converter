# **File specs** #
## **Physics** ##
### **CarPerformanceSpec** ###
#### **Size**: 1912 bytes ####
#### **Description**: This block describes full car physics specification for car that player can drive. Looks like it's not used for opponent cars and such files do not exist for traffic/cop cars at all. Big thanks to Five-Damned-Dollarz, he seems to be the only one guy who managed to understand most of the fields in this block. His specification: https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e ####
<details>
<summary>Click to see block specs (65 fields)</summary>

| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **mass_front_axle** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | The meaning is theoretical. For all cars value is mass / 2 |
| 4 | **mass_rear_axle** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | The meaning is theoretical. For all cars value is mass / 2 |
| 8 | **mass** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Car mass |
| 12 | **unknowns0** | 4 * (4) | Array of 4 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 28 | **brake_bias** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | how much car rotates when brake? |
| 32 | **unknowns1** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 36 | **center_of_gravity** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | probably the height of mass center in meters |
| 40 | **max_brake_decel** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 44 | **unknowns2** | 4 * (2) | Array of 2 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 52 | **drag** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 56 | **top_speed** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 60 | **efficiency** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 64 | **body__wheel_base** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | The distance betweeen rear and front axles in meters |
| 68 | **burnout_div** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 72 | **body__wheel_track** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | The distance betweeen left and right wheels in meters |
| 76 | **unknowns3** | 4 * (2) | Array of 2 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 84 | **mps_to_rpm_factor** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * gearRatio) |
| 88 | **transmission__gears_count** | 4 | 4-bytes unsigned integer (little endian) | Amount of drive gears + 2 (R,N?) |
| 92 | **transmission__final_drive_ratio** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | - |
| 96 | **roll_radius** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 100 | **unknowns4** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 104 | **transmission__gear_ratios** | 4 * (8) | Array of 8 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Only first <gear_count> values are used. First element is the reverse gear ratio, second one is unknown |
| 136 | **engine__torque_count** | 4 | 4-bytes unsigned integer (little endian) | Torques LUT (lookup table) size |
| 140 | **front_roll_stiffness** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 144 | **rear_roll_stiffness** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 148 | **roll_axis_height** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 152 | **unknowns5** | 4 * (3) | Array of 3 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube? |
| 164 | **slip_angle_cutoff** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 168 | **normal_coefficient_loss** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 172 | **engine__max_rpm** | 4 | 4-bytes unsigned integer (little endian) | - |
| 176 | **engine__min_rpm** | 4 | 4-bytes unsigned integer (little endian) | - |
| 180 | **engine__torques** | 8 * (60) | Array of 60 items<br/>Item type: [EngineTorqueRecord](#enginetorquerecord) | LUT (lookup table) of engine torque depending on RPM. <engine__torque_count> first elements used |
| 660 | **transmission__upshifts** | 4 * (5) | Array of 5 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | RPM value, when automatic gear box should upshift. 1 element per drive gear |
| 680 | **unknowns6** | 2 * (4) | Array of 4 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit real number (little-endian), where last 8 bits is a fractional part | Unknown purpose |
| 688 | **unknowns7** | 4 * (7) | Array of 7 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 716 | **unknowns8** | 2 * (2) | Array of 2 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit real number (little-endian), where last 8 bits is a fractional part | Unknown purpose |
| 720 | **inertia_factor** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 724 | **body_roll_factor** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 728 | **body_pitch_factor** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 732 | **front_friction_factor** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 736 | **rear_fricton_factor** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 740 | **body__length** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Chassis body length in meters |
| 744 | **body__width** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Chassis body width in meters |
| 748 | **steering__max_auto_steer_angle** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 752 | **steering__auto_steer_mult_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 756 | **steering__auto_steer_div_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 760 | **steering__steering_model** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 764 | **steering__auto_steer_velocities** | 4 * (4) | Array of 4 items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (little endian) | Unknown purpose |
| 780 | **steering__auto_steer_velocity_ramp** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 784 | **steering__auto_steer_velocity_attenuation** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 788 | **steering__auto_steer_ramp_mult_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 792 | **steering__auto_steer_ramp_div_shift** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 796 | **lateral_accel_cutoff** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 800 | **unknowns9** | 4 * (13) | Array of 13 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 852 | **engine_shifting__shift_timer** | 4 | 4-bytes unsigned integer (little endian) | Unknown exactly, but it seems to be ticks taken to shift. Tick is probably 100ms |
| 856 | **engine_shifting__rpm_decel** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 860 | **engine_shifting__rpm_accel** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 864 | **engine_shifting__clutch_drop_decel** | 4 | 4-bytes unsigned integer (little endian) | Unknown purpose |
| 868 | **engine_shifting__neg_torque** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 872 | **body__clearance** | 4 | EA games 32-bit real number (little-endian), where last 7 bits is a fractional part | - |
| 876 | **body__height** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | - |
| 880 | **center_x** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 884 | **grip_curve_front** | 512 | Array of 512 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 1396 | **grip_curve_rear** | 512 | Array of 512 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 1908 | **hash** | 4 | 4-bytes unsigned integer (little endian) | Check sum of this block contents |
</details>

### **EngineTorqueRecord** ###
#### **Size**: 8 bytes ####
#### **Description**: Engine torque for given RPM record ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **rpm** | 4 | 4-bytes unsigned integer (little endian) | - |
| 4 | **torque** | 4 | 4-bytes unsigned integer (little endian) | - |
### **CarSimplifiedPerformanceSpec** ###
#### **Size**: 460 bytes ####
#### **Description**: This block describes simpler version of car physics. It is not clear how and when is is used ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **unknowns0** | 4 * (3) | Array of 3 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown. Some values for playable cars, always zeros for non-playable |
| 12 | **moment_of_inertia** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Not clear how to interpret |
| 16 | **unknowns1** | 4 * (3) | Array of 3 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Unknown purpose |
| 28 | **power_curve** | 4 * (100) | Array of 100 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Not clear how to interpret |
| 428 | **top_speeds** | 4 * (6) | Array of 6 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Maximum car speed (m/s) per gear |
| 452 | **max_rpm** | 4 | EA games 32-bit real number (little-endian), where last 16 bits is a fractional part | Max engine RPM |
| 456 | **gear_count** | 4 | 4-bytes unsigned integer (little endian) | Gears amount |
## **Bitmaps** ##
### **Bitmap16Bit0565** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x78 | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 2 * (width * height) | Array of width * height items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 2\*width\*height) | Array of block_size - (16 + 2\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap4Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: Single-channel image, 4 bits per pixel. Used in FFN font files and some NFS2SE SHPI directories as some small sprites, like "dot". Seems to be always used as alpha channel, so we save it as white image with alpha mask ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7a | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 0..? | Array of width * height sub-byte numbers. Each number consists of 4 bits | Font atlas bitmap data |
### **Bitmap8Bit** ###
#### **Size**: 16..? bytes ####
#### **Description**: 8bit bitmap can be serialized to image only with palette. Basically, for every pixel it uses 8-bit index of color in assigned palette. The tricky part is to determine how the game understands which palette to use. In most cases, if bitmap has embedded palette, it should be used, EXCEPT Autumn Valley fence texture: there embedded palette should be ignored. In all other cases it is tricky even more: it uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, palette can be in a different SHPI before this one. In CONTROL directory most of QFS files use !pal even from different QFS file! It is a mystery how to reliably pick palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7b | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | width * height | Array of width * height items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Color indexes of bitmap pixels. The actual colors are in assigned to this bitmap palette |
| 16..? | **trailing_bytes** | block_size - (16 + width\*height) | Array of block_size - (16 + width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
| 16..? | **palette** (optional) | 8..1040 | One of types:<br/>[PaletteReference](#palettereference)<br/>[Palette24BitDos](#palette24bitdos)<br/>[Palette24Bit](#palette24bit)<br/>[Palette32Bit](#palette32bit)<br/>[Palette16Bit](#palette16bit) | Palette, assigned to this bitmap or reference to external palette?. The exact mechanism of choosing the correct palette (except embedded one) is unknown |
### **Bitmap32Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7d | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 4 * (width * height) | Array of width * height items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 4\*width\*height) | Array of block_size - (16 + 4\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap16Bit1555** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7e | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 2 * (width * height) | Array of width * height items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 1555 color, arrrrrgg_gggbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 2\*width\*height) | Array of block_size - (16 + 2\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
### **Bitmap24Bit** ###
#### **Size**: 16..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7f | Resource ID |
| 1 | **block_size** | 3 | 3-bytes unsigned integer (little endian) | Bitmap block size 16+2\*width\*height + trailing bytes length. For "WRAP" SHPI directory it contains some different unknown data |
| 4 | **width** | 2 | 2-bytes unsigned integer (little endian) | Bitmap width in pixels |
| 6 | **height** | 2 | 2-bytes unsigned integer (little endian) | Bitmap height in pixels |
| 8 | **unknowns** | 4 | Array of 4 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 12 | **x** | 2 | 2-bytes unsigned integer (little endian) | X coordinate of bitmap position on screen. Used for menu/dash sprites |
| 14 | **y** | 2 | 2-bytes unsigned integer (little endian) | Y coordinate of bitmap position on screen. Used for menu/dash sprites |
| 16 | **bitmap** | 3 * (width * height) | Array of width * height items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (little-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors of bitmap pixels |
| 16..? | **trailing_bytes** | block_size - (16 + 3\*width\*height) | Array of block_size - (16 + 3\*width\*height) items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Looks like aligning size to be divisible by 4 |
## **Fonts** ##
### **FfnFont** ###
#### **Size**: 48..? bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == FNTF | Resource ID |
| 4 | **file_size** | 4 | 4-bytes unsigned integer (little endian) | This file size in bytes |
| 8 | **unknowns0** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 10 | **symbols_amount** | 2 | 2-bytes unsigned integer (little endian) | Amount of symbols, defined in this font |
| 12 | **unknowns1** | 16 | Array of 16 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 28 | **bitmap_data_pointer** | 2 | 2-bytes unsigned integer (little endian) | Pointer to bitmap block |
| 30 | **unknowns2** | 2 | Array of 2 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 32 | **definitions** | 11 * (symbols_amount) | Array of symbols_amount items<br/>Item type: [SymbolDefinitionRecord](#symboldefinitionrecord) | Definitions of chars in this bitmap font |
| 32..? | **skip_bytes** | up to offset bitmap_data_pointer | Array of up to offset bitmap_data_pointer items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer. Always == 0xad | 4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36) |
| 32..? | **bitmap** | 16..? | [Bitmap4Bit](#bitmap4bit) | Font atlas bitmap data |
### **SymbolDefinitionRecord** ###
#### **Size**: 11 bytes ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **code** | 2 | 2-bytes unsigned integer (little endian) | Code of symbol |
| 2 | **glyph_width** | 1 | 1-byte unsigned integer | Width of symbol in font bitmap |
| 3 | **glyph_height** | 1 | 1-byte unsigned integer | Height of symbol in font bitmap |
| 4 | **glyph_x** | 2 | 2-bytes unsigned integer (little endian) | Position (x) of symbol in font bitmap |
| 6 | **glyph_y** | 2 | 2-bytes unsigned integer (little endian) | Position (Y) of symbol in font bitmap |
| 8 | **x_advance** | 1 | 1-byte unsigned integer | Gap between this symbol and next one in rendered text |
| 9 | **x_offset** | 1 | 1-byte signed integer | Offset (x) for drawing the character image |
| 10 | **y_offset** | 1 | 1-byte signed integer | Offset (y) for drawing the character image |
## **Palettes** ##
### **PaletteReference** ###
#### **Size**: 8 bytes ####
#### **Description**: Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. Probably a reference to palette which should be used, that's why named so ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x7c | Resource ID |
| 1 | **unknowns** | 7 | Array of 7 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
### **Palette24BitDos** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x22 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 3 * (0..256) | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb | Colors LUT |
### **Palette24Bit** ###
#### **Size**: 16..784 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x24 | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 3 * (0..256) | Array of 0..256 items<br/>Item size: 3 bytes<br/>Item type: EA games 24-bit color (big-endian), rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette32Bit** ###
#### **Size**: 16..1040 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2a | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 4 * (0..256) | Array of 0..256 items<br/>Item size: 4 bytes<br/>Item type: EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb | Colors LUT |
### **Palette16Bit** ###
#### **Size**: 16..528 bytes ####
#### **Description**: Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, meaning the index of color in LUT of assigned palette ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 1 | 1-byte unsigned integer. Always == 0x2d | Resource ID |
| 1 | **unknowns** | 15 | Array of 15 items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Unknown purpose |
| 16 | **colors** | 2 * (0..256) | Array of 0..256 items<br/>Item size: 2 bytes<br/>Item type: EA games 16-bit 0565 color, rrrrrggg_gggbbbbb | Colors LUT |