import math
from typing import Dict

from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    ArrayBlock,
    CompoundBlock,
    FixedPointBlock,
)
from resources.eac.fields.numbers import IntegerAngleBlock


# TNFS when saving some of the calculated values, uses `floor` instead of `round`
def floor_16(value):
    pow16 = 2**16
    return math.floor(value * pow16) / pow16


def floor_8(value):
    return math.floor(value * 256) / 256


def _fixed(**kwargs):
    return FixedPointBlock(length=4, fraction_bits=16, is_signed=True, **kwargs)


def _ufixed(**kwargs):
    return FixedPointBlock(length=4, fraction_bits=16, is_signed=False, **kwargs)


def _fixed8(**kwargs):
    return FixedPointBlock(length=4, fraction_bits=8, is_signed=True, **kwargs)


def _int(**kwargs):
    return IntegerBlock(length=4, is_signed=True, **kwargs)


# TNFS 24-bit angle: 0x1000000 = full turn
def _angle24(**kwargs):
    return IntegerAngleBlock(full_turn=0x1000000, length=4, is_signed=True, **kwargs)


def _uint(**kwargs):
    return IntegerBlock(length=4, is_signed=False, **kwargs)


class PlayerCarPhysics(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Player car physics: the full physics specification of a car the player can drive '
            '(`SIMDATA/CARSPECS/'
            '*.PBS`, QFS-compressed, 1912 bytes uncompressed). Loaded by `Fiziks_PreInitCar` (SE 0x4400f4, DOS '
            '0x63e72, PSX 0x80038ea4); the game keeps the same layout in memory (DOS, SE, PSX). Readers are named '
            'as in [tnfs-1995](https://github.com/marcos2250/tnfs-1995) with Win95 SE addresses; "not read" = no '
            'reader in the DOS, SE and PSX executables. Physics ticks are 1/30 s, angles are 24-bit (0x1000000 = '
            'full turn). Rally mode changes some fields in memory after loading (DOS, SE): rear grip table := '
            'front, `unknown_0x320` and `thrust_scale` halved and their inverses recomputed, `friction_f/r` and '
            '`max_brake_force_1/2` halved, `cog_height` x 1.5, `efficiency` x 0x14c/256 on track 3, else x '
            '0x133/256. PSX rally: `lat_acc_cutoff` x 0.625, `cog_height` x 7/4, `efficiency` x a per-track value, '
            '`drive_bias` = 0.5. Thanks to [Five-Damned-Dollarz](https://gist.github.com/Five-Damned-Dollarz/'
            '99e955994ebbcf970532406a197b580e) and [marcos2250](https://github.com/marcos2250/tnfs-1995/blob/main/'
            'tnfs_files.c)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        mass_front = (
            _fixed(),
            {
                'description': 'Mass on the front axle (kg). Front weight fraction = `mass_front * inv_mass` '
                '(`Fiziks_InitCar`, SE 0x42ff60). Equals `mass_rear` in all files'
            },
        )
        mass_rear = (_fixed(), {'description': 'Mass on the rear axle (kg)'})
        mass = (
            _fixed(programmatic_value=lambda ctx: ctx.data('mass_front') + ctx.data('mass_rear')),
            {
                'description': 'Total car mass (kg), `mass_front + mass_rear`. Only feeds car fields that nothing '
                'reads (`Fiziks_InitCar`): the game uses `inv_mass`'
            },
        )
        inv_mass_f = (
            _fixed(programmatic_value=lambda ctx: floor_16(1 / ctx.data('mass_front'))),
            {'description': '`1 / mass_front`, rounded down. Only feeds a car field that nothing reads'},
        )
        inv_mass_r = (
            _fixed(programmatic_value=lambda ctx: floor_16(1 / ctx.data('mass_rear'))),
            {'description': '`1 / mass_rear`, rounded down. Only feeds a car field that nothing reads'},
        )
        inv_mass = (
            _fixed(programmatic_value=lambda ctx: floor_16(1 / (ctx.data('mass_front') + ctx.data('mass_rear')))),
            {
                'description': '`1 / mass`, rounded down. Used for the weight distribution, drag / mass '
                '(`Fiziks_InitCar`) and the torque table (`tnfs_load_torque_table`, SE 0x409990)'
            },
        )
        drive_bias = (
            _ufixed(),
            {
                'description': 'Front share of the drive force, 0.0 = RWD, 1.0 = FWD (`tnfs_physics_update`, SE '
                '0x430cb0). 0 also enables the burnout rule of `tnfs_engine_thrust` (SE 0x42f138). 0 in all files '
                'but LDIABL (0.35) and TRAFFC (0.4)'
            },
        )
        brake_bias_f = (
            _ufixed(),
            {
                'description': 'Front share of the pedal brake force, 0.0-1.0 (`tnfs_physics_update`); the rear '
                'gets the rest'
            },
        )
        brake_bias_r = (
            _ufixed(programmatic_value=lambda ctx: 1 - ctx.data('brake_bias_f')),
            {
                'description': 'Rear share of the brake force, `1 - brake_bias_f` (raw 65536 - `brake_bias_f` in '
                'all files). Not read: the game uses total - front'
            },
        )
        cog_height = (
            _fixed(),
            {
                'description': 'Height of the centre of gravity (m). Weight transfer factor = `cog_height * '
                'wheel_base_inv` (`Fiziks_InitCar`): moves grip between front and rear under longitudinal force. '
                'Rally mode x 1.5 (PSX x 7/4)'
            },
        )
        max_brake_force_1 = (
            _ufixed(),
            {
                'description': 'Cap of the absolute longitudinal tire force while braking (brake > 100 or '
                'handbrake) below 26.8 m/s (60 mph); also the brake force when the car rolls against the selected '
                'gear (`tnfs_physics_update`). Deceleration (m/s²) = this * `force_to_accel` (~10 for ANSX). Rally '
                'mode halves it'
            },
        )
        max_brake_force_2 = (
            _ufixed(),
            {
                'description': 'Same cap from 26.8 to 40 m/s; above 40 m/s the larger of `max_brake_force_1` and '
                'this. Differs from `max_brake_force_1` in 6 of 9 files (ANSX 25.5 / 37.5). Rally mode halves it'
            },
        )
        max_tire_coeff = (_fixed(), {'description': 'Maximal tire coefficient (0.84-1.35). Not read'})
        drag = (
            _fixed(),
            {
                'description': 'Air drag (kg/m, ½ * air density * drag coefficient * frontal area). `Fiziks_InitCar` '
                'replaces it in memory with `drag * inv_mass`; deceleration = that * surface factor * speed² '
                '(`tnfs_drag_force`, SE 0x42f630)'
            },
        )
        top_speed = (
            _fixed(),
            {
                'description': 'Top speed (m/s). Above it `tnfs_physics_update` raises the drag so that it cancels '
                'the thrust, except on track id 6'
            },
        )
        efficiency = (
            _fixed(),
            {
                'description': 'Drivetrain efficiency (0.5-2.0), multiplies the torque table '
                '(`tnfs_load_torque_table`); x 0xf8/256 with the automatic gearbox. `Fiziks_PreInitCar` sets it to 0 '
                'on a `checksum` mismatch, and when the file `By_R&T` can be created in the CARSPECS folder (DOS '
                'flag 0xf7bbe, SE 0x4c5ccc; probably an anti-copy trap, the folder being read-only on the CD). Rally '
                'mode: x 0x14c/256 on track 3, else x 0x133/256'
            },
        )
        wheel_base = (
            _fixed(),
            {'description': 'Distance between the front and rear axles (m): car wheelbase and yaw factors'},
        )
        wheel_base_inv = (
            _fixed(programmatic_value=lambda ctx: floor_16(1 / ctx.data('wheel_base'))),
            {'description': '`1 / wheel_base`, rounded down. Weight transfer factor (`Fiziks_InitCar`)'},
        )
        wheel_track = (
            _fixed(),
            {'description': 'Distance between the left and right wheels (m). Not read'},
        )
        wheel_track_inv = (
            _fixed(programmatic_value=lambda ctx: floor_16(1 / ctx.data('wheel_track'))),
            {'description': '`1 / wheel_track`, rounded down. Not read'},
        )
        rear_weight_fraction = (
            _fixed(),
            {'description': 'Rear weight fraction, `mass_rear / mass` (0.5 in all files). Not read'},
        )
        mps_to_rpm = (
            _fixed(),
            {
                'description': 'Engine rpm = speed (m/s) * this * gear ratio (`tnfs_engine_rev_limiter` SE 0x42ee68, '
                '`tnfs_engine_auto_shift_change` SE 0x4098a0, `tnfs_engine_thrust`)'
            },
        )
        num_gears = (
            _uint(),
            {
                'description': 'Number of used `gear_ratios` entries: reverse, neutral and `num_gears - 2` forward '
                'gears. Upshifts stop at gear index `num_gears - 3` (`tnfs_control_shift_gears` SE 0x438c84, '
                '`tnfs_engine_auto_shift_change`)'
            },
        )
        final_drive = (_fixed(), {'description': 'Final drive ratio. Only read by `tnfs_load_torque_table`'})
        wheel_radius = (_fixed(), {'description': 'Wheel radius (m). Not read, the game uses `inv_wheel_rad`'})
        inv_wheel_rad = (
            _fixed(programmatic_value=lambda ctx: floor_16(1 / ctx.data('wheel_radius'))),
            {'description': '`1 / wheel_radius`, rounded down. Only read by `tnfs_load_torque_table`'},
        )
        gear_ratios = (
            ArrayBlock(length=8, child=_fixed()),
            {
                'description': 'Gear ratios, index = selected gear + 2: [0] reverse (negative), [1] neutral, [2] '
                'first gear and up (`tnfs_engine_rev_limiter`, `tnfs_engine_auto_shift_change`, '
                '`tnfs_engine_thrust`). The neutral ratio only gives the wheel rpm in neutral. The first '
                '`num_gears` entries are used, the rest is garbage'
            },
        )
        num_torques = (_uint(), {'description': 'Number of used `torques` entries (51; 41 in P911)'})
        roll_stiff_f = (_fixed(), {'description': 'Front roll stiffness (10000.0 in all files). Not read'})
        roll_stiff_r = (_fixed(), {'description': 'Rear roll stiffness (10000.0 in all files). Not read'})
        roll_axis_y = (_fixed(), {'description': 'Roll axis height (m). Not read'})
        front_roll_stiffness_2 = (_fixed(), {'description': '0.5 in all files. Not read'})
        rear_roll_stiffness_2 = (_fixed(), {'description': '0.5 in all files. Not read'})
        weight_transfer_factor = (
            _fixed(),
            {
                'description': '0.001-0.27. Not read: the weight transfer factor of the game is `cog_height * '
                'wheel_base_inv`'
            },
        )
        slip_cutoff = (
            _angle24(),
            {
                'description': 'Max tire slip angle, 24-bit angle: 0x1FE667 = 44.9° in all files. Larger slip '
                'angles are clamped to it and set skid bit 1 (`tnfs_tire_forces`, SE 0x42fb88)'
            },
        )
        normal_loss = (_fixed(), {'description': 'Normal coefficient loss. Not read'})
        max_rpm = (
            _uint(),
            {
                'description': 'Engine redline rpm (`rpm_redline` in the game engine). Rpm limit with the throttle '
                '= this * throttle / 256 (`tnfs_engine_rev_limiter`, `tnfs_engine_thrust`). Engine sound pitch '
                'value = rpm * 127 / (max_rpm + 2000), at most 127 (`tnfs_sfx_engine_player`, SE 0x4444b8, DOS '
                '0x668ab). Tachometer needle: min(rpm, max_rpm + 980) * 600 / max_rpm (SE 0x42221c, 0x420d0c)'
            },
        )
        min_rpm = (
            _uint(),
            {'description': 'Engine idle rpm (`rpm_idle`), engine rpm floor (`tnfs_engine_rev_limiter`)'},
        )
        torques = (
            ArrayBlock(
                length=60,
                child=CompoundBlock(
                    fields=[
                        ('rpm', IntegerBlock(length=4), {}),
                        ('torque', IntegerBlock(length=4), {}),
                    ],
                    inline_description='Two 32bit unsigned integers (little-endian): rpm and torque (N*m)',
                ),
            ),
            {
                'description': 'Engine torque by rpm, the first `num_torques` entries are used, the rest is garbage. '
                'The game reads only the first rpm and assumes 200 rpm steps (true in all files): entry = (rpm '
                'rounded to 200 - rpm[0]) / 200 (`tnfs_engine_get_torque`, SE 0x409a04). '
                '`tnfs_load_torque_table` turns each torque in memory into the 16.16 acceleration per unit of gear '
                'ratio, `torque * final_drive * efficiency * inv_wheel_rad * inv_mass`'
            },
        )
        upshifts = (
            ArrayBlock(length=7, child=IntegerBlock(length=4)),
            {
                'description': 'Automatic gearbox rpm: [g] = upshift from gear index g to g + 1; it shifts down when '
                'the rpm in the lower gear would be below 15/16 of [g - 1] (`tnfs_engine_auto_shift_change`). '
                '`tnfs_engine_thrust` uses [1] - 500 as the burnout rpm limit. The first `num_gears - 3` entries '
                'are used, the rest is garbage'
            },
        )
        gear_efficiency = (
            ArrayBlock(length=8, child=_fixed8()),
            {
                'description': 'Per-gear multiplier of the wheel torque, index = selected gear + 2 like '
                '`gear_ratios` (`tnfs_engine_thrust`). The first `num_gears` entries are used, the rest is garbage'
            },
        )
        inertia_factor = (
            _fixed(),
            {
                'description': '0.5 in all files. Only feeds the car moment of inertia (`Fiziks_InitCar`), which '
                'nothing reads'
            },
        )
        roll_factor = (
            _fixed(),
            {'description': 'Visual body roll from the lateral acceleration (`tnfs_physics_update`), no unit'},
        )
        pitch_factor = (
            _fixed(),
            {'description': 'Visual body pitch from the longitudinal acceleration (`tnfs_physics_update`), no unit'},
        )
        friction_f = (
            _fixed(),
            {
                'description': 'Front tire friction coefficient: front grip = this * front weight fraction * 9.81 '
                '(`Fiziks_InitCar`). Rally mode halves it'
            },
        )
        friction_r = (
            _fixed(),
            {'description': 'Rear tire friction coefficient, like `friction_f`. Rally mode halves it'},
        )
        body_len = (
            _fixed(),
            {
                'description': 'Body length (m). Copied to the car length, then overwritten by `half_length * 2` of '
                'the car PDN in `tnfs_ai_init_car` (SE 0x4407b8): no effect, all 9 cars have PDN sizes'
            },
        )
        body_width = (
            _fixed(),
            {'description': 'Body width (m). Overwritten by `half_width * 2` of the car PDN, like `body_len`'},
        )
        auto_steer = (
            _int(),
            {
                'description': '24-bit angle per m/s (983 in all files). Digital steering, wheel centred, moving '
                'forward: the auto-steer target (road heading) is taken only if its absolute value < this * speed '
                '(`tnfs_control_steering_a`, SE 0x438954)'
            },
        )
        steer_mult = (_uint(), {'description': 'Auto-steer ramp multiplier shift (1). Not read'})
        steer_div = (_uint(), {'description': 'Auto-steer ramp divider shift (1). Not read'})
        steer_model = (_uint(), {'description': 'Steering model (2). Not read'})
        steer_vel = (
            ArrayBlock(length=4, child=IntegerBlock(length=4)),
            {
                'description': 'Auto-steer velocities (2, 4, 8, 16). Only [1] is read: steering rate per tick = '
                'min(`steer_vel_ramp` - min(speed * `steer_vel_att`, 1.5), 1.6) * [1] (`tnfs_control_steering_a`)'
            },
        )
        steer_vel_ramp = (
            _fixed(),
            {'description': 'Base steering rate (2.2-2.5), see `steer_vel` (`tnfs_control_steering_a`)'},
        )
        steer_vel_att = (
            _fixed(),
            {'description': 'Steering rate reduction per m/s, at most 1.5 in total (`tnfs_control_steering_a`)'},
        )
        steer_ramp_mult = (
            _uint(),
            {
                'description': 'Shift count: steering rate << this when the target and the auto-steer angle are on '
                'the same side of the current angle (`tnfs_control_steering_a`)'
            },
        )
        steer_ramp_div = (
            _uint(),
            {
                'description': 'Shift count: steering rate >> this otherwise (`tnfs_control_steering_a`; SE and PSX '
                'only, DOS has no such branch)'
            },
        )
        lat_acc_cutoff = (
            _fixed(),
            {
                'description': 'Max absolute lateral acceleration (m/s², 17.5-40), also the road grip increment '
                '(`tnfs_physics_update`). PSX rally mode x 0.625'
            },
        )
        unknown_0x320 = (
            _fixed8(),
            {
                'is_unknown': True,
                'description': 'Equals `thrust_scale` in all files (2.5; TRAFFC 5.5, TSUPRA 2.7). Not read; rally '
                'mode (DOS, SE) halves it and recomputes `unknown_0x320_inv`',
            },
        )
        unknown_0x320_inv = (
            _fixed8(programmatic_value=lambda ctx: floor_8(1 / ctx.data('unknown_0x320'))),
            {'is_unknown': True, 'description': '`1 / unknown_0x320`, rounded down (raw 65536 / raw). Not read'},
        )
        thrust_scale = (
            _fixed8(),
            {
                'description': 'Thrust multiplier (`tnfs_engine_thrust`): 2.5, TRAFFC 5.5, TSUPRA 2.7. Rally mode '
                'halves it and recomputes `force_to_accel`'
            },
        )
        force_to_accel = (
            _fixed8(programmatic_value=lambda ctx: floor_8(1 / ctx.data('thrust_scale'))),
            {
                'description': '`1 / thrust_scale`, rounded down (raw 65536 / raw): summed longitudinal tire force '
                '* this = acceleration (m/s²) (`tnfs_physics_update`)'
            },
        )
        unknown_0x330 = (_uint(), {'is_unknown': True, 'description': '102 in all files. Not read'})
        has_abs = (
            _fixed(),
            {
                'description': 'Car has ABS if > 0 (1.0); ABS is on if this and the player option are both set '
                '(`Fiziks_PreInitCar`)'
            },
        )
        has_tcs = (_fixed(), {'description': 'Car has traction control if > 0 (1.0), like `has_abs`'})
        throttle_on_ramp = (
            _uint(),
            {'description': 'Throttle (0-255) rise per tick (`tnfs_control_throttle`, SE 0x438b70)'},
        )
        throttle_off_ramp = (_uint(), {'description': 'Throttle (0-255) fall per tick (`tnfs_control_throttle`)'})
        brake_on_ramp_1 = (
            _uint(),
            {
                'description': 'Brake (0-255) rise per tick, x 1.25, while the brake is below 144 '
                '(`tnfs_control_brake`, SE 0x438bc8)'
            },
        )
        brake_on_ramp_2 = (_uint(), {'description': 'Brake rise per tick, x 1.25, from 144 up (`tnfs_control_brake`)'})
        brake_off_ramp_1 = (
            _uint(),
            {'description': 'Brake fall per tick while the brake is below 144 (`tnfs_control_brake`)'},
        )
        brake_off_ramp_2 = (_uint(), {'description': 'Brake fall per tick from 144 up (`tnfs_control_brake`)'})
        shift_timer = (
            _uint(),
            {
                'description': 'Ticks with the gear disengaged while shifting (`tnfs_control_shift_gears`, '
                '`tnfs_engine_auto_shift_control` SE 0x42ed94). Manual downshift: half of it; automatic N -> D: '
                '+1; F512TR (car model 4): +3 when (time & 0x31) == 0x10'
            },
        )
        rpm_dec = (
            _uint(),
            {
                'description': 'Rpm fall per tick towards idle without throttle while the gear is disengaged, half '
                'in neutral (`tnfs_engine_rev_limiter`)'
            },
        )
        rpm_acc = (
            _uint(),
            {
                'description': 'Rpm rise per tick, x throttle / 256, while the gear is disengaged, half in neutral '
                '(`tnfs_engine_rev_limiter`)'
            },
        )
        drop_rpm_dec = (
            _uint(),
            {
                'description': 'In gear: engine rpm fall per tick towards the wheel rpm; / 8 while the rear wheels '
                'spin with throttle > 220 (`tnfs_engine_rev_limiter`)'
            },
        )
        drop_rpm_inc = (
            _uint(),
            {
                'description': 'In gear: engine rpm rise per tick towards the wheel rpm (`tnfs_engine_rev_limiter`; '
                'its branch multiplying this by a per-gear table is unreachable)'
            },
        )
        neg_torque = (
            _uint(),
            {
                'description': 'Engine braking: force = rpm difference * this / 256 * gear ratio, x 8 when the '
                'wheels drive the engine (`tnfs_engine_thrust`)'
            },
        )
        incar_camera_height = (
            _fixed(),
            {'description': 'In-car camera height (m, ~1.0) (in-car camera setup, SE 0x405630). Not read by PSX'},
        )
        center_y = (
            _uint(),
            {
                'description': 'In-car view vertical centre (pixels of 320x200): the in-car view windows get the y '
                'offset (center_y - 108) * screen height / 200 (in-car camera setup, SE 0x405630). Not read by PSX. '
                'The formula is certain, its meaning (projection centre) is an interpretation'
            },
        )
        grip_table_f = (
            ArrayBlock(length=512, child=IntegerBlock(length=1)),
            {
                'description': 'Front tire grip by slip angle, grip = value / 128 (the game: value << 9 as 16.16). '
                'Index = slip angle (24-bit) >> 12: 0.088° steps over 0-45° (`tnfs_tire_slide_table`, read in '
                '`tnfs_tire_forces`; DOS 0x593d5). Index 511 is unreachable with the 44.9° `slip_cutoff` and holds '
                'garbage'
            },
        )
        grip_table_r = (
            ArrayBlock(length=512, child=IntegerBlock(length=1)),
            {
                'description': 'Rear tire grip by slip angle, like `grip_table_f`. Rally mode (DOS, SE) replaces it '
                'with the front table in memory'
            },
        )
        checksum = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: sum(ctx.result[:1880])),
            {
                'description': 'Byte sum of the first 1880 bytes (0x758: all but the last 28 bytes of '
                '`grip_table_r`). On a mismatch `Fiziks_PreInitCar` sets `efficiency` to 0'
            },
        )

    def serializer_class(self):
        from serializers import JsonSerializer

        return JsonSerializer


class CarAiAndCrashBody(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Car AI and crash body: the AI driving model and the collision body of a car '
            '(`SIMDATA/CARFAMS/*.PDN`, QFS-compressed, 460 bytes uncompressed), one per car slot, player included. '
            'Loaded by `tnfs_ai_pdn_file` (SE 0x40fa3c, DOS 0x47425, PSX 0x8001eaa8), applied by `tnfs_ai_init_car` '
            '(SE 0x4407b8). Angles are 24-bit (0x1000000 = full turn)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        half_width = (
            _ufixed(),
            {
                'description': 'Half width (x) of the collision body (m); car width = 2 * this, it overrides PBS '
                '`body_width` (`tnfs_ai_init_car`). Zero in all traffic and cop PDNs: if any of the three half '
                'sizes is 0, the sizes come from the car 3D model'
            },
        )
        half_height = (
            _ufixed(),
            {'description': 'Half height (y) of the collision body (m), also the collision height offset'},
        )
        half_length = (
            _ufixed(),
            {
                'description': 'Half length (z) of the collision body (m); car length = 2 * this, it overrides PBS '
                '`body_len`'
            },
        )
        moment_of_inertia = (
            _fixed(),
            {
                'description': 'Crash-body moment of inertia (1.4-2.25), no physical unit; angular acceleration '
                'factor = 1 / this (`tnfs_collision_data_reset` and the rebound functions)'
            },
        )
        mass = (
            _ufixed(),
            {
                'description': 'Relative crash-body mass (1.0 typical, 0.5-1.5), no physical unit; linear '
                'acceleration factor = 1 / this. Car to car impulses are split by the mass ratio'
            },
        )
        handling_factor = (
            _angle24(),
            {
                'description': 'Racers only (`tnfs_ai_racer_speed`, SE 0x470a9c, DOS 0x80c50, PSX 0x8005bcc8), '
                '24-bit angle (0xA0000 = 14.1°): target speed * (0.8 + 0.203 * (1 - turn / this)), turn = road '
                'heading change per track node. 0xFF0000 (TSUPRA, TRAFFC, traffic, cops) = no corner slowdown. '
                'Copied to car+0x168, its inverse to car+0x16c'
            },
        )
        speed_factor = (
            _fixed(),
            {
                'description': 'Racers only: target speed multiplier (0.92-1.0) (`tnfs_ai_racer_speed`, '
                'car+0x170). 1.0 in traffic and cop PDNs'
            },
        )
        power_curve = (
            ArrayBlock(length=100, child=_fixed()),
            {
                'description': 'AI acceleration by speed (`tnfs_ai_drive_car`, SE 0x46f3e8, DOS 0x7e961, PSX '
                '0x80059d68): speed gain per AI update at index abs(speed in m/s) + 1, x 8 (traffic), x 4 '
                '(racers), x 6 (cops), minus the drive argument of the function. The car slows down when [index - '
                '1] is 0. In racer PDNs the first 0 is at the top gear speed rounded up; traffic PDNs have a linear '
                '0.2 -> 0 curve, COPMUST the P911 curve. Uncertain: the exact time scale and the drive argument'
            },
        )
        top_speeds = (
            ArrayBlock(length=6, child=_fixed()),
            {
                'description': 'Top speed (m/s) per AI gear, 0 = gear skipped (leading zeros); all 0 in traffic and '
                "cop PDNs. Racers' engine rpm = 0.75 * `max_rpm` * speed / top speed of the gear, a shift timer "
                'starts at each gear change (`tnfs_ai_opp_engine_and_cornering`, SE 0x46c278, DOS 0x79af9)'
            },
        )
        max_rpm = (
            _fixed(),
            {'description': "Racers' engine rpm cap, drives the opponent engine sound. 0 in traffic and cop PDNs"},
        )
        gear_count = (
            IntegerBlock(length=4),
            {
                'description': 'Read only as the traffic horn pitch index, when `tnfs_ai_lane_change` starts the '
                'horn (tnfs-1995 names it `pdn_number_of_gears`). Not the number of gears: 5 in every racer PDN, '
                'also in CZR1, DVIPER, P911 and TSUPRA with 6 `top_speeds`. The game plays the traffic horn '
                '(collision bank sample 0x3f) at pitch value `table[index] * doppler >> 8`, table at DOS 0x81aa9 = '
                '0x40, 0x40, 0x64, 0x5a, 0x50, 0x46, 0x3c, 0x32, 0x2d, 0x28. Values: crx 2, bmw 3, jetta 3, sunbird '
                '4, wagon 4, pickup 5, probe 5, traffc 5, axxess 6, jeep 6, lemans 6, rodeo 8, vandura 8, copmust 0 '
                '(the cop never honks); 7 and 9 unused'
            },
        )

    def serializer_class(self):
        from serializers import JsonSerializer

        return JsonSerializer
