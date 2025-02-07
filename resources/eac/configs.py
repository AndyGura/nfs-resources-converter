from io import BufferedReader, BytesIO
from math import floor, ceil
from typing import Dict

from library.context import WriteContext, ReadContext
from library.read_blocks import DeclarativeCompoundBlock, UTF8Block, BytesBlock, ArrayBlock, DataBlock, EnumByteBlock
from resources.eac.fields.numbers import RationalNumber, Nfs1TimeField


class TnfsTopSpeed(RationalNumber):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'TNFS top speed record. Appears to be 24-bit real number (sign unknown because '
                                     'big values show up as N/A in the game), little-endian, where last 8 bits is a '
                                     'fractional part. For determining speed, ONLY INTEGER PART of this number should '
                                     'be multiplied by 2,240000000001 and rounded up, e.g. 0xFF will be equal to '
                                     '572mph. Note: probably game multiplies number by 2,24 with some fast algorithm '
                                     'so it rounds up even integer result, because 0xFA (*2,24 == 560.0) shows up in '
                                     'game as 561mph'}

    def __init__(self, **kwargs):
        super().__init__(length=3, is_signed=False, byte_order="little", fraction_bits=8, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        value = super().read(buffer, ctx, name, read_bytes_amount)
        int_part = floor(value)
        frac_part = value - int_part
        int_part = ceil(int_part * 2.240000000001)
        return int_part + frac_part

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        int_part = floor(data)
        frac_part = data - int_part
        int_part = floor(int_part / 2.24)
        return super().write(int_part + frac_part, ctx, name)


class BestRaceRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=11),
                {'description': 'Racer name'})
        unk0 = (BytesBlock(length=4),
                {'is_unknown': True})
        car_id = (EnumByteBlock(enum_names=[(0, 'RX-7'),
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
                                            ]),
                  {'description': 'A car identifier. Last 4 options are unclear, names came from decompiled NFS.EXE'})
        unk1 = (BytesBlock(length=11),
                {'is_unknown': True})
        time = Nfs1TimeField(length=4), {'description': 'Total track time in seconds'}
        unk2 = (BytesBlock(length=1),
                {'is_unknown': True})
        top_speed = TnfsTopSpeed(), {'description': 'Top speed'}
        game_mode = (EnumByteBlock(enum_names=[(0, 'time_trial'),
                                               (1, 'head_to_head'),
                                               (2, 'full_grid_race'),
                                               ]),
                     {'description': 'Game mode. In the game shown as "t.t.", "h.h." or empty string'})
        unk3 = (BytesBlock(length=3, required_value=b'\x00\x00\x00'),
                {'is_unknown': True})


class TrackStats(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        best_lap_1 = (BestRaceRecord(),
                      {'description': 'Best single lap time (closed track). Best time of first segment for open track'})
        best_lap_2 = (BestRaceRecord(),
                      {'description': 'Best time of second segment (open track). Zeros for closed track'})
        best_lap_3 = (BestRaceRecord(),
                      {'description': 'Best time of third segment (open track). Zeros for closed track'})
        top_speed_1 = (BestRaceRecord(),
                       {'description': 'Top speed on first segment (open track). Zeros for closed track'})
        top_speed_2 = (BestRaceRecord(),
                       {'description': 'Top speed on second segment (open track). Zeros for closed track'})
        top_speed_3 = (BestRaceRecord(),
                       {'description': 'Top speed on third segment (open track). Zeros for closed track'})
        best_race_time_table_1 = (ArrayBlock(length=10, child=BestRaceRecord()),
                                  {'description': 'Best 10 runs of the whole race with minimum amount of laps: '
                                                  'for open track total time of all 3 segments, for closed track '
                                                  'time of minimum selection of laps (2 or 4 depending on track)'})
        best_race_time_table_2 = (ArrayBlock(length=10, child=BestRaceRecord()),
                                  {'description': 'Best 10 runs of the whole race with middle amount of laps (6 '
                                                  'or 8 depending on track). Zeros for open track'})
        best_race_time_table_3 = (ArrayBlock(length=10, child=BestRaceRecord()),
                                  {'description': 'Best 10 runs of the whole race with maximum amount of laps (12 or 16'
                                                  ' depending on track). Zeros for open track'})
        top_race_speed = (BestRaceRecord(),
                          {'description': 'Top speed on the whole race. Why it is not equal to max stat between '
                                          'top_speed_1, top_speed_2 and top_speed_3 for open track?'})
        unk = (BytesBlock(length=1224),
               {'is_unknown': True})


class TnfsConfigDat(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        player_name = (UTF8Block(length=42),
                       {'description': "Player name, leading with zeros. Though game allows to set name with as "
                                       "many as 8 characters, the game seems to work fine with name up to 42 "
                                       "symbols, though some part of name will be cut off in the UI"})
        unk0 = (BytesBlock(length=139),
                {'is_unknown': True})
        city_stats = TrackStats()
        coastal_stats = TrackStats()
        alpine_stats = TrackStats()
        rusty_springs_stats = TrackStats()
        autumn_valley_stats = TrackStats()
        burnt_sienna_stats = TrackStats()
        vertigo_ridge_stats = TrackStats()
        transtropolis_stats = TrackStats()
        lost_vegas_stats = TrackStats()
        unk1 = (BestRaceRecord(),
                {'is_unknown': True})
        unk2 = (BytesBlock(length=177),
                {'is_unknown': True})
        unlocks_level = (EnumByteBlock(enum_names=[(0, 'none'),
                                                   (1, 'warrior_vegas_mirror'),
                                                   (2, 'warrior_vegas_mirror_rally'),
                                                   ]),
                         {'description': 'Level of unlocked features: warrior car, lost vegas track, mirror track mode,'
                                         ' rally track mode'})
        unk3 = (BytesBlock(length=1),
                {'is_unknown': True})
