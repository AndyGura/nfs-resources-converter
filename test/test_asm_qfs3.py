import os
import unittest

from resources.eac.compressions.qfs3 import Qfs3Compression


class TestAsmQFS3Algorythm(unittest.TestCase):

    def test_0_al1(self):
        pass
        # parser = Qfs3Compression()
        # file_name = 'games/nfs1/FRONTEND/ART/CHECK/AL1.QFS'
        # with open(file_name, 'rb', buffering=30) as file:
        #     uncompressed = parser.uncompress(file, os.path.getsize(file_name))
        #     print('CHECKING OUTPUT....')
        #     with open('test/samples/AL1.FSH', 'rb', buffering=30) as fsh_file:
        #         fsh = fsh_file.read()
        #         self.assertEqual(len(fsh), len(uncompressed))
        #         for i in range(len(fsh)):
        #             if i % 10000 == 0:
        #                 print(f"{i}/{len(fsh)}")
        #             self.assertEqual(fsh[i], uncompressed[i])

    def test_1_vertbst(self):
        pass
        # parser = Qfs3Compression()
        # file_name = 'games/nfs1/FRONTEND/ART/TRACKSEL/VERTBST.QFS'
        # with open(file_name, 'rb', buffering=30) as file:
        #     uncompressed = parser.uncompress(file, os.path.getsize(file_name))
        #     print('CHECKING OUTPUT....')
        #     with open('test/samples/VERTBST.FSH', 'rb', buffering=30) as fsh_file:
        #         fsh = fsh_file.read()
        #         self.assertEqual(len(fsh), len(uncompressed))
        #         for i in range(len(fsh)):
        #             if i % 10000 == 0:
        #                 print(f"{i}/{len(fsh)}")
        #             self.assertEqual(fsh[i], uncompressed[i])

    def test_2_ldiabl_pbs(self):
        parser = Qfs3Compression()
        file_name = 'games/nfs1/SIMDATA/CARSPECS/LDIABL.PBS'
        with open(file_name, 'rb', buffering=30) as file:
            uncompressed = parser.uncompress(file, os.path.getsize(file_name))
            print('CHECKING OUTPUT....')
            with open('test/samples/LDIABL.PBS.BIN', 'rb', buffering=30) as fsh_file:
                fsh = fsh_file.read()
                self.assertEqual(len(fsh), len(uncompressed))
                for i in range(len(fsh)):
                    if i % 10000 == 0:
                        print(f"{i}/{len(fsh)}")
                    self.assertEqual(fsh[i], uncompressed[i])

    def test_3_gtitle(self):
        pass
        # parser = Qfs3Compression()
        # file_name = 'games/nfs1/FRONTEND/GART/TITLE.QFS'
        # with open(file_name, 'rb', buffering=30) as file:
        #     uncompressed = parser.uncompress(file, os.path.getsize(file_name))
        #     print('CHECKING OUTPUT....')
        #     with open('test/samples/GTITLE.FSH', 'rb', buffering=30) as fsh_file:
        #         fsh = fsh_file.read()
        #         self.assertEqual(len(fsh), len(uncompressed))
        #         for i in range(len(fsh)):
        #             if i % 10000 == 0:
        #                 print(f"{i}/{len(fsh)}")
        #             self.assertEqual(fsh[i], uncompressed[i])

    def test_4_gvertbst(self):
        pass
        # parser = Qfs3Compression()
        # file_name = 'games/nfs1/FRONTEND/GART/TRACKSEL/VERTBST.QFS'
        # with open(file_name, 'rb', buffering=30) as file:
        #     uncompressed = parser.uncompress(file, os.path.getsize(file_name))
        #     print('CHECKING OUTPUT....')
        #     with open('test/samples/GVERTBST.FSH', 'rb', buffering=30) as fsh_file:
        #         fsh = fsh_file.read()
        #         self.assertEqual(len(fsh), len(uncompressed))
        #         for i in range(len(fsh)):
        #             if i % 10000 == 0:
        #                 print(f"{i}/{len(fsh)}")
        #             self.assertEqual(fsh[i], uncompressed[i])
