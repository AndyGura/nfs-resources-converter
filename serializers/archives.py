import os
import traceback
from os.path import isdir
from typing import List

import config
import serializers
from library.exceptions import DataIntegrityException
from library.utils import format_exception, path_join
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock, PaletteReference
from resources.eac.bitmaps import EacImage, EacPalette
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars

general_config = config.general_config()


class ShpiArchiveSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def ui_serialization(self):
        return {
            'file_type': 'PNG-s directory',
            'is_directory': True,
            'output_file_name_suffix': None,
            'reversible': True,
            'reversible_settings_patch': {
                'images__save_images_only': True,
            }
        }

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        items = [(x['alias'], x['item']['data'], block.item_block.possible_blocks[x['item']['choice_index']])
                 for x in data['children']]
        skipped_resources = []
        save_image_names = {}
        unaliased_idx = 0
        output = []
        for i, (name, item_data, item_block) in enumerate(items):
            if isinstance(item_block, PaletteReference):
                continue
            if name is None:
                # that's a resource, assigned to the previous bitmap
                if i > 0 and items[i - 1][0] is not None:
                    suffix = 'extra'
                    if isinstance(item_block, EacPalette):
                        suffix = 'pal'
                    name = f'{items[i - 1][0]}_{suffix}'
                else:
                    name = f'internal_{unaliased_idx}'
                    unaliased_idx += 1
            if isinstance(item_data, Exception):
                skipped_resources.append((name, format_exception(item_data)))
                continue
            try:
                if not self.settings.images__save_images_only or isinstance(item_block, EacImage):
                    serializer = serializers.get_serializer(item_block, item_data)
                    file_name = escape_chars(name).replace('/', '_')
                    if save_image_names.get(file_name):
                        original_file_name = file_name
                        i = 0
                        while save_image_names.get(file_name):
                            file_name = f'{original_file_name}{i}'
                            i += 1
                    output.extend(serializer.serialize(item_data, path_join(path, file_name),
                                                       block=item_block,
                                                       id=join_id(id, 'children', name, 'item', 'data')))
                    save_image_names[file_name] = True
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if not self.settings.images__save_images_only:
            with open(path_join(path, 'positions.txt'), 'w') as f:
                for name, item in [(name, data) for name, data, block in items if isinstance(block, EacImage)]:
                    f.write(f"{name}: {item['position']['x']}, {item['position']['y']}\n")
            output.append(path_join(path, 'positions.txt'))
        if self.settings.maps__save_spherical_skybox_texture:
            try:
                if '.FAM__' in id:
                    # build TNFS horizon texture
                    horz = next(x for name, x, _ in items if name == 'horz')
                    from library.utils.nfs1_panorama_to_spherical import nfs1_panorama_to_spherical
                    nfs1_panorama_to_spherical(id[id.index('.FAM') - 7:id.index('.FAM') - 4],
                                               path_join(path, 'horz.png'),
                                               path_join(path, 'spherical.png'),
                                               horz['pivot']['y'])
                    output.append(path_join(path, 'spherical.png'))
                elif ('TRACKS/PC/TR0' in id or 'TRACKS/SE/TR0' in id) and ('0.QFS' in id or '0M.QFS' in id):
                    # build NFS2 horizon texture
                    from PIL import Image, ImageOps
                    import math
                    source_images = []
                    out_half_width = 0
                    for i in range(0, 8):
                        img = Image.open(path_join(path, f'000{i}.png'))
                        source_images.append(img)
                        out_half_width += img.width
                    out_half_height = int(out_half_width / 2)
                    out_image = Image.new(source_images[0].mode, (out_half_width * 2, out_half_height * 2), 0xff000000)
                    w = 0
                    for src in source_images:
                        out_image.paste(src, (w, math.floor((out_image.height - src.height) / 2)))
                        out_image.paste(src, (w, math.floor((out_image.height - src.height) / 2)))
                        src_mirrored = ImageOps.mirror(src)
                        out_image.paste(src_mirrored, (out_image.width - src.width - w,
                                                       math.floor((out_image.height - src.height) / 2)))
                        w += src.width
                    out_image.save(path_join(path, f'spherical.png'))
                    output.append(path_join(path, 'spherical.png'))
            except:
                pass

        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
            output.append(path_join(path, 'skipped.txt'))
        return output

    def deserialize(self, file_paths: List[str], id=None, block=None, **kwargs) -> None:
        if not file_paths or not isdir(file_paths[0]):
            raise Exception('A directory must be selected for ShpiArchiveSerializer')
        new_shpi = block.new_data()

        path = file_paths[0]
        file_names = [x for x in os.listdir(path)]
        img_block = EacImage()
        img_serializer = img_block.serializer_class()()

        for file_name in file_names:
            img = img_serializer.deserialize([path_join(path, file_name)],
                                             join_id(id, f'children/{len(new_shpi["children"])}/item/data'),
                                             img_block)

            new_shpi['children'].append({
                'pre_offset_payload': b'',
                'post_offset_payload': b'',
                'alias': file_name[:-4],
                'item': {'choice_index': block.item_block.get_choice_index_by_class_name('EacImage'),
                         'data': img}
            })
        return new_shpi


class WwwwArchiveSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def ui_serialization(self):
        return {
            'file_type': None,
            'is_directory': True,
            'output_file_name_suffix': None,
            'reversible': False,
            'reversible_settings_patch': {}
        }

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        if id.endswith('.CFM') and data['num_items'] == 4:
            # car CFM file
            names = ['high-poly', 'high-poly-assets', 'low-poly', 'low-poly-assets']
        elif id.endswith('.FAM') and data['num_items'] == 4:
            # track FAM file
            names = ['background', 'foreground', 'skybox', 'props']
        else:
            names = [str(i) for i in range(data['num_items'])]
        children = list(zip(names, data['children']))
        skipped_resources = []
        # after orip skip shpi block. It will be exported by orip serializer
        skip_next_shpi = False
        output = []
        for i, (name, child) in enumerate(children):
            item = child['item']
            if item is None:
                continue
            item_block = block.item_block.possible_blocks[item['choice_index']]
            item_data = item['data']
            if isinstance(item_data, Exception):
                skipped_resources.append((name, format_exception(item_data)))
                continue
            if skip_next_shpi:
                assert isinstance(item_block, ShpiBlock), \
                    DataIntegrityException('After ORIP geometry in wwww archive only SHPI directory expected!')
                skip_next_shpi = False
                continue
            if isinstance(item_block, OripGeometry):
                skip_next_shpi = True
            try:
                serializer = serializers.get_serializer(item_block, item_data)
                output.extend(serializer.serialize(item_data, path_join(path, name), block=item_block,
                                                   id=join_id(id, 'children', str(i), 'item', 'data')))
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
            output.append(path_join(path, 'skipped.txt'))
        return output


class SoundBankSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        if ((id.endswith('SW.BNK') or id.endswith('TRAFFC.BNK') or id.endswith('TESTBANK.BNK'))
                and len(data['children']) == 4):
            # car soundbanks
            names = ['engine_on', 'engine_off', 'honk', 'gear']
        else:
            names = [hex(i) for (i, x) in enumerate(data['items_descr']) if x > 0]
        items = zip(names, data['children'])
        skipped_resources = []
        item_block = block.field_blocks_map['children'].child
        output = []
        for name, item in [(name, item) for name, item in items]:
            try:
                serializer = serializers.get_serializer(item_block, item)
                output.extend(serializer.serialize(item, path_join(path, name), id=join_id(id, 'children', name)))
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
            output.append(path_join(path, 'skipped.txt'))
        return output


class BigfArchiveSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        items = [(child['alias'], child['item']['data'], block.item_block.possible_blocks[child['item']['choice_index']])
                 for child in data['children']]
        skipped_resources = []
        save_image_names = {}
        output = []
        for i, (name, item_data, item_block) in enumerate(items):
            if isinstance(item_data, Exception):
                skipped_resources.append((name, format_exception(item_data)))
                continue
            try:
                serializer = serializers.get_serializer(item_block, item_data)
                file_name = escape_chars(name).replace('/', '_')
                if save_image_names.get(file_name):
                    original_file_name = file_name
                    i = 0
                    while save_image_names.get(file_name):
                        file_name = f'{original_file_name}{i}'
                        i += 1
                output.extend(serializer.serialize(item_data, path_join(path, file_name),
                                                   block=item_block,
                                                   id=join_id(id, 'children', str(i), 'item', 'data')))
                save_image_names[file_name] = True
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
            output.append(path_join(path, 'skipped.txt'))
        return output
