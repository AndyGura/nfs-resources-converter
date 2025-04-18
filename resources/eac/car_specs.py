import math
from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock, IntegerBlock, ArrayBlock, CompoundBlock, BytesBlock,
                                 FixedPointBlock)


# TNFS when saving some of the calculated values, uses `floor` instead of `round`
def floor_16(value):
    pow16 = 2 ** 16
    return math.floor(value * pow16) / pow16

class CarPerformanceSpec(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': "This block describes full car physics specification for car that player can "
                                     "drive. Thanks to [Five-Damned-Dollarz](https://gist.github.com/Five-Damned-"
                                     "Dollarz/99e955994ebbcf970532406a197b580e) and [marcos2250](https://github.com/"
                                     "marcos2250/tnfs-1995/blob/main/tnfs_files.c)"}

    class Fields(DeclarativeCompoundBlock.Fields):
        mass_front = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Mass applied to front axle (kg)'})
        mass_rear = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                     {'description': 'Mass applied to rear axle (kg)'})
        mass = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                {'description': 'Total car mass (kg). Always == `mass_front + mass_rear`',
                 'programmatic_value': lambda ctx: ctx.data('mass_front') + ctx.data('mass_rear')})
        inv_mass_f = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Inverted mass applied to front axle in kg, `1 / mass_front`',
                       'programmatic_value': lambda ctx: floor_16(1 / ctx.data('mass_front'))})
        inv_mass_r = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Inverted mass applied to rear axle in kg, `1 / mass_rear`',
                       'programmatic_value': lambda ctx: floor_16(1 / ctx.data('mass_rear'))})
        inv_mass = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                    {'description': 'Inverted mass in kg, `1 / mass`',
                     'programmatic_value': lambda ctx: floor_16(1 / (ctx.data('mass_front') + ctx.data('mass_rear')))})
        drive_bias = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                      {'description': 'Bias for drive force (0.0-1.0, where 0 is RWD, 1 is FWD), determines the amount '
                                      'of force applied to front and rear axles: 0.7 will distribute force 70% '
                                      'on the front, 30% on the rear'})
        brake_bias_f = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                        {'description': 'Bias for brake force (0.0-1.0), determines the amount of braking force '
                                        'applied to front and rear axles: 0.7 will distribute braking force 70% '
                                        'on the front, 30% on the rear'})
        brake_bias_r = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                        {'description': 'Bias for brake force for rear axle. Always == `1 - brake_bias_f`',
                         'programmatic_value': lambda ctx: 1 - ctx.data('brake_bias_f')})
        mass_y = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                  {'description': 'Probably the height of mass center in meters'})
        brake_force = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                       {'description': 'Brake force in unknown units'})
        brake_force2 = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                        {'description': 'Brake force, equals to `brake_force`. Not clear why PBS has two of these, '
                                        'first number is responsible for braking on reverse, neutral and first gears, '
                                        'second number is responsible for braking on second gear. '
                                        'Interestingly, all gears > 2 use both numbers with unknown rules. '
                                        'Tested it on lamborghini',
                         'programmatic_value': lambda ctx: ctx.data('brake_force')})
        unk0 = (BytesBlock(length=4),
                {'is_unknown': True})
        drag = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                {'description': 'Drag force, units are unknown'})
        top_speed = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                     {'description': 'Max vehicle speed in meters per second'})
        efficiency = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': ''})
        wheel_base = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'The distance betweeen rear and front axles in meters'})
        burnout_div = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': ''})
        wheel_track = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'The distance betweeen left and right wheels in meters'})
        unk1 = (BytesBlock(length=8),
                {'is_unknown': True})
        mps_to_rpm = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * gearRatio)'})
        num_gears = (IntegerBlock(length=4),
                     {'description': 'Amount of drive gears + 2 (R,N?)'})
        final_drive = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Final drive ratio'})
        wheel_radius = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Wheel radius in meters'})
        inv_wheel_rad = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                         {'description': 'Inverted wheel radius in meters, `1 / wheel_radius`',
                          'programmatic_value': lambda ctx: floor_16(1 / ctx.data('wheel_radius'))})
        gear_ratios = (ArrayBlock(length=8, child=FixedPointBlock(length=4, fraction_bits=16,
                                                                 is_signed=True)),
                       {'description': "Only first `num_gears` values are used. First element is the "
                                       "reverse gear ratio, second one is unknown"})
        num_torques = (IntegerBlock(length=4),
                       {'description': 'Torques LUT (lookup table) size'})
        roll_stiff_f = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Roll stiffness front axle'})
        roll_stiff_r = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Roll stiffness rear axle'})
        roll_axis_y = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Roll axis height'})
        unk2 = (ArrayBlock(length=3, child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                {'is_unknown': True,
                 'description': 'those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube?'})
        slip_cutoff = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Slip angle cut-off'})
        normal_loss = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Normal coefficient loss'})
        max_rpm = (IntegerBlock(length=4),
                   {'description': 'Engine max RPM'})
        min_rpm = (IntegerBlock(length=4),
                   {'description': 'Engine min RPM'})
        torques = (ArrayBlock(length=60,
                              child=CompoundBlock(fields=[('rpm', IntegerBlock(length=4), {}),
                                                          ('torque', IntegerBlock(length=4), {}), ],
                                                  inline_description="Two 32bit unsigned integers (little-endian). "
                                                                     "First one is RPM, second is a torque")),
                   {'description': "LUT of engine torque depending on RPM. `num_torques` first elements used"})
        upshifts = (ArrayBlock(length=7, child=IntegerBlock(length=4)),
                    {'description': 'RPM value, when automatic gear box should upshift. 1 element per drive gear'})
        gear_efficiency = (ArrayBlock(length=8, child=IntegerBlock(length=4)),
                           {'description': ''})
        inertia_factor = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                          {'description': ''})
        roll_factor = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Body roll factor'})
        pitch_factor = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Body pitch factor'})
        friction_f = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Front axle friction factor'})
        friction_r = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Rear axle friction factor'})
        body_len = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                    {'description': 'Chassis body length in meters'})
        body_width = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Chassis body width in meters'})
        auto_steer = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                      {'description': 'Max auto steer angle'})
        steer_mult = (IntegerBlock(length=4),
                      {'description': 'auto_steer_mult_shift'})
        steer_div = (IntegerBlock(length=4),
                     {'description': 'auto_steer_div_shift'})
        steer_model = (IntegerBlock(length=4),
                       {'description': 'Steering model'})
        steer_vel = (ArrayBlock(length=4, child=IntegerBlock(length=4)),
                     {'description': 'Auto steer velocities'})
        steer_vel_ramp = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                          {'description': 'Auto steer velocity ramp'})
        steer_vel_att = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                         {'description': 'Auto steer velocity attenuation'})
        steer_ramp_mult = (IntegerBlock(length=4),
                           {'description': 'auto_steer_ramp_mult_shift'})
        steer_ramp_div = (IntegerBlock(length=4),
                          {'description': 'auto_steer_ramp_div_shift'})
        lat_acc_cutoff = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                          {'description': 'Lateral acceleration cut-off'})
        unk3 = (BytesBlock(length=8),
                {'is_unknown': True,
                 'description': 'First 4 bytes is integer number, and TNFS after reading file divides it in half at 0x00440364'})
        final_ratio = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Final drive torque ratio'})
        thrust_factor = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                         {'description': 'Thrust to acceleration factor'})
        unk4 = (BytesBlock(length=36),
                {'is_unknown': True})
        shift_timer = (IntegerBlock(length=4),
                       {'description': 'Seems to be ticks taken to shift. Tick is 1 / 60 of a second'})
        rpm_dec = (IntegerBlock(length=4),
                   {'description': 'RPM decrease when gas pedal released'})
        rpm_acc = (IntegerBlock(length=4),
                   {'description': 'RPM increase when gas pedal pressed'})
        drop_rpm_dec = (IntegerBlock(length=4),
                        {'description': 'Clutch drop RPM decrease'})
        drop_rpm_inc = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Clutch drop RPM increase'})
        neg_torque = (FixedPointBlock(length=4, fraction_bits=7, is_signed=True),
                      {'description': 'Negative torque'})
        height = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                  {'description': 'Body height in meters'})
        center_y = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                    {'description': ''})
        grip_table_f = (ArrayBlock(length=512, child=FixedPointBlock(length=1, fraction_bits=4)),
                        {'description': 'Grip table for front axle. Unit is unknown'})
        grip_table_r = (ArrayBlock(length=512, child=FixedPointBlock(length=1, fraction_bits=4)),
                        {'description': 'Grip table for rear axle. Unit is unknown. Windows version overwrites this '
                                        'table with values from "grip_table_f" at 0x00440349'})
        checksum = (IntegerBlock(length=4),
                    {'programmatic_value': lambda ctx: sum(ctx.result[:1880]),
                     'description': 'Check sum of this block contents. Equals to sum of 1880 first bytes. If wrong, '
                                    'game sets field "efficiency" to zero'})


class CarSimplifiedPerformanceSpec(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': "This block describes simpler version of car physics. Used by game for other cars"}

    class Fields(DeclarativeCompoundBlock.Fields):
        col_size_x = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                      {'description': 'Collision model size (x) in meters. Zero for all non-playable cars'})
        col_size_y = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                      {'description': 'Collision model size (y) in meters. Zero for all non-playable cars'})
        col_size_z = (FixedPointBlock(length=4, fraction_bits=16, is_signed=False),
                      {'description': 'Collision model size (z) in meters. Zero for all non-playable cars'})
        moment_of_inertia = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                             {'description': 'Not clear how to interpret'})
        mass = (FixedPointBlock(length=4, fraction_bits=6, is_signed=False),
                {'description': 'Vehicle mass (kg?)'})
        unk0 = (IntegerBlock(length=4, is_signed=False),
                {'is_unknown': True})
        unk1 = (IntegerBlock(length=4, is_signed=False),
                {'is_unknown': True})
        power_curve = (ArrayBlock(length=100, child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                       {'description': 'Not clear how to interpret'})
        top_speeds = (ArrayBlock(length=6, child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                      {'description': 'Maximum car speed (m/s) per gear'})
        max_rpm = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                   {'description': 'Max engine RPM'})
        gear_count = (IntegerBlock(length=4),
                      {'description': 'Gears amount'})
