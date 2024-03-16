import os
import traceback

import serializers
from library.exceptions import DataIntegrityException
from library.utils import format_exception
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import AnyBitmapBlock, Bitmap8Bit
from resources.eac.geometries import OripGeometry
from resources.eac.palettes import PaletteReference, BasePalette, Palette24BitDos
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars


class ShpiArchiveSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def setup_for_reversible_serialization(self) -> bool:
        self.patch_settings({
            'images__save_images_only': True,
        })
        return True

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        children_field = block.field_blocks_map['children'].child
        items = [(alias, child['data'], children_field.possible_blocks[child['choice_index']])
                 for i, (alias, child) in enumerate(zip(data['children_aliases'], data['children']))]
        skipped_resources = []
        save_image_names = {}
        unaliased_idx = 0
        for i, (name, item_data, item_block) in enumerate(items):
            if isinstance(item_block, PaletteReference):
                continue
            if name is None:
                # that's a resource, assigned to the previous bitmap
                if i > 0 and items[i - 1][0] is not None:
                    suffix = 'extra'
                    if isinstance(item_block, BasePalette):
                        suffix = 'pal'
                    name = f'{items[i - 1][0]}_{suffix}'
                else:
                    name = f'internal_{unaliased_idx}'
                    unaliased_idx += 1
            if isinstance(item_data, Exception):
                skipped_resources.append((name, format_exception(item_data)))
                continue
            try:
                if not self.settings.images__save_images_only or isinstance(item_block, AnyBitmapBlock):
                    serializer = serializers.get_serializer(item_block, item_data)
                    file_name = escape_chars(name).replace('/', '_')
                    if save_image_names.get(file_name):
                        original_file_name = file_name
                        i = 0
                        while save_image_names.get(file_name):
                            file_name = f'{original_file_name}{i}'
                            i += 1
                    serializer.serialize(item_data, os.path.join(path, file_name),
                                         block=item_block,
                                         id=join_id(id, 'children', name, 'data'))
                    save_image_names[file_name] = True
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if not self.settings.images__save_images_only:
            with open(os.path.join(path, 'positions.txt'), 'w') as f:
                for name, item in [(name, data) for name, data, block in items if isinstance(block, AnyBitmapBlock)]:
                    f.write(f"{name}: {item['x']}, {item['y']}\n")
        if '.FAM__' in id and self.settings.maps__save_spherical_skybox_texture:
            try:
                next(x for name, x, _ in items if name == 'horz')
                from library.utils.nfs1_panorama_to_spherical import nfs1_panorama_to_spherical
                nfs1_panorama_to_spherical(id[id.index('.FAM') - 7:id.index('.FAM') - 4],
                                           os.path.join(path, 'horz.png'), os.path.join(path, 'spherical.png'))
            except StopIteration:
                pass
        if skipped_resources:
            with open(os.path.join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)

    def deserialize(self, path: str, id=None, block=None, quantize_new_palette=True, **kwargs) -> None:
        max_colors_amount = 255  # minus the last one, reserved for transparency
        generate_palettes = ['!pal']
        if '.CFM' in id:
            # last 6 colors are somehow special for cars:
            # 250th - 253th seem to always be rendered black
            # 254th is replaced woith tail colors in the game
            # 255th is transparent
            max_colors_amount = 250
            generate_palettes = ['!PAL', '!xxx']
        if '.FAM' in id:
            generate_palettes = ['!PAL']
        # build a new palette for SHPI
        from PIL import Image
        from collections import Counter
        from resources.eac.palettes import transparency_colors
        from serializers.bitmaps import BitmapWithPaletteSerializer
        individual_palettes = []
        file_names = [x for x in os.listdir(path)]
        images = [Image.open(os.path.join(path, x)) for x in file_names]
        # find unused color for marking transparency
        all_colors = set()
        for src in images:
            all_colors.union({(x[0] << 24) + (x[1] << 16) + (x[2] << 8) + (0xff if src.mode == 'RGB' else x[3])
                              for _, x in src.getcolors(src.size[0] * src.size[1])})
        # pick transparent color
        transparent = 0xff
        for c in transparency_colors:
            if c not in all_colors:
                transparent = c
                break
        tail_lights_color = 0
        if any(BitmapWithPaletteSerializer.has_tail_lights(join_id(id, f'children/{file_name[:-4]}/data')) for file_name
               in file_names):
            for c in transparency_colors:
                if c not in all_colors and c != transparent:
                    tail_lights_color = c
                    break
        # quantize all images, transparency replaced with solid color, picked above
        for i, src in enumerate(images):
            img = Image.new(
                "RGB",
                src.size,
                ((tail_lights_color & 0xff000000) >> 24, (tail_lights_color & 0xff0000) >> 16,
                 (tail_lights_color & 0xff00) >> 8)
                if BitmapWithPaletteSerializer.has_tail_lights(join_id(id, f'children/{file_names[i][:-4]}/data'))
                else (
                    (transparent & 0xff000000) >> 24, (transparent & 0xff0000) >> 16,
                    (transparent & 0xff00) >> 8)
            )
            img.paste(src, mask=(None if src.mode == 'RGB' else src.split()[3]))
            quantized_img = img.quantize(colors=max_colors_amount + 1)  # + transparent channel
            pil_palette = quantized_img.getpalette()
            individual_palettes.append(
                [(pil_palette[i] << 24) + (pil_palette[i + 1] << 16) + (pil_palette[i + 2] << 8) + 0xff for i in
                 range(0, len(pil_palette), 3)])
        # calculating common palette among images
        all_colors = sum(individual_palettes, [])
        color_counts = Counter(all_colors)
        most_common_colors = color_counts.most_common(max_colors_amount + 1)  # + transparent channel
        palette = [color[0] for color in most_common_colors]
        if len(palette) < 256:
            palette += [0] * (256 - len(palette))
        # place transparent color in the end
        try:
            idx = palette.index(transparent)
            palette = palette[:idx] + palette[(idx + 1):] + [transparent]
        except ValueError:
            palette[-1] = transparent
        if tail_lights_color:
            try:
                idx = palette.index(tail_lights_color)
                palette = palette[:idx] + palette[(idx + 1):-1] + [tail_lights_color, transparent]
            except ValueError:
                palette[-2] = tail_lights_color
        child_field = block.field_blocks_map['children'].child
        new_shpi = block.new_data()
        pal_block = Palette24BitDos()
        img_block = Bitmap8Bit()
        pal = pal_block.new_data()
        pal['colors'] = palette
        for pal_alias in generate_palettes:
            new_shpi['children'].append({'choice_index': next(i for (i, b) in enumerate(child_field.possible_blocks) if
                                                              isinstance(b, Palette24BitDos)),
                                         'data': pal})
            new_shpi['children_aliases'].append(pal_alias)
            new_shpi['offset_payloads'].append(b'')
        image_serializer = BitmapWithPaletteSerializer()
        bitmap8_choice = next(i for i in range(len(child_field.possible_blocks)) if
                              isinstance(child_field.possible_blocks[i], Bitmap8Bit))
        for name in file_names:
            alias = name[:-4]
            img = image_serializer.deserialize(os.path.join(path, name),
                                               join_id(id, f'children/{alias}'),
                                               img_block,
                                               palette=palette)
            new_shpi['children'].append({'choice_index': bitmap8_choice, 'data': img})
            new_shpi['children_aliases'].append(alias)
            new_shpi['offset_payloads'].append(b'')
        return new_shpi


class WwwwArchiveSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        if id.endswith('.CFM') and data['num_items'] == 4:
            # car CFM file
            names = ['high-poly', 'high-poly-assets', 'low-poly', 'low-poly-assets']
        elif id.endswith('.FAM') and data['num_items'] == 4:
            # track FAM file
            names = ['background', 'foreground', 'skybox', 'props']
        else:
            names = [str(i) for i in range(data['num_items'])]
        items = list(zip(names, data['children']))
        skipped_resources = []
        # after orip skip shpi block. It will be exported by orip serializer
        skip_next_shpi = False
        for i, (name, item) in enumerate(items):
            if item is None:
                continue
            item_block = block.child_block.possible_blocks[item['choice_index']]
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
                serializer.serialize(item_data, os.path.join(path, name), block=item_block,
                                     id=join_id(id, 'children', str(i), 'data'))
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(os.path.join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class SoundBankSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
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
        for name, item in [(name, item) for name, item in items]:
            try:
                serializer = serializers.get_serializer(item_block, item)
                serializer.serialize(item, os.path.join(path, name), id=join_id(id, 'children', name))
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(os.path.join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class BigfArchiveSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        children_field = block.field_blocks_map['children'].child
        items = [(alias, child['data'], children_field.possible_blocks[child['choice_index']])
                 for i, (alias, child) in enumerate(zip(data['children_aliases'], data['children']))]
        skipped_resources = []
        save_image_names = {}
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
                serializer.serialize(item_data, os.path.join(path, file_name),
                                     block=item_block,
                                     id=join_id(id, 'children', str(i), 'data'))
                save_image_names[file_name] = True
            except Exception as ex:
                if self.settings.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(os.path.join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
