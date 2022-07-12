import os

import serializers
from resources.eac.archives import ShpiArchive, WwwwArchive
from resources.eac.bitmaps import AnyBitmapResource
from serializers import BaseFileSerializer
from utils import format_exception


class ShpiArchiveSerializer(BaseFileSerializer):

    def serialize(self, block: ShpiArchive, path: str):
        path += '/'
        os.makedirs(path, exist_ok=True)
        super().serialize(block, path)
        items = [(block.children_descriptions[i].name, block.children[i]) for i in range(block.children_count)]
        skipped_resources = []
        for name, item in [(name, item) for name, item in items]:
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
        os.makedirs(path, exist_ok=True)
        super().serialize(block, path)
        if block.id.endswith('.CFM') and block.children_count == 4:
            names = ['high-poly', 'high-poly-assets', 'low-poly', 'low-poly-assets']
        elif block.id.endswith('.FAM') and block.children_count == 4:
            names = ['background', 'foreground', 'skybox', 'props']
        else:
            names = [str(i) for i in range(block.children_count)]
        items = [(names[i], block.children[i]) for i in range(block.children_count)]
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
