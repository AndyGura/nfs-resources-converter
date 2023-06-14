import os
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
            for name, item in [(name, item) for name, item in items if
                               isinstance(item, ReadData) and isinstance(item.block, AnyBitmapBlock)]:
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

    def deserialize(self, path: str, resource: ReadData, quantize_new_palette=True, **kwargs) -> None:
        # FIXME not supported operations listed below:
        # does not support adding/removing bitmaps
        # does not support changed image dimensions
        # does not support changed palette size
        # does not support cases where 8-bitmaps use different palette (is it even possible?)
        # totally breaks car tail lights (TNFS)
        # can break transparency
        # tested with only 8bit images (TNFS shpi archives)
        from resources.eac.bitmaps import Bitmap8Bit, AnyBitmapBlock
        from resources.eac.palettes import BasePalette
        bitmaps_8bit = [(index, read_data) for (index, read_data) in enumerate(resource.value.children) if
                        isinstance(read_data.block, Bitmap8Bit)]
        if len(bitmaps_8bit) > 0:
            shpi_pal = [read_data for read_data in resource.value.children if isinstance(read_data.block, BasePalette)][
                0]
            if quantize_new_palette:
                from PIL import Image
                from collections import Counter
                individual_palettes = []
                for img_path in (os.path.join(path, image.id.split('/')[-1] + '.png') for (_, image) in bitmaps_8bit):
                    src = Image.open(img_path)
                    img = Image.new("RGB", src.size, (255, 0, 255))
                    img.paste(src, mask=src.split()[3])
                    quantized_img = img.quantize(colors=256)
                    pil_palette = quantized_img.getpalette()
                    individual_palettes.append(
                        [(pil_palette[i] << 24) + (pil_palette[i + 1] << 16) + (pil_palette[i + 2] << 8) + 0xff for i in
                         range(0, len(pil_palette), 3)])
                all_colors = sum(individual_palettes, [])
                color_counts = Counter(all_colors)
                most_common_colors = color_counts.most_common(256)
                palette = [color[0] for color in most_common_colors]
                palette_colors = [] + palette
                if len(palette_colors) < 256:
                    palette_colors += [0] * (256 - len(palette_colors))
                shpi_pal.value.colors.value = [ReadData(value=x,
                                                        block_state={'id': resource.id + '/palette/colors/' + str(i)},
                                                        block=shpi_pal.block.instance_fields_map['colors'].child,
                                                        ) for i, x in enumerate(palette_colors)]
            else:
                palette = [x.value for x in shpi_pal.colors]
        for image in (read_data for read_data in resource.value.children if
                      isinstance(read_data.block, AnyBitmapBlock)):
            serializer = serializers.get_serializer(image.block)
            serializer.deserialize(os.path.join(path, image.id.split('/')[-1]), image, palette=palette)


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
