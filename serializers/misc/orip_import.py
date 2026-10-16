"""ORIP geometry (TNFS car models in CFM, track props in FAM) built from an OBJ + MTL, the inverse of what
`OripGeometrySerializer` exports: the polygons of the OBJ replace the ones of the ORIP loaded in the file, and what an
OBJ cannot hold is taken from that ORIP (the "current" one) or derived from the geometry:

- quads come back from the triangle pairs the export writes ((0, 1, 2) + (0, 2, 3), or (0, 2, 1) + (0, 3, 2) for
  `flip_normal`), two-sided polygons from a polygon followed by its reverse; OBJ quads stay quads, bigger faces are
  split in triangles. Texture coordinates equal to the corners of the texture are written as a polygon without
  `use_uv`, as the export makes them. Line polygons, chains and `alt_rasterizer` are not exported, so not imported
- labels and partitions from the mesh names ("lbl__<label>__<texture>", "__<partition>" suffix,
  `orip_sub_mesh_names`); the main partition of a mesh from the `objects` of "<obj name>_extra.json", else from the
  mesh of that name in the current ORIP, else wheel quads go to `outside`, other polygons to `surface`
- textures from the MTL: the material name when it is a FSH bitmap name (4 bytes at most, as the export names them),
  else the file name of its `map_Kd` texture. A material without `map_Kd`, with `Kd`, of no bitmap of the FSH is a
  flat colour polygon. UVs are scaled to texels with the size of the `map_Kd` image, else of the FSH bitmap
- material fields (names like `frntires`, colours) and the colour key / textured bits of the polygon type from the
  current polygons with the same texture, colour key of a new texture from the alpha of its PNG; materials no polygon
  uses (`tire1`..`tire4`, `pal`) are kept
- `fx_polys`: the wheel ground points `FL0`..`RR1` are the bottom corners of the wheel quads (labels `lt_frnt`...),
  the others are put at the position of the dummy "fx_<name>" of the extras file, else stay where they are in the
  current ORIP
- morphs: kept when all their moved vertices are still there, else made again for the front wheel quad and its `circ`
  quad, turned by 30 degrees (about weight 1.0 in the game)"""

import json
import math
import os
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from library.exceptions import DataIntegrityException
from serializers.common.three_d.obj_reader import read_obj, ObjMaterial
from serializers.geometries import ORIP_DRAWN_PARTITIONS, orip_sub_mesh_names, is_orip_name

# label of a wheel quad -> (fx_polys prefix of its ground points, material name, morph name turning it)
WHEEL_LABELS = {
    'lt_frnt': ('FL', b'frntires', 'left_tur'),
    'rt_frnt': ('FR', b'frntires', 'right_tu'),
    'lt_rear': ('RL', b'rertires', None),
    'rt_rear': ('RR', b'rertires', None),
}
MORPH_WHEEL_LABELS = {morph: label for label, (_, _, morph) in WHEEL_LABELS.items() if morph}
# the angle of a generated wheel morph (weight 1.0 in the game is about 30 degrees of wheel turn)
MORPH_ANGLE = math.radians(30)
# texture coordinates the export gives the corners of a polygon without `use_uv`
DEFAULT_UVS = [(0, 0), (1, 0), (1, 1), (0, 1)]
PARTITION_SUFFIXES = (*ORIP_DRAWN_PARTITIONS, 'none')
PARTITION_UNKNOWN_0X0C = {'inside': 1, 'surface': 0, 'outside': -1}


class _Polygon:
    def __init__(self, corners, mesh_name: str, material: Optional[str], flip=False):
        # (quantized position (x, y, z) in ORIP space, (u, v) in texture size units or None)
        self.corners = corners
        self.mesh_name = mesh_name
        self.material = material
        self.flip = flip
        self.two_sided = False
        self.label = None
        self.partition = None
        self.texture = ''

    def keys(self):
        return [(p, None if uv is None else (round(uv[0], 5), round(uv[1], 5))) for p, uv in self.corners]

    def winding(self):
        keys = self.keys()
        return keys[::-1] if self.flip else keys

    def is_reverse_of(self, other: '_Polygon') -> bool:
        if len(self.corners) != len(other.corners) or self.material != other.material:
            return False
        reverse = other.winding()[::-1]
        mine = self.winding()
        return any(mine[i:] + mine[:i] == reverse for i in range(len(mine)))


def _merge_triangles(t1: _Polygon, t2: _Polygon) -> Optional[_Polygon]:
    """The quad the export split in t1 and t2, or None"""
    if len(t1.corners) != 3 or len(t2.corners) != 3 or t1.material != t2.material:
        return None
    a, b = t1.keys(), t2.keys()
    if b[0] != a[0]:
        return None
    if b[1] == a[2] and len({a[0], a[1], a[2], b[2]}) == 4:
        corners, flip = [t1.corners[0], t1.corners[1], t1.corners[2], t2.corners[2]], False
    elif b[2] == a[1] and len({a[0], a[1], a[2], b[1]}) == 4:
        corners, flip = [t1.corners[0], t1.corners[2], t1.corners[1], t2.corners[1]], True
    else:
        return None
    return _Polygon(corners, t1.mesh_name, t1.material, flip)


def _object_polygons(faces: List[_Polygon]) -> List[_Polygon]:
    polygons = []
    i = 0
    while i < len(faces):
        quad = _merge_triangles(faces[i], faces[i + 1]) if i + 1 < len(faces) else None
        if quad:
            polygons.append(quad)
            i += 2
            continue
        face = faces[i]
        i += 1
        if len(face.corners) > 4:
            polygons.extend(
                _Polygon([face.corners[0], face.corners[j], face.corners[j + 1]], face.mesh_name, face.material)
                for j in range(1, len(face.corners) - 1)
            )
        elif len(face.corners) >= 3:
            polygons.append(face)
    for polygon in polygons:
        # a triangle with the corner texture coordinates in (0, 2, 1) order: a flipped one without `use_uv`
        uvs = [uv for _, uv in polygon.corners]
        if len(polygon.corners) == 3 and not polygon.flip and uvs == [DEFAULT_UVS[0], DEFAULT_UVS[2], DEFAULT_UVS[1]]:
            polygon.corners = [polygon.corners[0], polygon.corners[2], polygon.corners[1]]
            polygon.flip = True
    result = []
    for polygon in polygons:
        if result and result[-1].is_reverse_of(polygon) and not result[-1].two_sided:
            result[-1].two_sided = True
        else:
            result.append(polygon)
    return result


def _round_uv(uv):
    # the export writes texel / size: snap the float noise of the text, so that corners compare equal
    return tuple(round(x * 2**20) / 2**20 for x in uv)


def _parse_mesh_name(name: str, texture: str) -> Tuple[str, Optional[str], Optional[str]]:
    """(mesh name without the partition suffix, label, partition suffix or None) of an exported mesh name"""
    name = re.sub(r'\.\d{3}$', '', name)  # suffix of Blender for repeated names
    parts = name.split('__')
    label = None
    rest = parts
    if len(parts) >= 2 and parts[0] == 'lbl':
        label, rest = parts[1], parts[2:]
    partition = None
    if rest and rest[-1] in PARTITION_SUFFIXES and (len(rest) > 1 or rest[-1] != texture):
        partition = rest[-1]
        name = name[: -len(partition) - 2]
    return name, label, partition


def texture_alias(material_name: Optional[str], materials: Dict[str, ObjMaterial]) -> Optional[str]:
    """FSH bitmap name of an OBJ material: its name when it is one (4 bytes at most, as the export names them), else
    the file name of its `map_Kd` texture; '' without a material, None when neither fits"""
    if material_name is None:
        return ''
    if len(material_name.encode('utf-8')) <= 4:
        return material_name
    material = materials.get(material_name)
    if material and material.texture_path:
        stem = os.path.splitext(os.path.basename(material.texture_path))[0]
        if len(stem.encode('utf-8')) <= 4:
            return stem
    return None


def obj_texture_files(obj_path: str) -> Dict[str, str]:
    """FSH bitmap name -> image file of the textures the OBJ uses: the `map_Kd` files of its materials, else
    "assets/<name>.png" next to it (where the export puts them), when the file is there"""
    objects, materials = read_obj(obj_path)
    result = {}
    for material_name in {face.material for obj in objects for face in obj.faces if face.material is not None}:
        alias = texture_alias(material_name, materials)
        if not alias:
            continue
        material = materials.get(material_name)
        path = material.texture_path if material and material.texture_path else None
        if not path or not os.path.isfile(path):
            path = os.path.join(os.path.dirname(obj_path), 'assets', f'{alias}.png')
        if os.path.isfile(path):
            result[alias] = path
    return result


def _image_size(path: Optional[str]) -> Optional[Tuple[int, int]]:
    if not path or not os.path.isfile(path):
        return None
    from PIL import Image

    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def _has_transparency(path: Optional[str]) -> bool:
    if not path or not os.path.isfile(path):
        return False
    from PIL import Image

    try:
        with Image.open(path) as image:
            alpha = image.convert('RGBA').getchannel('A')
            return alpha.getextrema()[0] < 128
    except Exception:
        return False


def orip_from_obj(
    obj_path: str,
    current: dict,
    shpi_textures: Dict[str, Tuple[int, int]],
    fraction_bits: int,
) -> Tuple[dict, str]:
    """ORIP data from the OBJ (with its MTL and "<obj name>_extra.json" next to it), replacing the geometry of
    `current`. `shpi_textures`: bitmap name -> (width, height) of the FSH next to the ORIP. `fraction_bits`: of the
    vertex coordinates (7 in CFM, 4 in FAM). Returns the data and a summary for the user"""
    objects, materials = read_obj(obj_path)
    extras = {}
    extras_path = os.path.splitext(obj_path)[0] + '_extra.json'
    if os.path.isfile(extras_path):
        with open(extras_path) as f:
            extras = json.load(f)
    scale = 1 << fraction_bits
    warnings = []

    def quantize(v):
        # OBJ axes are the ORIP axes with y and z swapped (the export swaps them)
        return round(v[0] * scale), round(v[2] * scale), round(v[1] * scale)

    # 1. polygons with their mesh name, label, texture
    polygons: List[_Polygon] = []
    texture_names: Dict[Optional[str], str] = {}
    unknown_materials = set()

    def texture_name(material_name: Optional[str]) -> str:
        if material_name not in texture_names:
            alias = texture_alias(material_name, materials)
            if alias is None:
                unknown_materials.add(material_name)
            texture_names[material_name] = alias or ''
        return texture_names[material_name]

    for obj in objects:
        faces = [
            _Polygon(
                [
                    (quantize(v), None if face.uvs is None else _round_uv((face.uvs[i][0], 1 - face.uvs[i][1])))
                    for i, v in enumerate(face.vertices)
                ],
                obj.name,
                face.material,
            )
            for face in obj.faces
        ]
        for polygon in _object_polygons(faces):
            polygon.texture = texture_name(polygon.material)
            polygon.mesh_name, polygon.label, polygon.partition = _parse_mesh_name(obj.name, polygon.texture)
            polygons.append(polygon)
    if unknown_materials:
        raise DataIntegrityException(
            'ORIP textures are FSH bitmaps with names of 4 bytes at most: name the materials (or their map_Kd files) '
            f'after the bitmaps. Materials with other names: {", ".join(sorted(unknown_materials))}'
        )
    if not polygons:
        raise DataIntegrityException(f'No polygons in {os.path.basename(obj_path)}')

    # 2. partitions
    current_partition_names = [p['name'] for p in current['partitions']]
    current_drawn = [n for n in current_partition_names if n.lower() in ORIP_DRAWN_PARTITIONS]
    current_names, current_polygon_partitions = orip_sub_mesh_names(current)
    current_mesh_partitions = {}
    for name, partition in zip(current_names, current_polygon_partitions):
        current_mesh_partitions.setdefault(name, partition)
    extras_partitions = {name: props.get('partition') for name, props in extras.get('objects', {}).items()}
    for polygon in polygons:
        if polygon.partition is not None:
            partition = None if polygon.partition == 'none' else polygon.partition
        elif polygon.mesh_name in extras_partitions:
            partition = extras_partitions[polygon.mesh_name]
        elif polygon.mesh_name in current_mesh_partitions:
            partition = current_mesh_partitions[polygon.mesh_name]
        elif not current_drawn:
            partition = None
        elif polygon.label in WHEEL_LABELS and 'outside' in current_drawn:
            partition = 'outside'
        else:
            partition = 'surface' if 'surface' in current_drawn else current_drawn[0]
        polygon.partition = partition

    # 3. vertices: shared by position, but not between the wheel parts (moved by the morphs) and the others
    vertex_keys: Dict[tuple, int] = {}
    positions: List[Tuple[int, int, int]] = []

    def is_wheel_part(polygon: _Polygon) -> bool:
        return polygon.label in WHEEL_LABELS or polygon.texture.lower() == 'circ'

    def vertex_index(position, group) -> int:
        key = (position, group)
        if key not in vertex_keys:
            vertex_keys[key] = len(positions)
            positions.append(position)
        return vertex_keys[key]

    polygon_vertices = [
        [vertex_index(p, 'wheel' if is_wheel_part(polygon) else '') for p, _ in polygon.corners] for polygon in polygons
    ]

    # 4. materials and polygon types, following the current polygons of the same texture
    current_materials = current['materials']
    current_material_names = [m['name'].rstrip(b'\0') for m in current_materials]
    by_texture = defaultdict(Counter)
    for p in current['polygons']:
        m = current_materials[p['material_index']]
        by_texture[m['file_name']][p['material_index']] += 1
        by_texture[('type', m['file_name'])][(bool(p['polygon_type'] & 0x80), bool(p['polygon_type'] & 0x08))] += 1
    most_common_0x0f = Counter(m['unknown_0x0f'] for m in current_materials).most_common(1)
    most_common_0x10 = Counter(m['unknown_0x10'] for m in current_materials).most_common(1)
    default_material = {
        'name': b'\0' * 8,
        'file_name': '',
        'color': 0,
        'unknown_0x0f': most_common_0x0f[0][0] if most_common_0x0f else 0,
        'unknown_0x10': most_common_0x10[0][0] if most_common_0x10 else 0,
    }
    polygon_unk = Counter(p['unk'] for p in current['polygons']).most_common(1)
    polygon_unk = polygon_unk[0][0] if polygon_unk else 0

    def texture_path(polygon: _Polygon) -> Optional[str]:
        material = materials.get(polygon.material) if polygon.material else None
        if material and material.texture_path:
            return material.texture_path
        if polygon.texture:
            path = os.path.join(os.path.dirname(obj_path), 'assets', f'{polygon.texture}.png')
            return path if os.path.isfile(path) else None
        return None

    new_materials: List[dict] = []
    material_indices: Dict[tuple, int] = {}

    def material_index(material: dict) -> int:
        key = tuple(material[k] for k in ('name', 'file_name', 'color', 'unknown_0x0f', 'unknown_0x10'))
        if key not in material_indices:
            material_indices[key] = len(new_materials)
            new_materials.append(dict(material))
        return material_indices[key]

    polygon_materials, polygon_types = [], []
    missing_textures = set()
    for polygon in polygons:
        obj_material: Optional[ObjMaterial] = materials.get(polygon.material) if polygon.material else None
        is_flat = (
            obj_material is not None
            and obj_material.texture_path is None
            and obj_material.diffuse is not None
            and polygon.texture not in shpi_textures
        )
        if polygon.label in WHEEL_LABELS:
            # the game puts the tyre textures on the materials with these names
            name = WHEEL_LABELS[polygon.label][1]
            template = next((m for m, n in zip(current_materials, current_material_names) if n == name), None)
            material = dict(template) if template else {**default_material, 'name': name.ljust(8, b'\0')}
            textured, color_key = True, True
        else:
            used = by_texture.get(polygon.texture)
            material = dict(current_materials[used.most_common(1)[0][0]]) if used else dict(default_material)
            material['file_name'] = polygon.texture
            types = by_texture.get(('type', polygon.texture))
            if is_flat:
                textured, color_key = False, False
                r, g, b = (max(0, min(255, round(c * 255))) for c in obj_material.diffuse)
                material['color'] = (r << 16) | (g << 8) | b
            elif types:
                textured, color_key = types.most_common(1)[0][0]
            else:
                textured = bool(polygon.texture)
                color_key = textured and _has_transparency(texture_path(polygon))
            if textured and polygon.texture and polygon.texture not in shpi_textures:
                missing_textures.add(polygon.texture)
        polygon_materials.append(material_index(material))
        polygon_types.append(len(polygon.corners) | (0x08 if color_key else 0) | (0x80 if textured else 0))
    used_in_current = {p['material_index'] for p in current['polygons']}
    for i, material in enumerate(current_materials):
        # looked up by name only (tire1..tire4, pal), or unused
        if i not in used_in_current:
            material_index(material)

    # 5. texture coordinates, in texels
    uv_keys: Dict[Tuple[int, int], int] = {}
    vertex_uvs = []
    polygon_uvs = []
    sizes = {}
    for polygon in polygons:
        uvs = [uv for _, uv in polygon.corners]
        if any(uv is None for uv in uvs) or uvs == DEFAULT_UVS[: len(uvs)]:
            polygon_uvs.append(None)
            continue
        if polygon.texture not in sizes:
            sizes[polygon.texture] = _image_size(texture_path(polygon)) or shpi_textures.get(polygon.texture) or (1, 1)
        width, height = sizes[polygon.texture]
        indices = []
        for u, v in uvs:
            key = (round(u * width), round(v * height))
            if key not in uv_keys:
                uv_keys[key] = len(vertex_uvs)
                vertex_uvs.append({'u': key[0], 'v': key[1]})
            indices.append(uv_keys[key])
        polygon_uvs.append(indices)

    # 6. fx_polys: wheel ground points from the wheel quads, the others from the extras dummies or the current ORIP
    current_vertices = current['vertices']['data']
    fx_positions: Dict[str, Tuple[int, int, int]] = {}
    fx_names = []
    for entry in current['fx_polys']:
        if entry['name'] in fx_positions or entry['index'] >= len(current_vertices):
            continue
        v = current_vertices[entry['index']]
        fx_names.append(entry['name'])
        fx_positions[entry['name']] = (round(v['x'] * scale), round(v['y'] * scale), round(v['z'] * scale))
    for dummy in extras.get('dummies', []):
        fx_name = dummy.get('properties', {}).get('fx')
        if not fx_name or not dummy.get('name', '').startswith('fx_') or dummy.get('name') != f'fx_{fx_name}':
            continue
        if fx_name not in fx_positions:
            fx_names.append(fx_name)
        x, z, y = dummy['position']  # dummies are in OBJ axes
        fx_positions[fx_name] = (round(x * scale), round(y * scale), round(z * scale))
    fx_vertices = {}
    upper_case = not any(n[:2] in ('fl', 'fr', 'rl', 'rr') for n in fx_names)
    for polygon, vertices in zip(polygons, polygon_vertices):
        if polygon.label not in WHEEL_LABELS or len(vertices) < 3:
            continue
        prefix = WHEEL_LABELS[polygon.label][0]
        prefix = prefix if upper_case else prefix.lower()
        bottom = sorted(vertices, key=lambda i: (positions[i][1], -positions[i][2]))[:2]
        # 0 at the front edge (+z), 1 at the rear
        for n, i in enumerate(sorted(bottom, key=lambda i: -positions[i][2])):
            name = f'{prefix}{n}'
            if name not in fx_names:
                fx_names.append(name)
            fx_vertices.setdefault(name, i)
    fx_polys = []
    for name in fx_names:
        if name in fx_vertices:
            index = fx_vertices[name]
        else:
            position = fx_positions[name]
            index = vertex_keys.get((position, ''), vertex_keys.get((position, 'wheel')))
            if index is None:
                index = vertex_index(position, 'fx')
        fx_polys.append({'name': name, 'offset': [], 'index': index})

    # 7. morphs: kept when their vertices are still there, else made again from the front wheel quads
    morphs = []
    for morph in current['morphs']:
        moved = {}
        for i in range(morph['num_vertices']):
            v = current_vertices[current['vmap'][morph['vmap_offset'] + i]]
            d = current_vertices[morph['first_delta'] + i]
            moved[(round(v['x'] * scale), round(v['y'] * scale), round(v['z'] * scale))] = (d['x'], d['y'], d['z'])
        indices = {i: moved[positions[i]] for k, i in vertex_keys.items() if k[1] == 'wheel' and k[0] in moved}
        if moved and len(indices) == len(moved):
            morphs.append((morph['name'], sorted(indices.items())))
            continue
        label = MORPH_WHEEL_LABELS.get(morph['name'])
        generated = _wheel_morph(label, polygons, polygon_vertices, positions, scale) if label else None
        if generated:
            morphs.append((morph['name'], generated))
            warnings.append(f'morph {morph["name"]} made again')
        else:
            warnings.append(f'morph {morph["name"]} dropped: no {label or "wheel"} quad')

    # 8. partitions
    polygon_lists = defaultdict(list)
    non_sort_has_all = any(
        p['name'] == 'NON-SORT' and p['num_polygons'] >= len(current['polygons']) > 0 for p in current['partitions']
    )
    partition_names = list(current_partition_names)
    for polygon in polygons:
        if polygon.partition and polygon.partition not in [n.lower() for n in partition_names]:
            partition_names.append(polygon.partition)
    if 'NON-SORT' not in partition_names and any(p.partition is None for p in polygons):
        partition_names.insert(0, 'NON-SORT')
    other_partition_meshes = defaultdict(set)
    for partition in current['partitions']:
        if partition['name'].lower() in ORIP_DRAWN_PARTITIONS or partition['name'] == 'NON-SORT':
            continue
        for i in range(partition['num_polygons']):
            pi = current['vmap'][partition['polygons_start'] + i]
            if 0 <= pi < len(current_names):
                other_partition_meshes[partition['name']].add(current_names[pi].split('__none')[0])
    for pi, polygon in enumerate(polygons):
        for name in partition_names:
            if name == 'NON-SORT':
                if non_sort_has_all or not current_drawn or polygon.partition is None:
                    polygon_lists[name].append(pi)
            elif name.lower() in ORIP_DRAWN_PARTITIONS:
                if polygon.partition == name.lower():
                    polygon_lists[name].append(pi)
            elif polygon.mesh_name in other_partition_meshes[name]:
                polygon_lists[name].append(pi)

    # 9. vmap and the tables
    vmap = []
    new_polygons = []
    for polygon, vertices, uvs, material, polygon_type in zip(
        polygons, polygon_vertices, polygon_uvs, polygon_materials, polygon_types
    ):
        offset_2d = len(vmap)
        if uvs is not None:
            vmap.extend(uvs)
        offset_3d = len(vmap)
        vmap.extend(vertices)
        new_polygons.append(
            {
                'polygon_type': polygon_type,
                'mapping': {
                    'two_sided': polygon.two_sided,
                    'flip_normal': polygon.flip,
                    'not_in_draw_list': False,
                    'chain': False,
                    'use_uv': uvs is not None,
                    'alt_rasterizer': False,
                    '6': False,
                    '7': False,
                },
                'material_index': material,
                'unk': polygon_unk,
                'offset_3d': offset_3d,
                'offset_2d': offset_2d if uvs is not None else offset_3d,
            }
        )
    vertices = [{'x': x / scale, 'y': y / scale, 'z': z / scale} for x, y, z in positions]
    new_morphs = []
    for name, moved in morphs:
        new_morphs.append(
            {'name': name, 'num_vertices': len(moved), 'vmap_offset': len(vmap), 'first_delta': len(vertices)}
        )
        for i, delta in moved:
            vmap.append(i)
            vertices.append({'x': delta[0], 'y': delta[1], 'z': delta[2]})
    current_partitions = {p['name']: p for p in current['partitions']}
    new_partitions = []
    for name in partition_names:
        template = current_partitions.get(name)
        new_partitions.append(
            {
                'name': name,
                'unknown_0x08': template['unknown_0x08'] if template else 0,
                'unknown_0x0c': template['unknown_0x0c'] if template else PARTITION_UNKNOWN_0X0C.get(name.lower(), 0),
                'polygons_start': len(vmap),
                'num_polygons': len(polygon_lists[name]),
                'unknown_0x18': template['unknown_0x18'] if template else 0,
            }
        )
        vmap.extend(polygon_lists[name])
    labels = [
        {'name': polygon.label, 'offset': [], 'index': pi}
        for pi, polygon in enumerate(polygons)
        if polygon.label and is_orip_name(polygon.label)
    ]
    for entry in [*labels, *fx_polys]:
        if len(entry['name'].encode('utf-8', errors='surrogateescape')) > 7:
            raise DataIntegrityException(f'ORIP label / fx name "{entry["name"]}" is longer than 7 bytes')
        entry['offset'] = [0] * (7 - len(entry['name'].encode('utf-8', errors='surrogateescape')))

    data = dict(current)
    data.update(
        {
            'polygons': new_polygons,
            'unk_uvs': b'',
            'vertex_uvs': vertex_uvs,
            'unk_materials': b'',
            'materials': new_materials,
            'unk_morphs': b'',
            'morphs': new_morphs,
            'unk_partitions': b'',
            'partitions': new_partitions,
            'unk_fxp': b'',
            'fx_polys': fx_polys,
            'unk_lbl': b'',
            'labels': labels,
            'unk_vrtx': b'',
            'vertices': {**current['vertices'], 'data': vertices},
            'unk_vmap': b'',
            'vmap': vmap,
            'instance_counter': 0,
        }
    )
    _update_counts(data)

    report = f'{len(new_polygons)} polygons, {len(positions)} vertices, {len(new_materials)} materials'
    if missing_textures:
        warnings.append(f'textures not in the FSH: {", ".join(sorted(missing_textures))}')
    if warnings:
        report += '. ' + '; '.join(warnings)
    return data, report


def _wheel_morph(label, polygons, polygon_vertices, positions, scale) -> Optional[List[Tuple[int, tuple]]]:
    """Deltas turning the wheel quad labelled `label` and the `circ` quad at its inner side left by `MORPH_ANGLE`
    about the vertical axis through the centre of the wheel quad"""
    wheel = next((v for p, v in zip(polygons, polygon_vertices) if p.label == label), None)
    if not wheel:
        return None
    xs = [positions[i][0] for i in wheel]
    zs = [positions[i][2] for i in wheel]
    cx, cz = sum(xs) / len(xs), sum(zs) / len(zs)
    moved = set(wheel)
    # the inner tyre face: the circ polygon nearest to the wheel, on its side of the car
    circs = [
        v
        for p, v in zip(polygons, polygon_vertices)
        if p.texture.lower() == 'circ' and p.label is None and all((positions[i][0] > 0) == (cx > 0) for i in v)
    ]
    if circs:

        def distance(v):
            return abs(sum(positions[i][2] for i in v) / len(v) - cz) + abs(
                sum(positions[i][0] for i in v) / len(v) - cx
            )

        circ = min(circs, key=distance)
        if min(positions[i][2] for i in circ) <= max(zs) and max(positions[i][2] for i in circ) >= min(zs):
            moved.update(circ)
    c, s = math.cos(MORPH_ANGLE), math.sin(MORPH_ANGLE)
    result = []
    for i in sorted(moved):
        dx, dz = positions[i][0] - cx, positions[i][2] - cz
        result.append((i, ((dx * c - dz * s - dx) / scale, 0.0, (dx * s + dz * c - dz) / scale)))
    return result


def _update_counts(data: dict):
    # the counts the reader reads the tables with (the writer computes them too)
    data['num_vrtx'] = len(data['vertices']['data'])
    data['num_shape_vrtx'] = data['num_vrtx'] - sum(m['num_vertices'] for m in data['morphs'])
    data['num_uvs'] = len(data['vertex_uvs'])
    data['num_polygons'] = len(data['polygons'])
    data['num_materials'] = len(data['materials'])
    data['num_morphs'] = len(data['morphs'])
    data['num_partitions'] = len(data['partitions'])
    data['num_fxp'] = len(data['fx_polys'])
    data['num_lbl'] = len(data['labels'])
