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
        mock_data = "This is a test payload for compression".encode('utf-8') + b'\xFF\x28\x28'
        # mock_data = b'\xFF\x28\x28'
        block = EacCompressedBlock()
        compressed = block.pack({'data': mock_data, 'choice_index': block.get_choice_index_by_class_name('BytesBlock')})

        decompressed_asm = Qfs2ASMCompression().uncompress(BytesIO(compressed), len(compressed))
        decompressed = block.unpack(ReadContext.from_bytes(compressed), read_bytes_amount=len(compressed))
        # FIXME what is that extra 0x00 produced by ASM decompressor?
        self.assertEqual(mock_data + b'\x00', bytes(decompressed_asm),
                         'Decompressed ASM data does not match original data')
        self.assertEqual(mock_data + b'\x00', decompressed['data'], 'Decompressed data does not match original data')

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
            self.memstore(0x10 + i, int.from_bytes(input_data[i:i + 1], signed=False, byteorder='little'), size=1)

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
        self.define_variable('patterns_index_table_pointer', 0,
                             4)  # ptr to var_11C, start of some 256 bytes index table, probably patterns
        self.define_variable('ds:dword_53034C', 0, 4)  # ptr to var_21C, never reassigned
        self.define_variable('ds:dword_530348', 0, 4)
        self.define_variable('write_pointer', 0, 4)  # write pointer

        if not self.loc_4A96E4():
            if not self.loc_4A972E():
                self.loc_4A9746()
            self.loc_4A9749()
            while self.clear_patterns_index_table():
                pass
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
        self.loc_4A98C8()
        return self.asm_virtual_memory[input_length + 0x1000:self.get_value('write_pointer')[0] + 1]

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
                 jz      loc_4A98C8 """)

    def loc_4A972E(self):
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

    def loc_4A9746(self):
        return self.run_block(""" add     ebx, 3

 """)

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
                 jz      short loc_4A98C8""")

    def loc_4A98BF(self):
        return self.run_block("""inc     ecx
                 mov     [ecx-1], dl""")

    def loc_4A98C8(self):
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
            self.memstore(0x500 + i, int.from_bytes(input_data[i:i + 1], signed=False, byteorder='little'), size=1)

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
                self.run_block("lea     ebx, [ebx+3]")
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
        return self.asm_virtual_memory[500 * 1024:end_cursor]

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
