from io import BufferedReader, SEEK_CUR
from typing import List, Dict

from buffer_utils import read_int
from parsers.resources.collections import ArchiveResource
from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.eac.geometries import OripGeometry


class WwwwArchive(ArchiveResource):

    def get_children_descriptors(self, buffer: BufferedReader, length: int) -> List[Dict]:
        buffer.seek(4, SEEK_CUR)
        instance_count = read_int(buffer)
        children = [{'start_offset': read_int(buffer)} for i in range(0, instance_count)]
        children = [x for x in children if x['start_offset'] > 0]
        children = sorted(children, key=lambda x: x['start_offset'])
        for i, child in enumerate(children):
            child['name'] = str(i)
            child['length'] = children[i + 1]['start_offset'] - child['start_offset'] if i < len(
                children) - 1 else length - children[-1]['start_offset']
        return children

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        length = super().read(buffer, length, path)
        # attach shpi to orip
        for index, geometry in enumerate(self.resources):
            if not isinstance(geometry, ReadBlockWrapper) or not issubclass(geometry.block_class, OripGeometry):
                continue
            try:
                next_resource = self.resources[index + 1]
                if isinstance(next_resource, SHPIArchive):
                    geometry.textures_archive = next_resource
                    next_resource.parent = geometry
                    self.resources.remove(next_resource)
            except IndexError:
                pass
        # if car fam file
        if (
                self.name.upper().endswith('.CFM') and
                len(self.resources) == 2 and
                bool(getattr(self.resources[0], 'textures_archive', None)) and
                bool(getattr(self.resources[1], 'textures_archive', None))
        ):
            self.resources[0].name = 'high-poly'
            self.resources[1].name = 'low-poly'
        # if track fam file
        elif (
                self.name.upper().endswith('.FAM') and
                len(self.resources) == 4 and
                isinstance(self.resources[0], WwwwArchive) and
                isinstance(self.resources[1], WwwwArchive) and
                isinstance(self.resources[2], SHPIArchive) and
                isinstance(self.resources[3], WwwwArchive)
        ):
            self.resources[0].name = 'background'
            self.resources[1].name = 'foreground'
            self.resources[2].name = 'skybox'
            self.resources[3].name = 'props'
        return length

    def save_converted(self, path: str):
        super().save_converted(path)
        try:
            if self.resources[2].name == 'skybox':
                from parsers.resources.misc import nfs1_panorama_to_spherical
                nfs1_panorama_to_spherical(archive=self,
                                           file_name=f'{path}/skybox/horz.png',
                                           out_file_name=f'{path}/skybox/spherical.png')
        except Exception as ex:
            pass


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
