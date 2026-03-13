import unittest
from io import BytesIO
from os.path import getsize

from library.read_blocks import DataBlock
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries.nfs5 import CrpGeometry


class TestCrpGeometry(unittest.TestCase):

    def test_crp_should_remain_the_same(self):
        compression = RefPackCompression()
        b = open('test/samples/356b.crp', 'rb', buffering=100 * 1024 * 1024)
        uncompressed = compression.uncompress(b, getsize('test/samples/356b.crp'))

        block = CrpGeometry()
        DataBlock.root_read_ctx.buffer = BytesIO(uncompressed)
        data = block.unpack(DataBlock.root_read_ctx, name='356b.crp', read_bytes_amount=len(uncompressed))
        output = block.pack(data, name='356b.crp')

        self.assertEqual(len(uncompressed), len(output))
        for i, x in enumerate(uncompressed):
            self.assertEqual(x, output[i], f"Wrong value at index {i}")
