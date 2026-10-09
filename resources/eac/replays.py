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
# demo): the race setup, the highlights, the recording buffer, the replay state and the stats of 9 cars.
# Sizes are fixed, the file is always 100374 bytes.
#
# The game runs at 60 ticks per second. Positions and speeds are 16.16 fixed point numbers, angles are 24-bit
# numbers (0x1000000 is a full turn).
#
# DOS versions have the same blocks with different sizes (e.g. 150000 bytes recording buffer, 30 keyframes), this
# format is the SE one.

REPLAY_KEYFRAMES = 16
REPLAY_CONTROL_SAMPLES = 7200
REPLAY_PLAYERS = 2
REPLAY_OTHER_CARS = 8


def _fixed(**kwargs):
    return FixedPointBlock(length=4, fraction_bits=16, is_signed=True, **kwargs)


def _int(**kwargs):
    return IntegerBlock(length=4, is_signed=True, **kwargs)


def _uint(length, **kwargs):
    return IntegerBlock(length=length, is_signed=False, **kwargs)


class TnfsReplayPlayer(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Settings of one player, 0x4b bytes. The structure starts at the name, so the last '
            'field of the previous player is directly in front of it',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=8), {'description': 'Player name'})
        unk0 = (BytesBlock(length=1), {'is_unknown': True})
        car_id = (_int(), {'description': 'Index of the car in the car list of the game'})
        transmission = (
            _int(),
            {
                'description': 'Boolean. Used as the "automatic gear" flag of the car, and selects the variant of '
                'the car physics'
            },
        )
        option_a = (
            _int(),
            {'description': 'Boolean, traction control option. Applied only if the car PBS `has_tcs` (0x338) is set'},
        )
        option_b = (
            _int(),
            {'description': 'Boolean, ABS option. Applied only if the car PBS `has_abs` (0x334) is set'},
        )
        unk1 = (_int(), {'is_unknown': True})
        sound_value_0 = (
            _int(),
            {'description': 'Taken from the sound configuration when the replay is saved, 0 without a sound card'},
        )
        sound_value_1 = (
            _int(),
            {'description': 'Taken from the sound configuration when the replay is saved, 0 without a sound card'},
        )
        unk2 = (_int(), {'is_unknown': True})
        sound_value_2 = (
            _int(),
            {'description': 'Taken from the sound configuration when the replay is saved, 0 without a sound card'},
        )
        unk3 = (BytesBlock(length=0x4B - 9 - 4 * 9), {'is_unknown': True})


class TnfsReplaySetup(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Settings of the race the replay was recorded in, 0x348 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (BytesBlock(length=2), {'is_unknown': True})
        track_index = (
            _int(),
            {
                'description': 'Selected track in the track group. With `track_group` is used as an index of '
                "the game's track tables (`track_group * 0xa6b + track_index * 0x27`)"
            },
        )
        track_group = (_int(), {'description': 'Selected track group, see `track_index`'})
        track_name = (
            UTF8Block(length=10),
            {'description': 'Track file name without extension, e.g. `cl2` for CL2.TRI'},
        )
        game_mode = (
            _int(),
            {
                'description': 'Same as the game mode of the best race records: 0 time trial, 1 head to head, '
                '2 full grid race. 3 also starts a race of 8 cars'
            },
        )
        is_multiplayer = (_int(), {'description': 'Boolean. 1 for the multiplayer game'})
        race_flags = (_int(), {'description': 'Bit flags of the race. The game checks bits 2, 3 and 5'})
        unk1 = (_int(), {'is_unknown': True})
        unk2 = (_int(), {'is_unknown': True})
        extra_cars_a = (
            _int(),
            {
                'description': 'Amount of the cars in addition to the racers. Set to 1 in the single player game when '
                'the game mode is head to head, race flag 4 is not set and `track_group` is less than 3, 0 otherwise'
            },
        )
        unk3 = (_int(), {'is_unknown': True})
        extra_cars_b = (
            _int(),
            {
                'description': 'Amount of the cars in addition to the racers. Set to 6 under the same conditions as '
                '`extra_cars_a`, 0 otherwise'
            },
        )
        unk4 = (_int(), {'is_unknown': True})
        random_seed = (
            _int(),
            {
                'description': 'Seed of the random generator of the race. Is a unix time in seconds of the moment '
                'the race started'
            },
        )
        unk5 = (BytesBlock(length=2), {'is_unknown': True})
        players = (
            ArrayBlock(child=TnfsReplayPlayer(), length=REPLAY_PLAYERS),
            {'description': 'Settings of the players of this machine (up to 2 in the multiplayer game)'},
        )
        unk6 = (BytesBlock(length=0x310 - 0x3E - 0x4B * REPLAY_PLAYERS), {'is_unknown': True})
        player_id = (
            _int(),
            {'description': 'Index of the player car of this machine (`g_player_id` in the game code)'},
        )
        unk7 = (BytesBlock(length=0x348 - 0x314), {'is_unknown': True})


class TnfsReplayHighlightClip(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Interesting part of the race to be shown on the replay summary',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        start_tick = (_int(), {'description': 'First tick of the clip'})
        end_tick = (_int(), {'description': 'Last tick of the clip'})
        coolness = (_int(), {'description': 'Highlight score of the clip'})


class TnfsReplayHighlights(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Highlights of the race, found by the game during the race, 0x9a4 bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        clips = (
            ArrayBlock(child=TnfsReplayHighlightClip(), length=30),
            {'description': 'Clips, selected at the end of the race from the best seconds. First `clip_count` used'},
        )
        best_seconds = (
            ArrayBlock(child=_int(), length=30),
            {'description': 'Numbers of the best seconds of the race, picked by the highest `seconds` score'},
        )
        clip_count = (_int(), {'description': 'Amount of used `clips`'})
        state = (_int(), {'description': 'Replay playback state. -2 until the replay is started'})
        unk0 = (BytesBlock(length=0x18), {'is_unknown': True})
        seconds = (
            ArrayBlock(child=_uint(4), length=480),
            {
                'description': 'The score of every second of the race. The value is `second_number << 8 | score`, '
                'where score is the highest highlight score of the second (0 if nothing happened), plus 0x80 until '
                'the second is selected to be a clip'
            },
        )
        current_second = (
            _int(),
            {'description': 'Recording tick divided by 60, updated each time a highlight is recorded'},
        )
        unk1 = (BytesBlock(length=0x20), {'is_unknown': True})


class TnfsReplayCarState(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Physics state of a car, copied from the car data structure (0x168 bytes). Field '
            'names are the names of the car data fields in the game code',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (_uint(4), {'is_unknown': True})
        unk1 = (_uint(4), {'is_unknown': True})
        unk2 = (_uint(1), {'is_unknown': True})
        unk3 = (_uint(2), {'is_unknown': True})
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
        collision_data = (BytesBlock(length=0x94), {'description': 'Collision data of the car', 'is_unknown': True})
        car_road_speed = (_int(), {})
        field_158 = (_int(), {'description': 'Random group index'})
        lane_slack = (_int(), {})
        unk4 = (_uint(4), {'is_unknown': True})


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
        unk0 = (_uint(1), {'is_unknown': True})
        time_off_ground = (_int(), {})
        unk1 = (_int(), {'is_unknown': True})
        slope_force_lat = (_int(), {})
        unk2 = (_int(), {'is_unknown': True})
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
        unk0 = (_uint(1), {'is_unknown': True})


class TnfsReplayRecording(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Replay recording buffer (0x15e00 bytes). A replay is played by restoring the '
            'state of the cars from the last keyframe and then simulating the game with the recorded controls',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        controls_low = (
            ArrayBlock(child=BytesBlock(length=REPLAY_CONTROL_SAMPLES), length=REPLAY_PLAYERS),
            {
                'description': 'Low bytes of the control word of every player, one sample per 4 ticks. Bits 0-5 '
                'of the word is the steering (0x20 is the centre), bits 6-11 the throttle/brake axis (0x1e is the '
                'neutral)'
            },
        )
        controls_high = (
            ArrayBlock(child=BytesBlock(length=REPLAY_CONTROL_SAMPLES), length=REPLAY_PLAYERS),
            {
                'description': 'High bytes of the control word of every player, one sample per 4 ticks. Bits 12-15 '
                'of the word are the gear change (bits 12 and 13), bit 14 is a flag, bit 15 is the handbrake. '
                'Neutral word is 0x07a0'
            },
        )
        player_frames = (
            ArrayBlock(child=ArrayBlock(child=TnfsReplayPlayerFrame(), length=REPLAY_KEYFRAMES), length=REPLAY_PLAYERS),
            {'description': 'Keyframes of the player cars, a keyframe every 0x708 ticks (30 seconds)'},
        )
        other_frames = (
            ArrayBlock(
                child=ArrayBlock(child=TnfsReplayOtherFrame(), length=REPLAY_OTHER_CARS), length=REPLAY_KEYFRAMES
            ),
            {'description': 'Keyframes of the other cars, a keyframe every 0x708 ticks (30 seconds)'},
        )


class TnfsReplayStats(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Race stats of one car, 0x1d2 bytes. Times are in ticks (1/60 of second)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        lap_times = (
            ArrayBlock(child=_int(), length=17),
            {'description': 'Race time at the end of each lap (0 until the lap is finished)'},
        )
        unk0 = (BytesBlock(length=0x198 - 0x44), {'is_unknown': True})
        best_accel_time_1 = (_int(), {'description': 'Best acceleration time, 99999 if none'})
        best_accel_time_2 = (_int(), {'description': 'Best acceleration time, 99999 if none'})
        best_brake_time_1 = (_int(), {'description': 'Best braking time, 999 if none'})
        best_brake_time_2 = (_int(), {'description': 'Best braking time, 999 if none'})
        quarter_mile_speed = (_fixed(), {})
        quarter_mile_time = (_int(), {'description': '99999 if none'})
        penalty_count = (_int(), {})
        warning_count = (_int(), {})
        unk1 = (_int(), {'is_unknown': True})
        finish_time = (
            _int(),
            {'description': 'Race time when the car finished the race. 0 if not finished, 999999 if timed out'},
        )
        unk2 = (_int(), {'is_unknown': True})
        top_speed = (_fixed(), {})
        unk3 = (BytesBlock(length=0x1D2 - 0x1C8), {'is_unknown': True})


class TnfsReplay(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Replay of the race, saved in `GAMEDATA\\REPLAY`. Reverse engineered from the '
            "decompiled game code, the cars' states are copied from its physics data structures. The 4 replays "
            'REPLAY, REPLAY1, REPLAY2 and REPLAY3 are the replays of the game that cannot be replaced.',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        setup = (TnfsReplaySetup(), {'description': 'Race settings'})
        highlights = (TnfsReplayHighlights(), {'description': 'Highlights of the race'})
        recording = (TnfsReplayRecording(), {'description': 'Controls and car states'})
        world_state = (
            BytesBlock(length=0xCC8),
            {
                'description': 'State of the race that is not stored in the cars, every 0x708 ticks. Contains '
                'the state of the random generator, the AI tables, the police state, etc.',
                'is_unknown': True,
            },
        )
        stats = (ArrayBlock(child=TnfsReplayStats(), length=9), {'description': 'Stats of the cars'})

    def serializer_class(self):
        from serializers import JsonSerializer

        return JsonSerializer
