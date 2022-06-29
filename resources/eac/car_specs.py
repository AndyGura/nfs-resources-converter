from resources.basic.array_field import ArrayField
from resources.basic.atomic import IntegerField
from resources.basic.compound_block import CompoundBlock
from resources.eac.fields.numbers import Nfs1Float32, Nfs1Float16, Nfs1Float32_7


class EngineTorqueRecord(CompoundBlock):
    block_description = "Engine torque for given RPM record"

    class Fields(CompoundBlock.Fields):
        rpm = IntegerField(static_size=4)
        torque = IntegerField(static_size=4)


class CarPerformanceSpec(CompoundBlock):
    block_description = "This block describes full car physics specification for car that player can drive. Looks " \
                        "like it's not used for opponent cars and such files do not exist for traffic/cop cars " \
                        "at all. Big thanks to Five-Damned-Dollarz, he seems to be the only one guy who managed to " \
                        "understand most of the fields in this block. His specification: " \
                        "https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e"

    class Fields(CompoundBlock.Fields):
        mass_front_axle = Nfs1Float32(is_unknown=True,
                                      description='The meaning is theoretical. For all cars value is mass / 2')
        mass_rear_axle = Nfs1Float32(is_unknown=True,
                                     description='The meaning is theoretical. For all cars value is mass / 2')
        mass = Nfs1Float32(description='Car mass')
        unknowns0 = ArrayField(length=4, child=Nfs1Float32(), is_unknown=True)
        brake_bias = Nfs1Float32(is_unknown=True, description='how much car rotates when brake?')
        unknowns1 = Nfs1Float32(is_unknown=True)
        center_of_gravity = Nfs1Float32(is_unknown=True, description='probably the height of mass center in meters')
        max_brake_decel = Nfs1Float32(is_unknown=True)
        unknowns2 = ArrayField(length=2, child=Nfs1Float32(), is_unknown=True)
        drag = Nfs1Float32(is_unknown=True)
        top_speed = Nfs1Float32(is_unknown=True)
        efficiency = Nfs1Float32(is_unknown=True)
        body__wheel_base = Nfs1Float32(description='The distance betweeen rear and front axles in meters')
        burnout_div = Nfs1Float32(is_unknown=True)
        body__wheel_track = Nfs1Float32(description='The distance betweeen left and right wheels in meters')
        unknowns3 = ArrayField(length=2, child=Nfs1Float32(), is_unknown=True)
        mps_to_rpm_factor = Nfs1Float32(description='Used for optimization: speed(m/s) = RPM / (mpsToRpmFactor * '
                                                    'gearRatio)')
        transmission__gears_count = IntegerField(static_size=4, description='Amount of drive gears + 2 (R,N?)')
        transmission__final_drive_ratio = Nfs1Float32()
        roll_radius = Nfs1Float32(is_unknown=True)
        unknowns4 = Nfs1Float32(is_unknown=True)
        transmission__gear_ratios = ArrayField(length=8, child=Nfs1Float32(),
                                               description="Only first <gear_count> values are used. First element is "
                                                           "the reverse gear ratio, second one is unknown")
        engine__torque_count = IntegerField(static_size=4, description='Torques LUT (lookup table) size')
        front_roll_stiffness = Nfs1Float32(is_unknown=True)
        rear_roll_stiffness = Nfs1Float32(is_unknown=True)
        roll_axis_height = Nfs1Float32(is_unknown=True)
        unknowns5 = ArrayField(length=3, child=Nfs1Float32(), is_unknown=True,
                               description="those are 0.5,0.5,0.18 (F512TR) center of mass? Position of collision cube?")
        slip_angle_cutoff = Nfs1Float32(is_unknown=True)
        normal_coefficient_loss = Nfs1Float32(is_unknown=True)
        engine__max_rpm = IntegerField(static_size=4)
        engine__min_rpm = IntegerField(static_size=4)
        engine__torques = ArrayField(child=EngineTorqueRecord(), length=60,
                                     description="LUT (lookup table) of engine torque depending on RPM. <engine__torque_count> "
                                                 "first elements used")
        transmission__upshifts = ArrayField(length=5, child=IntegerField(static_size=4),
                                            description='RPM value, when automatic gear box should upshift. 1 element '
                                                        'per drive gear')
        unknowns6 = ArrayField(length=4, child=Nfs1Float16(), is_unknown=True)
        unknowns7 = ArrayField(length=7, child=Nfs1Float32(), is_unknown=True)
        unknowns8 = ArrayField(length=2, child=Nfs1Float16(), is_unknown=True)
        inertia_factor = Nfs1Float32(is_unknown=True)
        body_roll_factor = Nfs1Float32(is_unknown=True)
        body_pitch_factor = Nfs1Float32(is_unknown=True)
        front_friction_factor = Nfs1Float32(is_unknown=True)
        rear_fricton_factor = Nfs1Float32(is_unknown=True)
        body__length = Nfs1Float32(description='Chassis body length in meters')
        body__width = Nfs1Float32(description='Chassis body width in meters')
        steering__max_auto_steer_angle = Nfs1Float32(is_unknown=True)
        steering__auto_steer_mult_shift = IntegerField(static_size=4, is_unknown=True)
        steering__auto_steer_div_shift = IntegerField(static_size=4, is_unknown=True)
        steering__steering_model = IntegerField(static_size=4, is_unknown=True)
        steering__auto_steer_velocities = ArrayField(length=4, child=IntegerField(static_size=4), is_unknown=True)
        steering__auto_steer_velocity_ramp = Nfs1Float32(is_unknown=True)
        steering__auto_steer_velocity_attenuation = Nfs1Float32(is_unknown=True)
        steering__auto_steer_ramp_mult_shift = IntegerField(static_size=4, is_unknown=True)
        steering__auto_steer_ramp_div_shift = IntegerField(static_size=4, is_unknown=True)
        lateral_accel_cutoff = Nfs1Float32(is_unknown=True)
        unknowns9 = ArrayField(length=13, child=Nfs1Float32(), is_unknown=True)
        engine_shifting__shift_timer = IntegerField(static_size=4, is_unknown=True,
                                                    description='Unknown exactly, but it seems to be ticks '
                                                                'taken to shift. Tick is probably 100ms')
        engine_shifting__rpm_decel = IntegerField(static_size=4, is_unknown=True)
        engine_shifting__rpm_accel = IntegerField(static_size=4, is_unknown=True)
        engine_shifting__clutch_drop_decel = IntegerField(static_size=4, is_unknown=True)
        engine_shifting__neg_torque = Nfs1Float32(is_unknown=True)
        body__clearance = Nfs1Float32_7()
        body__height = Nfs1Float32()
        center_x = Nfs1Float32(is_unknown=True)
        grip_curve_front = ArrayField(child=IntegerField(static_size=1), length=512, is_unknown=True)
        grip_curve_rear = ArrayField(child=IntegerField(static_size=1), length=512, is_unknown=True)
        hash = IntegerField(static_size=4, description='Check sum of this block contents', is_unknown=True)


class CarSimplifiedPerformanceSpec(CompoundBlock):
    block_description = "This block describes simpler version of car physics. It is not clear how and when is is used"

    class Fields(CompoundBlock.Fields):
        unknowns0 = ArrayField(length=3, child=Nfs1Float32(), is_unknown=True,
                               description='Unknown. Some values for playable cars, always zeros for non-playable')
        moment_of_inertia = Nfs1Float32(description='Not clear how to interpret')
        unknowns1 = ArrayField(length=3, child=Nfs1Float32(), is_unknown=True)
        power_curve = ArrayField(length=100, child=Nfs1Float32(), description='Not clear how to interpret')
        top_speeds = ArrayField(length=6, child=Nfs1Float32(), description='Maximum car speed (m/s) per gear')
        max_rpm = Nfs1Float32(description='Max engine RPM')
        gear_count = IntegerField(static_size=4, description='Gears amount')
