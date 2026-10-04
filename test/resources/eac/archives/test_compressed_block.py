import os
import unittest
from io import BytesIO, BufferedReader

from library.context import ReadContext
from library.utils.asm_runner import AsmRunner
from resources.eac.archives import EacCompressedBlock
from resources.eac.compressions.base import BaseCompressionAlgorithm
from resources.eac.compressions.qfs2 import Qfs2Compression
from resources.eac.compressions.qfs3 import Qfs3Compression
from resources.eac.compressions.ref_pack import RefPackCompression


class TestEacCompressedBlock(unittest.TestCase):
    def test_should_compress_and_uncompress(self):
        mock_data = 'This is a test payload for compression'.encode('utf-8') + b'\xff\x28\x28'
        # mock_data = b'\xFF\x28\x28'
        block = EacCompressedBlock()
        compressed = block.pack({'data': mock_data, 'choice_index': block.get_choice_index_by_class_name('BytesBlock')})

        decompressed_asm = Qfs2ASMCompression().uncompress(BytesIO(compressed), len(compressed))
        decompressed = block.unpack(ReadContext.from_bytes(compressed), read_bytes_amount=len(compressed))
        self.assertEqual(mock_data, bytes(decompressed_asm), 'Decompressed ASM data does not match original data')
        self.assertEqual(mock_data, decompressed['data'], 'Decompressed data does not match original data')

    def test_qfs2_escaping_recursive_patterns_issue(self):
        # real part of file that was broken with first iteration of qfs2 algo, at the offset where something went wrong
        original_data = b'\x00\xee\x00\x00\x00\x00\x00\x17'
        # real patterns, generated for given file when scanned fully
        patterns = [[(0xEE, 0x0, 0x0)], [(0x9E, 0xEE, 0xEE)]]
        # the problem is following:
        # 1) we replace 0x00-s with 0xee and escape existing 0xee's: \xee\x00\x00\x00\x00 -> \xff\xee\xee\xee
        # 2) now we replace 0xee-s with 0x9e, but we have to skip escaped 0xee: \xff\xee\xee\xee -> \xff\xee\x9e
        compressed = Qfs2Compression().compress(BytesIO(original_data), len(original_data), hardcoded_patterns=patterns)
        self.assertEqual(
            compressed, b'F\xfb\x00\x00\x08\xff\x02\xee\x00\x00\x9e\xee\xee\x00\xff\xee\x9e\x00\x17\xff\x00'
        )

        decompressed = Qfs2Compression().uncompress(BytesIO(compressed), len(compressed))
        self.assertEqual(original_data, decompressed)

    # def test_qfs2_compression_efficiency(self):
    #     import tempfile
    #     import urllib.request
    #     from eac.archives import ShpiBlock
    #     from eac.bitmaps import EacImage
    #     from serializers import ImageSerializer
    #     shpi_block = ShpiBlock()
    #     data = shpi_block.new_data()
    #     data['children'].append({
    #         'pre_offset_payload': b'',
    #         'post_offset_payload': b'',
    #         'alias': 'AAAA',
    #         'item': {
    #             'choice_index': shpi_block.item_block.get_choice_index_by_class_name('EacImage'),
    #             'data': EacImage().new_data()
    #         }
    #     })
    #     with tempfile.TemporaryDirectory() as tmpdir:
    #         image_url = "https://picsum.photos/512/512?hmac=pJQXx7frJ1QUXHF_ysDKy3gb54RDtfk9C09G-iswhZE"
    #         tmp_dir = tempfile.gettempdir()
    #         image_path = os.path.join(tmp_dir, "sample_image.png")
    #         urllib.request.urlretrieve(image_url, image_path)
    #         data['children'][0]['item']['data'] = ImageSerializer().deserialize([image_path], block=EacImage())
    #     # shpi_block.action_convert_to_8bit(data, '', '!pal', '32Bit color format palette', 256, '')
    #     pure_data = shpi_block.write(data)
    #     compressed = Qfs2Compression().compress(BytesIO(pure_data), len(pure_data))
    #     decompressed = Qfs2Compression().uncompress(BytesIO(compressed), len(compressed))
    #     self.assertEqual(pure_data, decompressed)

    def test_qfs2_asm_decompression(self):
        parser_py = Qfs2Compression()
        parser_asm = Qfs2ASMCompression()
        file_name = 'test/samples/AL2.QFS'
        with open(file_name, 'rb') as file:
            uncompressed_py = parser_py.uncompress(file, os.path.getsize(file_name))
            file.seek(0)
            uncompressed_asm = parser_asm.uncompress(file, os.path.getsize(file_name))
            self.assertListEqual(list(uncompressed_py), list(uncompressed_asm))

    def test_refpack_asm_decompression(self):
        parser_py = RefPackCompression()
        parser_asm = RefPackASMCompression()
        file_name = 'test/samples/AL3.QFS'
        with open(file_name, 'rb') as file:
            uncompressed_py = parser_py.uncompress(file, os.path.getsize(file_name))
            file.seek(0)
            uncompressed_asm = parser_asm.uncompress(file, os.path.getsize(file_name))
            self.assertListEqual(list(uncompressed_py), list(uncompressed_asm))

    def test_qfs3_asm_decompression(self):
        for file_name in ['test/samples/LDIABL.PBS', 'test/samples/VERTBST.QFS']:
            with self.subTest(file_name=file_name), open(file_name, 'rb') as file:
                uncompressed_py = Qfs3Compression().uncompress(file, os.path.getsize(file_name))
                file.seek(0)
                uncompressed_asm = Qfs3ASMCompression().uncompress(file, os.path.getsize(file_name))
                self.assertListEqual(list(uncompressed_py), list(uncompressed_asm))

    def test_qfs3_decompression_al1(self):
        parser = Qfs3Compression()
        file_name = 'test/samples/AL1.QFS'
        with open(file_name, 'rb') as file:
            uncompressed = parser.uncompress(file, os.path.getsize(file_name))
            with open('test/samples/AL1.FSH', 'rb') as fsh_file:
                fsh = fsh_file.read()
                self.assertEqual(len(fsh), len(uncompressed))
                for i in range(len(fsh)):
                    self.assertEqual(fsh[i], uncompressed[i])

    def test_qfs3_decompression_vertbst(self):
        parser = Qfs3Compression()
        file_name = 'test/samples/VERTBST.QFS'
        with open(file_name, 'rb') as file:
            uncompressed = parser.uncompress(file, os.path.getsize(file_name))
            with open('test/samples/VERTBST.FSH', 'rb') as fsh_file:
                fsh = fsh_file.read()
                self.assertEqual(len(fsh), len(uncompressed))
                for i in range(len(fsh)):
                    self.assertEqual(fsh[i], uncompressed[i])

    def test_qfs3_decompression_ldiabl_pbs(self):
        parser = Qfs3Compression()
        file_name = 'test/samples/LDIABL.PBS'
        with open(file_name, 'rb') as file:
            uncompressed = parser.uncompress(file, os.path.getsize(file_name))
            with open('test/samples/LDIABL.PBS.BIN', 'rb') as fsh_file:
                fsh = fsh_file.read()
                self.assertEqual(len(fsh), len(uncompressed))
                for i in range(len(fsh)):
                    self.assertEqual(fsh[i], uncompressed[i])

    def test_qfs3_decompression_gtitle(self):
        parser = Qfs3Compression()
        file_name = 'test/samples/GTITLE.QFS'
        with open(file_name, 'rb') as file:
            uncompressed = parser.uncompress(file, os.path.getsize(file_name))
            with open('test/samples/GTITLE.FSH', 'rb') as fsh_file:
                fsh = fsh_file.read()
                self.assertEqual(len(fsh), len(uncompressed))
                for i in range(len(fsh)):
                    self.assertEqual(fsh[i], uncompressed[i])

    def test_qfs3_decompression_gvertbst(self):
        parser = Qfs3Compression()
        file_name = 'test/samples/GVERTBST.QFS'
        with open(file_name, 'rb') as file:
            uncompressed = parser.uncompress(file, os.path.getsize(file_name))
            with open('test/samples/GVERTBST.FSH', 'rb') as fsh_file:
                fsh = fsh_file.read()
                self.assertEqual(len(fsh), len(uncompressed))
                for i in range(len(fsh)):
                    self.assertEqual(fsh[i], uncompressed[i])


class Qfs2ASMCompression(BaseCompressionAlgorithm, AsmRunner):
    # ebx is read pointer
    # ecx is write pointer
    # var_14 is value_indicator
    def uncompress(self, buffer: BufferedReader, input_length: int) -> bytes:
        self.memstore(0, input_length, size=4)
        # write compressed data to the beginning (almost)
        input_data = buffer.read(input_length)
        for i in range(input_length):
            self.memstore(0x10 + i, int.from_bytes(input_data[i : i + 1], signed=False, byteorder='little'), size=1)

        # set stack pointer after input length + offset for script variables
        self.esp = input_length + 0x10 + 0x550
        # arguments
        self.define_variable('ptr_p4', 4, 4)  # pointer compressed data in memory 100%
        self.memstore(self.esp + 0x4, 0x10, size=4)

        self.define_variable('ptr_p8', 8, 4)  # pointer where to save file
        self.memstore(self.esp + 0x8, input_length + 0x1000, size=4)

        self.define_variable('var_21C', -0x21C, 1)
        self.define_variable('var_11C', -0x11C, 1)
        self.define_variable('var_1C', -0x1C, 4)
        self.define_variable('var_18', -0x18, 4)
        self.define_variable('var_14', -0x14, 4)
        self.define_variable('original_esp_pointer', 0, 4)  # original function esp
        self.define_variable(
            'patterns_index_table_pointer', 0, 4
        )  # ptr to var_11C, start of some 256 bytes index table, probably patterns
        self.define_variable('ds:dword_53034C', 0, 4)  # ptr to var_21C, never reassigned
        self.define_variable('ds:dword_530348', 0, 4)
        self.define_variable('write_pointer', 0, 4)  # write pointer

        if not self.loc_4A96E4():
            if not self.is_without_file_size():
                self.seek_3()
            self.loc_4A9749()
            while self.clear_patterns_index_table():
                pass

            # read patterns metadata
            if not self.loc_4A9794():
                self.loc_4A97B1()
                while self.fill_patterns_index_table():
                    pass

            while True:
                if self.is_using_pattern():
                    # pattern index is in dl now
                    # al == value from index table
                    if self.is_pattern_non_recursive():
                        if self.loc_4A98B6():
                            break
                        self.loc_4A98BF()
                    else:
                        # reads from index table for first byte to al
                        self.loc_4A9822()
                        while not self.is_dont_have_pattern_for_value():
                            self.insert_pattern()
                        self.append_al_to_result()
                        while not self.is_dont_have_pattern_for_value_2():
                            self.loc_4A9888()
                        self.append_al_to_result_do_not_inc_write_pointer()
                else:
                    self.insert_plain_value()
        self.cleanup()
        return self.asm_virtual_memory[input_length + 0x1000 : self.get_value('write_pointer')[0]]

    def insert_qfs2_pattern(self):
        self.run_block("""
            push    ebx
            push    edx""")
        # check is first byte as al pattern
        while not self.run_block("""
                xor     edx, edx
                mov     ebx, original_esp_pointer
                mov     dl, al
                cmp     byte ptr [edx+ebx], 0
                jz      short loc_4A96CE"""):
            # recursive call: insert pattern from fist byte
            self.run_block("""
                mov     eax, patterns_index_table_pointer
                mov     al, [edx+eax]
                and     eax, 0FFh
                call    insert_qfs2_pattern
                mov     eax, ds:dword_53034C
                mov     al, [edx+eax]""")
        # append second byte as al to result
        self.run_block("""
            mov     edx, write_pointer
            inc     edx
            mov     [edx-1], al
            mov     write_pointer, edx
            pop     edx
            pop     ebx""")

    def loc_4A96E4(self):
        return self.run_block("""  push    ebx
                 push    esi
                 push    edi
                 push    ebp
                 sub     esp, 30Ch
                 mov     edx, [esp+31Ch+ptr_p4]
                 mov     ecx, [esp+31Ch+ptr_p8]
                 mov     eax, esp
                 mov     ebx, edx
                 mov     original_esp_pointer, eax
                 lea     eax, [esp+31Ch+var_11C]
                 xor     esi, esi
                 mov     patterns_index_table_pointer, eax
                 lea     eax, [esp+31Ch+var_21C]
                 mov     [esp+31Ch+var_14], esi
                 mov     ds:dword_53034C, eax
                 test    edx, edx
                 jz      cleanup """)

    def is_without_file_size(self):
        return self.run_block(""" xor     eax, eax
                 lea     ebx, [edx+1]
                 mov     al, [edx]
                 xor     edx, edx
                 shl     eax, 8
                 mov     dl, [ebx]
                 add     eax, edx
                 inc     ebx
                 cmp     eax, 47FBh
                 jnz     short loc_4A9749 """)

    def seek_3(self):
        return self.run_block(""" add     ebx, 3""")

    def loc_4A9749(self):
        return self.run_block("""  
                 xor     eax, eax
                 mov     al, [ebx]
                 mov     [esp+31Ch+var_14], eax
                 mov     edx, [esp+31Ch+var_14]
                 xor     eax, eax
                 shl     edx, 8
                 mov     al, [ebx+1]
                 add     edx, eax
                 inc     ebx
                 mov     [esp+31Ch+var_14], edx
                 xor     eax, eax
                 shl     edx, 8
                 mov     al, [ebx+1]
                 inc     ebx
                 add     edx, eax
                 inc     ebx
                 mov     [esp+31Ch+var_14], edx
                 xor     eax, eax

 """)

    def clear_patterns_index_table(self):
        return self.run_block("""  
                 mov     esi, original_esp_pointer
                 mov     byte ptr [esi+eax], 0
                 inc     eax
                 cmp     eax, 100h
                 jl      short loc_4A9782""")

    def loc_4A9794(self):
        return self.run_block("""inc     ebx
                 xor     eax, eax
                 mov     al, [ebx-1]
                 inc     ebx
                 mov     byte ptr [esi+eax], 1
                 xor     eax, eax
                 mov     al, [ebx-1]
                 xor     esi, esi
                 mov     [esp+31Ch+var_1C], eax
                 test    eax, eax
                 jle     short loc_4A9805""")

    def loc_4A97B1(self):
        return self.run_block("""mov     ebp, [esp+31Ch+var_1C]

 """)

    def fill_patterns_index_table(self):
        return self.run_block("""  
                 xor     edx, edx
                 mov     eax, patterns_index_table_pointer
                 mov     dl, [ebx]
                 lea     edi, [ebx+1]
                 add     eax, edx
                 lea     ebx, [edi+1]
                 mov     [esp+31Ch+var_18], eax
                 mov     al, [edi]
                 mov     edi, [esp+31Ch+var_18]
                 mov     [edi], al
                 mov     eax, ds:dword_53034C
                 add     eax, edx
                 mov     edi, ebx
                 mov     [esp+31Ch+var_18], eax
                 mov     al, [edi]
                 mov     edi, [esp+31Ch+var_18]
                 mov     [edi], al
                 mov     eax, original_esp_pointer
                 inc     esi
                 inc     ebx
                 mov     byte ptr [edx+eax], 0FFh
                 cmp     esi, ebp
                 jl      short loc_4A97B8

 """)

    def is_using_pattern(self):
        # pushes next byte to dl (pattern or not?)
        # pushes value from index table to al (if == 0, no pattern found)
        return self.run_block("""  
                 xor     edx, edx
                 mov     eax, original_esp_pointer
                 mov     dl, [ebx]
                 mov     al, [edx+eax]
                 inc     ebx
                 test    al, al
                 jnz     short loc_4A981C """)

    def insert_plain_value(self):
        return self.run_block("""  inc     ecx
                 mov     [ecx-1], dl
 """)

    def is_pattern_non_recursive(self):
        # probably checks if recursive or not
        return self.run_block("""  
                 jge     loc_4A98B6""")

    def loc_4A9822(self):
        return self.run_block("""  
                 mov     eax, patterns_index_table_pointer
                 mov     ds:dword_530348, ebx
                 mov     write_pointer, ecx
                 mov     al, [edx+eax]
 """)

    def is_dont_have_pattern_for_value(self):
        return self.run_block("""  
                 mov     edi, original_esp_pointer
                 movzx   esi, al
                 cmp     byte ptr [edi+esi], 0
                 jz      short loc_4A9861""")

    def insert_pattern(self):
        return self.run_block(""" 
                 mov     eax, patterns_index_table_pointer
                 mov     al, [esi+eax]
                 and     eax, 0FFh
                 call    insert_qfs2_pattern
                 mov     eax, ds:dword_53034C
                 mov     al, [esi+eax]""")

    def append_al_to_result(self):
        return self.run_block("""  
                 mov     ecx, write_pointer
                 mov     [ecx], al
                 inc     ecx
                 mov     eax, ds:dword_53034C
                 mov     write_pointer, ecx

 """)

    def is_dont_have_pattern_for_value_2(self):
        return self.run_block("""  
                 mov     al, [edx+eax]
                 xor     edx, edx
                 mov     esi, original_esp_pointer
                 mov     dl, al
                 cmp     byte ptr [edx+esi], 0
                 jz      short loc_4A98A1""")

    def loc_4A9888(self):
        return self.run_block("""
                 mov     eax, patterns_index_table_pointer
                 mov     al, [edx+eax]
                 and     eax, 0FFh
                 call    insert_qfs2_pattern
                 mov     eax, ds:dword_53034C""")

    def append_al_to_result_do_not_inc_write_pointer(self):
        return self.run_block("""  
                 mov     ecx, write_pointer
                 inc     ecx
                 mov     ebx, ds:dword_530348
                 mov     [ecx-1], al""")

    def loc_4A98B6(self):
        return self.run_block("""  
                 xor     edx, edx
                 mov     dl, [ebx]
                 inc     ebx
                 test    edx, edx
                 jz      short cleanup""")

    def loc_4A98BF(self):
        return self.run_block("""inc     ecx
                 mov     [ecx-1], dl""")

    def cleanup(self):
        return self.run_block("""
                 mov     eax, [esp+31Ch+var_14]
                 mov     write_pointer, ecx
                 mov     ds:dword_530348, ebx
                 add     esp, 30Ch
                 pop     ebp
                 pop     edi
                 pop     esi
                 pop     ebx """)


class RefPackASMCompression(BaseCompressionAlgorithm, AsmRunner):
    # ebx is read pointer
    # ecx is write pointer
    # var_14 is value_indicator
    def uncompress(self, buffer: BufferedReader, input_length: int) -> bytes:
        input_data = buffer.read(input_length)
        for i in range(input_length):
            self.memstore(0x500 + i, int.from_bytes(input_data[i : i + 1], signed=False, byteorder='little'), size=1)

        # set stack pointer after input length + offset for script variables
        self.esp = 0x50
        # arguments
        self.define_variable('arg_0', 8, 4)  # input ptr
        self.memstore(self.esp + 0x4, 0x500, size=4)
        self.define_variable('arg_4', 0xC, 4)  # output ptr
        self.memstore(self.esp + 0x8, 500 * 1024, size=4)
        self.define_variable('arg_8', 0x10, 4)
        self.memstore(self.esp + 0xC, 1, size=4)
        self.define_variable('var_4', -0x4, 4)

        if not self.loc_4A822C():
            if not self.run_block("""
                    mov     ax, [ebx]
                    lea     ebx, [ebx+2]
                    and     al, 1
                    jz      short loc_4A825A"""):
                self.run_block('lea     ebx, [ebx+3]')
            if not self.loc_4A825A():
                self.run_block("""xor     ecx, ecx""")
                while True:
                    pack_code_and_0x80 = self.check_pack_code_0x80()
                    should_continue_outer = False
                    should_break_outer = False
                    while True:
                        if pack_code_and_0x80:
                            if not self.loc_4A82A1():
                                should_continue_outer = True
                                self.run_block("""
                                    lea     ebx, [ebx+2]
                                    mov     ch, dl
                                    mov     cl, dh
                                    and     edx, 1Ch
                                    shr     ch, 5
                                    shr     edx, 2
                                    neg     ecx
                                    lea     esi, [ecx+edi-1]
                                    lea     ecx, [edx+3]
                                    rep movsb""")
                                break
                            if not self.loc_4A827C():
                                continue
                        if self.check_pack_code_0x40():
                            # 0x20 block
                            if self.loc_4A82FC():
                                if self.loc_4A8330():
                                    pack_code_and_0x80 = self.run_block("""
                                        lea     ecx, [edx+5]
                                        rep movsb
                                        or      cl, [ebx]
                                        mov     edx, [ebx]
                                        jns     loc_4A82A1""")
                                    continue
                                else:
                                    pack_code_and_0x80 = self.run_block("""
                                        lea     ecx, [edx+5]
                                        lea     edx, [edx+5]
                                        shr     ecx, 2
                                        and     edx, 3
                                        rep movsd
                                        mov     ecx, edx
                                        rep movsb
                                        or      cl, [ebx]
                                        mov     edx, [ebx]
                                        jns     loc_4A82A1""")
                                    continue
                            else:
                                if self.run_block("""cmp     dl, 0FCh
                                                     jnb     short loc_4A831C"""):
                                    self.run_block("""
                                        mov     ecx, edx
                                        lea     esi, [ebx+1]
                                        and     ecx, 3
                                        rep movsb""")
                                    should_continue_outer = False
                                    should_break_outer = True
                                    break
                                else:
                                    # else block in normal algo
                                    should_continue_outer = True
                                    pack_code_and_0x80 = self.run_block("""
                                        and     edx, 1Fh
                                        lea     esi, [ebx+1]
                                        lea     ecx, [edx+1]
                                        rep     movsd
                                        mov     ebx, esi
                                        or      cl, [esi]
                                        mov     edx, [esi]
                                        jns     short loc_4A82A1""")
                                    continue
                        else:
                            should_continue_outer = True
                            pack_code_and_0x80 = self.loc_4A82CB()
                            continue
                    if should_continue_outer:
                        continue
                    if should_break_outer:
                        break
        end_cursor = self.edi
        self.loc_4A8326()
        return self.asm_virtual_memory[500 * 1024 : end_cursor]

    def loc_4A822C(self):
        return self.run_block("""
            push    ebp
            mov     ebp, esp
            add     esp, 0FFFFFFFCh
            push    ebx
            push    esi
            push    edi
            mov     ecx, [ebp+arg_8]
            mov     ebx, [ebp+arg_0]
            mov     edi, [ebp+arg_4]
            mov     [ebp+var_4], 0
            or      ebx, ebx
            jz      loc_4A8326""")

    def loc_4A8326(self):
        return self.run_block("""
            mov     eax, [ebp+var_4]
            pop     edi
            pop     esi
            pop     ebx""")

    def loc_4A825A(self):
        return self.run_block("""
            xor     eax, eax
            mov     al, [ebx]
            shl     eax, 10h
            mov     ah, [ebx+1]
            mov     al, [ebx+2]
            lea     ebx, [ebx+3]
            mov     [ebp+var_4], eax
            cmp     ecx, 0
            jz      loc_4A8326""")

    def check_pack_code_0x80(self):
        return self.run_block("""
            or      cl, [ebx]
            mov     edx, [ebx]
            jns     short loc_4A82A1""")

    def loc_4A82A1(self):
        return self.run_block("""
            and     ecx, 3
            jnz     short loc_4A827C""")

    def loc_4A827C(self):
        return self.run_block("""
            lea     esi, [ebx+2]
            rep movsb
            mov     ebx, esi
            mov     ch, dl
            mov     cl, dh
            and     edx, 1Ch
            shr     ch, 5
            shr     edx, 2
            neg     ecx
            lea     esi, [ecx+edi-1]
            lea     ecx, [edx+3]
            rep movsb
            or      cl, [ebx]
            mov     edx, [ebx]
            js      short loc_4A82C7""")

    def check_pack_code_0x40(self):
        return self.run_block("""
            add     cl, cl
            js      short loc_4A82FC""")

    def loc_4A82CB(self):
        return self.run_block("""
            mov     cl, dh
            lea     esi, [ebx+3]
            shr     ecx, 6
            and     ecx, 3
            rep movsb
            mov     ebx, esi
            mov     ecx, edx
            shr     ecx, 10h
            mov     ch, dh
            and     ch, 3Fh
            neg     ecx
            lea     esi, [ecx+edi-1]
            and     edx, 3Fh
            lea     ecx, [edx+4]
            rep movsb
            or      cl, [ebx]
            mov     edx, [ebx]
            jns     short loc_4A82A1""")

    def loc_4A82FC(self):
        return self.run_block("""
            add     cl, cl
            jns     short loc_4A8330""")

    def loc_4A8330(self):
        return self.run_block("""
            mov     ecx, edx
            lea     esi, [ebx+4]
            and     ecx, 3
            rep movsb
            mov     ebx, esi
            mov     ecx, edx
            mov     eax, edx
            and     ecx, 10h
            shr     eax, 8
            shl     ecx, 0Ch
            mov     cl, ah
            mov     ch, al
            neg     ecx
            lea     esi, [ecx+edi-1]
            rol     edx, 8
            shr     dh, 2
            and     edx, 3FFh
            cmp     ecx, 0FFFFFFFCh
            jge     short loc_4A8388""")


# Semi-decompiled QFS3 decoder: register-level Python translation of the game's ASM routine, where the two
# stack-resident lookup tables are still accessed through the AsmRunner's virtual memory. Kept only as a regression
# test for the AsmRunner and as a reference for how the pure-Python Qfs3Compression was derived from it.
class Qfs3ASMCompression(BaseCompressionAlgorithm, AsmRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, asm_virtual_memory_size=2 * 1024, **kwargs)
        self.output_length = 0
        self.index_table_0 = []
        self.unk_table = [0] * 256
        self.unk_table_2 = [0] * 256
        self.unk_table_3 = [0] * 256  # maybe has different size
        self.accumulator = 0
        self.available_acc_bits = 0

    def append_to_output(self, buffer, value):
        buffer.extend(value.to_bytes(1, 'little'))

    def reuse_output_byte(self, buffer, length):
        value = buffer[-1]
        for i in range(length):
            self.append_to_output(buffer, value)

    def read_next(self, buffer):
        self.accumulator = _qfs3_asm_read_short(buffer, 'big') | (self.accumulator << 16)

    def accumulate_if_needed(self, buffer):
        if self.available_acc_bits < 0:
            self.read_next(buffer)
            self.esi = self.accumulator << -self.available_acc_bits
            self.available_acc_bits += 16

    def uncompress(self, buffer: BufferedReader, input_length: int) -> bytes:
        uncompressed: bytearray = bytearray()

        table_110 = [0] * 16

        self.define_variable('var_14C', -0x14C, 4)
        self.define_variable('var_154', -0x154, 4)

        index_table_0_capacity = 0
        unk_counter = 0

        self.available_acc_bits = 0
        file_header = self.accumulator = _qfs3_asm_read_short(buffer, 'big')
        if (file_header & 0xFB) != 0xFB:
            raise ValueError('Invalid QFS3 file header')
        self.read_next(buffer)
        self.esi = self.accumulator << 16
        # if compressed size presented
        if file_header & 0x100:
            self.edx = _qfs3_asm_read_int(buffer, 'big')
            self.available_acc_bits = 8
            self.esi = self.edx << 8
            self.accumulator = self.edx
            # reset size presented flag bit
            file_header = file_header & 0xFEFF
        self.ebx = self.esi >> 0x18
        self.available_acc_bits -= 8
        self.esi = self.esi << 8
        self.accumulate_if_needed(buffer)
        self.eax = self.esi >> 16
        self.available_acc_bits -= 16
        self.esi = self.esi << 16
        self.output_length = self.eax
        self.accumulate_if_needed(buffer)
        self.edx = self.output_length = self.output_length | (self.ebx << 16)
        self.ebx = 1
        self.eax = self.esi >> 0x18
        self.available_acc_bits -= 8
        self.esi = self.esi << 8
        unk_1 = self.al
        self.accumulate_if_needed(buffer)
        unk_90 = 1
        unk_3 = 15
        unk_2 = 4
        self.ebp = 0
        while True:
            self.ebp = self.ebp << 1
            self.ecx = index_table_0_capacity
            self.eax = self.ebp - self.ecx
            self.edx = unk_2
            assert self.edx % 4 == 0  # logic below will work in different way if not
            self.unk_table_3[int(self.edx / 4)] = self.eax
            if self.get_register_signed_value('esi') >= 0:
                self.eax = 2
                if (self.esi >> 16) == 0:
                    self.edx = 0
                    while self.edx == 0:
                        self.edx = self.esi >> 0x1F
                        self.eax += 1
                        self.available_acc_bits -= 1
                        self.esi = self.esi << 1
                        self.accumulate_if_needed(buffer)
                else:
                    while self.get_register_signed_value('esi') >= 0:
                        self.esi = self.esi << 1
                        self.eax += 1
                    self.edx = self.eax - 1
                    self.available_acc_bits -= self.edx
                    self.esi = self.esi << 1
                    self.accumulate_if_needed(buffer)
                if self.get_register_signed_value('eax') <= 16:
                    self.edx = self.esi >> (0x20 - self.eax)
                    self.ecx = self.al
                    self.available_acc_bits -= self.eax
                    self.esi = self.esi << self.cl
                    self.accumulate_if_needed(buffer)
                else:
                    self.ebx = self.eax - 16
                    self.edx = self.esi >> (0x20 - self.ebx)
                    self.ecx = self.bl
                    self.available_acc_bits -= self.ebx
                    self.esi = self.esi << self.cl
                    self.accumulate_if_needed(buffer)
                    self.ebx = self.esi >> 16
                    self.available_acc_bits -= 16
                    self.esi = self.esi << 16
                    self.accumulate_if_needed(buffer)
                    self.edx = (self.edx << 16) | self.ebx
                self.edx += 1 << self.al
            else:
                self.edx = self.esi >> 0x1D
                self.available_acc_bits -= 3
                self.esi = self.esi << 3
                self.accumulate_if_needed(buffer)
            self.edx -= 4
            self.eax = unk_2
            assert self.eax % 4 == 0
            table_110[int(self.eax / 4)] = self.edx
            self.eax = index_table_0_capacity
            self.ebp += self.edx
            self.eax += self.edx
            self.ecx = 0
            index_table_0_capacity = self.eax
            if self.edx != 0:
                self.cl = unk_3 & 0xFF
                self.eax = self.ebp << self.cl
                self.ecx = self.eax & 0xFFFF
            self.ebx = unk_3 - 1
            self.eax = unk_2 = unk_2 + 4
            unk_3 = self.ebx
            self.ebx = unk_90 + 1
            self.set_value('[esp+eax+550h+var_154]', self.ecx)
            unk_90 = self.ebx
            if self.edx == 0:
                continue
            if self.ecx == 0:
                break
        self.ecx = 0xFFFFFFFF
        unk_8 = self.ebx - 1
        self.set_value('[esp+ebx*4+550h+var_154]', self.ecx)
        self.ebx = 0
        huff_table_0_iter_ptr = 0
        self.eax = 0xFF
        unk_4 = 0
        if index_table_0_capacity > 0:
            self.index_table_0 = [None] * index_table_0_capacity
            while True:
                if self.get_register_signed_value('esi') >= 0:
                    self.edx = 2
                    if (self.esi >> 16) == 0:
                        while True:
                            self.ebp = self.esi
                            self.edx += 1
                            self.available_acc_bits -= 1
                            self.ebp = self.ebp >> 0x1F
                            self.esi = self.esi << 1
                            self.accumulate_if_needed(buffer)
                            if self.ebp != 0:
                                break
                    else:
                        while self.get_register_signed_value('esi') >= 0:
                            self.esi = self.esi << 1
                            self.edx += 1
                        self.ebx = self.edx - 1
                        self.available_acc_bits -= self.ebx
                        self.esi = self.esi << 1
                        self.accumulate_if_needed(buffer)
                    self.ebx = self.accumulator << 8
                    if self.get_register_signed_value('edx') <= 16:
                        self.ebx = self.esi >> (0x20 - self.edx)
                        self.cl = self.dl
                        self.available_acc_bits -= self.edx
                        self.esi = self.esi << self.cl
                        self.accumulate_if_needed(buffer)
                    else:
                        unk_4 = self.edx - 16
                        self.ecx = 0x20 - unk_4
                        self.ebx = self.esi >> self.cl
                        self.cl = unk_4
                        self.esi = self.esi << self.cl
                        self.available_acc_bits -= unk_4
                        self.accumulate_if_needed(buffer)
                        self.ecx = self.esi >> 16
                        self.available_acc_bits -= 16
                        self.esi = self.esi << 16
                        unk_7 = self.ecx
                        self.accumulate_if_needed(buffer)
                        self.ecx = unk_7
                        self.ebx = (self.ebx << 16) | self.ecx
                    self.cl = self.dl
                    self.edx = 1 << self.cl
                    self.ebx += self.edx
                else:
                    self.ebx = self.esi >> 0x1D
                    self.available_acc_bits -= 3
                    self.esi = self.esi << 3
                    self.accumulate_if_needed(buffer)
                self.ebx -= 3
                while self.ebx != 0:
                    self.al += 1
                    self.edx = self.al
                    if self.edx not in self.index_table_0:
                        self.ebx -= 1
                self.edx = self.al
                self.edx = huff_table_0_iter_ptr
                self.ecx = index_table_0_capacity
                self.ebx = self.edx + 1
                self.index_table_0[self.edx] = self.al
                huff_table_0_iter_ptr = self.ebx
                if self.get_register_signed_value('ebx') >= self.get_register_signed_value('ecx'):
                    break
        self.unk_table_2 = [0x40] * 256
        self.edx = 0
        self.ebx = 0
        self.ecx = unk_8
        unk_5 = 1
        unk_9 = 0
        if self.ecx >= 1:
            self.ecx = 7
            self.eax = 4
            unk_2 = self.ecx
            unk_3 = self.eax
            while True:
                self.eax = unk_3
                assert self.eax % 4 == 0
                self.eax = table_110[int(self.eax / 4)]
                self.ebp = unk_5
                unk_6 = self.eax
                if self.get_register_signed_value('ebp') >= 9:
                    break
                self.ecx = unk_2
                self.ebp = 1 << self.cl
                break_outer = False
                continue_outer = False
                while True:
                    self.eax = unk_6 - 1
                    unk_6 = self.eax
                    if self.eax == 0xFFFFFFFF:
                        self.ebp = unk_3 = unk_3 + 4
                        self.eax = unk_2 = unk_2 - 1
                        self.ecx = unk_5 + 1
                        unk_5 = self.ecx
                        self.ebp = unk_8
                        if self.get_register_signed_value('ecx') <= self.get_register_signed_value('ebp'):
                            continue_outer = True
                            break
                        else:
                            break_outer = True
                            break
                    else:
                        index_table_0_value = self.index_table_0[unk_counter]
                        unk_counter += 1
                        unk_0 = unk_5
                        self.ecx = index_table_0_value
                        self.eax = unk_1
                        if self.eax == self.ecx:
                            self.eax = unk_5
                            unk_9 = self.eax
                            unk_0 = 0x60
                        self.eax = 0
                        if self.get_register_signed_value('ebp') <= 0:
                            continue
                        while self.get_register_signed_value('eax') < self.get_register_signed_value('ebp'):
                            self.edx += 1
                            self.cl = index_table_0_value
                            self.ebx += 1
                            self.unk_table[self.edx - 1] = self.cl
                            self.cl = unk_0
                            self.eax += 1
                            self.unk_table_2[self.ebx - 1] = self.cl
                if break_outer:
                    break
                if continue_outer:
                    continue
                break
        while True:
            if len(uncompressed) > self.output_length:
                raise Exception('Uncompress algorythm writes more that file length')
            self.eax = self.unk_table_2[self.esi >> 0x18]
            self.available_acc_bits -= self.eax
            while self.available_acc_bits >= 0:
                self.edx = self.esi >> 0x18
                for _ in range(4):
                    self.append_to_output(uncompressed, self.unk_table[self.edx])
                    self.esi = self.esi << self.al
                    self.edx = self.esi >> 0x18
                    self.eax = self.unk_table_2[self.edx]
                    self.available_acc_bits -= self.eax
                    if self.available_acc_bits < 0:
                        break
            self.available_acc_bits += 0x10
            if self.available_acc_bits >= 0:
                self.append_to_output(uncompressed, self.unk_table[(self.esi >> 0x18)])
                self.read_next(buffer)
                self.esi = self.accumulator << (0x10 - self.available_acc_bits)
                continue
            self.available_acc_bits += self.eax - 0x10
            if self.eax == 0x60:
                self.eax = unk_9
            else:
                self.eax = 8
                self.edx = self.esi >> 16
                self.ecx = 0x20
                while True:
                    self.eax += 1
                    self.ebp = self.get_value('[esp+ecx+550h+var_14C]')[0]
                    self.ecx += 4
                    if self.edx < self.ebp:
                        break
            self.ecx = 0x20 - self.eax
            self.edx = self.esi >> self.cl
            self.cl = self.al
            self.available_acc_bits -= self.eax
            self.esi = self.esi << self.cl
            self.ecx = self.unk_table_3[self.eax]
            self.eax = self.edx - self.ecx
            self.al = self.index_table_0[self.eax]
            if self.al != unk_1:
                if self.available_acc_bits >= 0:
                    self.append_to_output(uncompressed, self.al)
                    continue
            self.accumulate_if_needed(buffer)
            if self.al != unk_1:
                self.append_to_output(uncompressed, self.al)
                continue
            if self.get_register_signed_value('esi') >= 0:
                self.eax = 2
                if (self.esi >> 16) == 0:
                    self.ebp = 0
                    while unk0 == 0:
                        unk0 = self.esi >> 0x1F
                        self.eax += 1
                        self.available_acc_bits -= 1
                        self.esi = self.esi << 1
                        self.accumulate_if_needed(buffer)
                else:
                    while True:
                        self.esi = self.esi << 1
                        self.eax += 1
                        if self.get_register_signed_value('esi') < 0:
                            break
                    self.ecx = self.eax - 1
                    self.available_acc_bits -= self.ecx
                    self.esi = self.esi << 1
                    self.accumulate_if_needed(buffer)
                if self.get_register_signed_value('eax') <= 16:
                    self.ecx = 0x20 - self.eax
                    self.ebp = self.esi >> self.cl
                    self.available_acc_bits -= self.eax
                    self.cl = self.al
                    fill_bytes_length = self.ebp
                    self.esi = self.esi << self.cl
                    self.accumulate_if_needed(buffer)
                    self.cl = self.al
                    self.eax = (1 << self.cl) + fill_bytes_length
                else:
                    self.ecx = self.eax - 16
                    self.ebp = self.esi >> (0x20 - self.ecx)
                    self.esi = self.esi << self.cl
                    self.available_acc_bits -= self.ecx
                    unk_4 = self.ecx
                    fill_bytes_length = self.ebp
                    self.accumulate_if_needed(buffer)
                    self.ecx = self.esi >> 16
                    self.available_acc_bits -= 16
                    self.esi = self.esi << 16
                    unk3 = self.ecx
                    self.accumulate_if_needed(buffer)
                    self.ecx = fill_bytes_length << 16
                    self.eax = (1 << self.al) + (self.ecx | unk3)
                self.eax = self.eax - 4
                fill_bytes_length = self.eax
            else:
                self.eax = self.esi >> 0x1D
                self.available_acc_bits -= 3
                self.esi = self.esi << 3
                fill_bytes_length = self.eax
                self.accumulate_if_needed(buffer)
                fill_bytes_length -= 4
            self.ebp = fill_bytes_length
            if self.ebp == 0:
                self.ebp = self.esi >> 0x1F
                self.available_acc_bits -= 1
                self.esi = self.esi << 1
                self.accumulate_if_needed(buffer)
                if self.ebp != 0:
                    if file_header == 0x34FB:
                        value_b = value_a = 0
                        for i in range(self.output_length):
                            value_a += uncompressed[i]
                            value_b += value_a
                            uncompressed[i] = value_b & 0xFF
                    elif file_header == 0x32FB:
                        value = 0
                        for i in range(self.output_length):
                            value += uncompressed[i]
                            uncompressed[i] = value & 0xFF
                    break
                else:
                    self.eax = self.esi >> 0x18
                    self.available_acc_bits -= 8
                    self.esi = self.esi << 8
                    self.accumulate_if_needed(buffer)
                    self.append_to_output(uncompressed, self.eax & 0xFF)
            else:
                self.reuse_output_byte(uncompressed, self.ebp)
        return uncompressed


def _qfs3_asm_read_int(buffer, byteorder='little') -> int:
    return int.from_bytes(buffer.read(4), byteorder=byteorder)


def _qfs3_asm_read_short(buffer, byteorder='little') -> int:
    value = buffer.read(2)
    value = value.ljust(2, b'\0')
    return int.from_bytes(value, byteorder=byteorder)
