import unittest

from parsers.utils.asm_runner import AsmRunner


class TestAsmRunner(unittest.TestCase):

    def test_push_pop(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.esp = 16
        runner.run_command('mov eax, 228')
        runner.run_command('mov edx, 420')
        runner.run_command('push eax')
        runner.run_command('push edx')
        runner.run_command('pop ecx')
        runner.run_command('pop ebx')
        self.assertEqual(runner.ecx, 420)
        self.assertEqual(runner.ebx, 228)

    def test_sign_wrap_dec(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov al, 1')
        self.assertEqual(runner.al, 0b0000_0001)
        runner.run_command('dec al')
        self.assertEqual(runner.al, 0b0000_0000)
        runner.run_command('dec al')
        self.assertEqual(runner.al, 0b1111_1111)

    def test_sign(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov ah, 1')
        self.assertEqual(runner.ah, 1)
        self.assertEqual(runner.get_register_signed_value('ah'), 1)
        runner.run_command('dec ah')
        self.assertEqual(runner.ah, 0)
        self.assertEqual(runner.get_register_signed_value('ah'), 0)
        runner.run_command('dec ah')
        self.assertEqual(runner.ah, 255)
        self.assertEqual(runner.get_register_signed_value('ah'), -1)
        runner.run_command('dec ah')
        self.assertEqual(runner.ah, 254)
        self.assertEqual(runner.get_register_signed_value('ah'), -2)

    def test_sign_wrap_inc(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov al, 127')
        self.assertEqual(runner.al, 0b0111_1111)
        runner.run_command('inc al')
        self.assertEqual(runner.al, 0b1000_0000)
        runner.run_command('inc al')
        self.assertEqual(runner.al, 0b1000_0001)
        runner.run_command('mov al, 255')
        self.assertEqual(runner.al, 0b1111_1111)
        runner.run_command('inc al')
        self.assertEqual(runner.al, 0b0000_0000)

    def test_shl(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov al, 127')
        self.assertEqual(runner.al, 0b0111_1111)
        runner.run_command('shl al, 2')
        self.assertEqual(runner.al, 0b1111_1100)
        # check that MSB lost
        self.assertEqual(runner.eax, runner.al)

    def test_shr(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov al, 127')
        self.assertEqual(runner.al, 0b0111_1111)
        runner.run_command('shr al, 1')
        self.assertEqual(runner.al, 0b0011_1111)

    def test_shr_strange_bug(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov esi, 130023424')
        runner.run_command('mov     edx, 6')
        runner.run_command('mov     ecx, 20h')
        runner.run_command('mov     ebx, esi')
        runner.run_command('sub     ecx, edx')
        runner.run_command('shr     ebx, cl')
        self.assertEqual(runner.ebx, 0x1)

        # check that right bits did not go to al register
    def test_shr_lost_bits(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov ah, 255')
        runner.run_command('shr ah, 4')
        self.assertEqual(runner.eax, 0x00000F00)

    def test_or(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov al, 58h')
        self.assertEqual(runner.al, 0b0101_1000)
        runner.run_command('mov bl, 61h')
        self.assertEqual(runner.bl, 0b0110_0001)
        runner.run_command('or al, bl')
        self.assertEqual(runner.al, 0b0111_1001)
        self.assertEqual(runner.bl, 0b0110_0001)

    def test_read_from_memory(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov al, 17')
        runner.run_command('mov bl, 18')
        runner.run_command('mov cl, 19')
        runner.run_command('mov [2h], al')
        runner.run_command('mov [2h+1], bl')
        runner.run_command('mov [2h+2], cl')
        runner.run_command('mov dl, [2h]')
        self.assertEqual(runner.edx, 17)
        runner.run_command('mov dl, [2h+1]')
        self.assertEqual(runner.edx, 18)
        runner.run_command('mov dl, [2h+2]')
        self.assertEqual(runner.edx, 19)

    def test_pointer_arithmetic(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov     eax, 50h')
        runner.run_command('lea     ecx, [eax-10h]')
        self.assertEqual(runner.ecx, 0x40)

    def test_read_from_memory_16_bit(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov ax, 17')
        runner.run_command('mov bx, 18')
        runner.run_command('mov cx, 19')
        runner.run_command('mov [2h], ax')
        runner.run_command('mov [2h+2], bx')
        runner.run_command('mov [2h+4], cx')
        runner.run_command('mov dx, [2h]')
        self.assertEqual(runner.dx, 17)
        runner.run_command('mov dx, [2h+2]')
        self.assertEqual(runner.dx, 18)
        runner.run_command('mov dx, [2h+4]')
        self.assertEqual(runner.dx, 19)

    def test_read_from_memory_messed_up_pointers(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_block("""
            mov eax, 5 ; test 32bit
            mov ebx, 17
            mov [esp+eax], ebx
            inc eax ; second 32bit
            mov ebx, 22
            mov [esp+eax], ebx
            inc eax ; test 8bit
            mov bl, 6
            mov [esp+eax], bl
            inc eax ; test 32bit
            mov ebx, 4
            mov [esp+eax], ebx
            mov eax, 5""")
        runner.run_command("""mov edx, [esp+eax]""")
        self.assertEqual(runner.edx, 0x04061611)
        runner.run_command("""inc eax""")
        runner.run_command("""mov edx, [esp+eax]""")
        self.assertEqual(runner.edx, 0x040616)
        runner.run_command("""inc eax""")
        runner.run_command("""mov dl, [esp+eax]""")
        self.assertEqual(runner.dl, 0x06)
        runner.run_command("""inc eax""")
        runner.run_command("""mov edx, [esp+eax]""")
        self.assertEqual(runner.edx, 0x04)

    def test_byte_ptrs(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov [esp+4], 102030FBh')
        runner.define_variable('bptr', 2, 1)
        runner.run_command('mov eax, [esp+4+bptr]')
        self.assertEqual(runner.eax, 0x20)
        runner.run_command('mov [esp+4+bptr], 1')
        runner.run_command('mov eax, [esp+4]')
        self.assertEqual(runner.eax, 0x100130FB)

    def test_byte_ptrs_as_variables(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov [esp+4], 102030FBh')
        runner.run_command('mov al, byte ptr [esp+4]')
        runner.run_command('mov bl, byte ptr [esp+5]')
        runner.run_command('mov cl, byte ptr [esp+6]')
        runner.run_command('mov dl, byte ptr [esp+7]')
        self.assertEqual(runner.al, 0xFB)
        self.assertEqual(runner.bl, 0x30)
        self.assertEqual(runner.cl, 0x20)
        self.assertEqual(runner.dl, 0x10)
        runner.run_command('mov al, FFh')
        runner.run_command('mov bl, EEh')
        runner.run_command('mov cl, CCh')
        runner.run_command('mov dl, AAh')
        runner.run_command('mov     byte ptr [esp+4], al')
        runner.run_command('mov     byte ptr [esp+5], bl')
        runner.run_command('mov     byte ptr [esp+6], cl')
        runner.run_command('mov     byte ptr [esp+7], dl')
        runner.run_command('mov eax, [esp+4]')
        self.assertEqual(runner.eax, 0xAACCEEFF)

    def test_or_flags(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov eax, 0
            and     al, 1
            jz      short loc_4A825A""")
        self.assertTrue(res)

    def test_movsd(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.memstore(64, 0x10203040, 4)
        runner.memstore(68, 0x50607080, 4)
        runner.run_block("""
            mov     esi, 64
            mov     edi, 0
            mov     ecx, 2
            rep     movsd""")
        self.assertEqual(runner.memread(0, 4), 0x10203040)
        self.assertEqual(runner.memread(4, 4), 0x50607080)
        self.assertEqual(runner.esi, 72)
        self.assertEqual(runner.edi, 8)
        self.assertEqual(runner.ecx, 0)


    def test_byte_ptr_if_in_variable(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov [esp+4], 102030FBh')
        value, size = runner.get_value('[esp+4]')
        self.assertEqual(value, 0x102030FB)
        self.assertEqual(size, 4)
        # 1-byte ptr variable
        runner.define_variable('test_var', 0, 1)
        value, size = runner.get_value('[esp+4+test_var]')
        self.assertEqual(value, 0xFB)


    def test_byte_ptr_to_32bit_register(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov [esp+4], 102030FBh')
        runner.run_command('mov   esi, 5')
        runner.run_command('add   esi, esp')
        runner.run_command('movzx   esi, byte ptr [esi]')
        self.assertEqual(runner.esi, 0x30)

    def test_ptr_cmp(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        runner.run_command('mov [esp+4], 102030FBh')
        runner.run_command('mov   esi, 5')
        runner.run_command('mov   ebp, 102030h')
        runner.ZF = 0
        runner.run_command('cmp     ebp, [esp+esi]')
        self.assertEqual(runner.ZF, 1)

    def test_overflow_cmp(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov ah, 1
            mov bh, 255
            sub ah, bh
            cmp ah, 2
            jz _exit
        """)
        self.assertTrue(res)

    def test_overflow_test(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov ah, 1
            mov bh, 2
            sub ah, bh
            test ah, ah
            jl _exit
        """)
        self.assertTrue(res)

    def test_overflow_test_2(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov ah, 1
            mov bh, 2
            sub ah, bh
            test ah, ah
            jge _exit
        """)
        self.assertFalse(res)

    def test_overflow_test_3(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov ah, 1
            mov bh, 1
            sub ah, bh
            test ah, ah
            jl _exit
        """)
        self.assertFalse(res)

    def test_overflow_test_4(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov ah, 255
            mov bh, 250
            sub ah, bh
            test ah, ah
            jl _exit
        """)
        self.assertFalse(res)

    def test_add_negatives(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov eax, 0
            mov ebx, 0
            dec eax
            dec ebx
            add eax, ebx
            test eax, eax
            jl _exit
    """)
        self.assertTrue(res)

    def test_zero_leading_mov(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov ah, FEh
            movzx bx, ah
            movzx ecx, ah
        """)
        self.assertEqual(runner.bx, 0xFE)
        self.assertEqual(runner.ecx, 0xFE)

    def test_rol(self):
        runner = AsmRunner(asm_virtual_memory_size=128)
        res = runner.run_block("""
            mov eax, 120000FEh
            rol eax, 8
        """)
        self.assertEqual(runner.eax, 0xFE12)

    def test_moving_8bit_to_memory_should_not_erase_another_fields(self):
        runner = AsmRunner(asm_virtual_memory_size=16)
        for i in range(16):
            runner.memstore(i, 77, size=1)
        runner.run_block("""
            mov ecx, 8
            mov dl, 7Bh
            mov [ecx], dl
        """)
        self.assertEqual(' '.join('{:02x}'.format(x) for x in runner.asm_virtual_memory),
                         '4d 4d 4d 4d 4d 4d 4d 4d 7b 4d 4d 4d 4d 4d 4d 4d')

    def test_jge(self):
        runner = AsmRunner(asm_virtual_memory_size=16)
        res = runner.run_block("""
            mov     edi, 0
            sub     edi, 8
            test    edi, edi
            jge     short loc_4A853D
        """)
        self.assertFalse(res)
