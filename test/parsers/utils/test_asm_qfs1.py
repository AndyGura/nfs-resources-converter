import os
import traceback
import unittest
from io import BufferedReader

from parsers.resources.compressed import CompressedResource, Qfs2Archive, RefPackArchive
from parsers.utils.asm_runner import AsmRunner


class Qfs1ASMArchive(CompressedResource, AsmRunner):

    # ebx is read pointer
    # ecx is write pointer
    # var_14 is value_indicator
    def uncompress(self, buffer: BufferedReader, input_length: int) -> bytes:
        input_data = buffer.read(input_length)
        for i in range(input_length):
            self.memstore(0x500 + i, int.from_bytes(input_data[i:i+1], signed=False, byteorder='little'), size=1)

        # set stack pointer after input length + offset for script variables
        self.esp = 0x50
        # arguments
        self.define_variable('arg_0', 8, 4) # input ptr
        self.memstore(self.esp + 0x4, 0x500, size=4)
        self.define_variable('arg_4', 0xC, 4) # output ptr
        self.memstore(self.esp + 0x8, 500*1024, size=4)
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
        return self.asm_virtual_memory[500*1024:end_cursor]

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


class TestAsmQFS1Algorythm(unittest.TestCase):

    def test(self):
        parser_py = RefPackArchive()
        parser_asm = Qfs1ASMArchive()
        file_name = '../../../games/nfs1/FRONTEND/ART/CHECK/AL3.QFS'
        with open(file_name, 'rb', buffering=30) as file:
            uncompressed_py = parser_py.uncompress(file, os.path.getsize(file_name))
            file.seek(0)
            uncompressed_asm = parser_asm.uncompress(file, os.path.getsize(file_name))
            self.assertListEqual(list(uncompressed_py), list(uncompressed_asm))
