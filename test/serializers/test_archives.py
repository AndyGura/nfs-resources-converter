import unittest
import tempfile
import os
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import EacImage
from serializers.archives import ShpiArchiveSerializer


class TestShpiArchiveSerializer(unittest.TestCase):
    def test_duplicate_aliases_serialization(self):
        serializer = ShpiArchiveSerializer()
        serializer.patch_settings({'images__save_images_only': True})

        shpi_block = ShpiBlock()
        image_block = EacImage()

        shpi_data = shpi_block.new_data()
        # Create two images with equal aliases (4 characters)
        alias = "test"
        shpi_data['children'] = [
            {
                'alias': alias,
                'item': {
                    'choice_index': shpi_block.item_block.get_choice_index_by_class_name('EacImage'),
                    'data': image_block.new_data()
                },
                'pre_offset_payload': b'',
                'post_offset_payload': b''
            },
            {
                'alias': alias,
                'item': {
                    'choice_index': shpi_block.item_block.get_choice_index_by_class_name('EacImage'),
                    'data': image_block.new_data()
                },
                'pre_offset_payload': b'',
                'post_offset_payload': b''
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Serialize
            serializer.serialize(shpi_data, tmp_dir, block=shpi_block, id="test_shpi")
            
            # Check files saved
            files = os.listdir(tmp_dir)
            self.assertIn(f"{alias}.png", files)
            self.assertIn(f"{alias}0.png", files)
            
            # Deserialize
            deserialized_data = serializer.deserialize([tmp_dir], block=shpi_block, id="test_shpi")
            
            # Check aliases
            self.assertEqual(len(deserialized_data['children']), 2)
            self.assertEqual(deserialized_data['children'][0]['alias'], alias)
            self.assertEqual(deserialized_data['children'][1]['alias'], alias)

if __name__ == '__main__':
    unittest.main()
