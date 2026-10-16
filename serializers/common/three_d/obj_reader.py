"""Reader of Wavefront OBJ / MTL files: the meshes `export_scenes` writes, and what 3D editors write (Blender...)"""

import os
from typing import Dict, List, Optional, Tuple


class ObjFace:
    def __init__(self, vertices: List[Tuple[float, float, float]], uvs: Optional[List[Tuple[float, float]]], material):
        # positions of the corners, in file order
        self.vertices = vertices
        # texture coordinates (vt) of the corners, None when the face has none
        self.uvs = uvs
        # name of the "usemtl" material, None without one
        self.material = material


class ObjObject:
    def __init__(self, name: str):
        self.name = name
        self.faces: List[ObjFace] = []


class ObjMaterial:
    def __init__(self, name: str):
        self.name = name
        # absolute path of the "map_Kd" texture, None without one
        self.texture_path: Optional[str] = None
        # "Kd" diffuse color, 0..1 per component, None without one
        self.diffuse: Optional[Tuple[float, float, float]] = None


def _resolve_index(value: str, count: int) -> int:
    index = int(value)
    return index - 1 if index > 0 else count + index


def read_obj(path: str) -> Tuple[List[ObjObject], Dict[str, ObjMaterial]]:
    """Objects ("o" / "g", faces before any of them go to an object named after the file) with their faces, and the
    materials of the "mtllib" files (missing ones are skipped). "usemtl" applies to the faces after it, also across
    objects, as the format says. Lines, points, normals and smoothing groups are ignored"""
    positions, uvs = [], []
    objects: List[ObjObject] = []
    material_libraries = []
    current = None
    material = None
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.split('#', 1)[0].split()
            if not parts:
                continue
            keyword, args = parts[0], parts[1:]
            if keyword == 'v':
                positions.append((float(args[0]), float(args[1]), float(args[2])))
            elif keyword == 'vt':
                uvs.append((float(args[0]), float(args[1]) if len(args) > 1 else 0.0))
            elif keyword in ('o', 'g'):
                name = ' '.join(args) or 'default'
                # "g" right after "o" (or the other way round) names the same mesh
                if current is not None and not current.faces:
                    current.name = name
                else:
                    current = ObjObject(name)
                    objects.append(current)
            elif keyword == 'usemtl':
                material = ' '.join(args) or None
            elif keyword == 'mtllib':
                material_libraries.append(line.split('#', 1)[0].strip()[len('mtllib') :].strip())
            elif keyword == 'f':
                corners = [arg.split('/') for arg in args]
                face_positions = [positions[_resolve_index(c[0], len(positions))] for c in corners]
                face_uvs = None
                if all(len(c) > 1 and c[1] for c in corners):
                    face_uvs = [uvs[_resolve_index(c[1], len(uvs))] for c in corners]
                if current is None:
                    current = ObjObject(os.path.splitext(os.path.basename(path))[0])
                    objects.append(current)
                current.faces.append(ObjFace(face_positions, face_uvs, material))
    materials = {}
    for library in material_libraries:
        library_path = os.path.join(os.path.dirname(path), library)
        if os.path.isfile(library_path):
            materials.update(read_mtl(library_path))
    return [o for o in objects if o.faces], materials


def read_mtl(path: str) -> Dict[str, ObjMaterial]:
    materials = {}
    material = None
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.split('#', 1)[0].split()
            if not parts:
                continue
            keyword, args = parts[0], parts[1:]
            if keyword == 'newmtl':
                material = ObjMaterial(' '.join(args))
                materials[material.name] = material
            elif material is None:
                continue
            elif keyword == 'Kd' and len(args) >= 3:
                material.diffuse = (float(args[0]), float(args[1]), float(args[2]))
            elif keyword == 'map_Kd' and args:
                # options (-s 1 1 1, -bm 0.5...) come before the file name, which can have spaces
                texture = line.split('#', 1)[0].strip()[len('map_Kd') :].strip()
                tokens = texture.split(' ')
                while tokens and tokens[0].startswith('-'):
                    option = tokens.pop(0)
                    arg_count = {'-s': 3, '-o': 3, '-t': 3, '-mm': 2}.get(option, 1)
                    tokens = tokens[arg_count:]
                texture = ' '.join(tokens)
                if texture:
                    material.texture_path = os.path.normpath(os.path.join(os.path.dirname(path), texture))
    return materials
