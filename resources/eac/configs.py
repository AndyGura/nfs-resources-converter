from math import floor, ceil

from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import IntegerBlock, Utf8Block, EnumByteBlock, AtomicDataBlock
from library.read_blocks.compound import CompoundBlock
from library.read_data import ReadData
from resources.eac.fields.numbers import RationalNumber


class TnfsRecordTime(IntegerBlock):
    def __init__(self, **kwargs):
        super().__init__(static_size=4, is_signed=False, **kwargs)
        self.block_description = ('TNFS time field (in physics ticks?). 4-bytes unsigned integer, little-endian, '
                                  'equals to amount of seconds * 60')

    def from_raw_value(self, raw: bytes, state: dict):
        value = super().from_raw_value(raw, state)
        return value / 60

    def to_raw_value(self, data: ReadData) -> bytes:
        return super().to_raw_value(self.wrap_result(int(self.unwrap_result(data) * 60)))


class TnfsTopSpeed(RationalNumber):
    def __init__(self, **kwargs):
        super().__init__(static_size=3, is_signed=False, byte_order="little", fraction_bits=8, **kwargs)
        self.block_description = ('TNFS top speed record. Appears to be 24-bit real number (sign unknown because big '
                                  'values show up as N/A in the game), little-endian, where last 8 bits is a fractional '
                                  'part. For determining speed, ONLY INTEGER PART of this number should be multiplied by '
                                  '2,240000000001 and rounded up, e.g. 0xFF will be equal to 572mph. Note: probably '
                                  'game multiplies number by 2,24 with some fast algorithm so it rounds up even integer '
                                  'result, because 0xFA (*2,24 == 560.0) shows up in game as 561mph')

    def from_raw_value(self, raw: bytes, state: dict):
        value = super().from_raw_value(raw, state)
        int_part = floor(value)
        frac_part = value - int_part
        int_part = ceil(int_part * 2.240000000001)
        return int_part + frac_part

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        int_part = floor(value)
        frac_part = value - int_part
        int_part = floor(int_part / 2.24)
        return super().to_raw_value(self.wrap_result(int_part + frac_part))


class BestRaceRecord(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        name = Utf8Block(length=11, description='Racer name')
        unk0 = AtomicDataBlock(static_size=4)
        car_id = EnumByteBlock(enum_names=[(0, 'RX-7'),
                                           (1, 'NSX'),
                                           (2, 'SUPRA'),
                                           (3, '911'),
                                           (4, 'CORVETTE'),
                                           (5, 'VIPER'),
                                           (6, '512TR'),
                                           (7, 'DIABLO'),
                                           (8, 'WAR_SLEW?'),
                                           (9, 'WAR_WATCH?'),
                                           (10, 'WAR_TOURNY?'),
                                           (11, 'WAR?'),
                                           ],
                               description='A car identifier. Last 4 options are unclear, names came from decompiled NFS.EXE')
        unk1 = AtomicDataBlock(static_size=11)
        time = TnfsRecordTime(description='Total track time')
        unk2 = AtomicDataBlock(static_size=1)
        top_speed = TnfsTopSpeed(description='Top speed')
        game_mode = EnumByteBlock(enum_names=[(0, 'time_trial'),
                                              (1, 'head_to_head'),
                                              (2, 'full_grid_race'),
                                              ],
                                  description='Game mode. In the game shown as "t.t.", "h.h." or empty string')
        unk3 = AtomicDataBlock(static_size=3, required_value=b'\x00\x00\x00')

        unknown_fields = ['unk0', 'unk1', 'unk2', 'unk3']


class TrackStats(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        best_lap_1 = BestRaceRecord(description='Best single lap time (closed track). Best time of first segment for '
                                                'open track')
        best_lap_2 = BestRaceRecord(description='Best time of second segment (open track). Zeros for closed track')
        best_lap_3 = BestRaceRecord(description='Best time of third segment (open track). Zeros for closed track')
        top_speed_1 = BestRaceRecord(description='Top speed on first segment (open track). Zeros for closed track')
        top_speed_2 = BestRaceRecord(description='Top speed on second segment (open track). Zeros for closed track')
        top_speed_3 = BestRaceRecord(description='Top speed on third segment (open track). Zeros for closed track')
        best_race_time_table_1 = ArrayBlock(length=10, child=BestRaceRecord(),
                                            description='Best 10 runs of the whole race with minimum amount of laps: '
                                                        'for open track total time of all 3 segments, for closed track '
                                                        'time of minimum selection of laps (2 or 4 depending on track)')
        best_race_time_table_2 = ArrayBlock(length=10, child=BestRaceRecord(),
                                            description='Best 10 runs of the whole race with middle amount of laps (6 '
                                                        'or 8 depending on track). Zeros for open track')
        best_race_time_table_3 = ArrayBlock(length=10, child=BestRaceRecord(),
                                            description='Best 10 runs of the whole race with maximum amount of laps (12 '
                                                        'or 16 depending on track). Zeros for open track')
        top_race_speed = BestRaceRecord(description='Top speed on the whole race. Why it is not equal to max stat '
                                                    'between top_speed_1, top_speed_2 and top_speed_3 for open track?')
        unk = AtomicDataBlock(static_size=1224)

        unknown_fields = ['unk']


class TnfsConfigDat(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        player_name = Utf8Block(length=42,
                                description="Player name, leading with zeros. Though game allows to set name with as "
                                            "many as 8 characters, the game seems to work fine with name up to 42 "
                                            "symbols, though some part of name will be cut off in the UI")
        unk0 = AtomicDataBlock(static_size=139)
        city_stats = TrackStats()
        coastal_stats = TrackStats()
        alpine_stats = TrackStats()
        rusty_springs_stats = TrackStats()
        autumn_valley_stats = TrackStats()
        burnt_sienna_stats = TrackStats()
        vertigo_ridge_stats = TrackStats()
        transtropolis_stats = TrackStats()
        lost_vegas_stats = TrackStats()
        unk1 = BestRaceRecord()
        unk2 = AtomicDataBlock(static_size=177)
        unlocks_level = EnumByteBlock(enum_names=[(0, 'none'),
                                                  (1, 'warrior_vegas_mirror'),
                                                  (2, 'warrior_vegas_mirror_rally'),
                                                  ],
                                      description='Level of unlocked features: warrior car, lost vegas track, mirror track mode, rally track mode')
        unk3 = AtomicDataBlock(static_size=1)
        unknown_fields = ['unk0', 'unk1', 'unk2', 'unk3']
