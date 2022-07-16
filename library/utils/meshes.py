from resources.eac.bitmaps import AnyBitmapBlock


# Mesh with one single texture
class SubMesh:
    def __init__(self):
        self.name = None
        self.vertices = []
        self.polygons = []
        self.vertex_uvs = []
        self.texture_id = None
        self.scaled_uvs = set()

    def to_obj(self, face_index_increment, multiply_uvws=False, textures_shpi_block=None, mtllib=None,
               pivot_offset=(0, 0, 0)) -> str:
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
                for texture in textures_shpi_block.children:
                    if isinstance(texture, AnyBitmapBlock) and texture.id.split('/')[-1] == self.texture_id:
                        u_multiplier, v_multiplier = 1 / texture.width, 1 / texture.height
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

    # after deleting polygons should call this function
    def remove_orphaned_vertices(self):
        orphans = [vi for vi in range(len(self.vertices)) if
                   vi not in [element for sublist in self.polygons for element in sublist]]
        self.vertices = [v for (i, v) in enumerate(self.vertices) if i not in orphans]
        self.vertex_uvs = [v for (i, v) in enumerate(self.vertex_uvs) if i not in orphans]
        for removed_index in orphans[::-1]:
            for j, p in enumerate(self.polygons):
                self.polygons[j] = [idx if idx <= removed_index else idx - 1 for idx in p]
