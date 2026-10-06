import struct
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    ArrayBlock,
    BytesBlock,
)
from library.read_blocks.misc.value_validators import Eq

# NFS6 (Hot Pursuit 2) models (track compartments "compNN.o", "levelG.o", "trackg.o", "skyg.o", cars "car.o" etc.) are compiled
# EAGL (EA Graphics Library) models: 32-bit little-endian MIPS ELF relocatable object files. Everything lives in
# the ".data" section; named symbols point to the model parts, and relocations of ".data" are pointers between them.
# Symbols this module relies on:
#  - "__RenderMethod:::<name>" - a draw call. Word 0 points to the command list of its "__geoprimdatabuffer_*",
#    word 2 is relocated against "<microcode>__EAGLMicroCode" (the shader: NamedTexture, ShadowTexture,
#    BlendedOverlay, ...). Then go (count, pointer) pairs of shader parameters, incl. the textures
#    ("__EAGL::TAR:::*"), the vertex buffer and the index buffer with the real index count
#  - "__geoprimdatabuffer_*" - one word, followed by a command list. Command header word is (opcode << 16 | length
#    in words, including the header). Opcode 0x04 (tracks) or 0x4B (cars) declares a vertex buffer (args: 0, stride,
#    D3D FVF, -1, -1, pointer, vertex count, ...), opcode 0x07 draws an indexed triangle strip (args: primitive type, -1, -1, pointer to
#    16-bit indices, index count padded to even number), opcode 0x11 ends the list
#  - "__EAGL::TAR:::tar_NNNN_*" - texture reference. Bytes 4..8 are the name of the image in the FSH file: "track.fsh"
#    (in "persist.viv") for compartments, "level.fsh" for "levelG.o", "sky.fsh" for "skyg.o", "car.fsh" (wheels, in
#    "car.viv") or "skin" image of "skinNN.fsh" (paint, in "skin.viv") for cars
#  - "__Model:::<name>" - the model. Car models have geometry names ("ALPHA_OPAQUE_HOODShape",
#    "ALPHA_TRANS_WINShape~EASVehicleGlass", ...) of render methods "__GPRenderMethod_<name>_<i>" (`_eagl_geometry_names`)
#  - "__Skeleton:::<name>", "__Bone:::<name>.<bone>" - car skeleton ("skeleton.o", `read_eagl_skeleton`)
# Vertex positions are in world (model) space, Y is up. Cars: X right, front at -Z (right-handed, a mirrored export
# shows the license plate text mirrored). Vertex format is D3D FVF: position, blend weight (cars, always 0), normal
# (cars), diffuse color (BGRA) and 1..4 UV sets. UV set i belongs to texture n-1-i of the render method (n textures)

FVF_POSITION_MASK = 0xE
FVF_XYZ = 0x2
FVF_XYZB1 = 0x6
FVF_NORMAL = 0x10
FVF_DIFFUSE = 0x40
FVF_SPECULAR = 0x80

ELF_HEADER_SIZE = 52


class EaglSectionHeader(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'ELF32 section header'}

    class Fields(DeclarativeCompoundBlock.Fields):
        name_offset = (IntegerBlock(length=4), {'description': 'Offset of section name in the section names table'})
        section_type = (
            IntegerBlock(length=4),
            {'description': '1: program data (".data"), 2: symbol table, 3: string table, 9: relocations'},
        )
        flags = (IntegerBlock(length=4), {'description': 'Section flags'})
        address = (IntegerBlock(length=4), {'description': 'Virtual address, always 0'})
        offset = (IntegerBlock(length=4), {'description': 'Offset of section data in the file'})
        size = (IntegerBlock(length=4), {'description': 'Size of section data in bytes'})
        link = (IntegerBlock(length=4), {'description': 'Index of related section (string table of symbol table)'})
        info = (
            IntegerBlock(length=4),
            {'description': 'Extra info (for relocations: index of the section the relocations apply to)'},
        )
        alignment = (IntegerBlock(length=4), {'description': 'Section alignment'})
        entry_size = (IntegerBlock(length=4), {'description': 'Size of table entry, if section is a table'})


class EaglModel(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EAGL model, used by NFS6 for track compartments, sky, cars and other geometry. A 32-bit '
            'little-endian MIPS ELF relocatable object file with model data in ".data" section, where named symbols '
            'point to render methods, vertex/index buffers and texture references',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        magic = (IntegerBlock(length=4, value_validator=Eq(0x464C457F)), {'description': 'ELF magic "\\x7fELF"'})
        file_class = (IntegerBlock(length=1), {'description': '1: 32-bit'})
        data_encoding = (IntegerBlock(length=1), {'description': '1: little-endian'})
        elf_version = (IntegerBlock(length=1), {'description': 'Always 1'})
        os_abi = (IntegerBlock(length=1), {'description': 'Always 0'})
        padding = (BytesBlock(length=8), {'usage': 'io,doc', 'description': 'Zeros'})
        object_type = (IntegerBlock(length=2), {'description': '1: relocatable object file'})
        machine = (IntegerBlock(length=2), {'description': '8: MIPS'})
        version = (IntegerBlock(length=4), {'description': 'Always 1'})
        entry = (IntegerBlock(length=4), {'description': 'Entry point, always 0'})
        program_headers_offset = (IntegerBlock(length=4), {'description': 'Always 0, no program headers'})
        section_headers_offset = (IntegerBlock(length=4), {'description': 'Offset of section headers table'})
        flags = (IntegerBlock(length=4), {'description': 'MIPS flags'})
        header_size = (IntegerBlock(length=2), {'description': 'Size of this header, 52'})
        program_header_size = (IntegerBlock(length=2), {'description': 'Always 0'})
        program_headers_count = (IntegerBlock(length=2), {'description': 'Always 0'})
        section_header_size = (IntegerBlock(length=2), {'description': 'Size of section header, 40'})
        section_headers_count = (IntegerBlock(length=2), {'description': 'Amount of sections'})
        section_names_index = (
            IntegerBlock(length=2),
            {'description': 'Index of the section with section names'},
        )
        sections_data = (
            BytesBlock(length=(lambda ctx: ctx.data('section_headers_offset') - 52, 'section_headers_offset - 52')),
            {
                'usage': 'io,doc',
                'description': 'Sections: ".data" with the model, ".shstrtab" and ".strtab" string tables, ".symtab" '
                'symbol table (16-byte records: name offset, value, size, info, other, section index) and '
                '".rel.data" relocations of ".data" (8-byte records: offset, symbol index << 8 | type)',
            },
        )
        section_headers = (
            ArrayBlock(child=EaglSectionHeader(), length=lambda ctx: ctx.data('section_headers_count')),
            {'description': 'Section headers table'},
        )
        trailing_bytes = (
            BytesBlock(length=(lambda ctx: ctx.read_bytes_remaining, 'up to end of file')),
            {
                'usage': 'io,doc',
                'description': 'Zeros after section headers, usually none. Car "skeleton.o" has 40 of them: a '
                'section header slot of absent relocations section',
            },
        )

    def serializer_class(self):
        from serializers import EaglModelSerializer

        return EaglModelSerializer


@dataclass
class EaglMesh:
    name: str
    shader: str
    # texture names (aliases of FSH images), in render method order
    textures: List[str]
    vertices: List[Tuple[float, float, float]]
    # RGBA ints (0xRRGGBBAA), empty if vertex format has no diffuse color
    colors: List[int]
    uv_sets: List[List[Tuple[float, float]]]
    triangles: List[Tuple[int, int, int]] = field(default_factory=list)
    # name of the model geometry, drawn by this render method ("ALPHA_OPAQUE_HOODShape", ...), if model has names
    geometry_name: Optional[str] = None

    @property
    def main_texture_index(self) -> Optional[int]:
        """Index of the texture, which is drawn as base one. The first texture of "*Shadow*" shaders is a shadow
        map"""
        first = 1 if 'Shadow' in self.shader else 0
        return first if first < len(self.textures) else None

    @property
    def main_texture(self) -> Optional[str]:
        i = self.main_texture_index
        return self.textures[i] if i is not None else None

    @property
    def main_uvs(self) -> List[Tuple[float, float]]:
        i = self.main_texture_index
        if i is None or not self.uv_sets:
            return []
        return self.uv_sets[max(0, min(len(self.uv_sets) - 1, len(self.textures) - 1 - i))]


class _EaglElf:
    """Symbols and relocations of EAGL model ".data" section"""

    def __init__(self, data: dict):
        body = data['sections_data']
        headers = data['section_headers']

        def section_bytes(h):
            start = h['offset'] - ELF_HEADER_SIZE
            return body[start : start + h['size']]

        def string_at(table: bytes, offset: int) -> str:
            end = table.index(b'\0', offset)
            return table[offset:end].decode('latin-1')

        names = section_bytes(headers[data['section_names_index']])
        self.data_index = next(
            i for i, h in enumerate(headers) if h['section_type'] == 1 and string_at(names, h['name_offset']) == '.data'
        )
        self.data = section_bytes(headers[self.data_index])
        symtab_header = next(h for h in headers if h['section_type'] == 2)
        symtab = section_bytes(symtab_header)
        strtab = section_bytes(headers[symtab_header['link']])
        # (name, value, section index)
        self.symbols = []
        for i in range(len(symtab) // 16):
            name_offset, value, _, _, _, section_index = struct.unpack_from('<IIIBBH', symtab, 16 * i)
            self.symbols.append((string_at(strtab, name_offset), value, section_index))
        # offset in .data -> symbol
        self.relocations = {}
        for h in headers:
            if h['section_type'] == 9 and h['info'] == self.data_index:
                rel = section_bytes(h)
                for i in range(len(rel) // 8):
                    offset, info = struct.unpack_from('<II', rel, 8 * i)
                    self.relocations[offset] = self.symbols[info >> 8]
        self.data_symbols = {value: name for (name, value, idx) in self.symbols if idx == self.data_index and name}
        self.data_symbol_offsets = sorted(self.data_symbols)

    def u32(self, offset: int) -> int:
        return struct.unpack_from('<I', self.data, offset)[0]

    def pointer(self, offset: int) -> Optional[int]:
        """Target offset in .data of a relocated word, None if the word is not a pointer to .data"""
        symbol = self.relocations.get(offset)
        if symbol is None or symbol[2] != self.data_index:
            return None
        return self.u32(offset) + symbol[1]

    def symbol_end(self, offset: int) -> int:
        i = bisect_right(self.data_symbol_offsets, offset)
        return self.data_symbol_offsets[i] if i < len(self.data_symbol_offsets) else len(self.data)

    def commands(self, offset: int):
        while offset + 4 <= len(self.data):
            word = self.u32(offset)
            opcode, length = word >> 16, word & 0xFFFF
            if length == 0:
                return
            yield opcode, [self.u32(offset + 4 * i) for i in range(1, length)]
            if opcode == 0x11:
                return
            offset += 4 * length


def _decode_vertices(elf: _EaglElf, stride: int, fvf: int, pointer: int, count: int):
    texture_sets = (fvf >> 8) & 0xF
    # D3DFVF_XYZB1 (0x6)..D3DFVF_XYZB5 (0xE): position followed by 1..5 blend weights (car models: one, always 0)
    blend_weights = max(0, ((fvf & FVF_POSITION_MASK) - FVF_XYZB1) // 2 + 1)
    vertices, colors, uv_sets = [], [], [[] for _ in range(texture_sets)]
    for i in range(count):
        o = pointer + i * stride
        vertices.append(struct.unpack_from('<3f', elf.data, o))
        o += 12 + 4 * blend_weights
        if fvf & FVF_NORMAL:
            o += 12
        if fvf & FVF_DIFFUSE:
            b, g, r, a = elf.data[o : o + 4]
            colors.append(r << 24 | g << 16 | b << 8 | a)
            o += 4
        if fvf & FVF_SPECULAR:
            o += 4
        for uvs in uv_sets:
            uvs.append(struct.unpack_from('<2f', elf.data, o))
            o += 8
    return vertices, colors, uv_sets


def _strip_to_triangles(indices: List[int], vertex_count: int) -> List[Tuple[int, int, int]]:
    triangles = []
    for i in range(len(indices) - 2):
        a, b, c = indices[i : i + 3]
        if a == b or b == c or a == c or max(a, b, c) >= vertex_count:
            continue
        triangles.append((b, a, c) if i % 2 else (a, b, c))
    return triangles


def _string_at(elf: _EaglElf, offset: int) -> Optional[str]:
    end = elf.data.find(b'\0', offset)
    return elf.data[offset:end].decode('latin-1') if end >= 0 else None


def _eagl_geometry_names(elf: _EaglElf) -> Dict[str, str]:
    """Render method symbol suffix ("<model>_<i>") -> geometry name. Car models ("__Model:::car") have the amount of
    geometries at offset 0x9C of the model and a pointer to the table of their name pointers at 0xA0, i-th geometry
    is drawn by render method "__GPRenderMethod_<model>_<i>". Geometry names end with "~<microcode>" if it is not
    the default one: "ALPHA_TRANS_WINShape~EASVehicleGlass"""
    names = {}
    for symbol, model, section_index in elf.symbols:
        if section_index != elf.data_index or not symbol.startswith('__Model:::') or '.' in symbol:
            continue
        model_name = symbol.split(':::')[-1]
        if model + 0xA4 > len(elf.data):
            continue
        count, table = elf.u32(model + 0x9C), elf.pointer(model + 0xA0)
        if table is None or not 0 < count <= 1024:
            continue
        for i in range(count):
            name_pointer = elf.pointer(table + 4 * i)
            name = _string_at(elf, name_pointer) if name_pointer is not None else None
            if not name:
                break
            names[f'{model_name}_{i}'] = name
    return names


def read_eagl_meshes(data: dict) -> List[EaglMesh]:
    """Meshes of EAGL model (`EaglModel` data), one per render method"""
    elf = _EaglElf(data)
    geometry_names = _eagl_geometry_names(elf)
    meshes = []
    for name, rm, section_index in elf.symbols:
        if section_index != elf.data_index or not name.startswith('__RenderMethod:::'):
            continue
        shader_symbol = elf.relocations.get(rm + 8)
        shader = shader_symbol[0].replace('__EAGLMicroCode', '') if shader_symbol else ''
        # pointers in render method: textures, vertex and index buffers. Each pointer is preceded by item count
        textures = []
        pointers = {}
        for o in range(rm, elf.symbol_end(rm), 4):
            target = elf.pointer(o)
            if target is None:
                continue
            target_name = elf.data_symbols.get(target, '')
            if target_name.startswith('__EAGL::TAR:::'):
                textures.append(elf.data[target + 4 : target + 8].decode('latin-1'))
            pointers.setdefault(target, elf.u32(o - 4))
        commands_start = elf.pointer(rm)
        if commands_start is None:
            continue
        mesh = None
        for opcode, args in elf.commands(commands_start):
            if opcode in (0x04, 0x4B) and len(args) >= 7:
                stride, fvf, pointer, count = args[1], args[2], args[5], args[6]
                vertices, colors, uv_sets = _decode_vertices(elf, stride, fvf, pointer, count)
                mesh = EaglMesh(
                    name=name.split(':::')[-1],
                    shader=shader,
                    textures=textures,
                    vertices=vertices,
                    colors=colors,
                    uv_sets=uv_sets,
                    geometry_name=geometry_names.get(name.split('__GPRenderMethod_')[-1]),
                )
                meshes.append(mesh)
            elif opcode == 0x07 and len(args) >= 5 and mesh is not None:
                pointer, count = args[3], args[4]
                # index count in the command is padded to even number, render method has the real one
                real_count = pointers.get(pointer, count)
                if not 0 < real_count <= count:
                    real_count = count
                indices = struct.unpack_from(f'<{real_count}H', elf.data, pointer)
                mesh.triangles.extend(_strip_to_triangles(list(indices), len(mesh.vertices)))
    return meshes


def eagl_model_name(data: dict) -> Optional[str]:
    """Name of the model ("trackft", "skyfs", ...), from "__Model:::<name>" symbol"""
    elf = _EaglElf(data)
    return next((name.split(':::')[-1] for (name, _, _) in elf.symbols if name.startswith('__Model:::')), None)


@dataclass
class EaglBone:
    name: str
    # index of parent bone, -1 for the root
    parent: int
    # bind pose position in model space
    position: Tuple[float, float, float]


def read_eagl_skeleton(data: dict) -> List[EaglBone]:
    """Bones of EAGL skeleton (NFS6 car "skeleton.o"). "__Skeleton:::<name>" is followed by bone count at offset 8
    and 0x70-byte bone records at offset 0x10: scale (3 floats), parent index, rotation quaternion (x, y, z, w),
    local translation (3 floats), bone index, inverse bind pose matrix (4x4 floats, row vectors). Bone names are
    "__Bone:::<skeleton>.<name>" symbols with value 16 * bone index. Empty list if the model has no skeleton"""
    elf = _EaglElf(data)
    skeleton = next(
        (v for (name, v, idx) in elf.symbols if idx == elf.data_index and name.startswith('__Skeleton:::')), None
    )
    if skeleton is None:
        return []
    names = {
        v // 16: name.split(':::')[-1].split('.', 1)[-1]
        for (name, v, idx) in elf.symbols
        if idx == elf.data_index and name.startswith('__Bone:::')
    }
    count = elf.u32(skeleton + 8)
    bones = []
    for i in range(count):
        record = skeleton + 0x10 + 0x70 * i
        if record + 0x70 > len(elf.data):
            break
        parent = struct.unpack_from('<i', elf.data, record + 0xC)[0]
        m = struct.unpack_from('<16f', elf.data, record + 0x30)
        # inverse bind pose maps model space to bone space: p * R + t = 0 for the bone origin, so p = -t * R^T
        t = m[12:15]
        position = tuple(-sum(t[j] * m[4 * k + j] for j in range(3)) for k in range(3))
        bones.append(EaglBone(name=names.get(i, f'bone_{i}'), parent=parent, position=position))
    return bones
