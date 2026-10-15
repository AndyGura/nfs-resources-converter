import json
import os
import tempfile
import unittest
from io import BytesIO

from PIL import Image

from library import require_resource
from library.context import ReadContext
from resources.eac.bitmaps import EacImage, EacPalette
from serializers import ShpiArchiveSerializer
from serializers.misc.tnfs_car_colors import car_texture_palette, tnfs_car_colors

HIGH_POLY_ID = 'SIMDATA/CARFAMS/{}.CFM__children/1/item/data'


def _palette(colors=None):
    # internal RGBA ints, 24BitDos: 6-bit components << 2
    colors = colors or {}
    data = [(i << 24 | i << 16 | i << 8 | 0xFF) for i in range(256)]
    for index, rgb in colors.items():
        data[index] = rgb << 8 | 0xFF
    return {'resource_id': '24BitDos color format palette', 'colors': {'data': data}, 'last_color_transparent': False}


def _image(indices):
    return {'resource_id': '8Bit', 'bitmap': list(indices)}


def _items(palette, textures, xxx=None):
    items = [('!PAL', palette, EacPalette())]
    items += [(name, _image(indices), EacImage()) for name, indices in textures.items()]
    if xxx is not None:
        items.append(('!xxx', xxx, EacImage()))
    return items


class TestCarTexturePalette(unittest.TestCase):
    def test_unique_colors_stay(self):
        palette = _palette({250: 0x102030, 254: 0x8CF818})['colors']['data']
        self.assertEqual(car_texture_palette(palette), palette)

    def test_shared_color_gets_the_nearest_free_one(self):
        palette = _palette({250: 0x102030, 251: 0x102030})['colors']['data']
        result = car_texture_palette(palette)
        self.assertEqual(result[250], 0x102031FF)
        self.assertEqual(result[251], 0x102030FF)
        self.assertEqual(len({c >> 8 for c in result}), 256)

    def test_color_of_another_entry_moves_down_at_the_top(self):
        palette = _palette({3: 0xFFFFFF, 254: 0xFFFFFF})['colors']['data']
        self.assertEqual(car_texture_palette(palette)[254], 0xFFFFFEFF)
        self.assertEqual(car_texture_palette(palette)[3], 0xFFFFFFFF)


class TestTnfsCarColors(unittest.TestCase):
    def test_tail_lights_of_the_car_model(self):
        items = _items(_palette({254: 0x8CF818}), {'rsid': [1, 254], 'frnt': [1]})
        colors = tnfs_car_colors(HIGH_POLY_ID.format('F512TR'), items)
        self.assertEqual(
            colors['tail_lights'], {'texture_color': '#8cf818', 'textures': ['rsid'], 'off': '#181818', 'on': '#f81414'}
        )
        self.assertEqual(tnfs_car_colors(HIGH_POLY_ID.format('MF512TR'), items)['tail_lights']['off'], '#181818')

    def test_same_keys_for_every_car(self):
        items = _items(_palette({250: 0xFC6454, 251: 0xFC0000}), {'rear': [250, 251, 2], 'frnt': [2]})
        for name in ['COPMUST', 'TSUPRA', 'MY_COOL_CAR']:
            colors = tnfs_car_colors(HIGH_POLY_ID.format(name), items)
            self.assertEqual(colors['tail_lights']['textures'], [], name)
            self.assertEqual(colors['tail_lights']['off'], '#3c0c0c', name)
            light_bar = colors['light_bar']
            self.assertEqual(light_bar['textures'], ['rear'], name)
            self.assertEqual(light_bar['texture_colors'][:2], ['#fc6454', '#fc0000'], name)
            self.assertEqual(light_bar['siren_colors'], ['#fc0080', '#c00040', '#8000fc', '#4000c0'], name)
            self.assertEqual(light_bar['siren_colors_swapped'], ['#8000fc', '#4000c0', '#fc0080', '#c00040'], name)
            self.assertEqual(light_bar['swap_interval_ms'], 266.667, name)

    def test_shared_light_bar_colors_are_made_unique(self):
        items = _items(_palette({250: 0xFC0000, 251: 0xFC0000}), {'rear': [250, 251]})
        colors = tnfs_car_colors(HIGH_POLY_ID.format('MY_COOL_CAR'), items)
        self.assertEqual(colors['light_bar']['texture_colors'][:2], ['#fc0001', '#fc0000'])

    def test_palette_slice_of_xxx_unless_junk(self):
        raw = [1, 2, 3] * 85 + [0]
        items = _items(_palette(), {}, xxx={'resource_id': '8Bit', 'bitmap': raw})
        self.assertEqual(tnfs_car_colors(HIGH_POLY_ID.format('MY_COOL_CAR'), items)['palette_slice'], ['#04080c'] * 24)
        self.assertNotIn('palette_slice', tnfs_car_colors(HIGH_POLY_ID.format('MY_COOL_CAR'), _items(_palette(), {})))
        junk = _items(_palette(), {}, xxx={'resource_id': '8Bit', 'bitmap': [200] + raw[1:]})
        self.assertNotIn('palette_slice', tnfs_car_colors(HIGH_POLY_ID.format('MTSUPRA'), junk))


class TestTsupraCarColorsFile(unittest.TestCase):
    def test_car_colors_json_matches_png_colors(self):
        (shpi_id, block, data), _ = require_resource('test/samples/TSUPRA.CFM__children/1/item/data')
        with tempfile.TemporaryDirectory() as path:
            ShpiArchiveSerializer().serialize(data, path, shpi_id, block)
            files = os.listdir(path)
            self.assertNotIn('!xxx.png', files)
            with open(os.path.join(path, 'car_colors.json')) as f:
                colors = json.load(f)
            self.assertEqual(colors['tail_lights']['texture_color'], '#8cf818')
            self.assertEqual(len(colors['palette_slice']), 24)
            for key, texture_colors in [
                ('tail_lights', [colors['tail_lights']['texture_color']]),
                ('light_bar', colors['light_bar']['texture_colors']),
            ]:
                for texture in colors[key]['textures']:
                    pixels = set(Image.open(os.path.join(path, f'{texture}.png')).convert('RGB').get_flattened_data())
                    pixels = {r << 16 | g << 8 | b for r, g, b in pixels}
                    self.assertTrue(pixels & {int(c[1:], 16) for c in texture_colors}, f'{key} {texture}')


def _png_pixels(path):
    return {
        name: list(Image.open(os.path.join(path, name)).convert('RGBA').get_flattened_data())
        for name in sorted(os.listdir(path))
        if name.endswith('.png')
    }


class TestTnfsCarTexturesDeserialization(unittest.TestCase):
    def _round_trip(self, wwww_index):
        (shpi_id, block, data), _ = require_resource(f'test/samples/TSUPRA.CFM__children/{wwww_index}/item/data')
        original = dict(data)
        try:
            with tempfile.TemporaryDirectory() as exported, tempfile.TemporaryDirectory() as reexported:
                ShpiArchiveSerializer().serialize(data, exported, shpi_id, block)
                imported = ShpiArchiveSerializer().deserialize([exported], shpi_id, block)
                raw = block.write(imported)
                read_back = block.unpack(
                    ReadContext(BytesIO(raw), read_bytes_amount=len(raw)), read_bytes_amount=len(raw)
                )
                # as the GUI does: the imported data replaces the one in the file tree
                data.clear()
                data.update(read_back)
                ShpiArchiveSerializer().serialize(data, reexported, shpi_id, block)
                self.assertEqual(_png_pixels(exported), _png_pixels(reexported))
                with (
                    open(os.path.join(exported, 'car_colors.json')) as f1,
                    open(os.path.join(reexported, 'car_colors.json')) as f2,
                ):
                    self.assertEqual(json.load(f1), json.load(f2))
                children = {c['alias']: c['item']['data'] for c in original['children']}
                for child in read_back['children']:
                    if child['alias'] == '!PAL':
                        self.assertEqual(child['item']['data']['unk1'], b'\x03\x00')
                    if child['alias'].startswith('!'):
                        continue
                    special = lambda bitmap: [i if i >= 250 else -1 for i in bitmap]
                    self.assertEqual(
                        special(child['item']['data']['bitmap']), special(children[child['alias']]['bitmap'])
                    )
                return read_back
        finally:
            data.clear()
            data.update(original)

    def test_high_poly_textures_round_trip(self):
        read_back = self._round_trip(1)
        aliases = [c['alias'] for c in read_back['children']]
        self.assertEqual(aliases[0], '!PAL')
        self.assertEqual(aliases[-1], '!xxx')

    def test_low_poly_textures_round_trip_without_xxx(self):
        read_back = self._round_trip(3)
        self.assertNotIn('!xxx', [c['alias'] for c in read_back['children']])

    def test_quantizes_other_colors_to_250_deterministically(self):
        (shpi_id, block, _), _ = require_resource('test/samples/TSUPRA.CFM__children/1/item/data')
        with tempfile.TemporaryDirectory() as path:
            pixels = [(i % 256, i // 256 * 40, 7, 255) for i in range(400)]
            pixels += [(0x8C, 0xF8, 0x18, 255), (1, 2, 3, 0)]
            image = Image.new('RGBA', (len(pixels), 1))
            image.putdata(pixels)
            image.save(os.path.join(path, 'rsid.png'))
            with open(os.path.join(path, 'car_colors.json'), 'w') as f:
                json.dump({'tail_lights': {'texture_color': '#8cf818', 'textures': ['rsid'], 'off': '', 'on': ''}}, f)
            first = ShpiArchiveSerializer().deserialize([path], shpi_id, block)
            second = ShpiArchiveSerializer().deserialize([path], shpi_id, block)
        self.assertEqual(first, second)
        palette, rsid, xxx = [c['item']['data'] for c in first['children']]
        bitmap = rsid['bitmap']
        self.assertTrue(all(i < 250 for i in bitmap[:400]))
        self.assertEqual(bitmap[400:], [254, 255])
        self.assertEqual(palette['colors']['data'][254] >> 8, 0x8CF818)
        self.assertEqual(len(palette['colors']['data']), 256)
        self.assertEqual(set(c >> 8 for c in xxx['colors']['data']), {0})

    def test_whole_car_file_is_written_and_read(self):
        (file_id, block, data), _ = require_resource('test/samples/TSUPRA.CFM')
        (shpi_id, shpi_block, shpi_data), _ = require_resource('test/samples/TSUPRA.CFM__children/1/item/data')
        with tempfile.TemporaryDirectory() as path:
            ShpiArchiveSerializer().serialize(shpi_data, path, shpi_id, shpi_block)
            imported = ShpiArchiveSerializer().deserialize([path], shpi_id, shpi_block)
        copied = dict(data)
        copied['children'] = list(data['children'])
        copied['children'][1] = {**data['children'][1], 'item': {**data['children'][1]['item'], 'data': imported}}
        raw = block.write(copied)
        # ORIP picks the vertex format by the file name
        buffer = BytesIO(raw)
        buffer.name = 'TSUPRA.CFM'
        read_back = block.unpack(ReadContext(buffer, read_bytes_amount=len(raw)), read_bytes_amount=len(raw))
        textures = {c['alias'] for c in read_back['children'][1]['item']['data']['children']}
        materials = {m['file_name'] for m in read_back['children'][0]['item']['data']['materials'] if m['file_name']}
        self.assertTrue(materials <= textures, materials - textures)
