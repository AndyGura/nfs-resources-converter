from io import BufferedReader, SEEK_CUR
from typing import List, Dict

from buffer_utils import read_int
from parsers.resources.collections import ArchiveResource
from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.eac.geometries import OripGeometry

class SoundBank(ArchiveResource):

    @property
    def is_car_soundbank(self):
        return len(self.children_descriptors) == 4 and [x['start_offset'] for x in self.children_descriptors] == [552,
                                                                                                                  624,
                                                                                                                  696,
                                                                                                                  768] and (
                       'SW.BNK' in self.name or self.name in ['TRAFFC.BNK', 'TESTBANK.BNK'])

    def get_children_descriptors(self, buffer: BufferedReader, length: int) -> List[Dict]:
        start_offset = buffer.tell()
        children = [{'start_offset': read_int(buffer)} for i in range(0, 128)]
        children = [x for x in children if x['start_offset'] > 0]
        for child in children:
            if child['start_offset'] >= length:
                raise Exception(f'Child cannot start at offset {child["start_offset"]}. Resource length: {length}')
            child['name'] = hex(start_offset + child['start_offset'])
        children = sorted(children, key=lambda x: x['start_offset'])
        for i in range(0, len(children) - 1):
            children[i]['length'] = children[i + 1]['start_offset'] - children[i]['start_offset'] - 40
        children[-1]['length'] = length - children[-1]['start_offset']
        # TODO why + 40? I dont parse block headers...
        for child in children:
            child['start_offset'] += 40
        return children

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        length = super().read(buffer, length, path)
        if self.is_car_soundbank:
            self.resources[0].name = 'engine_on'
            self.resources[1].name = 'engine_off'
            self.resources[2].name = 'honk'
            self.resources[3].name = 'gear'
        return length
