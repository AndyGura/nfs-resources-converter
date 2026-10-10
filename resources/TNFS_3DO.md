# **TNFS (3DO) file specs** #

*Last time updated: 2026-10-10 05:08:05.740642+00:00*


# **Info by file extensions** #

**DriveData/CarData/\*.BigSpecsFam** player car physics. [Tnfs3doCarPhysics](#tnfs3docarphysics)

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #
## **Physics** ##
### **Tnfs3doCarPhysics** ###
#### **Size**: 1892 bytes ####
#### **Description**: Player car physics of TNFS 3DO (`DriveData/CarData/*.BigSpecsFam`, 1892 bytes): a big-endian wwww archive of three items, the physics fields (0x350 bytes) and the front and rear grip tables. The physics fields are the PC `PlayerCarPhysics` (PBS) layout without `max_brake_force_2` and `gear_efficiency`, the grip tables are the same, there is no checksum. Readers are named as in the 3DO `LaunchMe` executable (raw ARM binary, address = file offset) of [tnfs-1995](https://github.com/marcos2250/tnfs-1995); "not read" = no reader there. The file is loaded by `tnfs_carspecs_002` (0x16de0) for player 1; in a debug mode the game instead compiles a text `<car>.spec` (`tnfs_car_specs` 0x1f8c, which computes the derived fields) and writes it as `<car>.SpecsBin`. Physics ticks are 1/30 s, angles are 24-bit (0x1000000 = full turn) ####
| Offset | Name | Size (bytes) | Type | Description |
| --- | --- | --- | --- | --- |
| 0 | **resource_id** | 4 | UTF-8 string. Always == "wwww" | Resource ID |
| 4 | **num_items** | 4 | 4-bytes unsigned integer (big endian). Always == 0x3 | Number of wwww items: the physics fields (up to `center_y`), `grip_table_f`, `grip_table_r` |
| 8 | **items_descr** | 12 | Array of `3` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (big endian) | Item offsets: 0x14, 0x364, 0x564 |
| 20 | **mass_front** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Mass on the front axle (kg), `mass - mass_rear` in the spec compiler. Front weight fraction = `mass_front * inv_mass` (`tnfs_Fiziks_InitCar` 0x11530). Equals `mass_rear` in all files |
| 24 | **mass_rear** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Mass on the rear axle (kg), `mass * rear_weight_fraction` in the spec compiler |
| 28 | **mass** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Total car mass (kg), `mass_front + mass_rear`, the input of the spec compiler. `tnfs_Fiziks_InitCar` multiplies it by `inv_mass_f` / `inv_mass_r` into car fields |
| 32 | **inv_mass_f** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 / mass_front`, rounded down (`tnfs_Fiziks_InitCar`) |
| 36 | **inv_mass_r** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 / mass_rear`, rounded down (`tnfs_Fiziks_InitCar`) |
| 40 | **inv_mass** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 / mass`, rounded down. Used for the weight distribution, drag / mass (`tnfs_Fiziks_InitCar`) and the torque table (`tnfs_load_torque_table` 0x1e40) |
| 44 | **drive_bias** | 4 | 32-bit real number (big-endian, not signed), where last 16 bits is a fractional part | Front share of the drive force, 0.0 = RWD, 1.0 = FWD (`tnfs_physics_update` 0x11f78). 0 also enables the burnout rule of `tnfs_engine_thrust` (0x10784). 0 in all files but LDIABLO (0.3) |
| 48 | **brake_bias_f** | 4 | 32-bit real number (big-endian, not signed), where last 16 bits is a fractional part | Front share of the pedal brake force, 0.0-1.0 (`tnfs_physics_update`); the rear gets the rest. Pedal brake force = brake * 1.29 / 256 * (front grip + rear grip) |
| 52 | **brake_bias_r** | 4 | 32-bit real number (big-endian, not signed), where last 16 bits is a fractional part | Rear share of the brake force, `1 - brake_bias_f`. Not read: the game uses total - front |
| 56 | **cog_height** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Height of the centre of gravity (m). Weight transfer factor = `cog_height * wheel_base_inv` (`tnfs_Fiziks_InitCar`): moves grip between front and rear under longitudinal acceleration |
| 60 | **max_brake_force** | 4 | 32-bit real number (big-endian, not signed), where last 16 bits is a fractional part | Braking cap, an acceleration (m/s², 8.3-11.5): with the brake above 100 the longitudinal acceleration from the tires is capped to this and the lateral one to 1.5 x this (`tnfs_physics_update`). Also the rear brake force with the handbrake, and the brake force when the car rolls against the selected gear. PC splits it by speed into `max_brake_force_1` / `_2`, scaled by `force_to_accel` |
| 64 | **max_tire_coeff** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Braking deceleration in g: the spec compiler takes a speed (mph) and its stopping distance (ft) and stores v² / 2d / g (0.84-1.35). `tnfs_Fiziks_InitCar` adds `normal_loss * mass_front / 2` in memory and logs it ("Adjusted max tire co"); nothing else reads it |
| 68 | **drag** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Air drag (kg/m, ½ * air density * drag coefficient * frontal area). `tnfs_Fiziks_InitCar` replaces it in memory with `drag * inv_mass`; deceleration = that * surface factor * speed² (`tnfs_physics_drag_forces` 0x109e0) |
| 72 | **top_speed** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Top speed (m/s). Above it `tnfs_physics_update` raises the drag so that it cancels the thrust |
| 76 | **efficiency** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Drivetrain efficiency (0.5-0.86), multiplies the torque table (`tnfs_load_torque_table`): x 0xb4/256 with the automatic gearbox, + 0xd/256 when the option byte 0x10 is 5, and, in a game mode not identified yet, + 0x37/256 (tracks 1, 4, 5), 0x44/256 (other tracks below 6) or 0x55/256 (from 6 up) |
| 80 | **wheel_base** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Distance between the front and rear axles (m): car wheelbase, moment of inertia and yaw factors (`tnfs_Fiziks_InitCar`) |
| 84 | **wheel_base_inv** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 / wheel_base`, rounded down. Weight transfer factor (`tnfs_Fiziks_InitCar`) |
| 88 | **wheel_track** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Distance between the left and right wheels (m). Not read |
| 92 | **wheel_track_inv** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 / wheel_track`, rounded down. Not read |
| 96 | **rear_weight_fraction** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Rear weight fraction, the spec compiler always writes 0.5. Not read |
| 100 | **mps_to_rpm** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Engine rpm = speed (m/s) * this * gear ratio (`tnfs_engine_rev_limiter` 0x10564, `tnfs_engine_auto_shift` 0x1d68, `tnfs_engine_thrust`) |
| 104 | **num_gears** | 4 | 4-bytes unsigned integer (big endian) | Number of used `gear_ratios` entries: reverse, neutral and `num_gears - 2` forward gears. Upshifts stop at gear index `num_gears - 3` (`tnfs_control_shift_gears` 0x138bc, `tnfs_engine_auto_shift`) |
| 108 | **final_drive** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Final drive ratio. Only read by `tnfs_load_torque_table` |
| 112 | **wheel_radius** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Wheel radius (m). Not read, the game uses `inv_wheel_rad` |
| 116 | **inv_wheel_rad** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 / wheel_radius`, rounded down. Only read by `tnfs_load_torque_table` |
| 120 | **gear_ratios** | 32 | Array of `8` items<br/>Item size: 4 bytes<br/>Item type: 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Gear ratios, index = selected gear + 2: [0] reverse (negative), [1] neutral, [2] first gear and up (`tnfs_engine_rev_limiter`, `tnfs_engine_auto_shift`, `tnfs_engine_thrust`). The neutral ratio only gives the wheel rpm in neutral. The first `num_gears` entries are used, the rest is garbage |
| 152 | **num_torques** | 4 | 4-bytes unsigned integer (big endian). Always <= 60 | Number of used `torques` entries (51; 41 in P911), at most 60, the length of `torques`. The game uses the last one for any higher rpm (`tnfs_engine_torque_table` 0x1f2c) |
| 156 | **roll_stiff_f** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Front roll stiffness (10000.0 in all files). Not read: only the spec compiler uses it for `front_roll_stiffness_2` |
| 160 | **roll_stiff_r** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Rear roll stiffness (10000.0 in all files). Not read |
| 164 | **roll_axis_y** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Roll axis height (m). Not read: only the spec compiler uses it for `weight_transfer_factor` |
| 168 | **front_roll_stiffness_2** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Front share of the roll stiffness, `roll_stiff_f / (roll_stiff_f + roll_stiff_r)` in the spec compiler (0.5 in all files). Not read |
| 172 | **rear_roll_stiffness_2** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `1 - front_roll_stiffness_2` in the spec compiler (0.5 in all files). Not read |
| 176 | **weight_transfer_factor** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | `cog_height - roll_axis_y` in the spec compiler (0.18-0.23). Not read: the weight transfer factor of the game is `cog_height * wheel_base_inv` |
| 180 | **slip_cutoff** | 4 | 4-bytes signed integer (big endian), angle: 0x1000000 means 360 degrees | Max tire slip angle, 24-bit angle: 0x200000 = 45° in all files. Larger slip angles are clamped to it and set skid bit 1 (`tnfs_tire_forces` 0x10f70) |
| 184 | **normal_loss** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Normal coefficient loss (0.0007 in all files). Only adjusts `max_tire_coeff` in `tnfs_Fiziks_InitCar` |
| 188 | **max_rpm** | 4 | 4-bytes unsigned integer (big endian) | Engine redline rpm. Rpm limit with the throttle = this * throttle / 256 (`tnfs_engine_thrust`). Tachometer needle: min(rpm, max_rpm + 1500) (0xcbb0); race statistics count the gear shifts above max_rpm - 400 (0x13824) |
| 192 | **min_rpm** | 4 | 4-bytes unsigned integer (big endian) | Engine idle rpm, engine rpm floor (`tnfs_engine_rev_limiter`) |
| 196 | **torques** | 480 | Array of `60` items<br/>Item size: 8 bytes<br/>Item type: Two 32bit unsigned integers (big-endian): rpm and torque (N*m) | Engine torque by rpm, the first `num_torques` entries are used, the rest is garbage. The game reads only the first rpm and assumes 200 rpm steps (true in all files): entry = (rpm rounded to 200 - rpm[0]) / 200 (`tnfs_engine_torque_table`). `tnfs_load_torque_table` turns each torque in memory into the 16.16 acceleration per unit of gear ratio, `torque * final_drive * efficiency * inv_wheel_rad * inv_mass` |
| 676 | **upshifts** | 28 | Array of `7` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (big endian) | Automatic gearbox rpm: [g] = upshift from gear index g to g + 1; it shifts down when the rpm in the lower gear would be below 15/16 of [g - 1] (`tnfs_engine_auto_shift`). `tnfs_engine_thrust` uses [1] - 500 as the burnout rpm limit. The first `num_gears - 3` entries are used, the rest is garbage |
| 704 | **inertia_factor** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | 0.5 in all files. Car moment of inertia factor (`tnfs_Fiziks_InitCar`) |
| 708 | **roll_factor** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Visual body roll from the lateral acceleration (`tnfs_physics_update`), no unit |
| 712 | **pitch_factor** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Visual body pitch from the longitudinal acceleration (`tnfs_physics_update`), no unit |
| 716 | **friction_f** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Front tire friction coefficient: front grip = this * front weight fraction * 9.81 (`tnfs_Fiziks_InitCar`) |
| 720 | **friction_r** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Rear tire friction coefficient, like `friction_f` |
| 724 | **body_len** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Body length (m), copied to the car length of player 1 (`tnfs_carspecs_002` 0x16de0); other cars get 5.0 m |
| 728 | **body_width** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Body width (m), copied to the car width of player 1; other cars get 2.5 m |
| 732 | **auto_steer** | 4 | 4-bytes signed integer (big endian) | 24-bit angle per m/s (983 in all files). Moving forward without steering input: the auto-steer target (road heading) is taken only if its absolute value < this * speed (`tnfs_control_steering` 0x134e0) |
| 736 | **steer_mult** | 4 | 4-bytes unsigned integer (big endian) | Auto-steer ramp multiplier shift (1). Not read |
| 740 | **steer_div** | 4 | 4-bytes unsigned integer (big endian) | Auto-steer ramp divider shift (1). Not read |
| 744 | **steer_model** | 4 | 4-bytes unsigned integer (big endian) | Steering model (2). Not read |
| 748 | **steer_vel** | 16 | Array of `4` items<br/>Item size: 4 bytes<br/>Item type: 4-bytes unsigned integer (big endian) | Steering rates (2, 4, 8, 16), by the pad buttons held: [0] with a 33.75° (0x180000) steering lock, [1] with 37.97° (0x1b0000) and for centring, [2] with 42.19° (0x1e0000); [3] not read. Rate per tick = min(`steer_vel_ramp` - min(speed * `steer_vel_att`, 1.5), 1.6) * entry (`tnfs_control_steering`) |
| 764 | **steer_vel_ramp** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Base steering rate (2.2-2.5), see `steer_vel` (`tnfs_control_steering`) |
| 768 | **steer_vel_att** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Steering rate reduction per m/s, at most 1.5 in total (`tnfs_control_steering`) |
| 772 | **steer_ramp_mult** | 4 | 4-bytes unsigned integer (big endian) | Shift count: steering rate << this when the target and the auto-steer angle are on the same side of the current angle (`tnfs_control_steering`) |
| 776 | **steer_ramp_div** | 4 | 4-bytes unsigned integer (big endian) | Shift count (1). Not read |
| 780 | **lat_acc_cutoff** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Lateral acceleration cutoff (m/s², 13-17). Not read on 3DO |
| 784 | **front_grip_mult** | 4 | 32-bit real number (big-endian, signed), where last 8 bits is a fractional part | Front lateral grip multiplier (1.8 in all files): front lateral force cap = grip table value * front grip * this (`tnfs_tire_forces`). The PC PBS keeps this slot unused (`unknown_0x320`) |
| 788 | **front_grip_mult_inv** | 4 | 32-bit real number (big-endian, signed), where last 8 bits is a fractional part | `1 / front_grip_mult`, rounded down (raw 65536 / raw): scales the lateral force back when `tnfs_tire_forces` checks lateral + longitudinal force against the grip |
| 792 | **rear_grip_mult** | 4 | 32-bit real number (big-endian, signed), where last 8 bits is a fractional part | Rear lateral grip multiplier, like `front_grip_mult` (1.8 in all files). The PC PBS uses this slot as `thrust_scale` |
| 796 | **rear_grip_mult_inv** | 4 | 32-bit real number (big-endian, signed), where last 8 bits is a fractional part | `1 / rear_grip_mult`, rounded down (raw 65536 / raw), like `front_grip_mult_inv` |
| 800 | **burnout_div** | 4 | 32-bit real number (big-endian, signed), where last 8 bits is a fractional part | 0.4 in all files (8.8 fixed point, "burnOutDiv" in the 3DO debug symbols). Not read |
| 804 | **has_abs** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Car has ABS if > 0 (1.0); ABS is on if this and the player option are both set (`tnfs_carspecs_002`). Off in DVIPER and LDIABLO |
| 808 | **has_tcs** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | Car has traction control if > 0 (1.0), like `has_abs`. On in ANSX, CZR1 and TSUPRA |
| 812 | **throttle_on_ramp** | 4 | 4-bytes unsigned integer (big endian) | Throttle (0-255) rise per tick (`tnfs_control_throttle` 0x13764) |
| 816 | **throttle_off_ramp** | 4 | 4-bytes unsigned integer (big endian) | Throttle (0-255) fall per tick (`tnfs_control_throttle`) |
| 820 | **brake_on_ramp_1** | 4 | 4-bytes unsigned integer (big endian) | Brake (0-255) rise per tick, x 1.25, while the brake is below 144 (`tnfs_control_brake` 0x137ac) |
| 824 | **brake_on_ramp_2** | 4 | 4-bytes unsigned integer (big endian) | Brake rise per tick, x 1.25, from 144 up (`tnfs_control_brake`) |
| 828 | **brake_off_ramp_1** | 4 | 4-bytes unsigned integer (big endian) | Brake fall per tick while the brake is below 144 (`tnfs_control_brake`) |
| 832 | **brake_off_ramp_2** | 4 | 4-bytes unsigned integer (big endian) | Brake fall per tick from 144 up (`tnfs_control_brake`) |
| 836 | **shift_timer** | 4 | 4-bytes unsigned integer (big endian) | Ticks with the gear disengaged while shifting (`tnfs_control_shift_gears`, `tnfs_engine_autoshift` 0x10484). Manual downshift: half of it; car model 4: +3 when (time & 0x31) == 0x10 |
| 840 | **rpm_dec** | 4 | 4-bytes unsigned integer (big endian) | Rpm fall per tick towards idle without throttle while the gear is disengaged, half in neutral (`tnfs_engine_rev_limiter`) |
| 844 | **rpm_acc** | 4 | 4-bytes unsigned integer (big endian) | Rpm rise per tick, x throttle / 256, while the gear is disengaged, half in neutral (`tnfs_engine_rev_limiter`) |
| 848 | **drop_rpm_dec** | 4 | 4-bytes unsigned integer (big endian) | In gear: engine rpm fall per tick towards the wheel rpm; / 8 while the rear wheels spin with throttle > 220 (`tnfs_engine_rev_limiter`) |
| 852 | **drop_rpm_inc** | 4 | 4-bytes unsigned integer (big endian) | In gear: engine rpm rise per tick towards the wheel rpm (`tnfs_engine_rev_limiter`) |
| 856 | **neg_torque** | 4 | 4-bytes unsigned integer (big endian) | Engine braking: force = rpm difference * this / 256 * gear ratio, at most 16 * speed; x 4 when the wheels drive the engine (`tnfs_engine_thrust`) |
| 860 | **incar_camera_height** | 4 | 32-bit real number (big-endian, signed), where last 16 bits is a fractional part | In-car camera height (m, ~1.0) (in-car camera setup 0x168c) |
| 864 | **center_y** | 4 | 4-bytes unsigned integer (big endian) | In-car view vertical centre: the camera setup (0x168c) uses center_y - 120 |
| 868 | **grip_table_f** | 512 | Array of `512` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Front tire grip by slip angle, grip = value / 128 (the game: value << 9 as 16.16). Index = slip angle (24-bit) >> 12: 0.088° steps over 0-45° (`tnfs_tire_slide_table` 0x1045c, read in `tnfs_tire_forces`); slip angles from 0x1ffffe up read index 511. Item 1 of the wwww archive (`tnfs_carspecs_002` 0x16de0 loads it to car+0x4a8) |
| 1380 | **grip_table_r** | 512 | Array of `512` items<br/>Item size: 1 byte<br/>Item type: 1-byte unsigned integer | Rear tire grip by slip angle, like `grip_table_f`. Item 2 of the wwww archive (`tnfs_carspecs_002` 0x16de0 loads it to car+0x4ac) |
