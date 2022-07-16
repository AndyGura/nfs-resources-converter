import serializers
from resources.basic.exceptions import BlockIntegrityException
from resources.eac.archives import ShpiArchive, WwwwArchive
from resources.eac.bitmaps import AnyBitmapResource
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer
from utils import format_exception


class ShpiArchiveSerializer(BaseFileSerializer):

    def serialize(self, block: ShpiArchive, path: str):
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
            for name, item in [(name, item) for name, item in items if isinstance(item, AnyBitmapResource)]:
                f.write(f"{name}: {item.x}, {item.y}\n")
        if skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class WwwwArchiveSerializer(BaseFileSerializer):

    def serialize(self, block: WwwwArchive, path: str):
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
                assert isinstance(item, ShpiArchive), \
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

    def serialize(self, block: WwwwArchive, path: str):
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
