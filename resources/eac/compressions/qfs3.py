from io import BufferedReader

from buffer_utils import read_short, read_int
from parsers.utils.asm_runner import AsmRunner
from resources.eac.compressions.base import BaseCompressionAlgorithm


class Qfs3Compression(BaseCompressionAlgorithm, AsmRunner):

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
        self.accumulator = (read_short(buffer, 'big') | (self.accumulator << 16))

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
        file_header = self.accumulator = read_short(buffer, 'big')
        self.read_next(buffer)
        self.esi = self.accumulator << 16
        # if compressed size presented
        if file_header & 0x100:
            self.edx = read_int(buffer, 'big')
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
                self.edx += (1 << self.al)
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
