import os
import traceback

import config
import serializers
from library.exceptions import DataIntegrityException
from library.utils import format_exception, path_join
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import AnyBitmapBlock, Bitmap8Bit
from resources.eac.geometries import OripGeometry
from resources.eac.palettes import PaletteReference, BasePalette, Palette24BitDos
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars

general_config = config.general_config()


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
                    serializer.serialize(item_data, path_join(path, file_name),
                                         block=item_block,
                                         id=join_id(id, 'children', name, 'data'))
                    save_image_names[file_name] = True
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if not self.settings.images__save_images_only:
            with open(path_join(path, 'positions.txt'), 'w') as f:
                for name, item in [(name, data) for name, data, block in items if isinstance(block, AnyBitmapBlock)]:
                    f.write(f"{name}: {item['x']}, {item['y']}\n")
        if self.settings.maps__save_spherical_skybox_texture:
            try:
                if '.FAM__' in id:
                    # build TNFS horizon texture
                    horz = next(x for name, x, _ in items if name == 'horz')
                    from library.utils.nfs1_panorama_to_spherical import nfs1_panorama_to_spherical
                    nfs1_panorama_to_spherical(id[id.index('.FAM') - 7:id.index('.FAM') - 4],
                                               path_join(path, 'horz.png'),
                                               path_join(path, 'spherical.png'),
                                               horz['pivot_y'])
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
            except:
                pass

        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)

    def deserialize(self, path: str, id=None, block=None, quantize_new_palette=True, **kwargs) -> None:
        max_colors_amount = 255  # minus the last one, reserved for transparency
        generate_palettes = ['!pal']
        if '.CFM' in id:
            # last 6 colors are special for cars:
            # 250th, 251th - cop red blinker
            # 252th, 253th - cop blue blinker
            # 254th is replaced with tail colors in the game
            # 255th is transparent
            max_colors_amount = 250
            generate_palettes = ['!PAL', '!xxx']
        if '.FAM' in id:
            generate_palettes = ['!PAL']
        # build a new palette for SHPI
        from PIL import Image
        from collections import Counter
        from serializers.bitmaps import BitmapWithPaletteSerializer
        individual_palettes = []
        file_names = [x for x in os.listdir(path)]
        images = [Image.open(path_join(path, x)) for x in file_names]
        # find unused color for marking transparency
        all_colors = set()
        for src in images:
            all_colors.union({(x[0] << 24) + (x[1] << 16) + (x[2] << 8) + (0xff if src.mode == 'RGB' else x[3])
                              for _, x in src.getcolors(src.size[0] * src.size[1])})
        # pick transparent color
        transparent = 0xff
        for c in [0xFF_00_00_FF,
                  0x00_FF_00_FF,
                  0x00_00_FF_FF,
                  0xFF_FF_00_FF,
                  0xFF_00_FF_FF,
                  0x00_FF_FF_FF,
                  0xFF_FF_FF_FF,
                  0x00_00_00_FF]:
            if c not in all_colors:
                transparent = c
                break
        # quantize all images, transparency replaced with solid color, picked above
        for i, src in enumerate(images):
            img = Image.new(
                "RGB",
                src.size,
                ((transparent & 0xff000000) >> 24, (transparent & 0xff0000) >> 16,
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
            img = image_serializer.deserialize(path_join(path, name),
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
                serializer.serialize(item_data, path_join(path, name), block=item_block,
                                     id=join_id(id, 'children', str(i), 'data'))
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
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
                serializer.serialize(item, path_join(path, name), id=join_id(id, 'children', name))
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
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
                serializer.serialize(item_data, path_join(path, file_name),
                                     block=item_block,
                                     id=join_id(id, 'children', str(i), 'data'))
                save_image_names[file_name] = True
            except Exception as ex:
                if general_config.print_errors:
                    traceback.print_exc()
                skipped_resources.append((name, format_exception(ex)))
        if skipped_resources:
            with open(path_join(path, 'skipped.txt'), 'w') as f:
                for item in skipped_resources:
                    f.write("%s\t\t%s\n" % item)
