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
