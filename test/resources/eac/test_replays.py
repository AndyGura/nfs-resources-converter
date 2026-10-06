import unittest

from library import require_file


class TestTnfsReplay(unittest.TestCase):
    def test_replay_is_parsed(self):
        (name, block, data) = require_file('test/samples/REPLAY3.RPL')
        self.assertEqual('TnfsReplay', type(block).__name__)
        self.assertEqual('cl1', data['setup']['track_name'])
        self.assertEqual(1, data['setup']['game_mode'])
        self.assertEqual(2, len(data['setup']['players']))
        self.assertEqual('Mom?', data['setup']['players'][0]['name'])
        self.assertEqual(0, data['recording']['player_frames'][0][0]['car']['car_index'])
        self.assertEqual(8, data['highlights']['clip_count'])
        self.assertEqual(9, len(data['stats']))
        self.assertEqual(22588, data['stats'][2]['finish_time'])

    def test_replay_can_be_reconstructed(self):
        (name, block, data) = require_file('test/samples/REPLAY3.RPL')
        output = block.pack(data, name=name)
        with open('test/samples/REPLAY3.RPL', 'rb') as bdata:
            original = bdata.read()
        self.assertEqual(100374, len(original))
        self.assertEqual(len(original), len(output))
        self.assertEqual(original, output)
