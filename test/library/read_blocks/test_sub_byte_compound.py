import unittest
from io import BytesIO
from library.context import ReadContext
from library.exceptions import BlockDefinitionException
from library.read_blocks.compound import SubByteCompoundBlock, BitFlagsBlock

class TestSubByteCompoundBlock(unittest.TestCase):

    def test_read_write_mixed(self):
        schema = [
            (1, 'has_left_fence', 'boolean', [], 'flag is add left fence'),
            (1, 'has_right_fence', 'boolean', [], 'flag is add right fence'),
            (6, 'texture_id', 'number', [], 'texture id'),
        ]
        block = SubByteCompoundBlock(length=1, schema=schema)
        
        # Binary: 1 0 111111 (0xBF) -> left=True, right=False, texture=63
        data = bytes([0xBF])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertEqual(res['has_left_fence'], True)
        self.assertEqual(res['has_right_fence'], False)
        self.assertEqual(res['texture_id'], 63)
        
        # Write back
        packed = block.pack(res)
        self.assertEqual(packed, data)

    def test_read_write_enum(self):
        schema = [
            (6, 'unused', 'number', [], 'unused bits'),
            (2, 'mode', 'enum', ['low', 'med', 'high', 'ultra'], 'mode of operation'),
        ]
        block = SubByteCompoundBlock(length=1, schema=schema)
        
        # Binary: 000000 10 (0x02) -> mode='high'
        data = bytes([0x02])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertEqual(res['mode'], 'high')
        
        # Write back
        packed = block.pack(res)
        self.assertEqual(packed, data)
        
        # Test ultra
        res['mode'] = 'ultra'
        packed = block.pack(res)
        self.assertEqual(packed, bytes([0x03]))

    def test_bit_flags_block(self):
        # 1 byte flags
        flags = [(0, 'flag0'), (2, 'flag2'), (7, 'flag7')]
        block = BitFlagsBlock(length=1, flag_names=flags)
        
        # Binary: 10000101 (0x85)
        data = bytes([0x85])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertTrue(res['flag0'])
        self.assertFalse(res['1'])
        self.assertTrue(res['flag2'])
        self.assertTrue(res['flag7'])
        
        # Write back
        packed = block.pack(res)
        self.assertEqual(packed, data)

    def test_multi_byte_big_endian(self):
        # CrpPartInfo1: 2 bytes
        schema = [
            (4, 'damage', 'number', [], 'Damage switch'),
            (8, 'animation_index', 'number', [], 'animation index'),
            (4, 'lod', 'number', [], 'Level of detail'),
        ]
        block = SubByteCompoundBlock(length=2, schema=schema, byte_order='big')

        # Value: damage=0x8 (1000), animation=0x42 (01000010), lod=0x3 (0011)
        # Binary: 1000 01000010 0011 -> 0x8423 (MSB first: 84 23)
        data = bytes([0x84, 0x23])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertEqual(res['damage'], 0x8)
        self.assertEqual(res['animation_index'], 0x42)
        self.assertEqual(res['lod'], 0x3)

        # Write back
        packed = block.pack(res)
        self.assertEqual(packed, data)

    def test_multi_byte_little_endian(self):
        # same test for CrpPartInfo1, just bytes swapped
        schema = [
            (4, 'damage', 'number', [], 'Damage switch'),
            (8, 'animation_index', 'number', [], 'animation index'),
            (4, 'lod', 'number', [], 'Level of detail'),
        ]
        block = SubByteCompoundBlock(length=2, schema=schema, byte_order='little')
        data = bytes([0x23, 0x84])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertEqual(res['damage'], 0x8)
        self.assertEqual(res['animation_index'], 0x42)
        self.assertEqual(res['lod'], 0x3)
        packed = block.pack(res)
        self.assertEqual(packed, data)

    def test_invalid_schema_length(self):
        # 1 byte, but schema only defines 7 bits
        schema = [(7, 'too_short', 'number', [], 'too short')]
        with self.assertRaises(BlockDefinitionException):
            SubByteCompoundBlock(length=1, schema=schema)
            
        # 1 byte, but schema defines 9 bits
        schema = [(9, 'too_long', 'number', [], 'too long')]
        with self.assertRaises(BlockDefinitionException):
            SubByteCompoundBlock(length=1, schema=schema)
