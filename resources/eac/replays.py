from typing import Dict

from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    FixedPointBlock,
    ArrayBlock,
    BytesBlock,
    BitFlagsBlock,
    UTF8Block,
)


# TNFS SE replay (`*.RPL`) is a dump of the game's replay buffers, there is no header and no length fields. The game
# writes five consecutive blocks (`FUN_0044d420` in the Win95 SE executable, `tnfs_replay_save_buffer` in the DOS
# demo): the race setup, the highlights, the recording buffer, the world state and the stats of 9 cars.
# Sizes are fixed, the file is always 100374 bytes.
#
# Time: the game counts a 60/s clock (`g_sim_clock`), which advances by 2 per 30 Hz simulation tick; the race timer
# starts at 300 (5 s). Every time value of the replay (named "tick" or "clock" here) is in units of this clock.
# Controls are read and recorded every 4 clock units (every 2nd simulation tick, simulation flags 4, the "control
# step"), keyframes are taken every 0x708 clock units (30 s).
# The recording buffer is circular and keeps 8 minutes: control sample index = (clock % 0x7080) / 4, keyframe slot =
# (clock % 0x7080) / 0x708. It is not cleared between races, so everything past the recorded end (`world_state`
# `end_clock`) is stale data of earlier races.
# Positions and speeds are 16.16 fixed point numbers, angles are 24-bit numbers (0x1000000 is a full turn).
#
# Random generator: `tnfs_random_seed` (SE 0x428fe0) sets the LCG multiplier to the seed (`setup.random_seed`) and
# the modulus to seed * 3, both made odd; only the modulus variable is kept in the keyframes.
# Playback: `tnfs_replay_reinstate` (SE 0x44e354) restores the keyframe before the wanted clock, then simulates the
# race again with the recorded control words. Keyframes don't hold the whole game state, so only a playback from
# the start of the race is exact.
#
# This format is the Win95 SE one. DOS TNFS (163053 bytes) has the same blocks with other sizes:
# - setup 0x185 bytes: car counts at 0x1f..0x2f, seed at 0x37, player records of 0x59 bytes, grid order at 0xed,
#   player id at 0x179;
# - highlights 0xb84 bytes: same layout with `seconds[600]` (10 minutes), the playback state tail at 0xb60;
# - recording buffer 150000 bytes: 9000 control samples per player, player keyframes at 36000 (30 of 0x1a4 bytes
#   per player), other cars' keyframes at 0xef10 (30 of 0xb90 bytes);
# - world state 0x15a4 bytes: same header, 30 + 4 records, saved timers;
# - stats 0x1d0 bytes per car (0x1c8 int unknown, 0x1cc int car model);
# - keyframes every 0x4b0 clock units.
# PSX TNFS takes keyframes every 0x708 clock units and keeps 0x5460 clock units (6 minutes).

REPLAY_KEYFRAMES = 16
REPLAY_WORLD_KEYFRAMES = 20
REPLAY_CONTROL_SAMPLES = 7200
REPLAY_PLAYERS = 2
REPLAY_PLAYER_RECORDS = 8
REPLAY_OTHER_CARS = 8
REPLAY_CARS = 9

_CAR_MODELS = '0 TSupra, 1 LDiabl, 2 P911, 3 CZR1, 4 F512TR, 5 DVIPER, 6 ANSX, 7 MRX7'
_INPUT_DEVICES = '0 keyboard, 1 joystick, 2 mouse, 3 joystick buttons'


def _fixed(**kwargs):
    return FixedPointBlock(length=4, fraction_bits=16, is_signed=True, **kwargs)


def _int(**kwargs):
    return IntegerBlock(length=4, is_signed=True, **kwargs)


def _uint(length, **kwargs):
    return IntegerBlock(length=length, is_signed=False, **kwargs)


def _device_description(kind):
    return (
        f'{kind} input device: {_INPUT_DEVICES}. Copied to the input device globals (SE 0x4fb724 / 0x4fb728 / '
        '0x4fb72c, stride 0xc per player) by `tnfs_game_enter_drive_sim` (SE 0x4275f8) when the replay is played'
    )


class TnfsReplayPlayer(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Settings of one player, 0x4b bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (BytesBlock(length=2), {'is_unknown': True, 'description': '0 in every file'})
        name = (UTF8Block(length=8), {'description': 'Player name, first 8 bytes of the 9-byte name buffer'})
        name_terminator = (
            _uint(1),
            {
                'description': 'Last byte of the 9-byte name buffer, the null terminator of an 8-character name. '
                'Can hold a leftover character after a shorter name'
            },
        )
        car_model = (_int(), {'description': f'Car model: {_CAR_MODELS}'})
        automatic_transmission = (
            _int(),
            {
                'description': 'Boolean, gearbox option. Used as the "automatic gear" flag of the car, and selects the '
                'variant of the car physics'
            },
        )
        traction_control = (
            _int(),
            {'description': 'Boolean, traction control option. Applied only if the car PBS `has_tcs` (0x338) is set'},
        )
        abs = (
            _int(),
            {'description': 'Boolean, ABS option. Applied only if the car PBS `has_abs` (0x334) is set'},
        )
        unk1 = (_int(), {'is_unknown': True, 'description': 'Front-end / sound configuration value'})
        sound_on = (
            _int(),
            {
                'description': 'Sound configuration, non-zero when the sound is on (taken when the replay is '
                'saved, 0 without a sound card)'
            },
        )
        sound_value_1 = (
            _int(),
            {
                'description': 'Front-end / sound configuration value, taken when the replay is saved, 0 without '
                'a sound card'
            },
        )
        unk2 = (_int(), {'is_unknown': True, 'description': 'Front-end / sound configuration value'})
        sound_value_2 = (
            _int(),
            {
                'description': 'Front-end / sound configuration value, taken when the replay is saved, 0 without '
                'a sound card'
            },
        )
        unk3 = (_int(), {'is_unknown': True, 'description': 'Front-end / sound configuration value'})
        steering_device = (_int(), {'description': _device_description('Steering')})
        pedal_device = (_int(), {'description': _device_description('Throttle / brake')})
        shift_device = (_int(), {'description': _device_description('Gear shift')})
        unk4 = (
            _int(),
            {'is_unknown': True, 'description': 'Set to 0 by the game code, the files hold leftover values here'},
        )
        unk5 = (
            _int(),
            {'is_unknown': True, 'description': 'Set to 0 by the game code, the files hold leftover values here'},
        )
        unk6 = (_int(), {'is_unknown': True})


class TnfsReplaySetup(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Settings of the race the replay was recorded in, 0x348 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (BytesBlock(length=2), {'is_unknown': True})
        track_segment = (_int(), {'description': '0-based segment of an open track (`cl2` is segment 1 of CL)'})
        track_id = (
            _int(),
            {'description': 'Track: 0 CY, 1 CL, 2 AL, 3 TR1, 4 TR2, 5 TR6, 6 TR3, 7 TR7, 8 TR4'},
        )
        track_name = (
            UTF8Block(length=10),
            {'description': 'Track file name without extension, e.g. `cl2` for CL2.TRI'},
        )
        race_type = (
            _int(),
            {'description': 'Race type: 0 time trial, 1 head to head, 2 single race, 3 tournament'},
        )
        is_linked_game = (_int(), {'description': 'Boolean. 1 for the linked (multiplayer) game'})
        game_settings = (_int(), {'description': 'Bit flags `g_game_settings`: 4 is No Mercy'})
        racer_count = (_int(), {'description': 'Number of racing cars, players included'})
        player_count = (_int(), {'description': 'Number of players'})
        cop_count = (_int(), {'description': 'Number of police cars'})
        car_count = (_int(), {'description': 'Total number of cars: racers, cops and traffic'})
        traffic_count = (_int(), {'description': 'Number of traffic cars'})
        opponent_difficulty = (
            _int(),
            {'description': 'Opponent difficulty, the front-end option. Index of the table at SE 0x4c5ce0'},
        )
        random_seed = (
            _int(),
            {
                'description': 'Seed of the random generator of the race: unix time in seconds of the moment '
                'the race started (`time()`, SE FUN_00487bbf)'
            },
        )
        players = (
            ArrayBlock(child=TnfsReplayPlayer(), length=REPLAY_PLAYERS),
            {
                'description': 'Settings of the players of this machine (up to 2 in the linked game). Only the first '
                '`player_count` records are set for the race, the other one holds leftovers in the files (car model '
                '8, device values out of range)'
            },
        )
        unk1 = (
            BytesBlock(length=(REPLAY_PLAYER_RECORDS - REPLAY_PLAYERS) * 0x4B),
            {
                'is_unknown': True,
                'description': '0 in every file. Exactly the room of 6 more player records (0x3c + 8 * 0x4b = 0x294)',
            },
        )
        grid_order = (ArrayBlock(child=_int(), length=8), {'description': 'Grid order (race positions)'})
        car_slot_models = (
            ArrayBlock(child=_int(), length=REPLAY_CARS),
            {
                'description': 'Car model per car slot, 99 for none. Player slots hold 99 too, and in the files '
                'the stats `car_model` of a slot is not always the model of this table'
            },
        )
        car_slot_ids = (
            ArrayBlock(child=_int(), length=REPLAY_CARS),
            {
                'description': 'Id per car slot: 200 + car model for the racers (same model as the stats '
                '`car_model`), small numbers for the cop and traffic slots'
            },
        )
        has_cops = (_int(), {'description': 'Boolean, there is a police car in the race'})
        unk2 = (_int(), {'is_unknown': True})
        live_player_glue = (_int(), {'description': 'Live player glue (multiplayer)'})
        lap_count = (_int(), {'description': 'Number of laps'})
        link_latency = (_int(), {'description': 'Latency of the linked game'})
        player_id = (
            _int(),
            {'description': 'Index of the player car of this machine (`g_player_id` in the game code)'},
        )
        unk3 = (_int(), {'is_unknown': True})
        unk4 = (_int(), {'is_unknown': True})
        is_mirrored = (_int(), {'description': 'Boolean, mirror mode'})
        is_rally = (_int(), {'description': 'Boolean, rally mode'})
        track_variants = (
            ArrayBlock(child=_int(), length=9),
            {'description': 'Time of day / variant of every track, indexed by `track_id`'},
        )


class TnfsReplayHighlightClip(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Interesting part of the race to be shown on the replay summary',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        start_tick = (_int(), {'description': 'Clock of the clip start'})
        end_tick = (_int(), {'description': 'Clock of the clip end'})
        coolness = (_int(), {'description': 'Highlight score of the clip'})


class TnfsReplayHighlights(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Highlights of the race, found by the game during the race, 0x9a4 bytes. Highlight '
            'scores: rollover 0x5c, landing after more than 10 ticks airborne 0x54, hard fence hit 0x32, sideways / '
            'spin 0x57, fast skid 0x28, first move 0x78, race order swap 0x50, cop spun out 0x52, car-car hit from '
            'the table at SE 0x4b909c (20 30 32 34 60 70 80 0 37 38 38 39 92 95 98 0; index +1 when the car in slot '
            '2 is involved, +4 when a player is involved, +8 for a crash)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        clips = (
            ArrayBlock(child=TnfsReplayHighlightClip(), length=30),
            {
                'description': 'Clips, selected at the end of the race (SE 0x44d7d8): 30 passes pick the best '
                'marked `seconds`, a clip of second s is (s - 2) * 60 .. (s + 5) * 60 rounded down to 4, '
                'overlapping clips are merged. Without a highlight, one clip of the whole race with coolness 200. '
                'First `clip_count` used'
            },
        )
        best_seconds = (
            ArrayBlock(child=_int(), length=30),
            {'description': 'Numbers of the best seconds of the race, picked by the highest `seconds` score'},
        )
        clip_count = (_int(), {'description': 'Amount of used `clips`'})
        state = (
            _int(),
            {
                'description': 'Current clip index during playback: -2 none, -1 replay without clips, 0 and '
                'more the clip index'
            },
        )
        return_pending = (_int(), {'description': 'Playback state: return pending'})
        saved_camera = (_int(), {'description': 'Playback state: camera saved before the replay'})
        loop_clocks = (
            ArrayBlock(child=_int(), length=4),
            {'description': 'Playback state: loop / return clocks'},
        )
        seconds = (
            ArrayBlock(child=_uint(4), length=480),
            {
                'description': 'The score of every second of the race. The value is `clock / 60 << 8 | score`, '
                'plus 0x80 (a mark) until the second is selected for a clip. Written (SE 0x44d744) when the stored '
                'low byte, mark included, is less than the new score'
            },
        )
        current_second = (
            _int(),
            {'description': 'Recording clock divided by 60, updated each time a highlight is recorded'},
        )
        play_count = (_int(), {'description': 'Playback state: play count'})
        tv_camera = (_int(), {'description': 'Playback state: TV camera'})
        play_to_clock = (_int(), {'description': 'Playback state: clock to play to'})
        seek_target = (_int(), {'description': 'Playback state: seek target clock'})
        camera_restart = (_int(), {'description': 'Playback state: camera restart'})
        is_reinstating = (_int(), {'description': 'Playback state: a keyframe is being reinstated'})
        panel_state = (_int(), {'description': 'Playback state: replay panel state'})
        sound_restart = (_int(), {'description': 'Playback state: sound restart'})


class TnfsReplayCollisionData(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Rigid body of the car for the crash model and the collisions, 0x94 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        matrix = (ArrayBlock(child=_fixed(), length=9), {'description': 'Rotation matrix'})
        position = (ArrayBlock(child=_fixed(), length=3), {'description': 'Position x, y, z'})
        speed = (ArrayBlock(child=_fixed(), length=3), {'description': 'Speed x, y, z'})
        angular_speed = (ArrayBlock(child=_int(), length=3), {'description': 'Angular speed x, y, z'})
        unk0 = (
            ArrayBlock(child=_fixed(), length=3),
            {'is_unknown': True, 'description': '(0, -9.81, 0) in every active car of the files, gravity?'},
        )
        unk1 = (ArrayBlock(child=_fixed(), length=3), {'is_unknown': True})
        mass = (_fixed(), {'description': 'Mass'})
        inertia = (_fixed(), {'description': 'Moment of inertia'})
        linear_acceleration_factor = (_fixed(), {'description': 'Linear acceleration factor'})
        angular_acceleration_factor = (_fixed(), {'description': 'Angular acceleration factor'})
        edge_length = (_fixed(), {'description': 'Edge length'})
        half_size = (ArrayBlock(child=_fixed(), length=3), {'description': 'Half size of the body x, y, z'})
        crash_timer = (_int(), {'description': 'Crash timer'})
        ai_countdown = (_int(), {'description': 'AI countdown'})
        car_type_value = (
            _int(),
            {'description': '0xa0 for traffic and cop cars, about 100 for racers, 0 for players'},
        )
        unk2 = (_int(), {'is_unknown': True})
        traffic_speed_factor = (_fixed(), {'description': 'Speed factor of a traffic car'})


class TnfsReplayCarState(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Physics state of a car, copied from the car data structure (0x168 bytes). Field '
            'names are the names of the car data fields in the game code. Restoring it (SE 0x44dd9c) also zeroes '
            '`slide_front` / `slide_rear` and recomputes `track_slice_lap`; a player restore sets `tire_skid_front` '
            'to 0 and `tire_skid_rear` to 0 or 2',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        control_handler = (_int(), {'description': 'Control handler: 1 player, 2 AI'})
        crash_state = (
            _int(),
            {
                'description': 'Crash state: 1 busted, 2 player driving, 3 AI driving, 4 crash model, 5 wrecked, '
                '6 hidden'
            },
        )
        unk0 = (_uint(1), {'is_unknown': True, 'description': 'Always 0'})
        collision_flags = (_uint(2), {'description': 'Collision flags (car field +0x4e9)'})
        car_index = (_uint(1), {'description': 'Index of the car, 0 is the first player'})
        position = (ArrayBlock(child=_fixed(), length=3), {'description': 'Position x, y, z'})
        angle = (ArrayBlock(child=_int(), length=3), {'description': 'Angle x, y, z (24-bit angles)'})
        steer_angle = (_int(), {})
        target_angle = (_int(), {})
        is_crashed = (_int(), {})
        matrix = (ArrayBlock(child=_fixed(), length=9), {'description': 'Rotation matrix of the car'})
        track_slice = (_int(), {'description': 'Index of the track node'})
        lap_number = (_int(), {})
        speed_x = (_fixed(), {})
        speed_y = (_fixed(), {})
        speed_z = (_fixed(), {})
        speed_local_lat = (_fixed(), {})
        speed_local_vert = (_fixed(), {})
        speed_local_lon = (_fixed(), {})
        speed = (_fixed(), {})
        angular_speed = (_int(), {})
        car_length = (_fixed(), {})
        car_width = (_fixed(), {})
        center_line_distance = (_fixed(), {})
        side_width = (_fixed(), {})
        road_normals = (
            ArrayBlock(child=_fixed(), length=9),
            {'description': 'Road fence normal, road surface normal and road heading, 3 vectors'},
        )
        road_position = (ArrayBlock(child=_fixed(), length=3), {})
        ai_state = (_int(), {'description': 'Bit flags of the AI state of the car'})
        collision_height_offset = (_int(), {})
        collision_data = (TnfsReplayCollisionData(), {'description': 'Rigid body of the car'})
        car_road_speed = (_int(), {})
        field_158 = (_int(), {'description': 'Random group index'})
        lane_slack = (_int(), {})
        is_wrecked = (_int(), {'description': 'Boolean, the car is wrecked'})


class TnfsReplayPlayerFrame(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'State of a car driven by a player, 0x1a4 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        car = (TnfsReplayCarState(), {})
        throttle = (_uint(1), {})
        throttle_previous_pos = (_uint(1), {})
        brake = (_uint(1), {})
        is_shifting_gears = (_uint(1), {'description': 'Game value + 100'})
        rpm_engine = (_uint(2), {})
        rpm_vehicle = (_uint(2), {})
        road_grip_increment = (_int(), {})
        tire_grip_rear = (_int(), {})
        tire_grip_front = (_int(), {})
        speed_drivetrain = (_int(), {})
        tire_grip_loss = (_int(), {})
        gear_auto_selected = (_uint(1), {})
        gear_selected = (_uint(1), {'description': 'Game value + 2'})
        flags = (
            BitFlagsBlock(
                length=1,
                flag_names=[
                    (0, 'wheels_on_ground'),
                    (1, 'is_engine_cutoff'),
                    (2, 'handbrake'),
                    (3, 'is_gear_engaged'),
                    (5, 'tire_skid_rear'),
                ],
            ),
            {},
        )
        unused = (_uint(1), {'description': 'Never written by the game, a leftover byte'})
        time_off_ground = (_int(), {})
        last_shift_button = (_int(), {'description': 'Last gear shift button: 0 none, 1 down, 2 up'})
        slope_force_lat = (_int(), {})
        unk0 = (_int(), {'is_unknown': True, 'description': 'Car data field +0x3dd'})
        slope_force_lon = (_int(), {})
        thrust = (_int(), {})
        surface_type = (_int(), {})


class TnfsReplayOtherFrame(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'State of a car that is not driven by a player (its index is not less than the '
            'number of players), 0x172 bytes. Slots go in the order of the car indexes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        car = (TnfsReplayCarState(), {})
        speed_target = (_int(), {})
        target_center_line = (_int(), {})
        wheels_on_ground = (_uint(1), {})
        unused = (_uint(1), {'description': 'Byte at car data +0x340, not used'})


class TnfsReplayRecording(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Replay recording buffer (0x15e00 bytes), circular. A replay is played by '
            'restoring the state of the cars from a keyframe and then simulating the game with the recorded '
            'controls. Control words are built by SE 0x43915c and decoded by SE 0x438f00 (DOS 0x5e9c9). Bits 0-5: '
            'steering (keyboard: 0 left, 0x20 centre, 0x3c right; joystick: `g_joy_x` + 0x20); bits 6-11: '
            'throttle / brake axis (keyboard: 0x1e released, 5 throttle, 0x3c brake, brake wins when both are '
            'pressed; joystick: `g_joy_y` + 0x1e); bit 12 shift up, bit 13 shift down, bit 14 horn, bit 15 '
            'handbrake. The neutral word 0x7a0 is forced before clock 0x78, a disconnected linked player gets '
            '0xffff87a0',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        controls_low = (
            ArrayBlock(child=BytesBlock(length=REPLAY_CONTROL_SAMPLES), length=REPLAY_PLAYERS),
            {
                'description': 'Low bytes of the control word of every player, one sample per control step (4 clock '
                'units), sample index (clock % 0x7080) / 4'
            },
        )
        controls_high = (
            ArrayBlock(child=BytesBlock(length=REPLAY_CONTROL_SAMPLES), length=REPLAY_PLAYERS),
            {
                'description': 'High bytes of the control word of every player, one sample per control step (4 '
                'clock units), sample index (clock % 0x7080) / 4'
            },
        )
        player_frames = (
            ArrayBlock(child=ArrayBlock(child=TnfsReplayPlayerFrame(), length=REPLAY_KEYFRAMES), length=REPLAY_PLAYERS),
            {
                'description': 'Keyframes of the player cars, a keyframe every 0x708 clock units (30 seconds), slot '
                '(clock % 0x7080) / 0x708'
            },
        )
        other_frames = (
            ArrayBlock(
                child=ArrayBlock(child=TnfsReplayOtherFrame(), length=REPLAY_OTHER_CARS), length=REPLAY_KEYFRAMES
            ),
            {
                'description': 'Keyframes of the other cars, a keyframe every 0x708 clock units (30 seconds), slot '
                '(clock % 0x7080) / 0x708'
            },
        )


class TnfsReplayWorldKeyframe(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Race state that is not stored in the cars, taken with every keyframe, 0xa2 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        handler_order = (ArrayBlock(child=_int(), length=REPLAY_CARS), {'description': 'Car handler order'})
        race_order = (ArrayBlock(child=_int(), length=REPLAY_CARS), {'description': 'Race order of the cars'})
        unused_0 = (_int(), {'description': 'Not used'})
        unused_1 = (_int(), {'description': 'Not used'})
        other_car_count = (_int(), {'description': 'Number of cars other than the player'})
        ai_frame_counter = (_int(), {'description': 'AI frame counter'})
        is_police_chasing = (_int(), {'description': 'Boolean, the police is chasing'})
        random_state_0 = (
            BytesBlock(length=12),
            {'description': '12 bytes of `g_random_struct[0]`, from its offset 2'},
        )
        random_state_1 = (
            BytesBlock(length=12),
            {'description': '12 bytes of `g_random_struct[1]`, from its offset 2'},
        )
        police_chase_time = (_int(), {'description': 'Police chase time'})
        is_siren_on = (_int(), {'description': 'Boolean, siren sound flag'})
        random_lcg_mod = (
            _int(),
            {
                'description': 'Modulus variable of the random generator (seed * 3, made odd, at the race start). '
                'Differs from keyframe to keyframe in the files (odd values below 0x10000)'
            },
        )
        cop_park_position = (_int(), {'description': 'Park position of the cop (track node)'})
        random_direction_counter_0 = (_int(), {'description': 'Random direction counter'})
        random_direction_counter_1 = (_int(), {'description': 'Random direction counter'})
        hidden_traffic_count = (_int(), {'description': 'Number of hidden traffic cars'})
        unused_2 = (_int(), {'description': 'Dead global, not used'})
        unused_3 = (_int(), {'description': 'Not used'})
        unused_4 = (_uint(1), {'description': 'Dead byte, not used'})
        speeding_tickets = (_uint(1), {'description': 'Number of speeding tickets'})
        player_split_checkpoint = (_int(), {'description': 'Split checkpoint index of the player'})
        opponent_split_checkpoint = (_int(), {'description': 'Split checkpoint index of the opponent'})


class TnfsReplayWorldState(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'State of the race that is not stored in the cars, 0xcc8 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (_int(), {'is_unknown': True, 'description': '0 in every file'})
        end_clock = (_int(), {'description': 'Last recorded clock, the end of the recording'})
        unused_0 = (_int(), {'description': 'Not used'})
        unused_1 = (_int(), {'description': 'Not used'})
        keyframe_countdown = (
            _int(),
            {
                'description': 'Control steps until the next keyframe (set to 0x1c2 = 450 in SE, 300 in DOS, at '
                'every keyframe)'
            },
        )
        keyframes = (
            ArrayBlock(child=TnfsReplayWorldKeyframe(), length=REPLAY_WORLD_KEYFRAMES),
            {
                'description': 'One record per keyframe slot ((clock % 0x7080) / 0x708), 16 used, 4 spare. Records '
                'past `end_clock` are stale'
            },
        )
        saved_timers = (ArrayBlock(child=_int(), length=3), {'description': '3 saved timers'})


class TnfsReplayStats(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Race stats of one car, 0x1d2 bytes. Times are in clock units (1/60 of second)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        lap_times = (
            ArrayBlock(child=_int(), length=17),
            {'description': 'Race time at the end of each lap (0 until the lap is finished)'},
        )
        split_times = (
            ArrayBlock(child=_int(), length=85),
            {'description': 'Race time at every split checkpoint, 5 checkpoints per lap / segment'},
        )
        best_accel_time_1 = (_int(), {'description': 'Best acceleration time, 99999 if none'})
        best_accel_time_2 = (_int(), {'description': 'Best acceleration time, 99999 if none'})
        best_brake_time_1 = (_int(), {'description': 'Best braking time, 999 if none'})
        best_brake_time_2 = (_int(), {'description': 'Best braking time, 999 if none'})
        quarter_mile_speed = (_fixed(), {})
        quarter_mile_time = (_int(), {'description': '99999 if none'})
        penalty_count = (_int(), {})
        warning_count = (_int(), {})
        wreck_count = (_int(), {'description': 'Number of crash model resets while racing'})
        finish_time = (
            _int(),
            {
                'description': 'Race time when the car finished the race. 0 if not finished, 999999 if timed out. '
                'Estimated for the cars that did not finish when the race ends (SE 0x45af80)'
            },
        )
        race_distance = (_int(), {'description': 'Race distance: finish node * 0x30 / 10'})
        top_speed = (_fixed(), {})
        tournament_points = (IntegerBlock(length=2, is_signed=True), {'description': 'Tournament points'})
        finishing_position = (_int(), {'description': 'Finishing position'})
        car_model = (_int(), {'description': f'Car model: {_CAR_MODELS}'})


class TnfsReplay(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Replay of the race, saved in `GAMEDATA\\REPLAY`. Reverse engineered from the '
            "decompiled game code, the cars' states are copied from its physics data structures. The 4 replays "
            'REPLAY, REPLAY1, REPLAY2 and REPLAY3 are the replays of the game that cannot be replaced. Time values '
            'are in units of the 60/s game clock, which starts at 300 (5 s) for the race. The recording buffer is '
            'circular (8 minutes) and not cleared between races: data past `world_state.end_clock` is stale',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        setup = (TnfsReplaySetup(), {'description': 'Race settings'})
        highlights = (TnfsReplayHighlights(), {'description': 'Highlights of the race'})
        recording = (TnfsReplayRecording(), {'description': 'Controls and car states'})
        world_state = (
            TnfsReplayWorldState(),
            {'description': 'State of the race that is not stored in the cars, every keyframe'},
        )
        stats = (ArrayBlock(child=TnfsReplayStats(), length=REPLAY_CARS), {'description': 'Stats of the cars'})

    def serializer_class(self):
        from serializers import JsonSerializer

        return JsonSerializer
