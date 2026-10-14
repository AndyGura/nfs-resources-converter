import unittest

from library.block_checks import check_compatibility, collect_target_games
from library.context import CheckContext
from library.loader import require_file
from library.read_blocks.misc.compatibility import Compatibility
from resources.eac.archives import EacCompressedBlock


class TestTargetGames(unittest.TestCase):
    def test_files(self):
        eac = ['tnfs', 'nfs2', 'nfs2_se', 'nfs3', 'nfs4', 'nfs5', 'nfs6']
        expected = {
            'AL1.FSH': eac,
            'AL1.TRI': ['tnfs'],
            'CARDATA.VIV': ['nfs2', 'nfs2_se'],
            'DIABLOSW.BNK': ['tnfs'],
            'GEOMETRY.BIN': ['nfsu', 'nfsu2', 'nfsmw'],
            'GT1.FRD': ['nfs4'],
            'NFSU_B36.BUN': ['nfsu', 'nfsu2', 'nfsmw'],
            'REPLAY3.RPL': ['tnfs'],
            'TSUPRA.CFM': ['tnfs'],
            'nfs3_f355.viv': ['nfs3'],
            # compressed: the games of the algorithm and of the uncompressed data
            '356b.crp': ['nfs5'],  # RefPack
            'AL1.QFS': ['tnfs', 'nfs2', 'nfs2_se', 'nfs3', 'nfs4', 'nfs5'],  # QFS3
            'AL2.QFS': ['tnfs', 'nfs2', 'nfs2_se', 'nfs3', 'nfs4', 'nfs5'],  # QFS2
            'AL3.QFS': ['tnfs', 'nfs2', 'nfs2_se', 'nfs3', 'nfs4', 'nfs5'],  # RefPack
            'LDIABL.PBS': ['tnfs'],  # QFS3
        }
        for file_name, games in expected.items():
            with self.subTest(file_name):
                name, block, data = require_file(f'test/samples/{file_name}')
                self.assertEqual(collect_target_games(block, data, name), games)

    def test_compressed_block_intersects_with_content(self):
        name, block, data = require_file('test/samples/LDIABL.PBS')
        self.assertEqual(block.get_target_games(data, CheckContext(name=name, data=data, block=block)), ['tnfs'])

    def test_compressed_bytes(self):
        block = EacCompressedBlock()
        bytes_index = len(block.possible_blocks) - 1
        for flags in [0x10, 0x30, 0x46]:
            data = {'choice_index': bytes_index, 'data': b'\x00' * 8, 'compression_flags': flags}
            self.assertEqual(block.get_target_games(data, None), ['tnfs', 'nfs2', 'nfs2_se', 'nfs3', 'nfs4', 'nfs5'])

    def test_compressed_compatibility(self):
        # the compression says nothing, the uncompressed data decides
        name, block, data = require_file('test/samples/AL2.QFS')
        for game in collect_target_games(block, data, name):
            self.assertEqual(
                check_compatibility(block, data, name, game), {'game': game, 'state': 'unknown', 'problems': []}
            )
        name, block, data = require_file('test/samples/LDIABL.PBS')
        self.assertEqual(
            check_compatibility(block, data, name, 'tnfs'), {'game': 'tnfs', 'state': 'compatible', 'problems': []}
        )
