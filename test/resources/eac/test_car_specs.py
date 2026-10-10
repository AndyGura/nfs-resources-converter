import unittest

from library import require_file


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
