import os
import shutil
import struct
import tempfile
import unittest

from library import require_file
from resources.eac.archives.shpi_block import ShpiBlock
from resources.eac.bitmaps import EacImage, EacPalette


class TestShpiBlock(unittest.TestCase):
    def test_convert_to_8bit_quantizes_all_images_onto_one_shared_palette_and_roundtrips(self):
        block = ShpiBlock()
        data = block.new_data()
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        for alias, width, height, fill in [('img0', 4, 4, 0x60), ('img1', 4, 4, 0xC0)]:
            img_data = EacImage().new_data()
            img_data['resource_id'] = '32Bit color format bitmap'
            img_data['width'] = width
            img_data['height'] = height
            img_data['bitmap'] = [
                (x * fill << 24) | (y * fill << 16) | 0xFF for y in range(height) for x in range(width)
            ]
            data['children'].append(
                {
                    'post_offset_payload': b'',
                    'alias': alias,
                    'item': {'choice_index': image_choice, 'data': img_data},
                }
            )
        # a fully-shaped `read_data`, as read from a file
        data = block.unpack_from_bytes(block.pack(data, name='test'))

        block.action_convert_to_8bit(
            data,
            name='test',
            palette_name='!pal',
            palette_type='32Bit color format palette',
            num_colors=256,
            id='test_id',
        )

        # added at the end: the indices of the other items stay
        self.assertEqual(data['children'][-1]['alias'], '!pal')
        self.assertEqual(len(data['children']), 3)
        palette = data['children'][-1]['item']['data']['colors']['data']
        for child in data['children'][:-1]:
            self.assertEqual(child['item']['data']['resource_id'], '8Bit')
            self.assertTrue(all(0 <= idx < len(palette) for idx in child['item']['data']['bitmap']))

        packed = block.pack(data, name='test')
        reread = block.unpack_from_bytes(packed)
        self.assertEqual(reread['children'][-1]['item']['data']['colors']['data'], palette)

    def test_convert_to_8bit_with_0565_palette_roundtrips(self):
        block = ShpiBlock()
        data = block.new_data()
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        img_data = EacImage().new_data()
        img_data['resource_id'] = '32Bit color format bitmap'
        img_data['width'] = 2
        img_data['height'] = 2
        img_data['bitmap'] = [(x * 0x60 << 24) | (y * 0x60 << 16) | 0xFF for y in range(2) for x in range(2)]
        data['children'].append(
            {
                'post_offset_payload': b'',
                'alias': 'img0',
                'item': {'choice_index': image_choice, 'data': img_data},
            }
        )
        # a fully-shaped `read_data`, as read from a file
        data = block.unpack_from_bytes(block.pack(data, name='test'))

        block.action_convert_to_8bit(
            data,
            name='test',
            palette_name='!pal',
            palette_type='16Bit_0565 color format palette',
            num_colors=256,
            id='test_id',
        )

        packed = block.pack(data, name='test')
        reread = block.unpack_from_bytes(packed)
        self.assertEqual(reread['children'][-1]['item']['data']['resource_id'], '16Bit_0565 color format palette')

    def test_convert_to_8bit_keeps_items_and_drops_own_palettes(self):
        from copy import deepcopy

        import numpy as np

        from library.utils.id import join_id
        from serializers.bitmaps import ImageSerializer

        # the action runs on the loaded file: the palettes of the images are looked up in it
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'VERTBST.FSH')
            shutil.copy('test/samples/VERTBST.FSH', path)
            (name, block, data) = require_file(path, lazy=False)
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        image_block = block.item_block.possible_blocks[image_choice]
        aliases = [c['alias'] for c in data['children']]
        palette_index = next(i for i, c in enumerate(data['children']) if c['alias'].lower() == '!pal')
        image_indexes = [i for i, c in enumerate(data['children']) if c['item']['choice_index'] == image_choice]
        # an image with its own palette, which wins over !pal: reversed colors
        own = data['children'][image_indexes[0]]['item']['data']
        own['embedded_palette'] = deepcopy(data['children'][palette_index]['item']['data'])
        own['embedded_palette']['colors']['data'].reverse()
        # an item which is not an image
        data['children'].append(
            {'post_offset_payload': b'', 'alias': 'raw ', 'item': {'choice_index': block.bytes_choice, 'data': b'abc'}}
        )
        images = ImageSerializer()

        def look(index):
            return np.asarray(
                images.to_image(
                    data['children'][index]['item']['data'],
                    block=image_block,
                    id=join_id(name, 'children', str(index), 'item', 'data'),
                )
            ).astype(int)

        hot_spots = [data['children'][i]['item']['data']['hot_spots'] for i in image_indexes]
        before = [look(i) for i in image_indexes]
        block.action_convert_to_8bit(
            data, name=name, palette_name='!PAL', palette_type='24Bit color format palette', num_colors=256, id=name
        )
        # the palette of that name (any case) is replaced in place, the other items stay
        self.assertEqual([c['alias'] for c in data['children']], aliases + ['raw '])
        self.assertEqual(data['children'][-1]['item']['data'], b'abc')
        for i, previous, spots in zip(image_indexes, before, hot_spots):
            image = data['children'][i]['item']['data']
            self.assertEqual(image['resource_id'], '8Bit')
            self.assertIsNone(image['embedded_palette'])
            self.assertEqual(image['hot_spots'], spots)
            visible = previous[..., 3] > 0
            self.assertLess(np.abs(previous[..., :3] - look(i)[..., :3])[visible].mean(), 8)

    def test_convert_to_8bit_replaces_the_palette_the_images_use(self):
        from resources.eac.utils import _get_palette_from_shpi

        block = ShpiBlock()
        data = block.new_data()
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        palette_choice = block.item_block.get_choice_index_by_class_name('EacPalette')
        image = EacImage().new_data()
        image.update(resource_id='32Bit color format bitmap', width=2, height=1, bitmap=[0xFF0000FF, 0x00FF00FF])
        for alias, choice, item in [
            ('img0', image_choice, image),
            ('!PAL', palette_choice, EacPalette().new_data()),
            ('!pal', palette_choice, EacPalette().new_data()),
        ]:
            data['children'].append(
                {'post_offset_payload': b'', 'alias': alias, 'item': {'choice_index': choice, 'data': item}}
            )
        data = block.unpack_from_bytes(block.pack(data, name='test'))
        old_upper = data['children'][1]['item']['data']
        # TNFS FAM horizons have both names: the lookup takes !pal
        block.action_convert_to_8bit(
            data, name='test', palette_name='!PAL', palette_type='24Bit color format palette', num_colors=256, id='test'
        )
        self.assertEqual([c['alias'] for c in data['children']], ['img0', '!PAL', '!pal'])
        self.assertIs(data['children'][1]['item']['data'], old_upper)
        _, palette = _get_palette_from_shpi(block, data)
        self.assertIs(palette, data['children'][2]['item']['data'])
        self.assertEqual(len({palette['colors']['data'][i] for i in data['children'][0]['item']['data']['bitmap']}), 2)

    def test_convert_to_8bit_palette_name_is_one_the_images_find(self):
        block = ShpiBlock()
        data = block.new_data()
        image = EacImage().new_data()
        image.update(resource_id='32Bit color format bitmap', width=1, height=1, bitmap=[0xFF0000FF])
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        data['children'].append(
            {'post_offset_payload': b'', 'alias': '0000', 'item': {'choice_index': image_choice, 'data': image}}
        )
        data = block.unpack_from_bytes(block.pack(data, name='test'))
        args = dict(name='test', palette_type='24Bit color format palette', num_colors=256, id='test')
        with self.assertRaisesRegex(ValueError, 'by its name'):
            block.action_convert_to_8bit(data, palette_name='mypa', **args)
        with self.assertRaisesRegex(ValueError, 'already named "0000"'):
            block.action_convert_to_8bit(data, palette_name='0000', **args)

    def test_convert_to_8bit_makes_mipmaps_again(self):
        block = ShpiBlock()
        data = block.new_data()
        image = EacImage().new_data()
        image.update(resource_id='32Bit color format bitmap', width=4, height=4, bitmap=[0xFF0000FF] * 16)
        EacImage().action_generate_mipmaps(image)
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        data['children'].append(
            {'post_offset_payload': b'', 'alias': 'img0', 'item': {'choice_index': image_choice, 'data': image}}
        )
        data = block.unpack_from_bytes(block.pack(data, name='test'))
        block.action_convert_to_8bit(
            data, name='test', palette_name='!pal', palette_type='24Bit color format palette', num_colors=256, id='test'
        )
        image = data['children'][0]['item']['data']
        self.assertEqual(len(image['mipmaps']), 2 * 2 + 1)
        self.assertEqual(set(image['mipmaps']), set(image['bitmap']))

    def test_convert_to_8bit_keeps_tnfs_car_light_entries(self):
        import numpy as np

        from library.utils.id import join_id
        from serializers.bitmaps import ImageSerializer

        # the action runs on the loaded file: the palettes of the images are looked up in it
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'JEEP.CFM')
            shutil.copy('test/golden_corpus/JEEP.CFM', path)
            (name, block, cfm) = require_file(path, lazy=False)
        shpi_id = name + '__children/1/item/data'
        shpi_block = block.item_block.possible_blocks[cfm['children'][1]['item']['choice_index']]
        shpi = cfm['children'][1]['item']['data']
        image_choice = shpi_block.item_block.get_choice_index_by_class_name('EacImage')
        image_block = shpi_block.item_block.possible_blocks[image_choice]
        textures = [
            i
            for i, c in enumerate(shpi['children'])
            if c['item']['choice_index'] == image_choice and c['alias'] != '!xxx'
        ]
        xxx = next(c for c in shpi['children'] if c['alias'] == '!xxx')['item']['data']

        def look(i):
            data = shpi['children'][i]['item']['data']
            return np.asarray(
                ImageSerializer().to_image(
                    data, block=image_block, id=join_id(shpi_id, 'children', str(i), 'item', 'data')
                )
            )

        before = {i: look(i) for i in textures}
        lights = {i: [x for x in shpi['children'][i]['item']['data']['bitmap'] if 250 <= x <= 254] for i in textures}
        shpi_block.action_convert_to_8bit(
            shpi,
            name=shpi_id,
            palette_name='!PAL',
            palette_type='same as the current palette',
            num_colors=256,
            id=shpi_id,
        )
        for i in textures:
            # the car's colors fit the 250 entries: nothing changes on screen, the light pixels keep their entries
            self.assertTrue(np.array_equal(before[i], look(i)))
            self.assertEqual([x for x in shpi['children'][i]['item']['data']['bitmap'] if 250 <= x <= 254], lights[i])
        self.assertIs(next(c for c in shpi['children'] if c['alias'] == '!xxx')['item']['data'], xxx)

    def test_convert_to_8bit_keeps_partial_alpha_with_32bit_palette(self):
        block = ShpiBlock()
        data = block.new_data()
        image = EacImage().new_data()
        glow = [0xFFFF0000 | a for a in (0, 64, 128, 255)]
        image.update(width=4, height=1, bitmap=glow)
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        data['children'].append(
            {'post_offset_payload': b'', 'alias': 'glo1', 'item': {'choice_index': image_choice, 'data': image}}
        )
        data = block.unpack_from_bytes(block.pack(data, name='test'))
        block.action_convert_to_8bit(
            data,
            name='test',
            palette_name='!pal',
            palette_type='same as the current palette',
            num_colors=256,
            id='test',
        )
        palette = data['children'][-1]['item']['data']
        # no palette yet and partial alpha: a 32-bit palette
        self.assertEqual(palette['resource_id'], '32Bit color format palette')
        colors = palette['colors']['data']
        self.assertEqual([colors[i] & 0xFF for i in data['children'][0]['item']['data']['bitmap']], [0, 64, 128, 255])

    def test_fsh_should_remain_the_same(self):
        (name, block, fsh) = require_file('test/samples/VERTBST.FSH', lazy=False)
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_fsh_should_reconstruct_offsets(self):
        (name, block, fsh) = require_file('test/samples/VERTBST.FSH', lazy=False)
        fsh['num_items'] = 0
        fsh['items_descr'] = []
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')


class TestWwwwBlock(unittest.TestCase):
    def test_cfm_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/TSUPRA.CFM', lazy=False)
        output = block.pack(res, name=name)
        with open('test/samples/TSUPRA.CFM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_fam_with_gaps_between_items_should_remain_the_same(self):
        # nested WWWW archives here have alignment gaps before items, item offsets must point after them
        (name, block, res) = require_file('test/golden_corpus/AL1_001.FAM')
        output = block.pack(res, name=name)
        with open('test/golden_corpus/AL1_001.FAM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')


def write_out_of_order_bnk(dir_path: str) -> str:
    """DIABLOSW.BNK (indices 0x1, 0x2, 0x3, 0x20 at ascending offsets) with its offset table permuted so that the
    entries are not stored in index order, like in TNFS collision banks: file order becomes 0x1, 0x3, 0x20, 0x2.
    0x2 is the gear entry (random range 250, priority 30), 0x20 the one with priority 80"""
    with open('test/samples/DIABLOSW.BNK', 'rb') as f:
        original = f.read()
    table = [0] * 128
    table[0x1], table[0x2], table[0x3], table[0x20] = 0x200, 0x2D8, 0x248, 0x290
    path = os.path.join(dir_path, 'OUTORDER.BNK')
    with open(path, 'wb') as f:
        f.write(struct.pack('<128I', *table) + original[512:])
    return path


def write_shared_wave_data_bnk(dir_path: str) -> str:
    """DIABLOSW.BNK with the EACS header of entry 0x3 replaced by the one of entry 0x1, so both play the same wave
    data, like the indices of one wav in TNFS collision banks. The wave data of 0x3 stays in the file, unreferenced"""
    with open('test/samples/DIABLOSW.BNK', 'rb') as f:
        data = bytearray(f.read())
    data[0x290 + 40 : 0x290 + 72] = data[0x200 + 40 : 0x200 + 72]
    path = os.path.join(dir_path, 'SHARED.BNK')
    with open(path, 'wb') as f:
        f.write(data)
    return path


class TestSoundBankBlock(unittest.TestCase):
    def test_bnk_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/DIABLOSW.BNK')
        output = block.pack(res, name=name)
        with open('test/samples/DIABLOSW.BNK', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_bnk_entry_settings(self):
        (name, block, res) = require_file('test/samples/DIABLOSW.BNK')
        gear = res['items'][3]
        self.assertEqual(gear['eacs_header_offset'], 0x2D8 + 40)
        self.assertEqual(gear['random_range'], 250)
        self.assertEqual(gear['priority'], 30)
        self.assertEqual(gear['bend_range_semitones'], 0)
        self.assertEqual(gear['pan'], 64)
        self.assertEqual(gear['volume'], 127)
        self.assertEqual(res['items'][0]['bend_range_semitones'], 12)

    def test_bnk_item_indices_follow_file_order(self):
        (name, block, res) = require_file('test/samples/DIABLOSW.BNK')
        self.assertEqual(block.item_indices(res), [0x1, 0x2, 0x3, 0x20])
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_out_of_order_bnk(tmp_dir)
            (name, block, res) = require_file(path)
            with open(path, 'rb') as f:
                original = f.read()
            self.assertEqual(block.pack(res, name=name), original)
        indices = block.item_indices(res)
        self.assertEqual(indices, [0x1, 0x3, 0x20, 0x2])
        for index, item in zip(indices, res['items']):
            self.assertEqual(item['eacs_header_offset'], res['items_descr'][index] + 40)

    def test_bnk_with_shared_wave_data_should_remain_the_same(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_shared_wave_data_bnk(tmp_dir)
            (name, block, res) = require_file(path)
            with open(path, 'rb') as f:
                original = f.read()
            self.assertEqual(res['children'][2]['wave_data'], res['children'][0]['wave_data'])
            self.assertEqual(block.pack(res, name=name), original)


class TestBigfBlock(unittest.TestCase):
    def test_bigf_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/CARDATA.VIV', lazy=False)
        output = block.pack(res, name=name)
        with open('test/samples/CARDATA.VIV', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_bigf_tga_item_takes_only_its_own_length(self):
        (name, block, res) = require_file('test/samples/nfs3_f355.viv')
        with open('test/samples/nfs3_f355.viv', 'rb') as bdata:
            original = bdata.read()
        # directory entry: offset, length (big endian), null-terminated name, starting at byte 16
        pos = 16
        entries = {}
        for _ in range(res['num_items']):
            offset = int.from_bytes(original[pos : pos + 4], 'big')
            length = int.from_bytes(original[pos + 4 : pos + 8], 'big')
            end = original.index(0, pos + 8)
            entries[original[pos + 8 : end].decode()] = (offset, length)
            pos = end + 1
        offset, length = entries['car00.tga']
        child = next(x for x in res['children'] if x['alias'] == 'car00.tga')
        self.assertEqual(
            block.item_block.possible_blocks[child['item']['choice_index']].__class__.__name__, 'TargaImage'
        )
        self.assertEqual(child['item']['data'], original[offset : offset + length])

    def test_bigf_length_field_without_padding(self):
        from resources.eac.archives import BigfBlock

        block = BigfBlock()
        data = block.new_data()
        bytes_choice = block.item_block.get_choice_index_by_class_name('BytesBlock')
        data['children'] = [
            {
                'alias': alias,
                'item': {'choice_index': bytes_choice, 'data': payload},
                'post_offset_payload': post,
            }
            for alias, payload, post in [('a.bin', b'12345', bytes(3)), ('b.bin', b'678', b'')]
        ]
        # header 16 + 2 * (8 + 6), items 5 + 3, padding 3
        size = 16 + 28 + 8 + 3
        packed = block.pack(data)
        self.assertEqual(len(packed), size)
        self.assertEqual(int.from_bytes(packed[4:8], 'big'), size)
        # NFS6 car.viv: length field doesn't count padding between items. Kept as is on write
        nfs6_style = packed[:4] + (size - 3).to_bytes(4, 'big') + packed[8:]
        reread = block.unpack_from_bytes(nfs6_style)
        self.assertEqual(reread['length'], size - 3)
        self.assertEqual(block.pack(reread), nfs6_style)


def build_ea_sound_bank() -> bytes:
    """BNKl version 2 with 3 slots: 16-bit PCM stereo sound with a mono EA-XA layer, an empty slot, a one-shot"""

    def patch(tags: list) -> bytes:
        res = b'PT\x00\x00'
        for tag, value, length in tags:
            res += bytes([tag]) if value is None else bytes([tag, length]) + value.to_bytes(length, 'big')
        res += b'\xff'
        return res + bytes((-len(res)) % 4)

    pcm_stereo = struct.pack('<8h', 1, -1, 2, -2, 3, -3, 4, -4)
    ea_xa = bytes([0x0C]) + bytes([0x12] * 14)
    pcm_mono = struct.pack('<3h', 100, 200, 300)
    header_length = 12 + 3 * 4 + 3 * 64
    data_offsets = [header_length, header_length + len(pcm_stereo), header_length + len(pcm_stereo) + len(ea_xa)]
    patches = [
        patch(
            [
                (0x0E, 90, 1),
                (0xFD, None, 0),
                (0x85, 4, 2),
                (0x82, 2, 1),
                (0x86, 1, 1),
                (0x87, 3, 1),
                (0x88, data_offsets[0], 4),
                (0x8A, 0, 4),
                (0xFE, None, 0),
                (0x0E, 30, 1),
                (0xFD, None, 0),
                (0x83, 7, 1),
                (0x85, 28, 1),
                (0x86, 0, 0),
                (0x88, data_offsets[1], 4),
                (0x8A, 0, 4),
            ]
        ),
        patch([(0x11, 200, 1), (0xFD, None, 0), (0x84, 11025, 2), (0x85, 3, 1), (0x88, data_offsets[2], 4)]),
    ]
    patches = [x + bytes(64 - len(x)) for x in patches]
    # offsets are relative to the table slot: slot 0 at 12, slot 2 at 20, patches from 24
    table = struct.pack('<3I', 24 - 12, 0, 24 + 64 - 20)
    header = b'BNKl' + struct.pack('<HHI', 2, 3, header_length)
    return header + table + patches[0] + patches[1] + bytes(64) + pcm_stereo + ea_xa + pcm_mono


class TestEaSoundBank(unittest.TestCase):
    def test_bank_should_remain_the_same(self):
        from resources.eac.archives import EaSoundBank

        original = build_ea_sound_bank()
        block = EaSoundBank()
        data = block.unpack_from_bytes(original)
        self.assertEqual(block.item_indices(data), [0, 2])
        self.assertEqual(block.pack(data), original)
        self.assertEqual(block.estimate_packed_size(data), len(original))

    def test_patch_layers(self):
        from resources.eac.archives import EaSoundBank
        from resources.eac.audios import EaSoundPatch

        block = EaSoundBank()
        data = block.unpack_from_bytes(build_ea_sound_bank())
        layers = EaSoundPatch.layers(data['items'][0])
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0]['volume'], 90)
        self.assertEqual(layers[0]['channels'], 2)
        self.assertEqual((layers[0]['loop_start'], layers[0]['loop_end']), (1, 3))
        self.assertEqual(layers[1]['codec'], 7)
        self.assertEqual(layers[1]['loop_start'], 0)
        self.assertEqual(block.wave_data(data, layers[0])[:4], struct.pack('<2h', 1, -1))

    def test_tag_value_is_written_in_place(self):
        from resources.eac.archives import EaSoundBank

        block = EaSoundBank()
        data = block.unpack_from_bytes(build_ea_sound_bank())
        volume = next(x for x in data['items'][0]['tags'] if x['tag'] == 'volume')
        volume['value'] = 127
        reread = block.unpack_from_bytes(block.pack(data))
        self.assertEqual(reread['items'][0]['tags'][0]['value'], 127)
        volume['value'] = 0x1234
        with self.assertRaises(OverflowError):
            block.pack(data)

    def test_serialized_wavs(self):
        import json
        import wave
        from resources.eac.archives import EaSoundBank
        from serializers import EaSoundBankSerializer

        block = EaSoundBank()
        data = block.unpack_from_bytes(build_ea_sound_bank())
        with tempfile.TemporaryDirectory() as tmp_dir:
            EaSoundBankSerializer().serialize(data, tmp_dir, id='test.BNK', block=block)
            self.assertEqual(
                sorted(os.listdir(tmp_dir)),
                ['0x0.meta.json', '0x0.wav', '0x0_layer_1.meta.json', '0x0_layer_1.wav', '0x2.meta.json', '0x2.wav'],
            )
            with wave.open(os.path.join(tmp_dir, '0x0.wav')) as wf:
                self.assertEqual((wf.getnchannels(), wf.getframerate(), wf.getnframes()), (2, 22050, 4))
            with wave.open(os.path.join(tmp_dir, '0x0_layer_1.wav')) as wf:
                # coefficients 0, shift 12: every nibble 1 / 2 becomes a sample 1 / 2
                self.assertEqual(struct.unpack('<28h', wf.readframes(28)), (1, 2) * 14)
            with wave.open(os.path.join(tmp_dir, '0x2.wav')) as wf:
                self.assertEqual((wf.getframerate(), wf.readframes(3)), (11025, struct.pack('<3h', 100, 200, 300)))
            with open(os.path.join(tmp_dir, '0x0.meta.json')) as f:
                meta = json.load(f)
            self.assertTrue(meta['loop'])
            self.assertAlmostEqual(meta['loop_start_time_ms'], 1000 / 22050)
            self.assertAlmostEqual(meta['loop_end_time_ms'], 3000 / 22050)
            self.assertEqual(meta['volume'], 90)
            with open(os.path.join(tmp_dir, '0x2.meta.json')) as f:
                meta = json.load(f)
            self.assertFalse(meta['loop'])
            self.assertEqual(meta['random_detune_range'], 200)

    def test_nfs3_car_viv_banks(self):
        (name, block, res) = require_file('test/samples/nfs3_f355.viv')
        with open('test/samples/nfs3_f355.viv', 'rb') as f:
            original = f.read()
        banks = {
            x['alias']: x
            for x in res['children']
            if block.item_block.possible_blocks[x['item']['choice_index']].__class__.__name__ == 'EaSoundBank'
        }
        self.assertEqual(sorted(banks), ['car.bnk', 'ocar.bnk', 'ocard.bnk', 'scar.bnk'])
        bank_block = next(x for x in block.item_block.possible_blocks if x.__class__.__name__ == 'EaSoundBank')
        bank = banks['car.bnk']['item']['data']
        self.assertEqual(bank_block.item_indices(bank), [0, 1, 2, 3])
        packed = bank_block.pack(bank)
        self.assertIn(packed, original)


class TestShpiHeapOrder(unittest.TestCase):
    def test_item_data_keeps_its_order(self):
        block = ShpiBlock()
        data = block.new_data()
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        for alias, color in [('img0', 0xFF0000FF), ('img1', 0x00FF00FF)]:
            image = EacImage().new_data()
            image.update(width=1, height=1, bitmap=[color])
            data['children'].append(
                {'post_offset_payload': b'', 'alias': alias, 'item': {'choice_index': image_choice, 'data': image}}
            )
        packed = block.pack(data, name='test')
        # the same SHPI with the data of img1 stored first (TNFS SE menus store !pal last)
        heap = 16 + 2 * 8
        item0, item1 = packed[heap : heap + 20], packed[heap + 20 :]
        swapped = (
            packed[:16]
            + b'img0'
            + struct.pack('<I', heap + len(item1))
            + b'img1'
            + struct.pack('<I', heap)
            + item1
            + item0
        )
        read = block.unpack_from_bytes(swapped)
        self.assertEqual([c['alias'] for c in read['children']], ['img0', 'img1'])
        self.assertEqual(block.pack(read, name='test'), swapped)
        # an added item: directory order
        read['children'].append(read['children'][0])
        reread = block.unpack_from_bytes(block.pack(read, name='test'))
        self.assertEqual(
            [c['item']['data']['bitmap'] for c in reread['children']], [[0xFF0000FF], [0x00FF00FF], [0xFF0000FF]]
        )
