def register_maker(name):
    storage_name = '_' + name.lower()

    @property
    def prop(self):
        return getattr(self, storage_name)

    @prop.setter
    def prop(self, value):
        value = value & ((1 << 32) - 1)
        setattr(self, storage_name, value)

    return prop


def child_register_maker(name, size_bytes, master_register, offset_bits):

    mask = ((1 << size_bytes * 8) - 1) << offset_bits
    reverse_mask = ((1 << 32) - 1) & ~mask
    max_val = (1 << (size_bytes * 8) - 1)

    @property
    def prop(self):
        val = (getattr(self, master_register) & mask) >> offset_bits
        return val

    @prop.setter
    def prop(self, value):
        value = value & ((1 << (size_bytes * 8)) - 1)
        setattr(self, master_register,
                (getattr(self, master_register) & reverse_mask) | (value << offset_bits))

    return prop


def create_asm_registers(classname):
    class Class: pass
    Class.__name__ = classname
    setattr(Class, 'register_attrs', [
        'esi', 'edi', 'esp', 'ebp',
        'eax', 'ebx', 'ecx', 'edx',
        'ax', 'bx', 'cx', 'dx',
        'ah', 'bh', 'ch', 'dh',
        'al', 'bl', 'cl', 'dl',
    ])
    for key in ['esi', 'edi', 'esp', 'ebp']:
        setattr(Class, f'_{key}', 0)
        setattr(Class, key, register_maker(key))
    for key in ['a', 'b', 'c', 'd']:
        # extended register
        setattr(Class, f'_e{key}x', 0)
        setattr(Class, f'e{key}x', register_maker(f'e{key}x'))
        # 16-bit registers
        setattr(Class, f'{key}x', child_register_maker(f'{key}x', 2, f'_e{key}x', 0))
        # high 8-bit registers
        setattr(Class, f'{key}h', child_register_maker(f'{key}h', 1, f'_e{key}x', 8))
        # low 8-bit registers
        setattr(Class, f'{key}l', child_register_maker(f'{key}l', 1, f'_e{key}x', 0))
    return Class


AsmRegisters = create_asm_registers('AsmRegisters')
