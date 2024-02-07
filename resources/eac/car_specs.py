from typing import Dict

from library.read_blocks import DeclarativeCompoundBlock, IntegerBlock, ArrayBlock, CompoundBlock, BytesBlock
from resources.eac.fields.numbers import RationalNumber


class CarPerformanceSpec(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': "This block describes full car physics specification for car that player can "
                                     "drive. Looks like it's not used for opponent cars and such files do not exist for"
                                     " traffic/cop cars at all. Big thanks to Five-Damned-Dollarz, he seems to be the "
                                     "only one guy who managed to understand most of the fields in this block. "
                                     "[His specification](https://gist.github.com/Five-Damned-Dollarz/"
                                     "99e955994ebbcf970532406a197b580e)"}

    class Fields(DeclarativeCompoundBlock.Fields):
        mass_front_axle = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                           {'is_unknown': True,
                            'description': 'The meaning is theoretical. For all cars value is mass / 2'})
        mass_rear_axle = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                          {'is_unknown': True,
                           'description': 'The meaning is theoretical. For all cars value is mass / 2'})
        mass = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                {'description': 'Car mass (kg)'})
        unk0 = (BytesBlock(length=12),
                {'is_unknown': True})
        unk1 = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                {'is_unknown': True,
                 'description': 'Does something with front wheels slipping or braking'})
        brake_bias = (RationalNumber(length=4, fraction_bits=16, is_signed=False),
                      {'description': 'Bias for brake force (0.0-1.0), determines the amount of braking force '
                                      'applied to front and rear axles: 0.7 will distribute braking force 70% '
                                      'on the front, 30% on the rear'})
        unk2 = (BytesBlock(length=4),
                {'is_unknown': True})
        center_of_gravity = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                             {'is_unknown': True,
                              'description': 'probably the height of mass center in meters'})
        brake_forces = (ArrayBlock(length=2, child=RationalNumber(length=4, fraction_bits=16, is_signed=True)),
                        {'description': 'Brake forces, units are unknown. First number is responsible for braking on '
                                        'reverse, neutral and first gears, second number is responsible for braking on '
                                        'second gear. Interestingly, all gears > 2 use both numbers with unknown rules.'
                                        ' Tested it on lamborghini'})
        unk3 = (BytesBlock(length=4),
                {'is_unknown': True})
        drag = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                {'description': 'Drag force, units are unknown'})
        top_speed = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                     {'description': 'Max vehicle speed in meters per second'})
        efficiency = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                      {'is_unknown': True})
        body__wheel_base = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                            {'description': 'The distance betweeen rear and front axles in meters'})
        burnout_div = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                       {'is_unknown': True})
        body__wheel_track = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                             {'description': 'The distance betweeen left and right wheels in meters'})
        unk4 = (BytesBlock(length=8),
                {'is_unknown': True})
        mps_to_rpm_factor = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                             {'description': 'Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * gearRatio)'})
        transmission__gears_count = (IntegerBlock(length=4),
                                     {'description': 'Amount of drive gears + 2 (R,N?)'})
        transmission__final_drive_ratio = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                           {'description': 'Final drive ratio'})
        roll_radius = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                       {'is_unknown': True})
        unk5 = (BytesBlock(length=4),
                {'is_unknown': True})
        transmission__gear_ratios = (ArrayBlock(length=8, child=RationalNumber(length=4, fraction_bits=16,
                                                                               is_signed=True)),
                                     {'description': "Only first <gear_count> values are used. First element is the "
                                                     "reverse gear ratio, second one is unknown"})
        engine__torque_count = (IntegerBlock(length=4),
                                {'description': 'Torques LUT (lookup table) size'})
        front_roll_stiffness = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                {'is_unknown': True})
        rear_roll_stiffness = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                               {'is_unknown': True})
        roll_axis_height = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                            {'is_unknown': True})
        unk6 = (ArrayBlock(length=3, child=RationalNumber(length=4, fraction_bits=16, is_signed=True)),
                {'is_unknown': True,
                 'description': 'those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube?'})
        slip_angle_cutoff = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                             {'is_unknown': True})
        normal_coefficient_loss = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                   {'is_unknown': True})
        engine__max_rpm = (IntegerBlock(length=4),
                           {'description': 'Engine max RPM'})
        engine__min_rpm = (IntegerBlock(length=4),
                           {'description': 'Engine min RPM'})
        engine__torques = (ArrayBlock(child=CompoundBlock(fields=[('rpm', IntegerBlock(length=4), {}),
                                                                  ('torque', IntegerBlock(length=4), {}), ],
                                                          inline_description="Two 32bit unsigned integers (little-endian"
                                                                             "). First one is RPM, second is a torque"),
                                      length=60),
                           {'description': "LUT (lookup table) of engine torque depending on RPM. "
                                           "<engine__torque_count> first elements used"})
        transmission__upshifts = ArrayBlock(length=5, child=IntegerBlock(length=4),
                                            description='RPM value, when automatic gear box should upshift. 1 element '
                                                        'per drive gear'), {'description': ''}
        unk7 = (BytesBlock(length=40),
                {'is_unknown': True})
        inertia_factor = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                          {'is_unknown': True})
        body_roll_factor = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                            {'is_unknown': True})
        body_pitch_factor = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                             {'is_unknown': True})
        front_friction_factor = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                 {'is_unknown': True})
        rear_fricton_factor = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                               {'is_unknown': True})
        body__length = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Chassis body length in meters'})
        body__width = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                       {'description': 'Chassis body width in meters'})
        steering__max_auto_steer_angle = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                          {'is_unknown': True})
        steering__auto_steer_mult_shift = (IntegerBlock(length=4),
                                           {'is_unknown': True})
        steering__auto_steer_div_shift = (IntegerBlock(length=4),
                                          {'is_unknown': True})
        steering__steering_model = (IntegerBlock(length=4),
                                    {'is_unknown': True})
        steering__auto_steer_velocities = (ArrayBlock(length=4, child=IntegerBlock(length=4)),
                                           {'is_unknown': True})
        steering__auto_steer_velocity_ramp = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                              {'is_unknown': True})
        steering__auto_steer_velocity_attenuation = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                                     {'is_unknown': True})
        steering__auto_steer_ramp_mult_shift = (IntegerBlock(length=4),
                                                {'is_unknown': True})
        steering__auto_steer_ramp_div_shift = (IntegerBlock(length=4),
                                               {'is_unknown': True})
        lateral_accel_cutoff = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                {'is_unknown': True})
        unk8 = (BytesBlock(length=52),
                {'is_unknown': True})
        engine_shifting__shift_timer = (IntegerBlock(length=4),
                                        {'is_unknown': True,
                                         'description': 'Unknown exactly, but it seems to be ticks taken to shift. '
                                                        'Tick is probably 16ms'})
        engine_shifting__rpm_decel = (IntegerBlock(length=4),
                                      {'is_unknown': True})
        engine_shifting__rpm_accel = (IntegerBlock(length=4),
                                      {'is_unknown': True})
        engine_shifting__clutch_drop_decel = (IntegerBlock(length=4),
                                              {'is_unknown': True})
        engine_shifting__neg_torque = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                                       {'is_unknown': True})
        body__clearance = (RationalNumber(length=4, fraction_bits=7, is_signed=True),
                           {'description': 'Body clearance in meters'})
        body__height = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                        {'description': 'Body height in meters'})
        center_x = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                    {'is_unknown': True})
        unk9 = (ArrayBlock(child=IntegerBlock(length=1), length=512),
                {'is_unknown': True,
                 'description': 'Unknown values. in 3DO version "grip_curve_front" is here, takes the same space'})
        unk10 = (ArrayBlock(child=IntegerBlock(length=1), length=512),
                 {'is_unknown': True,
                  'description': 'Unknown values. in 3DO version "grip_curve_rear" is here, takes the same space'})
        hash = (IntegerBlock(length=4),
                {'programmatic_value': lambda ctx: sum(ctx.result[:1880]),
                 'description': 'Check sum of this block contents. Equals to sum of 1880 first bytes'})


class CarSimplifiedPerformanceSpec(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': "This block describes simpler version of car physics. Used by game for other cars"}

    class Fields(DeclarativeCompoundBlock.Fields):
        unknowns0 = (BytesBlock(length=12),
                     {'description': 'Unknown. Some values for playable cars, always zeros for non-playable',
                      'is_unknown': True})
        moment_of_inertia = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                             {'description': 'Not clear how to interpret'})
        unknowns1 = (BytesBlock(length=12),
                     {'is_unknown': True})
        power_curve = (ArrayBlock(length=100, child=RationalNumber(length=4, fraction_bits=16, is_signed=True)),
                       {'description': 'Not clear how to interpret'})
        top_speeds = (ArrayBlock(length=6, child=RationalNumber(length=4, fraction_bits=16, is_signed=True)),
                      {'description': 'Maximum car speed (m/s) per gear'})
        max_rpm = (RationalNumber(length=4, fraction_bits=16, is_signed=True),
                   {'description': 'Max engine RPM'})
        gear_count = (IntegerBlock(length=4),
                      {'description': 'Gears amount'})
