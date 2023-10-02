from math import floor, ceil

from library.read_blocks.array import ArrayBlock, ByteArray
from library.read_blocks.atomic import IntegerBlock, Utf8Block, EnumByteBlock, BytesField
from library.read_blocks.compound import CompoundBlock
from library.read_data import ReadData
from resources.eac.fields.numbers import RationalNumber


class TnfsRecordTime(IntegerBlock):
    def __init__(self, **kwargs):
        super().__init__(static_size=2, is_signed=False, **kwargs)
        self.block_description = 'TNFS time field (in physics ticks?). 2-bytes unsigned integer, equals to amount of seconds * 60'

    def from_raw_value(self, raw: bytes, state: dict):
        value = super().from_raw_value(raw, state)
        return value / 60

    def to_raw_value(self, data: ReadData) -> bytes:
        return super().to_raw_value(int(self.unwrap_result(data) * 60))


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
        return super().to_raw_value(int_part + frac_part)


class BestRaceRecord(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        name = Utf8Block(length=11, description='Racer name')
        unk0 = BytesField(static_size=4)
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
        unk1 = BytesField(static_size=11)
        time = TnfsRecordTime(description='Total track time')
        unk2 = BytesField(static_size=3)
        top_speed = TnfsTopSpeed(description='Top speed')
        tt_hh = EnumByteBlock(enum_names=[(0, 'T.T.'),
                                          (1, 'H.H.'),
                                          (2, 'None'),
                                          ], description='Unclear parameter. Shows up in the game')
        unk3 = BytesField(static_size=3)

        unknown_fields = ['unk0', 'unk1', 'unk2', 'unk3']


class TrackStats(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        some_records = ArrayBlock(length=6, child=BestRaceRecord(),
                                  description='Unknown records. For closed track only first record defined, next 5 are '
                                              'filled with zeros')
        best_times = ArrayBlock(length=30, child=BestRaceRecord(),
                                description='Best 10 runs of track per lap amount. For open track only 10 records '
                                            'defined, next 20 are filled with zeros')
        top_speed_stat = BestRaceRecord()
        unk = BytesField(static_size=1224)

        unknown_fields = ['unk0']


class TnfsConfigDat(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        unk0 = BytesField(static_size=181)
        city_stats = TrackStats()
        coastal_stats = TrackStats()
        alpine_stats = TrackStats()
        rusty_springs_stats = TrackStats()
        autumn_valley_stats = TrackStats()
        burnt_sienna_stats = TrackStats()
        vertigo_ridge_stats = TrackStats()
        transtropolis_stats = TrackStats()
        lost_vegas_stats = TrackStats()
        some_record = BestRaceRecord()
        unk1 = ByteArray(length_strategy="read_available")

        unknown_fields = ['unk0', 'unk1']
