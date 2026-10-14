import unittest
from copy import deepcopy

from library import require_file
from library.block_checks import check_compatibility, collect_warnings
from library.read_blocks.misc.compatibility import Compatibility
from resources.eac.car_specs import CarAiAndCrashBody


class TestPlayerCarPhysics(unittest.TestCase):
    def test_pbs_hash_can_be_reconstructed(self):
        (name, block, data) = require_file('test/samples/LDIABL.PBS__uncompressed')
        data['checksum'] = None
        output = block.pack(data, name=name)
        with open('test/samples/LDIABL.PBS__uncompressed', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')


class TestTnfs3doCarPhysics(unittest.TestCase):
    def test_round_trip(self):
        (name, block, data) = require_file('test/samples/LDIABLO.bigSpecsFam')
        self.assertEqual(block.__class__.__name__, 'Tnfs3doCarPhysics')
        self.assertEqual(data['mass'], 1753)
        self.assertEqual(data['max_brake_force'], 11.299987792968750)
        self.assertEqual(data['num_torques'], 51)
        self.assertEqual(data['rear_grip_mult'], 1.796875)
        self.assertEqual(len(data['grip_table_f']), 512)
        for key in ['mass', 'inv_mass', 'brake_bias_r', 'front_grip_mult_inv', 'rear_grip_mult_inv', 'items_descr']:
            data[key] = None
        with open('test/samples/LDIABLO.bigSpecsFam', 'rb') as f:
            self.assertEqual(f.read(), block.pack(data, name=name))


class TestCarSpecsChecks(unittest.TestCase):
    def _pbs(self):
        (name, block, data) = require_file('test/samples/LDIABL.PBS')
        return name, block, deepcopy(data)

    def test_stock_pbs_has_no_warnings(self):
        name, block, data = self._pbs()
        self.assertEqual(collect_warnings(block, data, name), [])

    def test_pbs_warnings(self):
        name, block, data = self._pbs()
        pbs = data['data']
        pbs['max_rpm'] = 6000
        pbs['top_speed'] = 120
        pbs['has_tcs'] = 1.0
        pbs['throttle_on_ramp'] = 10
        pbs['num_torques'] = 55
        pbs['drop_rpm_dec'] = 0
        pbs['torques'][0]['torque'] = 950
        messages = [w['message'] for w in collect_warnings(block, data, name)]
        self.assertEqual({w['id'] for w in collect_warnings(block, data, name)}, {name + '__data'})
        expected_starts = [
            'The automatic gearbox never shifts up from gear 1: `upshifts[0]` (7400 rpm)',
            '`top_speed` (120.0 m/s, 432 km/h) is never reached',
            '`torques` entries 51, 52, 53, 54 are not in 200 rpm steps',
            '`torques` entries 51, 52, 53, 54 have a torque below 0',
            'With traction control (`has_tcs`) a `throttle_on_ramp` below 12 (10)',
            'In gear 1 the peak wheel torque is above the 7.0 cap',
            '`drop_rpm_dec` is 0',
        ]
        self.assertEqual(len(messages), len(expected_starts), messages)
        for message, start in zip(messages, expected_starts):
            self.assertTrue(message.startswith(start), message)

    def test_3do_skips_pc_engine_warnings(self):
        (name, block, data) = require_file('test/samples/LDIABLO.bigSpecsFam')
        data = deepcopy(data)
        self.assertEqual(collect_warnings(block, data, name), [])
        data['has_tcs'] = 1.0
        data['throttle_on_ramp'] = 10
        data['min_rpm'] = 8000
        messages = [w['message'] for w in collect_warnings(block, data, name)]
        self.assertEqual(messages, ['Idle rpm `min_rpm` (8000) is not below the redline `max_rpm` (7500)'])

    def test_pdn_warnings(self):
        block = CarAiAndCrashBody()
        data = block.new_data()
        data.update({'half_width': 0.9, 'half_height': 0.6, 'half_length': 2.1, 'moment_of_inertia': 1.5, 'mass': 1.0})
        self.assertEqual(block.get_warnings(data, None), [])
        data['half_width'] = 0
        data['mass'] = 0
        self.assertEqual(
            block.get_warnings(data, None),
            [
                '`half_width` is 0: the game then ignores all three half sizes and takes the collision body size from '
                'the car model',
                '`mass` is 0: the game divides by it in collisions',
            ],
        )

    def test_compatibility(self):
        name, block, data = self._pbs()
        self.assertEqual(check_compatibility(block, data, name, 'tnfs')['state'], Compatibility.COMPATIBLE)
        self.assertEqual(check_compatibility(block, data, name, 'tnfs_3do')['state'], Compatibility.NOT_COMPATIBLE)
        self.assertEqual(check_compatibility(block, data, name, 'nfs2')['state'], Compatibility.UNKNOWN)
        self.assertEqual(check_compatibility(block, data, name, 'nfs3')['state'], Compatibility.NOT_COMPATIBLE)
        (name, block, data) = require_file('test/samples/LDIABLO.bigSpecsFam')
        self.assertEqual(check_compatibility(block, data, name, 'tnfs_3do')['state'], Compatibility.COMPATIBLE)
        self.assertEqual(check_compatibility(block, data, name, 'tnfs')['state'], Compatibility.NOT_COMPATIBLE)
