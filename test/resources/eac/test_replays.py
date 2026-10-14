import unittest

from library import require_file
from resources.eac.replays import (
    TnfsReplay,
    TnfsReplaySetup,
    TnfsReplayPlayer,
    TnfsReplayHighlights,
    TnfsReplayRecording,
    TnfsReplayPlayerFrame,
    TnfsReplayOtherFrame,
    TnfsReplayCarState,
    TnfsReplayCollisionData,
    TnfsReplayWorldState,
    TnfsReplayWorldKeyframe,
    TnfsReplayStats,
)


class TestTnfsReplay(unittest.TestCase):
    def test_replay_is_parsed(self):
        (name, block, data) = require_file('test/samples/REPLAY3.RPL')
        self.assertEqual('TnfsReplay', type(block).__name__)
        setup = data['setup']
        self.assertEqual('cl1', setup['track_name'])
        self.assertEqual(1, setup['track_id'])
        self.assertEqual(0, setup['track_segment'])
        self.assertEqual(1, setup['race_type'])
        self.assertEqual(0, setup['is_linked_game'])
        self.assertEqual(
            (2, 1, 1, 9, 6),
            (
                setup['racer_count'],
                setup['player_count'],
                setup['cop_count'],
                setup['car_count'],
                setup['traffic_count'],
            ),
        )
        self.assertEqual(834889156, setup['random_seed'])
        self.assertEqual(2, len(setup['players']))
        player = setup['players'][0]
        self.assertEqual('Mom?', player['name'])
        self.assertEqual(5, player['car_model'])
        self.assertEqual((1, 3, 0), (player['steering_device'], player['pedal_device'], player['shift_device']))
        self.assertEqual(1, setup['has_cops'])
        self.assertEqual([205, 200], setup['car_slot_ids'][:2])
        self.assertEqual(0, setup['player_id'])

        highlights = data['highlights']
        self.assertEqual(8, highlights['clip_count'])
        self.assertEqual(-2, highlights['state'])
        self.assertEqual((1560, 180), (highlights['play_to_clock'], highlights['seek_target']))
        for second, value in enumerate(highlights['seconds']):
            if value:
                # the index is the second of the circular 8-minute buffer, the value holds the absolute second
                self.assertEqual(second, (value >> 8) % 480)

        car = data['recording']['player_frames'][0][0]['car']
        self.assertEqual((0, 1, 2), (car['car_index'], car['control_handler'], car['crash_state']))
        self.assertAlmostEqual(-9.81, car['collision_data']['unk0'][1], places=2)

        world = data['world_state']
        self.assertEqual(6928, world['end_clock'])
        self.assertEqual(67, world['keyframe_countdown'])
        self.assertEqual(20, len(world['keyframes']))
        self.assertEqual(8, world['keyframes'][0]['other_car_count'])
        self.assertEqual([6, 0, 1], world['saved_timers'])

        self.assertEqual(9, len(data['stats']))
        self.assertEqual(22588, data['stats'][2]['finish_time'])
        self.assertEqual(5, data['stats'][0]['car_model'])
        self.assertEqual(1, data['stats'][0]['wreck_count'])

    def test_block_sizes(self):
        expected = [
            (TnfsReplay(), 100374),
            (TnfsReplaySetup(), 0x348),
            (TnfsReplayPlayer(), 0x4B),
            (TnfsReplayHighlights(), 0x9A4),
            (TnfsReplayRecording(), 0x15E00),
            (TnfsReplayPlayerFrame(), 0x1A4),
            (TnfsReplayOtherFrame(), 0x172),
            (TnfsReplayCarState(), 0x168),
            (TnfsReplayCollisionData(), 0x94),
            (TnfsReplayWorldState(), 0xCC8),
            (TnfsReplayWorldKeyframe(), 0xA2),
            (TnfsReplayStats(), 0x1D2),
        ]
        for block, size in expected:
            with self.subTest(block=type(block).__name__):
                self.assertEqual(size, len(block.pack(block.new_data())))

    def test_replay_can_be_reconstructed(self):
        (name, block, data) = require_file('test/samples/REPLAY3.RPL')
        output = block.pack(data, name=name)
        with open('test/samples/REPLAY3.RPL', 'rb') as bdata:
            original = bdata.read()
        self.assertEqual(100374, len(original))
        self.assertEqual(len(original), len(output))
        self.assertEqual(original, output)

    def test_replay_fields_are_consistent(self):
        (name, block, data) = require_file('test/samples/REPLAY3.RPL')
        tracks = ['cy', 'cl', 'al', 'tr1', 'tr2', 'tr6', 'tr3', 'tr7', 'tr4']
        setup = data['setup']
        self.assertTrue(setup['track_name'].startswith(tracks[setup['track_id']]))
        self.assertEqual(setup['car_count'], setup['racer_count'] + setup['cop_count'] + setup['traffic_count'])
        for player in setup['players'][: setup['player_count']]:
            self.assertIn(player['car_model'], range(8))
            for device in ('steering_device', 'pedal_device', 'shift_device'):
                self.assertIn(player[device], range(4))
        world = data['world_state']
        self.assertEqual(0, world['unk0'])
        # the countdown runs to the next keyframe, one control step per 4 clock units
        self.assertEqual((0x708 - world['end_clock'] % 0x708) // 4 - 1, world['keyframe_countdown'])
        self.assertEqual(setup['car_count'] - 1, world['keyframes'][0]['other_car_count'])
