import traceback

import serializers
from library.helpers.exceptions import BlockIntegrityException
from library.read_data import ReadData
from library.utils import format_exception
from library.utils.nfs1_panorama_to_spherical import nfs1_panorama_to_spherical
from resources.eac.archives import ShpiBlock, WwwwBlock, SoundBank
from resources.eac.bitmaps import AnyBitmapBlock
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer


class ShpiArchiveSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[ShpiBlock], path: str):
        path += '/'
        super().serialize(data, path)
        items = [(data.children_descriptions[i].name.value, data.children[i]) for i in range(data.children_count.value)]
        skipped_resources = []
        for name, item in [(name, item) for name, item in items]:
            if isinstance(item, Exception):
                skipped_resources.append((name, format_exception(item)))
                continue
            try:
                serializer = serializers.get_serializer(item.block)
                serializer.serialize(item, f'{path}{name}')
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        with open(f'{path}/positions.txt', 'w') as f:
            for name, item in [(name, item) for name, item in items if isinstance(item, ReadData) and isinstance(item.block, AnyBitmapBlock)]:
                f.write(f"{name}: {item.x.value}, {item.y.value}\n")
        if data.id and '.FAM__' in data.id and self.settings.maps__save_spherical_skybox_texture:
            try:
                horz_bitmap = next(x for name, x in items if name == 'horz')
                nfs1_panorama_to_spherical(data.id[data.id.index('.FAM') - 7:data.id.index('.FAM') - 4],
                                           f'{path}horz.png', f'{path}spherical.png')
            except StopIteration:
                pass
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class WwwwArchiveSerializer(BaseFileSerializer):

    def serialize(self, data: WwwwBlock, path: str):
        path += '/'
        super().serialize(data, path)
        if data.id.endswith('.CFM') and data.children_count == 4:
            # car CFM file
            names = ['high-poly', 'high-poly-assets', 'low-poly', 'low-poly-assets']
        elif data.id.endswith('.FAM') and data.children_count == 4:
            # track FAM file
            names = ['background', 'foreground', 'skybox', 'props']
        else:
            names = [str(i) for i in range(data.children_count.value)]
        items = [(names[i], data.children[i]) for i in range(data.children_count.value)]
        skipped_resources = []
        # after orip skip shpi block. It will be exported by orip serializer
        skip_next_shpi = False
        for name, item in [(name, item) for name, item in items]:
            if isinstance(item, Exception):
                skipped_resources.append((name, format_exception(item)))
                continue
            if skip_next_shpi:
                assert isinstance(item.block, ShpiBlock), \
                    BlockIntegrityException('After ORIP geometry in wwww archive only SHPI directory expected!')
                skip_next_shpi = False
                continue
            if isinstance(item.block, OripGeometry):
                skip_next_shpi = True
            try:
                serializer = serializers.get_serializer(item.block)
                serializer.serialize(item, f'{path}{name}')
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class SoundBankSerializer(BaseFileSerializer):

    def serialize(self, data: SoundBank, path: str):
        path += '/'
        super().serialize(data, path)
        if ((data.id.endswith('SW.BNK') or data.id.endswith('TRAFFC.BNK') or data.id.endswith('TESTBANK.BNK'))
                and len(data.children) == 4):
            # car soundbanks
            names = ['engine_on', 'engine_off', 'honk', 'gear']
        else:
            names = [hex(x.value) for x in data.children_offsets if x.value > 0]
        items = [(names[i], data.children[i]) for i in range(len(data.children))]
        skipped_resources = []
        for name, item in [(name, item) for name, item in items]:
            try:
                serializer = serializers.get_serializer(item.block)
                serializer.serialize(item, f'{path}{name}')
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
