import json
from io import BufferedReader, SEEK_CUR

from buffer_utils import read_utf_bytes, read_int, read_nfs1_float32, read_byte
from parsers.resources.base import BaseResource
from parsers.resources.collections import ArchiveResource


class BinaryResource(BaseResource):

    def __init__(self, id=None, length=None, save_binary_file=True):
        super().__init__()
        self.id = id
        self.length = length
        self.save_binary_file = save_binary_file

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        if self.length is not None:
            length = min(length, self.length)
        self.bytes = buffer.read(length)
        return length

    def save_converted(self, path: str):
        if self.save_binary_file:
            if self.id:
                path = f'{path}__{hex(self.id)}'
            with open(f'{path}.bin', 'w+b') as file:
                file.write(self.bytes)


class JsonOutputResource:
    dictionary = dict()

    def save_converted(self, path: str):
        with open(f'{path}.json', 'w') as file:
            file.write(json.dumps(self.dictionary))


class TextResource(BaseResource):

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.text = read_utf_bytes(buffer, length)
        return length

    def save_converted(self, path: str):
        with open(f'{path}.txt', 'w') as file:
            file.write(self.text)


class DashDeclarationResource(JsonOutputResource, TextResource):
    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.dictionary = {}
        length_read = super().read(buffer, length, path)
        values = self.text.split('\n')
        current_key = None
        current_key_ended = True
        for value in values:
            if value.startswith('#'):
                if not current_key_ended:
                    raise Exception(f'Unexpected new key {value}. Last key not finished')
                current_key = value[1:]
                current_key_ended = False
                continue
            if value == '':
                if not self.dictionary.get(current_key):
                    self.dictionary[current_key] = []
                current_key_ended = True
                continue
            if not current_key:
                raise Exception(f'Cannot parse value {value}. Unknown key')
            if self.dictionary.get(current_key) is not None:
                if current_key_ended:
                    self.dictionary[current_key].append([value])
                    current_key_ended = False
                else:
                    self.dictionary[current_key][-1].append(value)
            else:
                value = value.split(' ')
                value = value[0] if len(value) == 1 else value
                self.dictionary[current_key] = value if not current_key_ended else [value]
        return length_read


# https://gist.github.com/Five-Damned-Dollarz/99e955994ebbcf970532406a197b580e
class CarPBSFile(JsonOutputResource, BaseResource):

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.dictionary = {
            'engine': {},
            'transmission': {},
        }
        # those value meaning is theoretical. For all cars those values are the ame and equal to mass / 2
        mass_front_axle = read_nfs1_float32(buffer)
        mass_rear_axle = read_nfs1_float32(buffer)
        self.dictionary['mass'] = read_nfs1_float32(buffer)
        unk = [read_nfs1_float32(buffer) for _ in range(4)]
        brake_bias = read_nfs1_float32(buffer) # how much car rotates when brake? In this case should be used for chassis setup
        unk = read_nfs1_float32(buffer)
        center_of_gravity = read_nfs1_float32(buffer) # probably the height of mass center in meters
        max_brake_decel = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        drag = read_nfs1_float32(buffer)
        top_speed = read_nfs1_float32(buffer)
        efficiency = read_nfs1_float32(buffer)
        wheel_base = read_nfs1_float32(buffer)
        burnout_div = read_nfs1_float32(buffer)  # reduce lateral accel during burnout
        wheel_track = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        mps_to_rpm_factor = read_nfs1_float32(buffer)  # speed(m/s) = RPM / (mpsToRpmFactor * gearRatio)
        self.dictionary['mpsToRpmFactor'] = mps_to_rpm_factor
        gear_count = read_int(buffer)
        final_drive_ratio = read_nfs1_float32(buffer)
        self.dictionary['transmission']['finalDriveRatio'] = final_drive_ratio
        roll_radius = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        gear_ratios = [read_nfs1_float32(buffer) for _ in range(8)][:gear_count]
        self.dictionary['transmission']['reverseGearRatio'] = gear_ratios[0]
        self.dictionary['transmission']['gearRatios'] = gear_ratios[2:]
        torque_count = read_int(buffer)
        front_roll_stiffness = read_nfs1_float32(buffer)
        rear_roll_stiffness = read_nfs1_float32(buffer)
        roll_axis_height = read_nfs1_float32(buffer)
        # those 3 are 0.5, 0.5, 0.18 (F512TR) center of mass? position of collision cube?
        unk = [read_nfs1_float32(buffer) for _ in range(3)]
        slip_angle_cutoff = read_nfs1_float32(buffer)
        normal_coefficient_loss = read_nfs1_float32(buffer)
        self.dictionary['engine']['maxRpm'] = read_int(buffer)
        self.dictionary['engine']['minRpm'] = read_int(buffer)
        self.dictionary['engine']['torques'] = [{'rpm': read_int(buffer), 'torque': read_int(buffer)} for _ in range(torque_count)]
        buffer.seek(8 * (60 - torque_count), SEEK_CUR)
        self.dictionary['transmission']['upShifts'] = [read_int(buffer) for _ in range(5)]
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        unk = read_nfs1_float32(buffer)
        inertia_factor = read_nfs1_float32(buffer) # always 0.5
        body_roll_factor = read_nfs1_float32(buffer)  # g-force to body roll
        body_pitch_factor = read_nfs1_float32(buffer)  # g-force to body pitch
        front_friction_factor = read_nfs1_float32(buffer)
        rear_fricton_factor = read_nfs1_float32(buffer)
        body_length = read_nfs1_float32(buffer)
        body_width = read_nfs1_float32(buffer)
        # steering
        steering__max_auto_steer_angle = read_nfs1_float32(buffer)
        steering__auto_steer_mult_shift = read_int(buffer)
        steering__auto_steer_div_shift = read_int(buffer)
        steering__steering_model = read_int(buffer)
        steering__auto_steer_velocities = [read_int(buffer) for _ in range(4)]
        steering__auto_steer_velocity_ramp = read_nfs1_float32(buffer)
        steering__auto_steer_velocity_attenuation = read_nfs1_float32(buffer)
        steering__auto_steer_ramp_mult_shift = read_int(buffer)
        steering__auto_steer_ramp_div_shift = read_int(buffer)

        lateral_accel_cutoff = read_nfs1_float32(buffer)
        unk = [read_nfs1_float32(buffer) for _ in range(13)]

        # engine shifting
        engine_shifting__shift_timer = read_int(buffer)  # ticks taken to shift. Tick is probably 100ms
        engine_shifting__rpm_decel = read_int(buffer)
        engine_shifting__rpm_accel = read_int(buffer)
        engine_shifting__clutch_drop_decel = read_int(buffer)
        engine_shifting__neg_torque = read_nfs1_float32(buffer)

        ride_height = read_nfs1_float32(buffer)
        center_y = read_int(buffer)
        center_y = read_int(buffer)
        grip_curve_front = [read_byte(buffer) for _ in range(512)]
        grip_curve_rear = [read_byte(buffer) for _ in range(512)]
        assert (length - buffer.tell() == 4), Exception('Unexpected PBS file length')
        return length


class CarPDNFile(JsonOutputResource, BaseResource):
    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.dictionary = {}
        # values for playable cars, zeros for non-playable
        unk1 = [read_nfs1_float32(buffer) for _ in range(3)]
        moment_of_inertia = read_nfs1_float32(buffer)
        unk2 = [read_nfs1_float32(buffer) for _ in range(3)]
        power_curve = [read_nfs1_float32(buffer) for _ in range(100)]
        top_speeds = [read_nfs1_float32(buffer) for _ in range(6)]
        max_rpm = read_nfs1_float32(buffer)
        gear_count = read_int(buffer)

        return length


class Nfs1MapInfo(DashDeclarationResource):
    @property
    def ring_height(self) -> int:
        return int(self.dictionary.get('ring height'))

    @property
    def ring_y(self) -> int:
        return int(self.dictionary.get('ring y offset (bigger places horizon further down)'))


def nfs1_panorama_to_spherical(archive: ArchiveResource, file_name: str, out_file_name: str):
    from PIL import Image, ImageOps
    from numpy import average
    source = Image.open(file_name)

    out_half_width = 1024
    out_half_height = int(out_half_width / 2)

    map_id = archive.name[:3]
    scale_x = out_half_width / source.size[0]
    mirror_x = map_id in ['TR3', 'TR7']
    # It is a mystery how NFS decides how to position horizon. I tried everything in {map_id}INFO files,
    # but no stable correlations detected. NFS horizon is not a sphere, it is a separate 2D layer under 3D stage,
    # so output sky texture is approximate for FOV == 65
    scale_y = 2.12
    pos_y = 0
    if map_id in ['TR3', 'TR4']:
        scale_y = 1
    elif map_id == 'TR1':
        scale_y = 1.15
    elif map_id == 'TR2':
        scale_y = 0.86
    elif map_id == 'TR6':
        scale_y = 2.2
    if map_id == 'AL1':
        pos_y = 351
    elif map_id == 'AL2':
        pos_y = 336
    elif map_id == 'AL3':
        pos_y = 365
    elif map_id == 'CL1':
        pos_y = 375
    elif map_id == 'CL2':
        pos_y = 349
    elif map_id == 'CL3':
        pos_y = 374
    elif map_id == 'CY1':
        pos_y = 328
    elif map_id == 'CY2':
        pos_y = 294
    elif map_id == 'CY3':
        pos_y = 343
    elif map_id == 'TR1':
        pos_y = 324
    elif map_id == 'TR2':
        pos_y = 308
    elif map_id == 'TR3':
        pos_y = 367
    elif map_id == 'TR6':
        pos_y = 369
    elif map_id == 'TR7':
        pos_y = 342
    elif map_id == 'TR4':
        pos_y = 300

    scale_y = scale_y * out_half_width / 1024
    pos_y = int(pos_y * out_half_width / 1024)

    source_scaled = source.resize((int(source.size[0] * scale_x), int(source.size[1] * scale_y)), Image.ANTIALIAS)

    # INFO files have some values for top and bottom color, but I don't understand what exactly colors do they mean
    top_line_color = tuple([int(x)
                            for x in average(average(source.crop((0, 0, source.size[0], 1)), axis=0), axis=0)])
    bottom_line_color = tuple([int(x)
                               for x in average(average(source.crop((0,
                                                                     source.size[1] - 1,
                                                                     source.size[0],
                                                                     source.size[1])), axis=0), axis=0)])

    spherical = Image.new(source_scaled.mode, (out_half_width * 2, out_half_height * 2), 0xff000000)
    spherical.paste(top_line_color, [0, 0,
                                     spherical.size[0], int(pos_y + source_scaled.size[1] / 2)])
    spherical.paste(bottom_line_color, [0, int(pos_y + source_scaled.size[1] / 2),
                                        spherical.size[0], spherical.size[1]])
    spherical.paste(source_scaled, (out_half_width, pos_y))
    if mirror_x:
        source_scaled = ImageOps.mirror(source_scaled)
    spherical.paste(source_scaled, (out_half_width - source_scaled.size[0], pos_y))

    spherical.save(out_file_name)
