import os
import unittest
from io import BufferedReader

from library.utils.asm_runner import AsmRunner
from resources.eac.compressions.base import BaseCompressionAlgorithm
from resources.eac.compressions.qfs2 import Qfs2Compression


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


class TestAsmQFS2Algorythm(unittest.TestCase):

    def test(self):
        parser_py = Qfs2Compression()
        parser_asm = Qfs2ASMCompression()
        file_name = 'test/samples/AL2.QFS'
        with open(file_name, 'rb') as file:
            uncompressed_py = parser_py.uncompress(file, os.path.getsize(file_name))
            file.seek(0)
            uncompressed_asm = parser_asm.uncompress(file, os.path.getsize(file_name))
            self.assertListEqual(list(uncompressed_py), list(uncompressed_asm))
