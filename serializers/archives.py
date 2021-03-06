import serializers
from library.helpers.exceptions import BlockIntegrityException
from library.utils import format_exception
from library.utils.nfs1_panorama_to_spherical import nfs1_panorama_to_spherical
from resources.eac.archives import ShpiBlock, WwwwBlock, SoundBank
from resources.eac.bitmaps import AnyBitmapBlock
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer


class ShpiArchiveSerializer(BaseFileSerializer):

    def serialize(self, block: ShpiBlock, path: str):
        path += '/'
        super().serialize(block, path)
        items = [(block.children_descriptions[i].name, block.children[i]) for i in range(block.children_count)]
        skipped_resources = []
        for name, item in [(name, item) for name, item in items]:
            if isinstance(item, Exception):
                skipped_resources.append((name, format_exception(item)))
                continue
            try:
                serializer = serializers.get_serializer(item)
                serializer.serialize(item, f'{path}{name}')
            except Exception as ex:
                skipped_resources.append((name, format_exception(ex)))
        with open(f'{path}/positions.txt', 'w') as f:
            for name, item in [(name, item) for name, item in items if isinstance(item, AnyBitmapBlock)]:
                f.write(f"{name}: {item.x}, {item.y}\n")
        if '.FAM__' in block.id:
            try:
                horz_bitmap = next(x for name, x in items if name == 'horz')
                nfs1_panorama_to_spherical(block.id[block.id.index('.FAM') - 7:block.id.index('.FAM') - 4],
                                           f'{path}horz.png', f'{path}spherical.png')
            except StopIteration:
                pass
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class WwwwArchiveSerializer(BaseFileSerializer):

    def serialize(self, block: WwwwBlock, path: str):
        path += '/'
        super().serialize(block, path)
        if block.id.endswith('.CFM') and block.children_count == 4:
            # car CFM file
            names = ['high-poly', 'high-poly-assets', 'low-poly', 'low-poly-assets']
        elif block.id.endswith('.FAM') and block.children_count == 4:
            # track FAM file
            names = ['background', 'foreground', 'skybox', 'props']
        else:
            names = [str(i) for i in range(block.children_count)]
        items = [(names[i], block.children[i]) for i in range(block.children_count)]
        skipped_resources = []
        # after orip skip shpi block. It will be exported by orip serializer
        skip_next_shpi = False
        for name, item in [(name, item) for name, item in items]:
            if skip_next_shpi:
                assert isinstance(item, ShpiBlock), \
                    BlockIntegrityException('After ORIP geometry in wwww archive only SHPI directory expected!')
                skip_next_shpi = False
                continue
            if isinstance(item, OripGeometry):
                skip_next_shpi = True
            try:
                serializer = serializers.get_serializer(item)
                serializer.serialize(item, f'{path}{name}')
            except Exception as ex:
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class SoundBankSerializer(BaseFileSerializer):

    def serialize(self, block: SoundBank, path: str):
        path += '/'
        super().serialize(block, path)
        if ((block.id.endswith('SW.BNK') or block.id.endswith('TRAFFC.BNK') or block.id.endswith('TESTBANK.BNK'))
                and len(block.children) == 4):
            # car soundbanks
            names = ['engine_on', 'engine_off', 'honk', 'gear']
        else:
            names = [hex(x) for x in block.children_offsets if x > 0]
        items = [(names[i], block.children[i]) for i in range(len(block.children))]
        skipped_resources = []
        for name, item in [(name, item) for name, item in items]:
            try:
                serializer = serializers.get_serializer(item)
                serializer.serialize(item, f'{path}{name}')
            except Exception as ex:
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
