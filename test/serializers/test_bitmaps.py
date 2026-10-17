import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from PIL import Image

from api.endpoints.resource_api import ResourceAPI
from api.endpoints.serialization_api import SerializationAPI
from library import require_file, require_resource
from library.changes_service import ChangesService
from library.loader import clear_file_cache
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import EacImage, EacPalette
from serializers.archives import ShpiArchiveSerializer
from serializers.bitmaps import ImageSerializer

SAMPLES = os.path.join(os.path.dirname(__file__), '..', 'samples')
GOLDEN_CORPUS = os.path.join(os.path.dirname(__file__), '..', 'golden_corpus')


def image_ids(name, data):
    return [
        join_id(name, 'children', str(i), 'item', 'data')
        for i, c in enumerate(data['children'])
        if isinstance(c['item']['data'], dict) and 'bitmap' in c['item']['data']
    ]


class TestImageImport(unittest.TestCase):
    """PNG import over an image keeps the image and its format, only its pixels change"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_ws_instance = ChangesService.ws_instance
        ChangesService.ws_instance = mock.Mock()
        ChangesService.clear()
        self.api = SerializationAPI(SimpleNamespace(resource_api=ResourceAPI(api=None), static_path=self.temp_dir.name))

    def tearDown(self):
        ChangesService.clear()
        ChangesService.ws_instance = self.original_ws_instance
        self.temp_dir.cleanup()

    def copy(self, path):
        target = os.path.join(self.temp_dir.name, os.path.basename(path))
        shutil.copy(path, target)
        clear_file_cache(target)
        return target

    def export_png(self, id):
        (_, block, data), _ = require_resource(id)
        return ImageSerializer().serialize(
            data, os.path.join(self.temp_dir.name, 'export', id.split('__')[1].replace('/', '_')), id=id, block=block
        )[0]

    def test_reimporting_own_exports_keeps_the_file_byte_exact(self):
        # TNFS 8Bit images on the !pal of the SHPI, with hot spots and screen positions
        path = self.copy(os.path.join(SAMPLES, 'VERTBST.FSH'))
        with open(path, 'rb') as f:
            original = f.read()
        name, block, data = require_file(path, lazy=False)
        ids = image_ids(name, data)
        self.assertEqual(len(ids), 9)
        for id in ids:
            self.api.deserialize_resource(id, [self.export_png(id)])
        self.assertEqual(block.pack(data, name=name), original)

    def test_edited_8bit_image_keeps_its_fields_and_palette(self):
        path = self.copy(os.path.join(SAMPLES, 'VERTBST.FSH'))
        name, block, data = require_file(path, lazy=False)
        id = image_ids(name, data)[0]
        (_, image_block, image), _ = require_resource(id)
        before = {k: v for k, v in image.items() if k != 'bitmap'}
        png = self.export_png(id)
        edited = Image.open(png).convert('RGBA')
        edited.putpixel((0, 0), (255, 0, 0, 255))
        edited = edited.resize((edited.width + 2, edited.height), Image.NEAREST)
        edited.save(png)
        self.api.deserialize_resource(id, [png])
        (_, _, image), _ = require_resource(id)
        self.assertEqual(image['resource_id'], '8Bit')
        self.assertEqual(image['width'], before['width'] + 2)
        for field in ['position', 'pivot', 'hot_spots', 'text', 'embedded_palette']:
            self.assertEqual(image[field], before[field], field)
        # the red pixel takes the nearest color of the palette
        palette = ImageSerializer()._found_palette_colors(image, image_block, id)
        self.assertEqual(image['bitmap'][0], ImageSerializer.to_palette_indexes([0xFF0000FF], palette)[0])
        # the file stays readable
        repacked = block.pack(data, name=name)
        with open(path, 'wb') as f:
            f.write(repacked)
        clear_file_cache(path)
        (_, _, reread), _ = require_resource(id)
        self.assertEqual(reread['width'], before['width'] + 2)
        self.assertEqual(reread['hot_spots'], before['hot_spots'])

    def test_car_light_entries_take_their_exact_color_only(self):
        # TNFS car textures: entries 250..254 are recolored by the game (light bar, tail lights)
        path = self.copy(os.path.join(GOLDEN_CORPUS, 'JEEP.CFM'))
        name, _, data = require_file(path, lazy=False)
        id = join_id(name, 'children', '1', 'item', 'data', 'children', '1', 'item', 'data')
        (_, image_block, image), _ = require_resource(id)
        palette = ImageSerializer()._found_palette_colors(image, image_block, id)
        tail_light = palette[254]
        near_tail_light = (tail_light & 0xFFFFFF00) ^ 0x01000000 | 0xFF
        png = self.export_png(id)
        edited = Image.open(png).convert('RGBA')
        edited.putpixel((0, 0), tuple(tail_light.to_bytes(4, 'big')))
        edited.putpixel((1, 0), tuple(near_tail_light.to_bytes(4, 'big')))
        edited.save(png)
        self.api.deserialize_resource(id, [png])
        (_, _, image), _ = require_resource(id)
        self.assertEqual(image['bitmap'][0], 254)
        self.assertNotIn(image['bitmap'][1], [250, 251, 252, 253, 254])

    def test_8bit_exports_are_indexed_and_reimport_as_they_are(self):
        path = self.copy(os.path.join(SAMPLES, 'VERTBST.FSH'))
        name, _, data = require_file(path, lazy=False)
        id = image_ids(name, data)[0]
        (_, image_block, image), _ = require_resource(id)
        before = list(image['bitmap'])
        png = self.export_png(id)
        with Image.open(png) as exported:
            self.assertEqual(exported.mode, 'P')
            self.assertEqual(
                exported.convert('RGBA').tobytes(), ImageSerializer().to_image(image, image_block, id).tobytes()
            )
        self.api.deserialize_resource(id, [png])
        (_, _, image), _ = require_resource(id)
        self.assertEqual(image['bitmap'], before)

    def test_indexed_png_edited_as_indexed_is_imported_by_its_colors(self):
        # an editor keeping the PNG indexed: a palette entry recolored, a pixel moved to another entry
        path = self.copy(os.path.join(SAMPLES, 'VERTBST.FSH'))
        name, _, data = require_file(path, lazy=False)
        id = image_ids(name, data)[0]
        (_, image_block, image), _ = require_resource(id)
        palette = ImageSerializer()._found_palette_colors(image, image_block, id)
        png = self.export_png(id)
        edited = Image.open(png)
        edited.load()
        entry = image['bitmap'][1]
        other = next(i for i in range(len(palette)) if palette[i] != palette[entry] and palette[i] & 0xFF == 0xFF)
        rgb = bytearray(edited.getpalette('RGB'))
        rgb[entry * 3 : entry * 3 + 3] = (palette[other] >> 8).to_bytes(3, 'big')
        edited.putpalette(bytes(rgb), 'RGB')
        edited.save(png)
        self.api.deserialize_resource(id, [png])
        (_, _, image), _ = require_resource(id)
        self.assertEqual(image['resource_id'], '8Bit')
        self.assertEqual(palette[image['bitmap'][1]], palette[other])
        self.assertNotIn(entry, image['bitmap'])

    def test_other_formats_are_kept_and_mipmaps_made_again(self):
        block = EacImage()
        png = os.path.join(self.temp_dir.name, 'new.png')
        Image.new('RGBA', (8, 4), (200, 100, 50, 255)).save(png)
        for color_format in [
            '16Bit_0565 color format bitmap',
            '24Bit color format bitmap',
            'DXT1 compressed bitmap',
            '32Bit color format bitmap',
        ]:
            current = block.new_data()
            current.update(resource_id='32Bit color format bitmap', width=4, height=4, bitmap=[0xFFFFFFFF] * 16)
            current['position'] = {'x': 12, 'y': 34}
            block.action_convert_to_rgba(current, color_format, 'use palette', id=None)
            block.action_generate_mipmaps(current)
            image = ImageSerializer()._with_pixels_of(current, png, block, None)
            self.assertEqual(image['resource_id'], color_format)
            self.assertEqual((image['width'], image['height']), (8, 4))
            self.assertEqual(image['position'], {'x': 12, 'y': 34})
            self.assertEqual(len(image['mipmaps']), 4 * 2 + 2 * 1 + 1)
        # 4Bit keeps the alpha channel
        current = block.new_data({'resource_id': '4Bit'})
        Image.new('RGBA', (2, 1), (255, 255, 255, 7)).save(png)
        image = ImageSerializer()._with_pixels_of(current, png, block, None)
        self.assertEqual(image['bitmap'], [[0xFFFFFF07, 0xFFFFFF07]])

    def test_unchanged_mipmaps_are_kept(self):
        block = EacImage()
        current = block.new_data()
        current.update(resource_id='32Bit color format bitmap', width=2, height=2, bitmap=[0xFF0000FF] * 4)
        current['mipmaps'] = [0x00FF00FF]  # not what generating them would give
        png = os.path.join(self.temp_dir.name, 'same.png')
        Image.new('RGBA', (2, 2), (255, 0, 0, 255)).save(png)
        image = ImageSerializer()._with_pixels_of(current, png, block, None)
        self.assertEqual(image['mipmaps'], [0x00FF00FF])

    def test_to_palette_indexes(self):
        palette = [0xFF0000FF, 0x00FF00FF, 0xFF0000FF, 0x00000000, 0x0000FEFF]
        self.assertEqual(
            ImageSerializer.to_palette_indexes([0xFF0000FF, 0x10F010FF, 0x12345600, 0x0000FFFF], palette),
            [0, 1, 3, 4],
        )
        # an exact-only entry is not the nearest color of anything
        self.assertEqual(ImageSerializer.to_palette_indexes([0x0000FFFF, 0x0000FEFF], palette, [4]), [0, 4])

    def export_folder(self, id):
        (_, block, data), _ = require_resource(id)
        serializer = ShpiArchiveSerializer()
        serializer.patch_settings(serializer.ui_serialization()['reversible_settings_patch'])
        folder = os.path.join(self.temp_dir.name, 'folder')
        serializer.serialize(data, folder, id=id, block=block)
        return folder

    def test_folder_import_merges_by_name(self):
        path = self.copy(os.path.join(SAMPLES, 'VERTBST.FSH'))
        with open(path, 'rb') as f:
            original = f.read()
        name, block, data = require_file(path, lazy=False)
        aliases = [c['alias'] for c in data['children']]
        folder = self.export_folder(name)
        # exported as is: the file stays byte-exact
        result = self.api.deserialize_resource(name, [folder])
        self.assertEqual(result['report'], '9 replaced, 0 added')
        self.assertEqual(block.pack(data, name=name), original)

        # edited: one image painted, one file gone, a new image and other files added
        images = [
            (i, c['alias'], c['item']['data']) for i, c in enumerate(data['children']) if 'bitmap' in c['item']['data']
        ]
        (painted_index, painted_alias, painted), (kept_index, kept_alias, kept) = images[0], images[1]
        before_painted = {k: v for k, v in painted.items() if k != 'bitmap'}
        before_kept_bitmap = list(kept['bitmap'])
        png = os.path.join(folder, painted_alias + '.png')
        edited = Image.open(png).convert('RGBA')
        edited.putpixel((0, 0), (255, 0, 0, 255))
        edited.save(png)
        os.remove(os.path.join(folder, kept_alias + '.png'))
        Image.new('RGBA', (3, 2), (1, 2, 3, 255)).save(os.path.join(folder, 'new image.png'))
        Image.new('RGBA', (2, 2)).save(os.path.join(folder, 'spherical.png'))
        with open(os.path.join(folder, 'skipped.txt'), 'w') as f:
            f.write('x')
        result = self.api.deserialize_resource(name, [folder])
        self.assertEqual(result['report'], '8 replaced, 1 added. Ignored: skipped.txt, spherical.png')
        self.assertEqual([c['alias'] for c in data['children']], aliases + ['new '])
        # the palette item and the image without a file are kept, the painted one keeps its format and fields
        self.assertEqual(data['children'][kept_index]['item']['data']['bitmap'], before_kept_bitmap)
        painted = data['children'][painted_index]['item']['data']
        self.assertEqual({k: v for k, v in painted.items() if k != 'bitmap'}, before_painted)
        new_image = data['children'][-1]['item']['data']
        self.assertEqual((new_image['resource_id'], new_image['width']), ('32Bit color format bitmap', 3))
        # the new item reaches the GUI as an insert, not as a new children list
        changes = ChangesService.ws_instance.on_append_changes.call_args[0][0][0]['changes']
        inserts = [c for c in changes if c['op'] == 'array_insert']
        self.assertEqual([(c['id'], c['index']) for c in inserts], [(join_id(name, 'children'), len(aliases))])
        self.assertFalse(any(c['id'] == join_id(name, 'children') and c['op'] == 'set' for c in changes))

    def test_export_file_names(self):
        image, palette = EacImage(), EacPalette()
        items = [
            ('ga00', {}, image),
            ('!pal', {}, palette),
            ('ga00', {}, image),
            ('a/b<', {}, image),
            ('!PAL', {}, palette),
            # one file with "ga00" on Windows / macOS file systems
            ('GA00', {}, image),
        ]
        self.assertEqual(
            ShpiArchiveSerializer.export_file_names(items, False), {0: 'ga00', 2: 'ga000', 3: 'a_b--lt--', 5: 'GA001'}
        )
        self.assertEqual(
            ShpiArchiveSerializer.export_file_names(items, True),
            {0: 'ga00', 1: '!pal', 2: 'ga000', 3: 'a_b--lt--', 4: '!PAL0', 5: 'GA001'},
        )

    def test_folder_import_without_a_loaded_shpi_makes_new_images(self):
        folder = os.path.join(self.temp_dir.name, 'folder')
        os.makedirs(folder)
        Image.new('RGBA', (3, 2), (1, 2, 3, 255)).save(os.path.join(folder, 'abcd.png'))
        with open(os.path.join(folder, 'positions.txt'), 'w') as f:
            f.write('x')
        new_shpi = ShpiArchiveSerializer().deserialize([folder], id=None, block=ShpiBlock())
        self.assertEqual([c['alias'] for c in new_shpi['children']], ['abcd'])
        image = new_shpi['children'][0]['item']['data']
        self.assertEqual((image['resource_id'], image['width'], image['height']), ('32Bit color format bitmap', 3, 2))


class TestNewImagesFromFiles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.api = SerializationAPI(api=None)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_files_become_32bit_entries(self):
        path = os.path.join(self.temp_dir.name, 'VERTBST.FSH')
        shutil.copy(os.path.join(SAMPLES, 'VERTBST.FSH'), path)
        clear_file_cache(path)
        name, block, data = require_file(path)
        children_count = len(data['children'])
        files = [os.path.join(self.temp_dir.name, x) for x in ['grün_wheel.png', 'ab.jpg', 'notes.txt']]
        Image.new('RGBA', (3, 2), (255, 0, 0, 128)).save(files[0])
        Image.new('RGB', (4, 4), (0, 255, 0)).save(files[1])
        with open(files[2], 'w') as f:
            f.write('not an image')
        result = self.api.new_images_from_files(name, files)
        self.assertEqual(result['skipped'], [['notes.txt', 'not an image']])
        self.assertEqual([x['alias'] for x in result['items']], ['gr_n', 'ab'])
        image = result['items'][0]['item']['data']
        self.assertEqual((image['resource_id'], image['width'], image['height']), ('32Bit color format bitmap', 3, 2))
        self.assertEqual(image['bitmap'][0], 0xFF000080)
        self.assertEqual(len(data['children']), children_count, 'the archive is not changed')

    def test_archive_without_images(self):
        path = os.path.join(self.temp_dir.name, 'JEEP.CFM')
        shutil.copy(os.path.join(GOLDEN_CORPUS, 'JEEP.CFM'), path)
        clear_file_cache(path)
        name, _, _ = require_file(path)
        image = os.path.join(self.temp_dir.name, 'a.png')
        Image.new('RGBA', (1, 1)).save(image)
        with self.assertRaisesRegex(Exception, 'cannot hold images'):
            self.api.new_images_from_files(name, [image])


if __name__ == '__main__':
    unittest.main()


class TestNewImageDefaults(unittest.TestCase):
    def test_new_image_is_32bit_and_new_font_atlas_4bit(self):
        from resources.eac.fonts import FfnFont

        image = EacImage().new_data()
        self.assertEqual((image['resource_id'], image['width'], image['height']), ('32Bit color format bitmap', 1, 1))
        self.assertEqual(FfnFont().new_data()['bitmap']['resource_id'], '4Bit')

    def test_archive_image_stats(self):
        path = os.path.join(SAMPLES, 'VERTBST.FSH')
        name, _, data = require_file(path)
        stats = ResourceAPI(api=None).archive_image_stats(join_id(name, 'children', '0', 'item', 'data'))
        self.assertEqual(stats, {'images': 8, 'color_models': {'8Bit': 8}, 'with_mipmaps': 0})

    def test_palette_usage(self):
        name, _, data = require_file(os.path.join(SAMPLES, 'VERTBST.FSH'), lazy=False)
        palette_index = next(i for i, c in enumerate(data['children']) if c['alias'].lower() == '!pal')
        used = ResourceAPI(api=None).palette_usage(join_id(name, 'children', str(palette_index), 'item', 'data'))
        expected = set()
        for c in data['children']:
            if c['item']['data'].get('resource_id') == '8Bit':
                expected.update(c['item']['data']['bitmap'])
        self.assertEqual(used, sorted(expected))

    def test_unloaded_entries_carry_their_kind(self):
        from serializers.misc.json_utils import convert_bytes

        name, _, data = require_file(os.path.join(GOLDEN_CORPUS, 'JEEP.CFM'), lazy=True)
        clear_file_cache(name)
        name, _, data = require_file(os.path.join(GOLDEN_CORPUS, 'JEEP.CFM'), lazy=True)
        kinds = [convert_bytes(c).get('__kind__') for c in data['children']]
        self.assertEqual(kinds, ['OripGeometry', 'ShpiBlock', 'OripGeometry', 'ShpiBlock'])
        clear_file_cache(name)


class TestMipmapExport(unittest.TestCase):
    def test_every_level_of_a_non_square_image_is_exported(self):
        block = EacImage()
        image = block.new_data()
        image.update(width=4, height=8, bitmap=[0xFF0000FF] * 32)
        block.action_generate_mipmaps(image)
        with tempfile.TemporaryDirectory() as tmp:
            serializer = ImageSerializer()
            serializer.patch_settings({'images__save_mipmaps': True})
            files = serializer.serialize(image, os.path.join(tmp, 'img'), id='img', block=block)
            sizes = [Image.open(f).size for f in files[1:]]
        self.assertEqual(sizes, [(2, 4), (1, 2), (1, 1)])


class TestIndexedExport(unittest.TestCase):
    """8Bit images are saved as indexed PNGs which decode to the RGBA of `to_image`"""

    @staticmethod
    def rgba(path):
        with Image.open(path) as image:
            return image.mode, image.convert('RGBA').tobytes()

    def serialize(self, image, palette_colors=None, block=None, **settings):
        serializer = ImageSerializer()
        serializer.patch_settings(settings)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ImageSerializer, '_get_palette_colors', return_value=palette_colors or []):
                files = serializer.serialize(image, os.path.join(tmp, 'img'), id='img', block=block or EacImage())
            result = []
            for f in files:
                with open(f, 'rb') as file:
                    result.append((self.rgba(f), file.read()))
            return result

    def image_8bit(self, width, height, bitmap):
        image = EacImage().new_data()
        image.update(resource_id='8Bit', width=width, height=height, bitmap=bitmap)
        return image

    def test_pixels_keep_their_indexes_and_decode_to_the_same_rgba(self):
        import random

        rng = random.Random(7)
        # alpha 0 with color under it, partial alpha, duplicate colors, a palette shorter than the indexes
        palette = [rng.getrandbits(32) for _ in range(200)]
        palette[5] = palette[9] = 0x10203040
        palette[6] = 0x12345600
        image = self.image_8bit(16, 8, [rng.randrange(256) for _ in range(128)] + [5, 9])
        [((mode, rgba), png)] = self.serialize(image, palette)
        self.assertEqual(mode, 'P')
        self.assertEqual(rgba, ImageSerializer().to_image(image, palette_colors=palette).tobytes())
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'a.png')
            with open(path, 'wb') as f:
                f.write(png)
            with Image.open(path) as saved:
                self.assertEqual(list(saved.tobytes()), image['bitmap'][:128])
        # the same image gives the same bytes
        self.assertEqual(self.serialize(image, palette)[0][1], png)

    def test_transparency_is_written_only_where_the_palette_has_it(self):
        opaque = [0xFF0000FF, 0x00FF00FF, 0x0000FFFF]
        image = self.image_8bit(3, 1, [0, 1, 2])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'a.png')
            ImageSerializer.save_png(ImageSerializer().to_png_image(image, palette_colors=opaque), path)
            with Image.open(path) as saved:
                self.assertEqual(saved.mode, 'P')
                self.assertNotIn('transparency', saved.info)
            ImageSerializer.save_png(
                ImageSerializer().to_png_image(image, palette_colors=[0xFF000000, 0x00FF0080, 0x0000FFFF]), path
            )
            with Image.open(path) as saved:
                self.assertEqual(saved.info['transparency'], b'\x00\x80')
                self.assertEqual(
                    list(saved.convert('RGBA').getdata()), [(255, 0, 0, 0), (0, 255, 0, 128), (0, 0, 255, 255)]
                )

    def test_8bit_image_without_palette_keeps_the_index_in_alpha(self):
        image = self.image_8bit(2, 1, [0, 200])
        serializer = ImageSerializer()
        palette = serializer._get_palette_colors(image, EacImage(), 'img')
        [((mode, rgba), _)] = self.serialize(image, palette)
        self.assertEqual(mode, 'P')
        self.assertEqual(rgba, bytes([255, 255, 255, 0, 255, 255, 255, 200]))

    def test_other_formats_stay_rgba(self):
        block = EacImage()
        image = block.new_data()
        image.update(resource_id='32Bit color format bitmap', width=2, height=1, bitmap=[0xFF000080, 0x00FF00FF])
        [((mode, rgba), _)] = self.serialize(image)
        self.assertEqual((mode, rgba), ('RGBA', bytes([255, 0, 0, 128, 0, 255, 0, 255])))
        image = block.new_data({'resource_id': '4Bit'})
        image.update(width=2, height=1, bitmap=[[0xFFFFFF07, 0xFFFFFF0F]])
        [((mode, rgba), _)] = self.serialize(image)
        self.assertEqual((mode, rgba), ('RGBA', bytes([255, 255, 255, 7, 255, 255, 255, 15])))

    def test_8bit_mipmaps_are_indexed(self):
        palette = [0xFF0000FF, 0x00FF0000, 0x0000FF80, 0x000000FF]
        image = self.image_8bit(2, 2, [0, 1, 2, 3])
        image['mipmaps'] = [2]
        files = self.serialize(image, palette, images__save_mipmaps=True)
        self.assertEqual([mode for (mode, _), _ in files], ['P', 'P'])
        self.assertEqual(files[1][0][1], bytes([0, 0, 255, 128]))
