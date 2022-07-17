from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import IntegerBlock
from library.read_blocks.compound import CompoundBlock
from resources.eac.fields.numbers import RationalNumber


class EngineTorqueRecord(CompoundBlock):
    block_description = "Engine torque for given RPM record"

    class Fields(CompoundBlock.Fields):
        rpm = IntegerBlock(static_size=4)
        torque = IntegerBlock(static_size=4)


class CarPerformanceSpec(CompoundBlock):
    block_description = "This block describes full car physics specification for car that player can drive. Looks " \
                        "like it's not used for opponent cars and such files do not exist for traffic/cop cars " \
                        "at all. Big thanks to Five-Damned-Dollarz, he seems to be the only one guy who managed to " \
                        "understand most of the fields in this block. His specification: " \
                        "https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e"

    class Fields(CompoundBlock.Fields):
        mass_front_axle = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True,
                                         description='The meaning is theoretical. For all cars value is mass / 2')
        mass_rear_axle = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True,
                                        description='The meaning is theoretical. For all cars value is mass / 2')
        mass = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Car mass')
        unknowns0 = ArrayBlock(length=4, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True)
        brake_bias = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True,
                                    description='how much car rotates when brake?')
        unknowns1 = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        center_of_gravity = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True,
                                           description='probably the height of mass center in meters')
        max_brake_decel = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        unknowns2 = ArrayBlock(length=2, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True)
        drag = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        top_speed = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        efficiency = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        body__wheel_base = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                          description='The distance betweeen rear and front axles in meters')
        burnout_div = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        body__wheel_track = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                           description='The distance betweeen left and right wheels in meters')
        unknowns3 = ArrayBlock(length=2, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True)
        mps_to_rpm_factor = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                           description='Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * '
                                                       'gearRatio)')
        transmission__gears_count = IntegerBlock(static_size=4, description='Amount of drive gears + 2 (R,N?)')
        transmission__final_drive_ratio = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        roll_radius = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        unknowns4 = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        transmission__gear_ratios = ArrayBlock(length=8,
                                               child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                                               description="Only first <gear_count> values are used. First element is "
                                                           "the reverse gear ratio, second one is unknown")
        engine__torque_count = IntegerBlock(static_size=4, description='Torques LUT (lookup table) size')
        front_roll_stiffness = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        rear_roll_stiffness = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        roll_axis_height = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        unknowns5 = ArrayBlock(length=3, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True,
                               description="those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube?")
        slip_angle_cutoff = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        normal_coefficient_loss = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        engine__max_rpm = IntegerBlock(static_size=4)
        engine__min_rpm = IntegerBlock(static_size=4)
        engine__torques = ArrayBlock(child=EngineTorqueRecord(), length=60,
                                     description="LUT (lookup table) of engine torque depending on RPM. <engine__torque_count> "
                                                 "first elements used")
        transmission__upshifts = ArrayBlock(length=5, child=IntegerBlock(static_size=4),
                                            description='RPM value, when automatic gear box should upshift. 1 element '
                                                        'per drive gear')
        unknowns6 = ArrayBlock(length=4, child=RationalNumber(static_size=2, fraction_bits=8, is_signed=True), is_unknown=True)
        unknowns7 = ArrayBlock(length=7, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True)
        unknowns8 = ArrayBlock(length=2, child=RationalNumber(static_size=2, fraction_bits=8, is_signed=True), is_unknown=True)
        inertia_factor = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        body_roll_factor = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        body_pitch_factor = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        front_friction_factor = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        rear_fricton_factor = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        body__length = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                      description='Chassis body length in meters')
        body__width = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                     description='Chassis body width in meters')
        steering__max_auto_steer_angle = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                                        is_unknown=True)
        steering__auto_steer_mult_shift = IntegerBlock(static_size=4, is_unknown=True)
        steering__auto_steer_div_shift = IntegerBlock(static_size=4, is_unknown=True)
        steering__steering_model = IntegerBlock(static_size=4, is_unknown=True)
        steering__auto_steer_velocities = ArrayBlock(length=4, child=IntegerBlock(static_size=4), is_unknown=True)
        steering__auto_steer_velocity_ramp = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                                            is_unknown=True)
        steering__auto_steer_velocity_attenuation = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                                                   is_unknown=True)
        steering__auto_steer_ramp_mult_shift = IntegerBlock(static_size=4, is_unknown=True)
        steering__auto_steer_ramp_div_shift = IntegerBlock(static_size=4, is_unknown=True)
        lateral_accel_cutoff = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        unknowns9 = ArrayBlock(length=13, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True)
        engine_shifting__shift_timer = IntegerBlock(static_size=4, is_unknown=True,
                                                    description='Unknown exactly, but it seems to be ticks '
                                                                'taken to shift. Tick is probably 100ms')
        engine_shifting__rpm_decel = IntegerBlock(static_size=4, is_unknown=True)
        engine_shifting__rpm_accel = IntegerBlock(static_size=4, is_unknown=True)
        engine_shifting__clutch_drop_decel = IntegerBlock(static_size=4, is_unknown=True)
        engine_shifting__neg_torque = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        body__clearance = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)
        body__height = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        center_x = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, is_unknown=True)
        grip_curve_front = ArrayBlock(child=IntegerBlock(static_size=1), length=512, is_unknown=True)
        grip_curve_rear = ArrayBlock(child=IntegerBlock(static_size=1), length=512, is_unknown=True)
        hash = IntegerBlock(static_size=4, description='Check sum of this block contents', is_unknown=True)


class CarSimplifiedPerformanceSpec(CompoundBlock):
    block_description = "This block describes simpler version of car physics. It is not clear how and when is is used"

    class Fields(CompoundBlock.Fields):
        unknowns0 = ArrayBlock(length=3, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True,
                               description='Unknown. Some values for playable cars, always zeros for non-playable')
        moment_of_inertia = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                           description='Not clear how to interpret')
        unknowns1 = ArrayBlock(length=3, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                               is_unknown=True)
        power_curve = ArrayBlock(length=100, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                                 description='Not clear how to interpret')
        top_speeds = ArrayBlock(length=6, child=RationalNumber(static_size=4, fraction_bits=16, is_signed=True),
                                description='Maximum car speed (m/s) per gear')
        max_rpm = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Max engine RPM')
        gear_count = IntegerBlock(static_size=4, description='Gears amount')
