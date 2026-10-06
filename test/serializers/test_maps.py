import unittest
from unittest.mock import patch

from serializers.maps import _require_nfs4_texture_archive


class TestRequireNfs4TextureArchive(unittest.TestCase):
    def test_uses_own_archive_when_present(self):
        with patch('library.require_resource') as mock_require:
            mock_require.return_value = 'result'
            result = _require_nfs4_texture_archive('games/nfs4/Data/Tracks/Coastal/Trn.frd')
            self.assertEqual(result, 'result')
            mock_require.assert_called_once_with('games/nfs4/Data/Tracks/Coastal/Trn0.QFS__data')

    def test_falls_back_to_forward_track_archive_when_own_is_missing(self):
        # GT1/GT2/Park's reverse tracks ("Trn.FRD") have no dedicated "Trn0.QFS" - they reuse the
        # forward track's "Tr0.QFS" instead.
        def side_effect(id):
            if id == 'games/nfs4/Data/Tracks/GT1/Trn0.QFS__data':
                raise FileNotFoundError(2, 'No such file or directory')
            return 'result'

        with patch('library.require_resource', side_effect=side_effect) as mock_require:
            result = _require_nfs4_texture_archive('games/nfs4/Data/Tracks/GT1/Trn.frd')
            self.assertEqual(result, 'result')
            mock_require.assert_any_call('games/nfs4/Data/Tracks/GT1/Trn0.QFS__data')
            mock_require.assert_called_with('games/nfs4/Data/Tracks/GT1/Tr0.QFS__data')

    def test_forward_track_has_no_fallback(self):
        with patch(
            'library.require_resource', side_effect=FileNotFoundError(2, 'No such file or directory')
        ) as mock_require:
            with self.assertRaises(FileNotFoundError):
                _require_nfs4_texture_archive('games/nfs4/Data/Tracks/GT1/Tr.frd')
            mock_require.assert_called_once_with('games/nfs4/Data/Tracks/GT1/Tr0.QFS__data')

    def test_raises_when_no_candidate_exists(self):
        with patch('library.require_resource', side_effect=FileNotFoundError(2, 'No such file or directory')):
            with self.assertRaises(FileNotFoundError):
                _require_nfs4_texture_archive('games/nfs4/Data/Tracks/GT1/Trn.frd')


class TestTrackPropRotation(unittest.TestCase):
    def test_exported_quaternion_should_rotate_like_game_one(self):
        import math
        import random

        from serializers.maps import _quaternion_to_export_axes, _rotate_by_quaternion, _to_export_axes

        rnd = random.Random(1)
        for _ in range(100):
            q = [rnd.uniform(-1, 1) for _ in range(4)]
            length = math.sqrt(sum(c * c for c in q))
            q = tuple(c / length for c in q)
            v = [rnd.uniform(-5, 5) for _ in range(3)]
            w, x, y, z = _quaternion_to_export_axes(q)
            expected = _to_export_axes(_rotate_by_quaternion(q, v))
            actual = _rotate_by_quaternion((x, y, z, w), _to_export_axes(v))
            for a, b in zip(expected, actual):
                self.assertAlmostEqual(a, b)


class TestEacTrackSerializers(unittest.TestCase):
    def _serialize(self, path, out_dir, **settings):
        import shutil

        from library import require_file

        (name, block, data) = require_file(path)
        serializer = block.serializer_class()()
        serializer.patch_settings(
            {
                'geometry__save_obj': True,
                'geometry__save_blend': False,
                'geometry__export_to_gg_web_engine': False,
                'maps__save_terrain_collisions': False,
                'maps__save_invisible_wall_collisions': False,
                **settings,
            }
        )
        shutil.rmtree(out_dir, ignore_errors=True)
        return serializer.serialize(data, out_dir + '/', name, block)

    def test_frd_props_should_be_exported_as_dummies(self):
        import json
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'tr00')
            files = self._serialize(
                'test/golden_corpus/TR00.FRD', out, maps__save_as_chunked=True, maps__add_props_to_obj=False
            )
            # every model in its own folder, like other single models of the converter
            self.assertIn(os.path.join(out, 'props', 'xobj_0_0', 'geometry.obj'), files)
            with open(os.path.join(out, 'props', 'xobj_0_0', 'material.mtl')) as f:
                self.assertIn('map_Kd ../../textures/', f.read())
            with open(os.path.join(out, 'terrain_chunk_75_extra.json')) as f:
                dummies = json.load(f)['dummies']
            windmill = next(d for d in dummies if d['properties']['model_ref_id'] == 'xobj_302_0')
            self.assertEqual(windmill['properties']['type'], 'model')
            animation = json.loads(windmill['properties']['animation'])
            self.assertEqual(animation['delay'], 6)
            self.assertEqual(animation['frame_duration'], 6 / 64)
            self.assertEqual(len(animation['frames']), 17)
            self.assertEqual(animation['frames'][0]['position'], windmill['position'])
            # COL objects of NFS3 don't have known textures
            col_dummies = []
            for name in os.listdir(out):
                if name.endswith('_extra.json'):
                    with open(os.path.join(out, name)) as f:
                        col_dummies += [
                            d for d in json.load(f)['dummies'] if d['properties']['model_ref_id'].startswith('col_')
                        ]
            self.assertEqual(len(col_dummies), 2)
            self.assertTrue(all(d['properties']['is_unknown'] for d in col_dummies))

    def test_trk_props_should_be_baked_into_map(self):
        import json
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'tr02')
            self._serialize(
                'test/golden_corpus/TR02.TRK', out, maps__save_as_chunked=False, maps__add_props_to_obj=True
            )
            with open(os.path.join(out, 'map.obj')) as f:
                object_names = [line[2:].strip() for line in f if line.startswith('o ')]
            # props of the TRK blocks and of the COL file
            self.assertEqual(len({n.split('__')[0] for n in object_names if n.startswith('prop_')}), 333 + 176 + 82)
            with open(os.path.join(out, 'map_extra.json')) as f:
                objects = json.load(f)['objects']
            # the animated boat of the COL file
            self.assertTrue(objects)
            self.assertTrue(all(json.loads(o['animation'])['delay'] == 44 for o in objects.values()))

    def test_nfs4_frd_extra_objects_should_be_exported_as_dummies(self):
        import json
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'gt1')
            self._serialize(
                'test/golden_corpus/NFS4_GT1.FRD', out, maps__save_as_chunked=True, maps__add_props_to_obj=False
            )
            dummies = []
            for name in os.listdir(out):
                if name.endswith('_extra.json'):
                    with open(os.path.join(out, name)) as f:
                        dummies += json.load(f)['dummies']
            # 350 tree billboards of the blocks and 95 physics props of the global chunk
            self.assertEqual(len(dummies), 445)
            models = {d['properties']['model_ref_id'] for d in dummies}
            # the same models are exported once
            self.assertLess(len(models), 445)
            self.assertEqual(sorted(os.listdir(os.path.join(out, 'props'))), sorted(models))
            # physics props are rotated by their transform matrix
            self.assertTrue(any(d['quaternion'] != [1, 0, 0, 0] for d in dummies))
