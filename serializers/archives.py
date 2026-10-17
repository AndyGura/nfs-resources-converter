import json
import os
import traceback
from os.path import isdir
import re
from typing import Dict, List, Optional

import config
import serializers
from library.exceptions import DataIntegrityException
from library.utils import format_exception, path_join
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import EacImage, EacPalette
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars

general_config = config.general_config()


def entry_alias(file_name: str, length: Optional[int]) -> str:
    """Archive entry name for a file added from disk: its name without extension, 1 byte per character (other
    characters become "_"), cut to `length`"""
    alias = ''.join(c if ' ' <= c <= '~' else '_' for c in os.path.splitext(file_name)[0])
    return alias[:length] if length else alias


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
                'images__save_image_positions': False,
                'images__save_palettes': False,
                'images__save_mipmaps': False,
                'images__save_embedded_palette': False,
                'images__save_texts': False,
            },
        }

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        items = [
            (x['alias'], x['item']['data'], block.item_block.possible_blocks[x['item']['choice_index']])
            for x in data['children']
        ]
        skipped_resources = []
        output = []
        # textures of a TNFS car model: !xxx (often typed as a bitmap) goes to car_colors.json only
        is_tnfs_car = bool(id) and '.CFM__' in id.upper()
        file_names = self.export_file_names(items, self.settings.images__save_palettes, is_tnfs_car)
        for i, (name, item_data, item_block) in enumerate(items):
            if isinstance(item_data, Exception):
                skipped_resources.append((name, format_exception(item_data)))
                continue
            if i not in file_names:
                continue
            try:
                serializer = serializers.get_serializer(item_block, item_data)
                output.extend(
                    serializer.serialize(
                        item_data,
                        path_join(path, file_names[i]),
                        block=item_block,
                        id=join_id(id, 'children', str(i), 'item', 'data'),
                    )
                )
            except Exception as ex:
                traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if is_tnfs_car:
            from serializers.misc.tnfs_car_colors import tnfs_car_colors

            colors = tnfs_car_colors(id, items)
            with open(path_join(path, 'car_colors.json'), 'w') as f:
                json.dump(colors, f, indent=2)
            output.append(path_join(path, 'car_colors.json'))
        if self.settings.images__save_image_positions:
            with open(path_join(path, 'positions.txt'), 'w') as f:
                for name, item in [(name, data) for name, data, block in items if isinstance(block, EacImage)]:
                    f.write(f'{name}: {item["position"]["x"]}, {item["position"]["y"]}\n')
            output.append(path_join(path, 'positions.txt'))
        if self.settings.maps__save_spherical_skybox_texture:
            try:
                if '.FAM__' in id:
                    # build TNFS horizon texture
                    horz = next(x for name, x, _ in items if name == 'horz')
                    from library.loader import id_to_path
                    from library.utils.nfs1_panorama_to_spherical import nfs1_panorama_to_spherical

                    nfs1_panorama_to_spherical(
                        id_to_path(id),
                        path_join(path, 'horz.png'),
                        path_join(path, 'spherical.png'),
                        horz['pivot']['y'],
                    )
                    output.append(path_join(path, 'spherical.png'))
                elif ('TRACKS/PC/TR0' in id or 'TRACKS/SE/TR0' in id) and ('0.QFS' in id or '0M.QFS' in id):
                    # build NFS2 horizon texture
                    from PIL import Image, ImageOps
                    import math

                    source_images = []
                    out_half_width = 0
                    for i in range(0, 8):
                        # the images have palettes of their own (indexed PNGs): pasted as RGBA
                        img = Image.open(path_join(path, f'000{i}.png')).convert('RGBA')
                        source_images.append(img)
                        out_half_width += img.width
                    out_half_height = int(out_half_width / 2)
                    out_image = Image.new(source_images[0].mode, (out_half_width * 2, out_half_height * 2), 0xFF000000)
                    w = 0
                    for src in source_images:
                        out_image.paste(src, (w, math.floor((out_image.height - src.height) / 2)))
                        out_image.paste(src, (w, math.floor((out_image.height - src.height) / 2)))
                        src_mirrored = ImageOps.mirror(src)
                        out_image.paste(
                            src_mirrored,
                            (out_image.width - src.width - w, math.floor((out_image.height - src.height) / 2)),
                        )
                        w += src.width
                    out_image.save(path_join(path, f'spherical.png'))
                    output.append(path_join(path, 'spherical.png'))
            except:
                pass

        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write('%s\t\t%s\n' % item)
            output.append(path_join(path, 'skipped.txt'))
        return output

    @staticmethod
    def export_file_names(items, save_palettes: bool, is_tnfs_car: bool = False) -> Dict[int, str]:
        """File name (without extension) of every exported item by its index: the escaped item name, with 0, 1...
        appended to a name already taken, ignoring case (Windows and macOS file systems: "AUDI" and "audi" are one
        file). Palettes are exported only with `save_palettes`"""
        names = {}
        taken = set()
        for i, (name, item_data, item_block) in enumerate(items):
            if name is None:
                raise Exception(f'No alias for SHPI resource at index {i}')
            if is_tnfs_car and name == '!xxx':
                continue
            if isinstance(item_data, Exception) or (isinstance(item_block, EacPalette) and not save_palettes):
                continue
            file_name = original_file_name = escape_chars(name).replace('/', '_')
            n = 0
            while file_name.lower() in taken:
                file_name = f'{original_file_name}{n}'
                n += 1
            taken.add(file_name.lower())
            names[i] = file_name
        return names

    def deserialize(self, file_paths: List[str], id=None, block=None, **kwargs) -> dict:
        """The SHPI loaded under `id` merged with the files of the folder, matched to its items by the names the export
        gives them: an image file replaces the pixels of its image (`ImageSerializer.deserialize`), a `.pal.txt` file
        its palette, an image file of no item becomes a new 32-bit image at the end. Items without a file stay as
        they are, other files are ignored. The summary is left in `deserialize_report`"""
        if not file_paths or not isdir(file_paths[0]):
            raise Exception('A directory must be selected for ShpiArchiveSerializer')
        path = file_paths[0]
        if '.CFM__' in (id or '').upper():
            from serializers.misc.tnfs_car_colors import deserialize_tnfs_car_textures

            # textures of a TNFS car model: 8-bit on one palette, with the special colors of car_colors.json
            return deserialize_tnfs_car_textures(path, id, block)
        from PIL import Image, UnidentifiedImageError
        from serializers.bitmaps import ImageSerializer, PaletteSerializer

        current = self._current_shpi(id)
        shpi = dict(current) if current is not None else block.new_data()
        children = list(shpi['children'])
        items = [
            (x['alias'], x['item']['data'], block.item_block.possible_blocks[x['item']['choice_index']])
            for x in children
        ]
        image_files = {
            name: i for i, name in self.export_file_names(items, False).items() if isinstance(items[i][2], EacImage)
        }
        palette_files = {
            name: i for i, name in self.export_file_names(items, True).items() if isinstance(items[i][2], EacPalette)
        }
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        alias_length = block.field_blocks_map['children'].child.field_blocks_map['alias']._get_static_length()
        replaced, added, ignored = [], [], []

        def replace_item(i, data):
            child = children[i]
            children[i] = {**{k: child[k] for k in child}, 'item': {**child['item'], 'data': data}}
            replaced.append(child['alias'])

        for file_name in sorted(os.listdir(path)):
            file_path = path_join(path, file_name)
            stem = os.path.splitext(file_name)[0]
            if isdir(file_path):
                ignored.append(file_name)
            elif file_name.endswith('.pal.txt') and file_name[: -len('.pal.txt')] in palette_files:
                i = palette_files[file_name[: -len('.pal.txt')]]
                replace_item(i, PaletteSerializer().deserialize([file_path], block=items[i][2]))
            else:
                try:
                    Image.open(file_path).close()
                except UnidentifiedImageError, OSError:
                    ignored.append(file_name)
                    continue
                mipmap_of = re.match(r'^(.*)_mm_\d+$', stem)
                if stem in image_files:
                    i = image_files[stem]
                    image_id = join_id(id, 'children', str(i), 'item', 'data') if current is not None else None
                    replace_item(i, ImageSerializer()._with_pixels_of(items[i][1], file_path, items[i][2], image_id))
                elif file_name == 'spherical.png' or (mipmap_of and mipmap_of.group(1) in image_files):
                    # made by the export from the items: the horizon panorama, mipmap levels
                    ignored.append(file_name)
                else:
                    image_block = block.item_block.possible_blocks[image_choice]
                    children.append(
                        {
                            'post_offset_payload': b'',
                            'alias': entry_alias(file_name, alias_length),
                            'item': {
                                'choice_index': image_choice,
                                'data': ImageSerializer.new_image_data(file_path, image_block),
                            },
                        }
                    )
                    added.append(children[-1]['alias'])
        shpi['children'] = children
        report = f'{len(replaced)} replaced, {len(added)} added'
        if ignored:
            report += f'. Ignored: {", ".join(ignored)}'
        self.deserialize_report = report
        return shpi

    @staticmethod
    def _current_shpi(id) -> Optional[dict]:
        # the SHPI loaded under `id`, which the import merges into
        if not id:
            return None
        from library import require_resource

        try:
            (_, _, current), _ = require_resource(id)
        except Exception:
            return None
        return current if isinstance(current, dict) and 'children' in current else None


class WwwwArchiveSerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def ui_serialization(self):
        return {
            'file_type': None,
            'is_directory': True,
            'output_file_name_suffix': None,
            'reversible': False,
            'reversible_settings_patch': {},
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
                assert isinstance(item_block, ShpiBlock), DataIntegrityException(
                    'After ORIP geometry in wwww archive only SHPI directory expected!'
                )
                skip_next_shpi = False
                continue
            if isinstance(item_block, OripGeometry):
                skip_next_shpi = True
            try:
                serializer = serializers.get_serializer(item_block, item_data)
                output.extend(
                    serializer.serialize(
                        item_data,
                        path_join(path, name),
                        block=item_block,
                        id=join_id(id, 'children', str(i), 'item', 'data'),
                    )
                )
            except Exception as ex:
                traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write('%s\t\t%s\n' % item)
            output.append(path_join(path, 'skipped.txt'))
        return output


class SoundBankSerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        if (id.endswith('SW.BNK') or id.endswith('TRAFFC.BNK') or id.endswith('TESTBANK.BNK')) and len(
            data['children']
        ) == 4:
            # car soundbanks
            names = ['engine_on', 'engine_off', 'honk', 'gear']
        else:
            names = [hex(i) for i in block.item_indices(data)]
        items = zip(names, data['children'])
        skipped_resources = []
        item_block = block.field_blocks_map['children'].child
        output = []
        for i, (name, item) in enumerate(items):
            entry = data['items'][i]
            meta = {
                'bend_range_semitones': entry['bend_range_semitones'],
                'volume': entry['volume'],
                'pan': entry['pan'],
                'priority': entry['priority'],
                'random_range': entry['random_range'],
                'unknown_0x16': entry['unk4'],
            }
            try:
                serializer = serializers.get_serializer(item_block, item)
                output.extend(
                    serializer.serialize(item, path_join(path, name), id=join_id(id, 'children', str(i)), meta=meta)
                )
            except Exception as ex:
                traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write('%s\t\t%s\n' % item)
            output.append(path_join(path, 'skipped.txt'))
        return output


class BigfArchiveSerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        items = [
            (child['alias'], child['item']['data'], block.item_block.possible_blocks[child['item']['choice_index']])
            for child in data['children']
        ]
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
                    n = 0
                    while save_image_names.get(file_name):
                        file_name = f'{original_file_name}{n}'
                        n += 1
                output.extend(
                    serializer.serialize(
                        item_data,
                        path_join(path, file_name),
                        block=item_block,
                        id=join_id(id, 'children', str(i), 'item', 'data'),
                    )
                )
                save_image_names[file_name] = True
            except Exception as ex:
                traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write('%s\t\t%s\n' % item)
            output.append(path_join(path, 'skipped.txt'))
        return output
