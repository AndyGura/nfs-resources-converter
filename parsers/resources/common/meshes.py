# Mesh with one single texture
class SubMesh:
    def __init__(self):
        self.name = None
        self.vertices = []
        self.polygons = []
        self.vertex_uvs = []
        self.texture_id = None
        self.scaled_uvs = set()

    def to_obj(self, face_index_increment, multiply_uvws=False, textures_archive=None, mtllib=None, pivot_offset=(0, 0, 0)) -> str:
        res = f'\n\no {self.name}'
        if mtllib is not None:
            res += f'\nmtllib {mtllib}'
        res += '\n' + '\n'.join(['v ' + ' '.join(
            [str(coordinates[i] - pivot_offset[i]) for i in range(3)]
        ) for coordinates in self.vertices])
        u_multiplier, v_multiplier = 1, 1
        if multiply_uvws:
            uvs_scaled_to_texture = False
            if self.texture_id:
                for texture_res in textures_archive.resources:
                    from parsers.resources.bitmaps import BaseBitmap
                    if isinstance(texture_res, BaseBitmap) and texture_res.name == self.texture_id:
                        u_multiplier, v_multiplier = 1 / texture_res.width, 1 / texture_res.height
                        uvs_scaled_to_texture = True
                        break
            if not uvs_scaled_to_texture:
                u_multiplier = 1 / max([x[0] for x in self.vertex_uvs])
                v_multiplier = 1 / max([x[1] for x in self.vertex_uvs])
        uvs = [[
            uv[0] * u_multiplier if i not in self.scaled_uvs else uv[0],
            uv[1] * v_multiplier if i not in self.scaled_uvs else uv[1]
        ] for i, uv in enumerate(self.vertex_uvs)]
        res += '\n' + '\n'.join([f'vt {uv[0]} {1 - uv[1]}' for uv in uvs])
        if self.texture_id:
            res += '\nusemtl ' + self.texture_id
        res += '\n' + '\n'.join(
            ['f ' + ' '.join([f'{x + face_index_increment}/{x + face_index_increment}' for x in polygon]) for polygon in
             self.polygons])
        return res

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

