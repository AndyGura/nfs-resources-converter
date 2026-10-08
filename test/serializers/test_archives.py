import json
import unittest
import tempfile
import os
from unittest import mock

import serializers
from library import require_file, require_resource
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import EacImage
from serializers.archives import ShpiArchiveSerializer, SoundBankSerializer


class TestShpiArchiveSerializer(unittest.TestCase):
    def test_duplicate_aliases_serialization(self):
        serializer = ShpiArchiveSerializer()
        serializer.patch_settings(
            {
                'images__save_image_positions': False,
                'images__save_palettes': False,
                'images__save_mipmaps': False,
                'images__save_embedded_palette': False,
                'images__save_texts': False,
            }
        )

        shpi_block = ShpiBlock()
        image_block = EacImage()

        shpi_data = shpi_block.new_data()
        # Create two images with equal aliases (4 characters)
        alias = 'test'
        shpi_data['children'] = [
            {
                'alias': alias,
                'item': {
                    'choice_index': shpi_block.item_block.get_choice_index_by_class_name('EacImage'),
                    'data': image_block.new_data(),
                },
                'pre_offset_payload': b'',
                'post_offset_payload': b'',
            },
            {
                'alias': alias,
                'item': {
                    'choice_index': shpi_block.item_block.get_choice_index_by_class_name('EacImage'),
                    'data': image_block.new_data(),
                },
                'pre_offset_payload': b'',
                'post_offset_payload': b'',
            },
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Serialize
            serializer.serialize(shpi_data, tmp_dir, block=shpi_block, id='test_shpi')

            # Check files saved
            files = os.listdir(tmp_dir)
            self.assertIn(f'{alias}.png', files)
            self.assertIn(f'{alias}0.png', files)

            # Deserialize
            deserialized_data = serializer.deserialize([tmp_dir], block=shpi_block, id='test_shpi')

            # Check aliases
            self.assertEqual(len(deserialized_data['children']), 2)
            self.assertEqual(deserialized_data['children'][0]['alias'], alias)
            self.assertEqual(deserialized_data['children'][1]['alias'], alias)

    def test_item_ids_are_built_from_indexes(self):
        name, block, data = require_file('test/samples/VERTBST.FSH')
        serializer = ShpiArchiveSerializer()
        serializer.patch_settings({'images__save_image_positions': False, 'images__save_palettes': True})
        real_get_serializer = serializers.get_serializer
        ids = []

        def recording_get_serializer(*args, **kwargs):
            item_serializer = real_get_serializer(*args, **kwargs)
            real_serialize = item_serializer.serialize

            def serialize(*a, **kw):
                ids.append(kw['id'])
                return real_serialize(*a, **kw)

            item_serializer.serialize = serialize
            return item_serializer

        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            mock.patch.object(serializers, 'get_serializer', recording_get_serializer),
        ):
            serializer.serialize(data, tmp_dir, block=block, id=name)
        self.assertEqual(ids, [f'{name}__children/{i}/item/data' for i in range(len(data['children']))])
        for i, item_id in enumerate(ids):
            (_, _, item_data), _ = require_resource(item_id)
            self.assertIs(item_data, data['children'][i]['item']['data'])


class TestSoundBankSerializer(unittest.TestCase):
    def test_meta_has_loop_flag_and_bank_entry_settings(self):
        (name, block, res) = require_file('test/samples/DIABLOSW.BNK')
        with tempfile.TemporaryDirectory() as tmp_dir:
            SoundBankSerializer().serialize(res, tmp_dir, id=name, block=block)
            with open(os.path.join(tmp_dir, 'engine_on.meta.json')) as f:
                engine_on = json.load(f)
            with open(os.path.join(tmp_dir, 'gear.meta.json')) as f:
                gear = json.load(f)
        self.assertTrue(engine_on['loop'])
        self.assertEqual(engine_on['bend_range_semitones'], 12)
        self.assertEqual(engine_on['priority'], 50)
        self.assertFalse(gear['loop'])
        self.assertEqual(gear['loop_end_time_ms'], -0.0625)
        self.assertEqual(gear['bend_range_semitones'], 0)
        self.assertEqual(gear['random_range'], 250)
        self.assertEqual(gear['priority'], 30)
        self.assertEqual(gear['volume'], 127)
        self.assertEqual(gear['pan'], 64)
        self.assertEqual(gear['unknown_0x16'], 0)


if __name__ == '__main__':
    unittest.main()
