"""
Adds morph targets to a GLB written by the gg-web-engine Blender exporter, which exports without them
(`export_morph=False` in its `exporter.py`).

`export_scenes` calls `add_glb_morph_targets` after Blender has written the GLB, with the sub-meshes that have
`morph_targets`. Every glTF vertex of the mesh (node name = sub-mesh name) is matched with the sub-mesh vertex at the
same position (and the same texture coordinates when positions alone are ambiguous): Blender reorders and splits
vertices, but the GLB positions are the OBJ ones, since the OBJ is imported with forward Y / up Z and exported without
Y-up conversion. Each target becomes a glTF morph target with a POSITION accessor of relative deltas, named in
`mesh.extras.targetNames` (three.js GLTFLoader reads them into `morphTargetDictionary`), with default weights 0.
"""

import json
import math
import struct
from typing import List, Tuple

from .mesh import SubMesh

_GLB_MAGIC = b'glTF'
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942
_FLOAT = 5126
_ARRAY_BUFFER = 34962
_COMPONENT_SIZES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_COMPONENT_FORMATS = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
_TYPE_SIZES = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def read_glb(path: str) -> Tuple[dict, bytes]:
    with open(path, 'rb') as f:
        data = f.read()
    magic, version, length = struct.unpack_from('<4sII', data, 0)
    if magic != _GLB_MAGIC or version != 2:
        raise ValueError(f'Not a glTF 2.0 binary file: {path}')
    offset = 12
    gltf, binary = None, b''
    while offset < length:
        chunk_length, chunk_type = struct.unpack_from('<II', data, offset)
        chunk = data[offset + 8 : offset + 8 + chunk_length]
        if chunk_type == _CHUNK_JSON:
            gltf = json.loads(chunk.decode('utf-8'))
        elif chunk_type == _CHUNK_BIN and not binary:
            binary = chunk
        offset += 8 + chunk_length
    if gltf is None:
        raise ValueError(f'GLB without JSON chunk: {path}')
    return gltf, binary


def write_glb(path: str, gltf: dict, binary: bytes):
    json_chunk = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    json_chunk += b' ' * (-len(json_chunk) % 4)
    binary += b'\x00' * (-len(binary) % 4)
    length = 12 + 8 + len(json_chunk) + (8 + len(binary) if binary else 0)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', _GLB_MAGIC, 2, length))
        f.write(struct.pack('<II', len(json_chunk), _CHUNK_JSON))
        f.write(json_chunk)
        if binary:
            f.write(struct.pack('<II', len(binary), _CHUNK_BIN))
            f.write(binary)


def read_accessor(gltf: dict, binary: bytes, index: int) -> List[tuple]:
    accessor = gltf['accessors'][index]
    view = gltf['bufferViews'][accessor['bufferView']]
    components = _TYPE_SIZES[accessor['type']]
    fmt = '<' + _COMPONENT_FORMATS[accessor['componentType']] * components
    item_size = struct.calcsize(fmt)
    stride = view.get('byteStride') or item_size
    start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    return [struct.unpack_from(fmt, binary, start + i * stride) for i in range(accessor['count'])]


def _append_vec3_accessor(gltf: dict, binary: bytearray, vectors: List[List[float]]) -> int:
    binary.extend(b'\x00' * (-len(binary) % 4))
    data = b''.join(struct.pack('<3f', *v) for v in vectors)
    gltf.setdefault('bufferViews', []).append(
        {'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data), 'target': _ARRAY_BUFFER}
    )
    binary.extend(data)
    # float32 values, like the data, so that min / max bound it exactly
    as_float32 = [struct.unpack('<3f', struct.pack('<3f', *v)) for v in vectors]
    gltf.setdefault('accessors', []).append(
        {
            'bufferView': len(gltf['bufferViews']) - 1,
            'componentType': _FLOAT,
            'count': len(vectors),
            'type': 'VEC3',
            'min': [min(v[i] for v in as_float32) for i in range(3)],
            'max': [max(v[i] for v in as_float32) for i in range(3)],
        }
    )
    return len(gltf['accessors']) - 1


def _close(a, b, tolerance: float) -> bool:
    return all(math.isclose(x, y, abs_tol=tolerance) for x, y in zip(a, b))


def _match_vertex(sub_mesh: SubMesh, position, uv, tolerance: float) -> int:
    """Index of the sub-mesh vertex exported as the glTF vertex at `position` with texture coordinates `uv`: one with
    the same position, or with the same texture coordinates among them too when the vertices at that position have
    different morph deltas"""
    pivot = sub_mesh.pivot_offset
    candidates = [
        i for i, v in enumerate(sub_mesh.vertices) if _close([v[k] - pivot[k] for k in range(3)], position, tolerance)
    ]

    def same_deltas(indices):
        return all(len({tuple(deltas[i]) for i in indices}) == 1 for deltas in sub_mesh.morph_targets.values())

    if candidates and not same_deltas(candidates) and uv is not None:
        candidates = [i for i in candidates if _close(sub_mesh.vertex_uvs[i], uv, tolerance)]
    if not candidates:
        raise ValueError(f'Mesh "{sub_mesh.name}": no vertex at {position} for the morph targets')
    if not same_deltas(candidates):
        raise ValueError(f'Mesh "{sub_mesh.name}": vertices at {position} have different morph deltas')
    return candidates[0]


def add_glb_morph_targets(glb_path: str, sub_meshes: List[SubMesh], tolerance: float = 1e-4):
    """Adds the `morph_targets` of `sub_meshes` to the meshes of the nodes with their names in the GLB file"""
    sub_meshes = [sm for sm in sub_meshes if sm.morph_targets]
    if not sub_meshes:
        return
    gltf, binary = read_glb(glb_path)
    binary = bytearray(binary)
    nodes = {node.get('name'): node for node in gltf.get('nodes', []) if 'mesh' in node}
    for sub_mesh in sub_meshes:
        node = nodes.get(sub_mesh.name)
        if node is None:
            raise ValueError(f'Cannot add morph targets: no mesh node "{sub_mesh.name}" in {glb_path}')
        mesh = gltf['meshes'][node['mesh']]
        target_names = list(sub_mesh.morph_targets.keys())
        for primitive in mesh['primitives']:
            positions = read_accessor(gltf, binary, primitive['attributes']['POSITION'])
            uv_accessor = primitive['attributes'].get('TEXCOORD_0')
            # the same as the sub-mesh ones: the OBJ has 1 - v, the glTF exporter flips V back
            uvs = read_accessor(gltf, binary, uv_accessor) if uv_accessor is not None else [None] * len(positions)
            matches = [_match_vertex(sub_mesh, p, uv, tolerance) for p, uv in zip(positions, uvs)]
            primitive['targets'] = [
                {'POSITION': _append_vec3_accessor(gltf, binary, [sub_mesh.morph_targets[name][i] for i in matches])}
                for name in target_names
            ]
        mesh['weights'] = [0.0] * len(target_names)
        mesh.setdefault('extras', {})['targetNames'] = target_names
    gltf['buffers'][0]['byteLength'] = len(binary) + (-len(binary) % 4)
    write_glb(glb_path, gltf, bytes(binary))
