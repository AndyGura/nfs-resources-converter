import math
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Tuple, List


class BaseMesh(ABC):
    def __init__(self):
        self.name = None
        self.vertices = []
        self.polygons = []
        self.vertex_uvs = []
        self.pivot_offset = (0, 0, 0)

    def rotate_z(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        self.vertices = [[p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]]
                         for p in self.vertices]

    def apply_transform_matrix(self, m: List[List[float]]):
        for v in [m, *m]:
            if len(v) != 4:
                raise ValueError("Transform matrix must contain exactly 4 rows and columns")

        transformed_vertices = []
        for vertex in self.vertices:
            x, y, z = vertex[0], vertex[1], vertex[2]
            w = 1.0

            new_x = m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3] * w
            new_y = m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3] * w
            new_z = m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3] * w
            new_w = m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3] * w

            if new_w != 0:
                new_x /= new_w
                new_y /= new_w
                new_z /= new_w

            transformed_vertices.append([new_x, new_y, new_z])

        self.vertices = transformed_vertices

    @abstractmethod
    def to_obj(self, face_index_increment, mtllib=None, pivot_offset=None) -> Tuple[str, int]:
        raise NotImplementedError

    def change_axes(self, new_x='x', new_y='y', new_z='z'):
        map = {
            'x': 0,
            'y': 1,
            'z': 2,
        }

        def get_value_from_vertex_list(vertex: list[int], coordinate: str) -> int:
            value = vertex[map[coordinate[-1]]]
            if coordinate[0] == '-':
                value = -value
            return value

        self.vertices = [[
            get_value_from_vertex_list(v, new_x),
            get_value_from_vertex_list(v, new_y),
            get_value_from_vertex_list(v, new_z),
        ] for v in self.vertices]

    # after deleting polygons should call this function
    def remove_orphaned_vertices(self):
        usage_map = [False] * len(self.vertices)
        for p in self.polygons:
            for vi in p:
                usage_map[vi] = True
        orphans = [vi for vi, used in enumerate(usage_map) if not used]
        self.vertices = [v for (i, v) in enumerate(self.vertices) if i not in orphans]
        self.vertex_uvs = [v for (i, v) in enumerate(self.vertex_uvs) if i not in orphans]
        for removed_index in orphans:
            for j, p in enumerate(self.polygons):
                self.polygons[j] = [idx if idx <= removed_index else idx - 1 for idx in p]

    def extend(self, mesh: 'BaseMesh'):
        v_offset = (self.pivot_offset[0] - mesh.pivot_offset[0],
                    self.pivot_offset[1] - mesh.pivot_offset[1],
                    self.pivot_offset[2] - mesh.pivot_offset[2])
        v_index_surplus = len(self.vertices)
        self.vertices.extend([
            [v[0] + v_offset[0], v[1] + v_offset[1], v[2] + v_offset[2]] for v in mesh.vertices
        ])
        self.polygons.extend([
            [v + v_index_surplus for v in p] for p in mesh.polygons
        ])
        self.vertex_uvs.extend(mesh.vertex_uvs)

    def collapse_vertices(self):
        self.remove_orphaned_vertices()
        new_vertices = []
        new_uvs = []

        # spatial hash
        grid_size = 0.01
        grid = defaultdict(list)

        def get_key(v):
            return (int(v[0] // grid_size), int(v[1] // grid_size), int(v[2] // grid_size))

        # smart references to vertex for fast polygons migration
        self_vertices_map = [[i, v] for (i, v) in enumerate(self.vertices)]
        self_polygons_map = [[self_vertices_map[vi] for vi in p] for p in self.polygons]

        for i, vi in enumerate(self.vertices):
            key = get_key(vi)
            existing_v_index = None
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        neighbor_key = (key[0] + dx, key[1] + dy, key[2] + dz)
                        for (j, vj) in grid[neighbor_key]:
                            if abs(vi[0] - vj[0]) < 0.01 and abs(vi[1] - vj[1]) < 0.01 and abs(vi[2] - vj[2]) < 0.01:
                                existing_v_index = j
                                break
                        if existing_v_index is not None:
                            break
                    if existing_v_index is not None:
                        break
                if existing_v_index is not None:
                    break
            if existing_v_index is None:
                self_vertices_map[i][0] = len(new_vertices)
                new_vertices.append(vi)
                new_uvs.append(self.vertex_uvs[i])
                grid[key].append((i, vi))
            else:
                self_vertices_map[i][0] = self_vertices_map[existing_v_index][0]
                self_vertices_map[i][1] = None
        self.vertices = new_vertices
        self.vertex_uvs = new_uvs
        self.polygons = [[vi for (vi, _) in p] for p in self_polygons_map]


# Mesh with one single texture
class SubMesh(BaseMesh):
    def __init__(self):
        super().__init__()
        self.texture_id = None

    def to_obj(self, face_index_increment, mtllib=None, pivot_offset=None) -> Tuple[str, int]:
        if pivot_offset is None:
            pivot_offset = self.pivot_offset
        res = f'\n\no {self.name}'
        if mtllib is not None:
            res += f'\nmtllib {mtllib}'
        res += '\n' + '\n'.join(['v ' + ' '.join(
            [str(coordinates[i] - pivot_offset[i]) for i in range(3)]
        ) for coordinates in self.vertices])
        res += '\n' + '\n'.join([f'vt {uv[0]} {1 - uv[1]}' for uv in self.vertex_uvs])
        if self.texture_id:
            res += '\nusemtl ' + self.texture_id
        res += '\n' + '\n'.join(
            ['f ' + ' '.join([f'{x + face_index_increment}/{x + face_index_increment}' for x in polygon]) for polygon in
             self.polygons])
        return res, len(self.vertices)


# Mesh with multiple textures
class Mesh(BaseMesh):
    def __init__(self):
        super().__init__()
        self.texture_ids = []

    # splits mesh to few single-texture meshes. Returns list of tuples: ( mesh, vertex index map, polygon index map )
    def split_by_texture_ids(self) -> List[Tuple[SubMesh, List[int], List[int]]]:
        texture_ids = list({x for x in self.texture_ids})
        texture_ids.sort()
        if len(texture_ids) == 1:
            sm = SubMesh()
            sm.pivot_offset = self.pivot_offset
            sm.texture_id = texture_ids[0]
            sm.name = self.name + '__' + (sm.texture_id or 'None')
            sm.vertices = self.vertices
            sm.vertex_uvs = self.vertex_uvs
            sm.polygons = self.polygons
            return [(sm, list(range(len(self.vertices))), list(range(len(self.polygons))))]
        res = []
        for texture_id in texture_ids:
            sm = SubMesh()
            sm.name = (self.name or 'None') + '__' + (texture_id or 'None')
            sm.pivot_offset = self.pivot_offset
            sm.texture_id = texture_id
            vertex_indices = []
            polygon_indices = []
            for i, p in enumerate(self.polygons):
                if self.texture_ids[i] != texture_id:
                    continue
                polygon_indices.append(i)
                new_polygon = []
                for idx in p:
                    try:
                        new_idx = vertex_indices.index(idx)
                    except ValueError:
                        new_idx = len(vertex_indices)
                        vertex_indices.append(idx)
                    new_polygon.append(new_idx)
                sm.polygons.append(new_polygon)
            for v_idx in vertex_indices:
                sm.vertices.append(self.vertices[v_idx])
                sm.vertex_uvs.append(self.vertex_uvs[v_idx])
            res.append((sm, vertex_indices, polygon_indices))
        return res

    def to_obj(self, face_index_increment, mtllib=None, pivot_offset=None) -> Tuple[str, int]:
        sub_meshes = self.split_by_texture_ids()
        if len(sub_meshes) == 1:
            return sub_meshes[0][0].to_obj(face_index_increment, mtllib, pivot_offset)
        obj_texts = []
        for (sub_model, _, _) in sub_meshes:
            obj, fii = sub_model.to_obj(face_index_increment, mtllib, pivot_offset)
            obj_texts.append(obj)
            face_index_increment += fii
        return '\n\n'.join(obj_texts), face_index_increment

    def extend(self, mesh: 'Mesh'):
        super().extend(mesh)
        self.texture_ids.extend(mesh.texture_ids)


class CubeMesh(SubMesh):

    def _build_mesh(self):
        self.vertices = [(-self.dimensions[0] / 2, -self.dimensions[1] / 2, -self.dimensions[2] / 2),
                         (-self.dimensions[0] / 2, -self.dimensions[1] / 2, self.dimensions[2] / 2),
                         (-self.dimensions[0] / 2, self.dimensions[1] / 2, -self.dimensions[2] / 2),
                         (-self.dimensions[0] / 2, self.dimensions[1] / 2, self.dimensions[2] / 2),
                         (self.dimensions[0] / 2, -self.dimensions[1] / 2, -self.dimensions[2] / 2),
                         (self.dimensions[0] / 2, -self.dimensions[1] / 2, self.dimensions[2] / 2),
                         (self.dimensions[0] / 2, self.dimensions[1] / 2, -self.dimensions[2] / 2),
                         (self.dimensions[0] / 2, self.dimensions[1] / 2, self.dimensions[2] / 2)]

    def __init__(self, dimensions=(1, 1, 1), position=(0, 0, 0), **kwargs):
        super().__init__(**kwargs)
        self._dimensions = dimensions
        self._position = position
        self._build_mesh()
        self.polygons = [(0, 1, 2), (2, 1, 3),
                         (4, 6, 5), (5, 6, 7),
                         (1, 0, 5), (5, 0, 4),
                         (2, 6, 0), (0, 6, 4),
                         (1, 5, 3), (3, 5, 7),
                         (2, 3, 6), (6, 3, 7)]
        self.vertex_uvs = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, 0), (1, 1), (0, 1)]
        self.pivot_offset = (-self.position[0], -self.position[1], -self.position[2])

    @property
    def dimensions(self):
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value):
        self._dimensions = value
        self._build_mesh()

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = value
        self.pivot_offset = (-self.position[0], -self.position[1], -self.position[2])
