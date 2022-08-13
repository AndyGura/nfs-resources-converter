import re

from library.utils.virtual_asm_flags import VirtualAsmFlags
from library.utils.virtual_asm_registers import AsmRegisters


class AsmRunner(AsmRegisters, VirtualAsmFlags):

    def __init__(self, *args, asm_virtual_memory_size=1024*1024, **kwargs):    # 1mb may be enough for everyone :)
        super().__init__(*args, **kwargs)
        self.asm_virtual_memory = bytearray(asm_virtual_memory_size)
        self.variables = dict()

    # dict: key is variable name, value is tuple of value and size
    variables: dict[str, tuple[int, int]]

    def get_register_signed_value(self, register_name):
        # if not self._is_register_name(register_name):
        #     raise Exception('Not a register')
        value = self.__getattribute__(register_name)
        size = self._get_variable_size_in_bytes(register_name)
        return (value
                if (value & (1 << (size * 8 - 1))) == 0
                else value - (1 << (size * 8))) # 255 must be -1, 254 -> -2, so -value + 255

    def memstore(self, offset, value: int, size: int):
        b = value.to_bytes(length=size, byteorder='little', signed=False)
        for i in range(len(b)):
            self.asm_virtual_memory[offset + i] = b[i]

    def memread(self, offset, size: int):
        return int.from_bytes(self.asm_virtual_memory[offset:offset+size], 'little', signed=False)

    def _push(self, value: int):
        self.esp = self.esp - 4
        self.memstore(self.esp, value, size=4)

    def _pop(self):
        value = self._memread_4(self.esp)
        self.esp = self.esp + 4
        return value

    def _memread_1(self, offset: int) -> int:
        return self.memread(offset, 1)

    def _memread_2(self, offset: int) -> int:
        return self.memread(offset, 2)

    def _memread_4(self, offset: int) -> int:
        return self.memread(offset, 4)

    def define_variable(self, name, value, ptr_size=None):
        if name in self.variables:
            raise Exception(f'Variable {name} is already defined')
        self.variables[name] = (value, ptr_size)

    def run_block(self, block: str):
        should_jump = None
        for command in [c.strip() for c in block.split('\n') if c.strip()]:
            if should_jump is not None:
                raise Exception('Cannot run command after jump')
            should_jump = self.run_command(command)
        return should_jump

    def _is_register_name(self, variable: str) -> bool:
        return variable in self.register_attrs

    def _get_ptr_size(self, ptr_string: str) -> int:
        operands_sizes = {self.variables[x][1] for x in re.split(r'[+-]', ptr_string) if x in self.variables}
        if len(operands_sizes) > 1:
            raise Exception(f'Cannot determine pointer size for {ptr_string}')
        try:
            return operands_sizes.pop()
        except KeyError:
            return None

    def _get_variable_size_in_bytes(self, variable: str) -> int:
        if self._is_register_name(variable):
            if variable.startswith('e'):
                return 4
            if variable.endswith('x'):
                return 2
            return 1
        if variable.startswith('[') and variable.endswith(']'):
            return self._get_ptr_size(variable[1:-1])
        return None

    # returns (value, size_in_bytes)
    def get_value(self, variable: str, force_size=None, is_pointer=False, optimistic=False) -> tuple[int, int]:
        if variable.startswith('byte ptr '):
            variable = variable[9:]
            force_size = 1
        # if register
        if self._is_register_name(variable):
            return (self.__getattribute__(variable), force_size or self._get_variable_size_in_bytes(variable))
        # if plain value
        value_match = re.match('^([\dA-Fa-f]+h?)$', variable)
        if value_match:
            str = value_match.groups(1)[0]
            if str.endswith('h'):
                return int(str[:-1], 16), force_size
            return int(str, 10), force_size
        # if memory pointer
        if variable.startswith('[') and variable.endswith(']'):
            ptr_str = variable[1:-1]
            size = self._get_ptr_size(ptr_str) or force_size or 4
            ptr, _ = self.get_value(ptr_str, is_pointer=True)
            if size is None:
                size = 4
            return self.memread(ptr, size), size
        # if math statement
        if '+' in variable or '-' in variable:
            variables = re.split(r'[+-]', variable)
            operands = re.findall(r'([+-])', variable)
            res, size = self.get_value(variables[0], force_size=force_size)
            for i in range(len(operands)):
                subres, subsize = self.get_value(variables[i + 1])
                if operands[i] == '+':
                    res += subres
                elif operands[i] == '-':
                    res -= subres
                elif operands[i] == '*':
                    res *= subres
                else:
                    raise NotImplementedError('Unknown operand ' + operands[i])
                if subsize is not None:
                    size = min(size, subsize) if is_pointer else max(size, subsize)
            return res, force_size or size
        if '*' in variable:
            variables = variable.split('*')
            res, size = self.get_value(variables[0], force_size=force_size)
            for i in range(len(variables) - 1):
                subres, subsize = self.get_value(variables[i + 1])
                res *= subres
                if subsize is not None:
                    size = max(size, subsize)
            return res, force_size or size
        if variable in self.variables:
            var = self.variables[variable]
            return var[0], force_size or var[1]
        if optimistic:
            return 0, 0
        raise Exception(f"Unknown variable '{variable}'")

    def set_value(self, variable: str, value: int, size: int = None):
        # wrap value
        variable_size = self._get_variable_size_in_bytes(variable) or size or 4
        max_value = 1 << (variable_size * 8)
        while value < 0:
            value += max_value
        while value >= max_value:
            value -= max_value
        # if register
        if hasattr(self, variable):
            self.__setattr__(variable, value)
            return value, self._get_variable_size_in_bytes(variable)
        # if memory pointer
        if (variable.startswith('[') or variable.startswith('byte ptr [')) and variable.endswith(']'):
            if variable.startswith('byte ptr '):
                variable = variable[9:]
                ptr_size = 1
            else:
                ptr_size = self._get_ptr_size(variable[1:-1]) or size or 4
            ptr, _ = self.get_value(variable[1:-1])
            self.memstore(ptr, value, size=ptr_size)
            return value, size
        if variable in self.variables:
            old_value, size = self.variables[variable]
            self.variables[variable] = value, size
            return value, size
        raise Exception(f"Unknown variable '{variable}'")

    def get_msb(self, value, size):
        return (value >> ((8 * size) - 1)) & 1

    def get_lsb(self, value):
        return (value & 0x1)

    # returns if should jump after this command
    def run_command(self, command: str):
        # print('ASM: ', command)
        search = re.search('^(\w+)\s+([\w\d,\s\[\]+\-:*]+)(\s;.*)?$', command)
        if not search:
            raise Exception(f"Cannot parse statement {command}")
        operator = search.group(1)
        args: list[str] = [x.strip() for x in search.group(2).split(',')]
        if operator not in ['lea']:
            sizes: list[int] = [self.get_value(x, optimistic=True)[1] for x in args]
            values: list[int] = [self.get_value(x, optimistic=True)[0] for x in args]
        if operator == 'push':
            value, size = values[0], sizes[0]
            if size != 4:
                raise Exception(f'Cannot push variable with size, {size}')
            self._push(value)
        elif operator == 'pop':
            self.set_value(args[0], self._pop(), 4)
        elif operator == 'sub':
            result = values[0] - values[1]
            self.set_value(args[0], result, sizes[0])
            self.set_flags("SUB", values[0], values[1], result, sizes[0])
        elif operator == 'add':
            result = values[0] + values[1]
            self.set_value(args[0], result, sizes[0])
            self.set_flags("ADD", values[0], values[1], result, sizes[0])
        elif operator == 'mov' or operator == 'movzx':
            self.set_value(args[0], self.get_value(args[1], force_size=self._get_variable_size_in_bytes(args[0]))[0], size=self._get_variable_size_in_bytes(args[1]))
        elif operator == 'shl':
            countmask = 0x1f
            result = values[0]
            tempcount = values[1] & countmask
            while tempcount:
                self.CF = self.get_msb(result, sizes[0])
                result = result * 2
                tempcount -= 1
            result = result & self.get_mask(sizes[0])
            self.set_value(args[0], result, sizes[0])
            self.set_flags("SHL", values[0], values[1], result, sizes[0])
        elif operator == 'shr':
            result = values[0] >> values[1]
            self.set_value(args[0], result, sizes[0])
            self.set_flags("SHR", values[0], values[1], result, sizes[0])
        elif operator in ['xor', 'or', 'and']:
            op2 = values[1] & self.get_mask(sizes[0])
            if operator == 'xor':
                result = values[0] ^ op2
            elif operator == 'or':
                result = values[0] | op2
            else:  # and
                result = values[0] & op2
            self.set_value(args[0], result, sizes[0])
            self.set_flags("LOGIC", values[0], values[1], result, sizes[0])
        elif operator == 'lea':
            assert args[1].startswith('[') and args[1].endswith(']')
            self.set_value(args[0], self.get_value(args[1][1:-1])[0])
        elif operator == 'inc':
            result = values[0] + 1
            self.set_value(args[0], result)
            oldcf = self.CF
            self.set_flags("INC", values[0], 1, result, sizes[0])
            self.CF = oldcf
        elif operator == 'dec':
            result = values[0] - 1
            self.set_value(args[0], result)
            oldcf = self.CF
            self.set_flags("DEC", values[0], 1, result, sizes[0])
            self.CF = oldcf
        elif operator == 'neg':
            result = -values[0]
            self.set_value(args[0], result, sizes[0])
            self.set_flags("NEG", values[0], 0, result, sizes[0])
        elif operator == 'test':
            self.set_flags("LOGIC", values[0], values[1], values[0] & values[1], sizes[0])
        elif operator == 'cmp':
            self.set_flags("CMP", values[0], values[1], values[0] - values[1], sizes[0])
        elif operator == 'call':
            sub_func = self.__getattribute__(args[0])
            self._push(1)
            sub_func()
            self._pop()
        elif operator == 'rep' and (args[0] == 'movsb' or args[0] == 'movsd'):
            size = 4 if args[0] == 'movsd' else 1
            rep_count = self.ecx
            while rep_count > 0:
                self.memstore(self.edi, self.memread(self.esi, size), size)
                if not self.DF:
                    self.edi += size
                    self.esi += size
                else:
                    self.edi -= size
                    self.esi -= size
                rep_count -= 1
            self.ecx = 0
        elif operator == 'rol':
            size = sizes[0]
            op1value = values[0]
            op2value = values[1] & self.get_mask(size)
            tempcount = (op2value & 0x1f) % (size * 8)
            if tempcount > 0:
                while tempcount:
                    tempcf = self.get_msb(op1value, sizes[0])
                    op1value = (op1value * 2) + tempcf
                    tempcount -= 1
                self.CF = self.get_lsb(op1value)
                if op2value == 1:
                    self.OF = self.get_msb(op1value,  sizes[0]) ^ self.CF
            self.set_value(args[0], op1value)
        # Mnemonic        Condition tested  Description
        # jo              OF = 1            overflow
        # jno             OF = 0            not overflow
        # jc, jb, jnae    CF = 1            carry / below / not above nor equal
        # jnc, jae, jnb   CF = 0            not carry / above or equal / not below
        # je, jz          ZF = 1            equal / zero
        # jne, jnz        ZF = 0            not equal / not zero
        # jbe, jna        CF or ZF = 1      below or equal / not above
        # ja, jnbe        CF or ZF = 0      above / not below or equal
        # js              SF = 1            sign
        # jns             SF = 0            not sign
        # jp, jpe         PF = 1            parity / parity even
        # jnp, jpo        PF = 0            not parity / parity odd
        # jl, jnge        SF xor OF = 1     less / not greater nor equal
        # jge, jnl        SF xor OF = 0     greater or equal / not less
        # jle, jng    (SF xor OF) or ZF = 1 less or equal / not greater
        # jg, jnle    (SF xor OF) or ZF = 0 greater / not less nor equal
        elif operator == 'jb':
            return self.CF == 1
        elif operator == 'jnb':
            return self.CF == 0
        elif operator == 'jz':
            return self.ZF == 1
        elif operator == 'jnz':
            return self.ZF == 0
        elif operator == 'jbe':
            return self.CF == 1 or self.ZF == 1
        elif operator == 'jl':
            return self.SF != self.OF
        elif operator == 'jge':
            return self.SF == self.OF
        elif operator == 'jle':
            return (self.SF != self.OF) or self.ZF == 1
        elif operator == 'js':
            return self.SF == 1
        elif operator == 'jns':
            return self.SF == 0
        elif operator == 'jmp':
            return True
        else:
            raise Exception(f"Unknown command '{command}'")
