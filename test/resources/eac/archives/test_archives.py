import unittest

from library import require_file
from resources.eac.archives.shpi_block import ShpiBlock
from resources.eac.bitmaps import EacImage


class TestShpiBlock(unittest.TestCase):

    def test_convert_to_8bit_quantizes_all_images_onto_one_shared_palette_and_roundtrips(self):
        block = ShpiBlock()
        data = block.new_data()
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        for (alias, width, height, fill) in [('img0', 4, 4, 0x60), ('img1', 4, 4, 0xC0)]:
            img_data = EacImage().new_data()
            img_data['resource_id'] = '32Bit color format bitmap'
            img_data['width'] = width
            img_data['height'] = height
            img_data['bitmap'] = [(x * fill << 24) | (y * fill << 16) | 0xFF for y in range(height)
                                  for x in range(width)]
            data['children'].append({
                'pre_offset_payload': b'', 'post_offset_payload': b'', 'alias': alias,
                'item': {'choice_index': image_choice, 'data': img_data},
            })
        # `action_convert_to_8bit` serializes children to PNGs first, so it needs a fully-shaped
        # `read_data` - go through a real pack/unpack cycle rather than hand-building one.
        data = block.unpack_from_bytes(block.pack(data, name='test'))

        block.action_convert_to_8bit(data, name='test', palette_name='!pal',
                                     palette_type='32Bit color format palette', num_colors=256, id='test_id')

        self.assertEqual(data['children'][0]['alias'], '!pal')
        self.assertEqual(len(data['children']), 3)
        palette = data['children'][0]['item']['data']['colors']['data']
        for child in data['children'][1:]:
            self.assertEqual(child['item']['data']['resource_id'], '8Bit')
            self.assertTrue(all(0 <= idx < len(palette) for idx in child['item']['data']['bitmap']))

        packed = block.pack(data, name='test')
        reread = block.unpack_from_bytes(packed)
        self.assertEqual(reread['children'][0]['item']['data']['colors']['data'], palette)

    def test_convert_to_8bit_with_0565_palette_roundtrips(self):
        block = ShpiBlock()
        data = block.new_data()
        image_choice = block.item_block.get_choice_index_by_class_name('EacImage')
        img_data = EacImage().new_data()
        img_data['resource_id'] = '32Bit color format bitmap'
        img_data['width'] = 2
        img_data['height'] = 2
        img_data['bitmap'] = [(x * 0x60 << 24) | (y * 0x60 << 16) | 0xFF for y in range(2) for x in range(2)]
        data['children'].append({
            'pre_offset_payload': b'', 'post_offset_payload': b'', 'alias': 'img0',
            'item': {'choice_index': image_choice, 'data': img_data},
        })
        # `action_convert_to_8bit` serializes children to PNGs first, so it needs a fully-shaped
        # `read_data` - go through a real pack/unpack cycle rather than hand-building one.
        data = block.unpack_from_bytes(block.pack(data, name='test'))

        block.action_convert_to_8bit(data, name='test', palette_name='!pal',
                                     palette_type='16Bit_0565 color format palette', num_colors=256, id='test_id')

        packed = block.pack(data, name='test')
        reread = block.unpack_from_bytes(packed)
        self.assertEqual(reread['children'][0]['item']['data']['resource_id'], '16Bit_0565 color format palette')

    def test_fsh_should_remain_the_same(self):
        (name, block, fsh) = require_file('test/samples/VERTBST.FSH')
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_fsh_should_reconstruct_offsets(self):
        (name, block, fsh) = require_file('test/samples/VERTBST.FSH')
        fsh['num_items'] = 0
        fsh['items_descr'] = []
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestWwwwBlock(unittest.TestCase):

    def test_cfm_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/TSUPRA.CFM')
        output = block.pack(res, name=name)
        with open('test/samples/TSUPRA.CFM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestSoundBankBlock(unittest.TestCase):

    def test_bnk_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/DIABLOSW.BNK')
        output = block.pack(res, name=name)
        with open('test/samples/DIABLOSW.BNK', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestBigfBlock(unittest.TestCase):

    def test_bigf_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/CARDATA.VIV')
        output = block.pack(res, name=name)
        with open('test/samples/CARDATA.VIV', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
