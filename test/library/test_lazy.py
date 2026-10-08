import copy
import json
import math
import os
import pickle
import random
import shutil
import tempfile
import unittest
from unittest import mock

from library import require_file
from library.lazy import (
    FileChangedError,
    LazyDict,
    SourceClosedError,
    is_loaded,
    load_all,
    stats,
    transient,
)
from library.loader import clear_file_cache, probe_block_class
from resources.eac.archives import BigfBlock, ShpiBlock, WwwwBlock
from resources.eac.archives.compressed_block import EacCompressedBlock

SAMPLE_DIRS = ['test/samples', 'test/golden_corpus']


def _read(path, lazy):
    clear_file_cache(path)
    return require_file(path, lazy=lazy)


def _deep_equal(a, b) -> bool:
    """`==` treating NaN as equal to NaN (geometries have NaN vertex tangents)"""
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a.keys()) == list(b.keys()) and all(_deep_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    res = a == b
    return bool(res.all()) if hasattr(res, 'all') else bool(res)


class TestLazyDict(unittest.TestCase):
    PATH = 'test/golden_corpus/GRAPHICS.FSH'

    def setUp(self):
        (self.name, self.block, self.data) = _read(self.PATH, lazy=True)
        stats['parses'] = 0

    def tearDown(self):
        clear_file_cache(self.PATH)

    def test_indexing_and_seeded_values_do_not_parse(self):
        child = self.data['children'][1]
        self.assertIsInstance(child, dict)
        self.assertIsInstance(child, LazyDict)
        self.assertFalse(is_loaded(child))
        self.assertIsInstance(child['alias'], str)
        self.assertEqual(child['pre_offset_payload'], b'')
        self.assertIn('item', child)
        self.assertNotIn('foo', child)
        self.assertEqual(len(child), 4)
        self.assertTrue(child)
        self.assertIsNone(child.get('foo'))
        self.assertEqual(stats['parses'], 0)
        self.assertFalse(is_loaded(child))

    def test_access_parses_only_this_entry_once(self):
        child = self.data['children'][1]
        image = child['item']['data']
        self.assertEqual(stats['parses'], 1)
        self.assertTrue(is_loaded(child))
        self.assertIs(child['item']['data'], image)
        self.assertEqual(stats['parses'], 1)
        self.assertEqual(list(child.keys()), ['item', 'alias', 'pre_offset_payload', 'post_offset_payload'])
        self.assertFalse(any(is_loaded(c) for i, c in enumerate(self.data['children']) if i != 1))

    def test_whole_dict_readers_load_first(self):
        children = self.data['children']
        readers = [
            list,
            dict,
            lambda x: {**x},
            lambda x: x | {},
            lambda x: {} | x,
            lambda x: list(x.items()),
            lambda x: list(x.values()),
            lambda x: json.loads(json.dumps(x, default=lambda b: len(b))),
            copy.copy,
            lambda x: pickle.loads(pickle.dumps(x)),
            repr,
        ]
        for i, reader in enumerate(readers):
            child = children[i]
            res = reader(child)
            self.assertTrue(is_loaded(child), f'reader {i}')
            if isinstance(res, dict):
                self.assertIn('item', res, f'reader {i}')
                self.assertEqual(len(res), 4, f'reader {i}')

    def test_deepcopy_and_equality_of_unloaded_do_not_parse(self):
        before = copy.deepcopy(self.data)
        self.assertTrue(before == self.data)
        self.assertEqual(stats['parses'], 0)
        self.assertFalse(is_loaded(before['children'][0]))
        # change one entry: comparison sees it
        self.data['children'][0]['item']['data']['width'] += 1
        self.assertFalse(before == self.data)
        loaded = copy.deepcopy(self.data['children'][0])
        self.assertIs(type(loaded), dict)
        self.assertEqual(loaded, self.data['children'][0])

    def test_writes_load_first(self):
        child = self.data['children'][2]
        child['alias'] = 'abcd'
        self.assertTrue(is_loaded(child))
        self.assertIn('item', dict(child))
        self.assertEqual(child['alias'], 'abcd')
        other = self.data['children'][3]
        other.clear()
        self.assertTrue(is_loaded(other))
        self.assertEqual(stats['parses'], 1)

    def test_transient_drops_parsed_content(self):
        child = self.data['children'][4]
        with transient(child) as c:
            self.assertIn('data', c['item'])
        self.assertFalse(is_loaded(child))
        self.assertEqual(dict.__len__(child), 2)

    def test_untouched_and_partially_loaded_pack_is_exact(self):
        with open(self.PATH, 'rb') as f:
            original = f.read()
        self.assertEqual(self.block.pack(self.data, name=self.name), original)
        self.data['children'][5]['item']['data']
        self.assertEqual(self.block.pack(self.data, name=self.name), original)
        self.assertEqual(stats['parses'], 1)

    def test_load_all_equals_eager_read(self):
        (_, _, eager) = _read(self.PATH, lazy=False)
        self.assertNotIsInstance(eager['children'][0], LazyDict)
        (_, _, lazy) = _read(self.PATH, lazy=True)
        self.assertTrue(_deep_equal(load_all(lazy), eager))

    def test_eager_request_loads_cached_lazy_file(self):
        (_, _, data) = require_file(self.PATH, lazy=False)
        self.assertIs(data, self.data)
        self.assertTrue(all(is_loaded(c) for c in data['children']))

    def test_lazy_by_default_and_config_switch(self):
        clear_file_cache(self.PATH)
        (_, _, data) = require_file(self.PATH)
        self.assertFalse(is_loaded(data['children'][0]))
        clear_file_cache(self.PATH)
        with mock.patch.dict(os.environ, {'NFS_RESOURCES_CONVERTER_GENERAL_LAZY_LOADING': 'false'}):
            (_, _, data) = require_file(self.PATH)
        self.assertNotIsInstance(data['children'][0], LazyDict)


class TestLazySources(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp_dir, 'VERTBST.FSH')
        shutil.copy('test/samples/VERTBST.FSH', self.path)

    def tearDown(self):
        clear_file_cache(self.path)
        shutil.rmtree(self.tmp_dir)

    def test_changed_file_is_not_read(self):
        (_, _, data) = _read(self.path, lazy=True)
        with open(self.path, 'r+b') as f:
            f.seek(0, os.SEEK_END)
            f.write(b'\0')
        with self.assertRaises(FileChangedError):
            data['children'][0]['item']

    def test_closed_file_is_not_read(self):
        (name, block, data) = _read(self.path, lazy=True)
        clear_file_cache(self.path)
        with self.assertRaises(SourceClosedError):
            data['children'][0]['item']
        with self.assertRaises(SourceClosedError):
            block.pack(data, name=name)

    def test_nested_parts_from_compressed_data(self):
        # BIGF entries are QFS-compressed SHPI: inner entries are lazy over decompressed bytes
        path = 'test/samples/nfs3_f355.viv'
        (name, block, data) = _read(path, lazy=True)
        stats['parses'] = 0
        # aliases are seeded: only dash.qfs is parsed
        qfs = next(c for c in data['children'] if c['alias'] == 'dash.qfs')
        self.assertIsInstance(block.item_block.possible_blocks[qfs['item']['choice_index']], EacCompressedBlock)
        self.assertEqual(stats['parses'], 1)
        shpi = qfs['item']['data']['data']
        self.assertFalse(is_loaded(shpi['children'][0]))
        shpi['children'][0]['item']
        self.assertEqual(stats['parses'], 2)
        with open(path, 'rb') as f:
            self.assertEqual(block.pack(data, name=name), f.read())
        clear_file_cache(path)


class TestLazyEquivalence(unittest.TestCase):
    """Lazy read gives the same data as eager read, and untouched lazy archives are written back as they are"""

    @staticmethod
    def _sample_files():
        """Samples with lazy parts: archives, chunk bundles and compressed files"""
        from resources.blackbox.maps.nfsu import NfsuChunkBundle

        for directory in SAMPLE_DIRS:
            for file_name in sorted(os.listdir(directory)):
                path = os.path.join(directory, file_name)
                if not os.path.isfile(path):
                    continue
                with open(path, 'rb') as f:
                    try:
                        block_class = probe_block_class(f, path, os.path.getsize(path))
                    except NotImplementedError:
                        continue
                if issubclass(block_class, (ShpiBlock, WwwwBlock, BigfBlock, EacCompressedBlock, NfsuChunkBundle)):
                    yield path

    def test_lazy_read_equals_eager_read(self):
        checked_archives = 0
        for path in self._sample_files():
            with self.subTest(path=path):
                (name, block, eager) = _read(path, lazy=False)
                stats['parses'] = 0
                (name, block, lazy) = _read(path, lazy=True)
                self.assertEqual(stats['parses'], 0)
                with open(path, 'rb') as f:
                    original = f.read()
                is_archive = isinstance(block, (ShpiBlock, WwwwBlock, BigfBlock)) or (
                    isinstance(block, EacCompressedBlock)
                    and isinstance(block.possible_blocks[eager['choice_index']], (ShpiBlock, WwwwBlock, BigfBlock))
                )
                if is_archive or path.upper().endswith('.BUN'):
                    checked_archives += 1
                    self.assertEqual(block.pack(lazy, name=name), original)
                self.assertEqual(stats['parses'], 0)
                self.assertTrue(_deep_equal(load_all(lazy), eager))
                clear_file_cache(path)
        self.assertGreater(checked_archives, 10)

    def test_entries_load_independently_in_any_order(self):
        path = 'test/golden_corpus/GRAPHICS.FSH'
        (_, _, eager) = _read(path, lazy=False)
        (_, _, lazy) = _read(path, lazy=True)
        order = list(range(len(lazy['children'])))
        random.Random(1).shuffle(order)
        for i in order:
            stats['parses'] = 0
            self.assertTrue(_deep_equal(lazy['children'][i]['item'], eager['children'][i]['item']))
            self.assertEqual(stats['parses'], 1)
        self.assertTrue(_deep_equal(lazy, eager))
        clear_file_cache(path)

    def test_bundle_chunks_are_seeded_with_chunk_id(self):
        path = 'test/samples/NFSU_B36.BUN'
        (_, _, eager) = _read(path, lazy=False)
        (_, _, lazy) = _read(path, lazy=True)
        stats['parses'] = 0
        for e, l in zip(eager['chunks'], lazy['chunks']):
            id_field = 'chunk_id' if 'chunk_id' in e['data'] else 'header'
            self.assertEqual(l['data'][id_field], e['data'][id_field])
            self.assertIsNone(l['data'].get('not_a_field'))
        self.assertEqual(stats['parses'], 0)
        clear_file_cache(path)


if __name__ == '__main__':
    unittest.main()
