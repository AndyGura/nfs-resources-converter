from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import IntegerBlock, Utf8Block, EnumByteBlock, BytesField
from library.read_blocks.compound import CompoundBlock
from library.read_data import ReadData


class TnfsRecordTime(IntegerBlock):
    def __init__(self, *args, **kwargs):
        super().__init__(static_size=2, is_signed=False, *args, **kwargs)
        self.block_description = 'TNFS time field (in physics ticks?). 2-bytes unsigned integer, equals to amount of seconds * 60'

    def from_raw_value(self, raw: bytes, state: dict):
        value = super().from_raw_value(raw, state)
        return value / 60

    def to_raw_value(self, data: ReadData) -> bytes:
        return super().to_raw_value(int(data * 60))


class TnfsConfigDatRecord(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        name = Utf8Block(length=11, description='Racer name')
        unk0 = BytesField(length=4)
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
        unk1 = BytesField(length=11)
        time = TnfsRecordTime(description='Total track time')
        unk2 = BytesField(length=6)
        tt_hh = EnumByteBlock(enum_names=[(0, 'T.T.'),
                                          (1, 'H.H.'),
                                          (2, 'None'),
                                          ], description='Unclear parameter. Shows up in the game')
        unk3 = BytesField(length=3)

        unknown_fields = ['unk0', 'unk1', 'unk2', 'unk3']


class TnfsConfigDat(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        unk0 = BytesField(length=415)
        city_best_times = ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                     description='Best 10 runs of City track (all segments)')
        unk1 = BytesField(length=2277)
        coast_best_times = ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                      description='Best 10 runs of Coastal track (all segments)')
        unk2 = BytesField(length=2277)
        alpine_best_times = ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                       description='Best 10 runs of Alpine track (all segments)')
        unk3 = BytesField(length=2277)
        rusty_springs_best_times = ArrayBlock(length=3, child=ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                                                         description='Best 10 runs'),
                                              description='Best runs of Rusty Springs track per lap amount (4/8/16)')
        unk4 = BytesField(length=1497)
        autumn_valley_best_times = ArrayBlock(length=3, child=ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                                                         description='Best 10 runs'),
                                              description='Best runs of Autumn Valley track per lap amount (2/6/12)')
        unk5 = BytesField(length=1497)
        burnt_sienna_best_times = ArrayBlock(length=3, child=ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                                                        description='Best 10 runs'),
                                             description='Best runs of Burnt Sienna track per lap amount (2/6/12)')
        unk6 = BytesField(length=1497)
        vertigo_ridge_best_times = ArrayBlock(length=3, child=ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                                                         description='Best 10 runs'),
                                              description='Best runs of Vertigo Ridge track per lap amount (2/6/12)')
        unk7 = BytesField(length=1497)
        transtropolis_best_times = ArrayBlock(length=3, child=ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                                                         description='Best 10 runs'),
                                              description='Best runs of Transtropolis track per lap amount (2/6/12)')
        unk8 = BytesField(length=1497)
        lost_vegas_best_times = ArrayBlock(length=3, child=ArrayBlock(length=10, child=TnfsConfigDatRecord(),
                                                                      description='Best 10 runs'),
                                           description='Best runs of Lost Vegas track per lap amount (4/8/16)')
        unk9 = BytesField(length_strategy="read_available")

        unknown_fields = ['unk0', 'unk1', 'unk2', 'unk3', 'unk4', 'unk5', 'unk6', 'unk7', 'unk8', 'unk9']
