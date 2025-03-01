import json
import math
import os
import traceback
from copy import deepcopy
from string import Template
from typing import List, Dict

from resources.eac.maps import RoadSplinePoint
from resources.eac.utils import rotate_list
from serializers import BaseFileSerializer
from serializers.common.three_d import SubMesh, Mesh, Scene, export_scenes, BarrierPath


class TriMapSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    class TerrainChunk:

        def get_fence_height(self, fence_texture_name):
            # TODO determine where to get fence height from resource file
            # resource = self.tri_block.fam.resources[0]
            # for path in fence_texture_name.split('/'):
            #     resource = resource.get_resource_by_name(path)
            if self.tri_id.split('/')[-1][:3] in ['TR1', 'TR3']:
                # TR1 texture height == 64; TR3: 51
                return 1
            elif self.tri_id.split('/')[-1][:3] in ['AL1', 'TR2', 'TR6']:
                return 2  # TR2 95; TR6: 65; AL1: 64
            elif self.tri_id.split('/')[-1][:3] in ['TR7']:
                return 1.5  # TR7: 47
            # didn't test other tracks
            return 1

        def __init__(self, tri_id, tri_block, tri_data):
            self.tri_id = tri_id
            self.tri_block = tri_block
            self.tri_data = tri_data
            self.next_chunk = None
            self.matrix = None
            self.fence_texture_name = None
            self.has_left_fence = False
            self.left_fence_polygon_index = 3
            # FIXME hardcode
            if self.tri_id.split('/')[-1][:3] == 'TR3':
                self.left_fence_polygon_index = 2
            self.has_right_fence = False
            self.right_fence_polygon_index = 7
            self.lane_merge_initiated = False

        # for lane split and merge chunks. Happens in TNFS open tracks
        # pure magic. No idea how I wrote it
        def _make_vertex_offset(self, build_matrix_row, vertex_to_remove, vertex_to_duplicate, com_matrix_row):
            build_matrix_row = row = (build_matrix_row[:vertex_to_remove]
                                      + build_matrix_row[vertex_to_remove + 1:vertex_to_duplicate + 1]
                                      + build_matrix_row[vertex_to_duplicate:])
            # add a tiny offset for duplicated vertex so polygon will be rendered correctly
            row[vertex_to_duplicate - 1] = deepcopy(row[vertex_to_duplicate - 1])
            for i in ['x', 'y', 'z']:
                row[vertex_to_duplicate - 1][i] = row[vertex_to_duplicate - 1][i] * 0.99 + row[vertex_to_duplicate - 2][
                    i] * 0.01
            # fix vertex position in default matrix to omit holes in chunk connection (second point was removed from build matrix)
            row = com_matrix_row
            distance_to_left_vertex = math.sqrt(
                sum((row[vertex_to_remove][i] - row[vertex_to_remove - 1][i]) ** 2 for i in ['x', 'y', 'z']))
            distance_to_right_vertex = math.sqrt(
                sum((row[vertex_to_remove][i] - row[vertex_to_remove + 1][i]) ** 2 for i in ['x', 'y', 'z']))
            left_right_factor = distance_to_left_vertex / (distance_to_left_vertex + distance_to_right_vertex)
            # now vertex will be located on the straight line between neighbour vertices
            row[vertex_to_remove] = {
                i: row[vertex_to_remove - 1][i] * (1 - left_right_factor)
                   + row[vertex_to_remove + 1][i] * left_right_factor
                for i in ['x', 'y', 'z']}
            return build_matrix_row, com_matrix_row

        def read_matrix(self, rows, reference_points: List[RoadSplinePoint]):
            # This matrix from http://auroux.free.fr/nfs/nfsspecs.txt :
            # D10   D9   D8   D7   D6   D0   D1   D2   D3   D4   D5  node 4n+3
            # |  T |  T |  T |  T |  T || T  | T  | T  | T  | T  |
            # |    |    |    |    |    ||    |    |    |    |    |
            # C10   C9   C8   C7   C6   C0   C1   C2   C3   C4   C5  node 4n+2
            # | 10 |  9 |  8 |  7 |  6 || 1  | 2  | 3  | 4  | 5  |
            # |    |    |    |    |    ||    |    |    |    |    |
            # B10   B9   B8   B7   B6   B0   B1   B2   B3   B4   B5  node 4n+1
            # |    |    |    |    |    ||    |    |    |    |    |
            # |    |    |    |    |    ||    |    |    |    |    |
            # A10---A9---A8---A7---A6---A0---A1---A2---A3---A4---A5  node 4n
            self.reference_points = reference_points
            self.matrix = [None] * 4
            for row_index in range(4):
                A0 = {
                    'x': rows[row_index][0]['x'] + reference_points[row_index]['position']['x'],
                    'y': rows[row_index][0]['y'] + reference_points[row_index]['position']['y'],
                    'z': rows[row_index][0]['z'] + reference_points[row_index]['position']['z'],
                }
                A15 = [{**rows[row_index][i + 1]} for i in range(5)]
                A610 = [{**rows[row_index][i + 6]} for i in range(5)]
                # Each point is relative to the previous point
                for i in range(5):
                    for j in ['x', 'y', 'z']:
                        A15[i][j] += A0[j] if i == 0 else A15[i - 1][j]
                        A610[i][j] += A0[j] if i == 0 else A610[i - 1][j]
                A610.reverse()
                self.matrix[3 - row_index] = A610 + [A0] + A15
            self.build_matrix = deepcopy(self.matrix)
            for row_index in range(4):
                if reference_points[row_index]['item_mode'] == 'lane_split':
                    self.build_matrix[3 - row_index], self.matrix[3 - row_index] = self._make_vertex_offset(
                        self.build_matrix[3 - row_index],
                        2, 6,
                        self.matrix[3 - row_index]
                    )
                elif reference_points[row_index]['item_mode'] == 'lane_merge':
                    assert row_index == 0, Exception('Unexpected lane merge position!')
                    self.lane_merge_initiated = True

        def build_models(self, counter, texture_names):
            matrix = deepcopy(self.build_matrix)
            if self.next_chunk:
                matrix = [self.next_chunk.matrix[-1]] + matrix
                if self.lane_merge_initiated:
                    matrix[0], self.next_chunk.build_matrix[3] = self._make_vertex_offset(
                        matrix[0],
                        3, 6,
                        self.next_chunk.build_matrix[3]
                    )
            models = []
            for i in range(10):
                inverted_matrix = [list(x) for x in zip(*matrix)]
                model = SubMesh()
                model.vertices = [[v['x'], v['y'], v['z']] for v in sum(inverted_matrix[i:i + 2], [])]
                # in some cases, first polygon is placed differently (tunnels in Vertigo Ridge and Coastal #2)
                if i == 0:
                    for j in range(5):
                        vertices_matrix_indices = 0, 1
                        # we have 4 points, but 5 items in matrix. last should obey mode of 4th point
                        mode = self.reference_points[min(j, 3)]['item_mode']
                        # matrix_indices mapped as follows:
                        # A10   A9  A8  A7  A6  A0  A1  A2  A3  A4  A5
                        # 0     1   2   3   4   5   6   7   8   9   10
                        if mode == 'left_tunnel_A4_A7':
                            vertices_matrix_indices = 9, 3
                        if mode == 'left_tunnel_A4_A8':
                            vertices_matrix_indices = 9, 2
                        elif mode == 'left_tunnel_A5_A8':
                            vertices_matrix_indices = 10, 2
                        elif mode == 'right_tunnel_A9_A2':
                            vertices_matrix_indices = 1, 7
                        if vertices_matrix_indices != (0, 1):
                            model.vertices[j] = [
                                inverted_matrix[vertices_matrix_indices[0]][j]['x'],
                                inverted_matrix[vertices_matrix_indices[0]][j]['y'],
                                inverted_matrix[vertices_matrix_indices[0]][j]['z']
                            ]
                            model.vertices[j + 5] = [
                                inverted_matrix[vertices_matrix_indices[1]][j]['x'],
                                inverted_matrix[vertices_matrix_indices[1]][j]['y'],
                                inverted_matrix[vertices_matrix_indices[1]][j]['z'],
                            ]
                polygons = [
                    [[i, int(len(model.vertices) / 2) + i, 1 + i], [int(len(model.vertices) / 2) + i,
                                                                    int(len(model.vertices) / 2) + 1 + i,
                                                                    1 + i]] for i in
                    range(int(len(model.vertices) / 2) - 1)]
                model.polygons = [item for row in polygons for item in row]
                model.vertex_uvs = [[
                    (x % int(len(model.vertices) / 2)) / 2,
                    (0 if x < int(len(model.vertices) / 2) else 1) if i < int(len(model.vertices) / 2) else (
                        1 if x < int(len(model.vertices) / 2) else 0)
                ] for x in range(len(model.vertices))]
                model.texture_id = 'background/' + texture_names[i - 5 if i >= 5 else 9 - i]
                model.name = f'terrain_chunk_{counter}_{i}_{model.texture_id}'
                models.append(model)
            if self.has_left_fence:
                models.append(self.build_fence(counter, self.left_fence_polygon_index))
            if self.has_right_fence:
                models.append(self.build_fence(counter, self.right_fence_polygon_index))
            return models

        def build_fence(self, counter, index):
            is_left = index < 5
            matrix = deepcopy(self.matrix)
            if self.next_chunk:
                matrix = [self.next_chunk.matrix[-1]] + matrix
            model = SubMesh()
            for i in range(len(matrix)):
                road_point = matrix[i][index]
                # shift a bit (20cm) fence to fix z-fighting specifically on transtropolis track.
                # It has vertical walls, intersecting with fence
                # FIXME remove this after finding a way to render with custom z-buffer, required for NFS1 wheels
                if self.tri_id.split('/')[-1][:3] == 'TR7':
                    neighbour_point = matrix[i][index + 1 if is_left else index - 1]
                    distance = math.sqrt(sum(pow(neighbour_point[c] - road_point[c], 2) for c in ['x', 'y', 'z']))
                    koef = 0.2 / distance
                    road_point = {c: road_point[c] * (1 - koef) + neighbour_point[c] * koef for c in ['x', 'y', 'z']}
                model.vertices.append([road_point['x'], road_point['y'], road_point['z']])
                model.vertices.append([road_point['x'],
                                       road_point['y'] + self.get_fence_height(self.fence_texture_name),
                                       road_point['z']])
            for i in range(len(matrix) - 1):
                model.polygons.append([i * 2, i * 2 + 1, i * 2 + 3])
                model.polygons.append([i * 2 + 2, i * 2, i * 2 + 3])
            model.vertex_uvs = [[
                math.floor(x / 2),
                0 if x % 2 == 1 else 1
            ] for x in range(len(model.vertices))]
            model.texture_id = self.fence_texture_name
            model.name = f'terrain_chunk_{counter}_{"left" if is_left else "right"}fence_{self.fence_texture_name}'
            return model

    terrain_collisions_script = """
def find_terrain_chunks():
    import re
    pattern = re.compile(f"^terrain_chunk")
    return [x for x in bpy.data.objects if pattern.match(x.name)]

bpy.ops.object.select_all(action='DESELECT')
is_active_set = False
objects = find_terrain_chunks()
for object in objects:
    object.select_set(True)
    if not is_active_set:
        bpy.context.view_layer.objects.active = object
        is_active_set = True
if len(objects) > 0:
    bpy.ops.rigidbody.objects_add(type='PASSIVE')
for obj in bpy.context.selected_objects:
    obj.rigid_body.collision_shape = 'MESH'
"""

    wall_collisions_script = Template("""
import math
left_barrier = json.loads('$left_barrier')
right_barrier = json.loads('$right_barrier')
wall_cube_names = []
for barrier in [left_barrier, right_barrier]:
    if not barrier:
        continue
    for i in range(len(barrier['middle_points'])):
        rotation = barrier['orientations'][i]
        if barrier == left_barrier:
            rotation += math.pi
        bpy.ops.mesh.primitive_cube_add(location=(
                                            barrier['middle_points'][i][0] + math.cos(rotation),
                                            barrier['middle_points'][i][1] - math.sin(rotation),
                                            barrier['points'][i][2] + 100),
                                        scale=(1, barrier['lengths'][i] / 2, 125),
                                        rotation=(0, 0, -barrier['orientations'][i]))
        cube = bpy.data.objects['Cube']
        cube.name = f"wall_collision_{'left' if barrier == left_barrier else 'right'}_{i}"
        cube.hide_render = True
        cube.display_bounds_type = 'BOX'
        cube.display_type = 'BOUNDS'
        wall_cube_names.append(cube.name)
bpy.ops.object.select_all(action='DESELECT')
for name in wall_cube_names:
    bpy.data.objects[name].select_set(True)
bpy.ops.rigidbody.objects_add(type='PASSIVE')
for obj in bpy.context.selected_objects:
    obj.rigid_body.collision_shape = 'BOX'
""")

    def _get_texture_name_from_id(self, is_opened_track, texture_id):
        if is_opened_track:
            return f'{math.floor(texture_id / 3)}/{hex(10 + texture_id % 3)[2:].upper()}000'
        else:
            return ('0/' + str(math.floor(texture_id / 3)).zfill(2)
                    + hex(10 + texture_id % 3)[2:].upper()
                    + '0')  # zero scale is the biggest and always presented in FAM file

    def _texture_ids(self, tex_id, frame_count, is_opened_track):
        tex_id = math.floor(tex_id / 4)
        return [f"{tex_id + i}/0000" if is_opened_track else f"0/{str(tex_id + i).rjust(2, '0')}00"
                for i in range(max(frame_count, 1))]

    def _prop_json(self, data: dict, instance, is_opened_track,
                   use_local_coordinates) -> Dict:
        prop_definition = data['prop_descr'][instance['prop_descr_idx'] % len(data['prop_descr'])]
        spline_index = instance['road_point_idx']
        road_spline_vertex = data['road_spline'][spline_index]
        res = {
            'name': f'proxy_',
            'position': [
                instance['position']['x'] + road_spline_vertex['position']['x'],
                instance['position']['z'] + road_spline_vertex['position']['z'],
                instance['position']['y'] + road_spline_vertex['position']['y'],
            ],
            'rotation': [0, 0, -(instance['rotation'] + road_spline_vertex['orientation'])],
            'properties': {
                'is_prop': True,
                'type': prop_definition['type'],
                'road_index': spline_index,
            }
        }
        if use_local_coordinates:
            res['position'] = [
                res['position'][0] - data['road_spline'][spline_index - (spline_index % 4)]['position']['x'],
                res['position'][1] - data['road_spline'][spline_index - (spline_index % 4)]['position']['z'],
                res['position'][2] - data['road_spline'][spline_index - (spline_index % 4)]['position']['y'],
            ]
        if prop_definition['type'] == 'model':
            res['properties'] = {
                **res['properties'],
                'model_ref_id': prop_definition['data']['data']['resource_id']
            }
        elif prop_definition['type'] == 'bitmap':
            res['properties'] = {
                **res['properties'],
                'texture': ';'.join(self._texture_ids(
                    prop_definition['data']['data']['resource_id'],
                    prop_definition['data']['data']['frame_count']
                    if prop_definition['flags']['is_animated']
                    else 1,
                    is_opened_track)),
                'width': prop_definition['data']['data']['width'],
                'height': prop_definition['data']['data']['height'],
                'animation_interval': prop_definition['data']['data']['animation_interval']
            }
        elif prop_definition['type'] == 'two_sided_bitmap':
            res['properties'] = {
                **res['properties'],
                'texture': ';'.join(self._texture_ids(prop_definition['data']['data']['resource_id'],
                                                      1,
                                                      is_opened_track)),
                'back_texture': ';'.join(self._texture_ids(prop_definition['data']['data']['resource_id_2'],
                                                           1,
                                                           is_opened_track)),
                'width': prop_definition['data']['data']['width'],
                'back_width': prop_definition['data']['data']['width_2'],
                'height': prop_definition['data']['data']['height']
            }
        return res

    def render_tnfs_props(self, id, data, is_opened_track, min_id, max_id, pivot=(0, 0, 0)):
        meshes = []
        additional_textures = []
        for i, p in enumerate(data['props']):
            if p['road_point_idx'] > max_id or p['road_point_idx'] < min_id:
                continue
            descr = data['prop_descr'][p['prop_descr_idx']]
            spline_point = data['road_spline'][p['road_point_idx']]

            def position_mesh(mesh):
                mesh.rotate_z(-(p['rotation'] + spline_point['orientation']))
                mesh.pivot_offset = (
                    pivot[0] - (p['position']['x'] + spline_point['position']['x']),
                    pivot[1] - (p['position']['z'] + spline_point['position']['z']),
                    pivot[2] - (p['position']['y'] + spline_point['position']['y']),
                )

            if descr['type'] in ['bitmap', 'two_sided_bitmap']:
                width = descr['data']['data']['width']
                height = descr['data']['data']['height']
                mesh = SubMesh()
                mesh.name = f'prop_{i}'
                mesh.vertices = [
                    [-width / 2, 0, height],
                    [width / 2, 0, height],
                    [width / 2, 0, 0],
                    [-width / 2, 0, 0],
                ]
                mesh.vertex_uvs = [[0, 0], [1, 0], [1, 1], [0, 1]]
                mesh.polygons = [[0, 2, 3], [0, 1, 2]]
                position_mesh(mesh)
                mesh.texture_id = 'foreground/' + self._texture_ids(descr['data']['data']['resource_id'], 1,
                                                                    is_opened_track)[0]
                meshes.append(mesh)
                if descr['type'] == 'two_sided_bitmap':
                    width_2 = descr['data']['data']['width_2']
                    mesh = SubMesh()
                    mesh.name = f'prop_{i}_2'
                    mesh.vertices = [
                        [width / 2, 0, height],
                        [width / 2, width_2, height],
                        [width / 2, width_2, 0],
                        [width / 2, 0, 0],
                    ]
                    mesh.vertex_uvs = [[0, 0], [1, 0], [1, 1], [0, 1]]
                    mesh.polygons = [[0, 2, 3], [0, 1, 2]]
                    position_mesh(mesh)
                    mesh.texture_id = 'foreground/' + self._texture_ids(descr['data']['data']['resource_id_2'], 1,
                                                                        is_opened_track)[0]
                    meshes.append(mesh)
            else:
                from library import require_resource
                (prop_id, prop_block, prop_data), _ = require_resource(
                    os.path.join('/'.join(id.split('/')[:-2]),
                                 f'ETRACKFM/{id.split("/")[-1][:3]}_001.FAM__children/3/data/children'
                                 f'/{descr["data"]["data"]["resource_id"]}/data/children/0/data')
                )
                from serializers import OripGeometrySerializer
                _, shpi_block, shpi_data, sub_models = OripGeometrySerializer().build_mesh(prop_data, prop_id)
                for mesh in sub_models.values():
                    mesh.name = f'prop_{i}_' + mesh.name
                    mesh.texture_id = f"props/{descr['data']['data']['resource_id']}/0/assets/" + mesh.texture_id
                    position_mesh(mesh)
                    meshes.append(mesh)
                for ti, texture_name in enumerate(shpi_data['children_aliases']):
                    texture_block = shpi_block.field_blocks_map['children'].child.possible_blocks[
                        shpi_data['children'][ti]['choice_index']]
                    from resources.eac.bitmaps import AnyBitmapBlock
                    if not isinstance(texture_block, AnyBitmapBlock):
                        continue
                    additional_textures.append(f"props/{descr['data']['data']['resource_id']}/0/assets/{texture_name}")
        return (meshes, additional_textures)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        is_opened = data['loop_chunk'] == 0

        map_scene = Scene(name='map',
                          obj_name='map',
                          mtl_name='terrain',
                          mtl_texture_path_func=lambda
                              x: f'../../ETRACKFM/{id.split("/")[-1][:3]}_001.FAM/{x}.png',
                          skip_obj_export=self.settings.maps__save_as_chunked)
        scenes = [map_scene]

        # add road spline to map scene
        spline = data['road_spline'][:len(data['terrain']) * 4]
        curve = {
            'name': 'road_path',
            'closed': not is_opened,
            'points': [[x['position']['x'], x['position']['z'], x['position']['y']]
                       for x in spline],
            'properties': {
                # 'orientation': [-x['orientation'] for x in spline],
                'slope': [x['slope'] for x in spline],
                'slant': [x['slant_a'] for x in spline],
                'left_barrier_distance': [x['left_barrier'] for x in spline],
                'right_barrier_distance': [x['right_barrier'] for x in spline],
                'left_verge_distance': [x['left_verge'] for x in spline],
                'right_verge_distance': [x['right_verge'] for x in spline],
                'lanes_backward': [x['num_lanes'][0] for x in spline],
                'lanes_forward': [x['num_lanes'][1] for x in spline],
                'max_ai_speed': [data['ai_info'][math.floor(i / 4)]['max_ai_speed'] for i in
                                 range(len(data['terrain']) * 4)],
                'max_traffic_speed': [data['ai_info'][math.floor(i / 4)]['max_traffic_speed'] for i in
                                      range(len(data['terrain']) * 4)],
            },
        }
        if is_opened:
            # a terminal road path point: when go backwards, race ends after this point
            curve['properties']['start_point_index'] = 12
            # a finish road path point
            curve['properties']['finish_point_index'] = data['num_chunks'] * 4 - 179
        map_scene.curves.append(curve)

        # build terrain chunks
        chunks = []
        for (i, terrain_entry) in enumerate(data['terrain']):
            road_path_index = i * 4
            chunk = self.TerrainChunk(id, block, data)
            chunk.read_matrix(terrain_entry['rows'], data['road_spline'][road_path_index:road_path_index + 4])
            if terrain_entry['fence']['texture_id'] != 0 or terrain_entry['fence']['has_left_fence'] or \
                    terrain_entry['fence']['has_right_fence']:
                fence_texture_id = terrain_entry['fence']['texture_id']
                if is_opened:
                    if id.endswith('AL1.TRI') and fence_texture_id == 16:
                        fence_texture_id = fence_texture_id * 3
                    chunk.fence_texture_name = 'background/' + self._get_texture_name_from_id(is_opened,
                                                                                              fence_texture_id)
                else:
                    chunk.fence_texture_name = ('background/0/GA00'
                                                if id.split('/')[-1] in ['TR3.TRI', 'TR4.TRI', 'TR5.TRI']
                                                else 'background/0/ga00')
                chunk.has_left_fence = terrain_entry['fence']['has_left_fence']
                chunk.has_right_fence = terrain_entry['fence']['has_right_fence']
                map_scene.mtl_texture_names.append(chunk.fence_texture_name)
            chunks.append(chunk)
        for i, chunk in enumerate(chunks):
            chunk.next_chunk = (chunks[i + 1]
                                if (i < len(chunks) - 1)
                                else (None if is_opened else chunks[0]))

        # put terrain chunks in scenes
        for (i, terrain_entry) in enumerate(data['terrain']):
            texture_names = [self._get_texture_name_from_id(is_opened, tid) for tid in terrain_entry['texture_ids']]
            map_scene.mtl_texture_names.extend([f'background/{x}' for x in texture_names])
            meshes = chunks[i].build_models(i, texture_names)
            for mesh in meshes:
                mesh.change_axes(new_z='y', new_y='z')
            if self.settings.maps__save_as_chunked:
                position = (
                    data['road_spline'][i * 4]['position']['x'],
                    data['road_spline'][i * 4]['position']['z'],
                    data['road_spline'][i * 4]['position']['y'],
                )
                dummy = {
                    'name': f'chunk_{i}',
                    'position': position,
                    'properties': {
                        'is_chunk': True,
                        'chunk': f'terrain_chunk_{i}',
                    },
                }
                if i < len(data['terrain']) - 1:
                    dummy['properties']['children'] = [f'chunk_{i + 1}']
                elif not is_opened:
                    dummy['properties']['children'] = ['chunk_0']
                map_scene.dummies.append(dummy)
                for mesh in meshes:
                    mesh.pivot_offset = position
                scene = Scene(name=f'terrain_chunk_{i}',
                              sub_meshes=meshes,
                              obj_name=f'terrain_chunk_{i}',
                              mtl_name='terrain',
                              bake_textures=False,
                              skip_mtl_export=True)
                if self.settings.maps__add_props_to_obj:
                    (meshes, txs) = self.render_tnfs_props(id, data, is_opened, i * 4, (i + 1) * 4 - 1, position)
                    scene.sub_meshes.extend(meshes)
                    map_scene.mtl_texture_names.extend(txs)
                else:
                    scene.dummies = [self._prop_json(data, o, is_opened, True)
                                     for o in data['props']
                                     if (i + 1) * 4 > o['road_point_idx'] >= i * 4]
                    for j, d in enumerate(scene.dummies):
                        d['name'] += str(j)
                scenes.append(scene)
            else:
                map_scene.sub_meshes.extend(meshes)
        if not self.settings.maps__save_as_chunked:
            if self.settings.maps__add_props_to_obj:
                (meshes, txs) = self.render_tnfs_props(id, data, is_opened, 0, len(data['terrain']) * 4 - 1, (0, 0, 0))
                map_scene.sub_meshes.extend(meshes)
                map_scene.mtl_texture_names.extend(txs)
            else:
                prop_dummies = [self._prop_json(data, o, is_opened, False)
                                for o in data['props']
                                if len(data['terrain']) * 4 > o['road_point_idx'] >= 0]
                for i, d in enumerate(prop_dummies):
                    d['name'] += str(i)
                map_scene.dummies.extend(prop_dummies)

        if self.settings.maps__add_props_to_obj:
            resource_ids = [x['data']['data']['resource_id']
                            for x in data['prop_descr']
                            if x['type'] in ['bitmap', 'two_sided_bitmap']]
            resource_ids += [x['data']['data']['resource_id_2']
                             for x in data['prop_descr']
                             if x['type'] == 'two_sided_bitmap']
            map_scene.mtl_texture_names.extend([f'foreground/{self._texture_ids(x, 1, is_opened)[0]}'
                                                for x in resource_ids])

        if self.settings.maps__save_terrain_collisions:
            for scene in scenes:
                scene.extra_script += self.terrain_collisions_script

        if self.settings.maps__save_invisible_wall_collisions:
            left_barrier_points = BarrierPath(
                [[rp['position']['x'] + rp['left_barrier'] * math.cos(rp['orientation'] + math.pi),
                  rp['position']['y'],
                  rp['position']['z'] - rp['left_barrier'] * math.sin(rp['orientation'] + math.pi)
                  ] for rp in data['road_spline'][:len(data['terrain']) * 4]])
            right_barrier_points = BarrierPath(
                [[rp['position']['x'] + rp['right_barrier'] * math.cos(rp['orientation']),
                  rp['position']['y'],
                  rp['position']['z'] - rp['right_barrier'] * math.sin(rp['orientation'])
                  ] for rp in data['road_spline'][:len(data['terrain']) * 4]])
            if not is_opened:
                left_barrier_points.points += [left_barrier_points.points[0]]
                right_barrier_points.points += [right_barrier_points.points[0]]
                left_barrier_points.is_closed = right_barrier_points.is_closed = True

            left_barrier_points.optimize()
            left_barrier_points.points = [[p[0], p[2], p[1]] for p in left_barrier_points.points]
            left_barrier_points.z_up = True
            right_barrier_points.optimize()
            right_barrier_points.points = [[p[0], p[2], p[1]] for p in right_barrier_points.points]
            right_barrier_points.z_up = True

            map_scene.extra_script += self.wall_collisions_script.substitute({
                'left_barrier': json.dumps({
                    'points': left_barrier_points.points,
                    'middle_points': left_barrier_points.middle_points,
                    'lengths': left_barrier_points.lengths,
                    'orientations': left_barrier_points.orientations,
                }),
                'right_barrier': json.dumps({
                    'points': right_barrier_points.points,
                    'middle_points': right_barrier_points.middle_points,
                    'lengths': right_barrier_points.lengths,
                    'orientations': right_barrier_points.orientations,
                }),
            })

        # export scenes
        export_scenes(scenes, path, self.settings)


class TrkMapSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    terrain_collisions_script = """
def find_terrain_chunks():
    import re
    pattern = re.compile(f"^(block_)|(prop_)")
    return [x for x in bpy.data.objects if pattern.match(x.name)]

bpy.ops.object.select_all(action='DESELECT')
is_active_set = False
objects = find_terrain_chunks()
for object in objects:
    object.select_set(True)
    if not is_active_set:
        bpy.context.view_layer.objects.active = object
        is_active_set = True
if len(objects) > 0:
    bpy.ops.rigidbody.objects_add(type='PASSIVE')
for obj in bpy.context.selected_objects:
    obj.rigid_body.collision_shape = 'MESH'
"""

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id, block, **kwargs)
        from library import require_resource
        try:
            (_, _, texture_map), _ = require_resource(id[:-3] + 'COL__extrablocks/0/data_records/data')

            def get_texture(tex):
                return f"{texture_map[tex]['texture_number']:04}", texture_map[tex]['alignment']
        except Exception:
            if self.settings.print_errors:
                traceback.print_exc()

            def get_texture(tex):
                return f"{tex:04}", 0
        blocks = []
        for sb in data['superblocks']:
            blocks += sb['blocks']

        map_scene = Scene(name='map',
                          obj_name='map',
                          mtl_name='terrain',
                          mtl_texture_path_func=lambda x: f'textures/{x}.png',
                          skip_obj_export=self.settings.maps__save_as_chunked)
        scenes = [map_scene]

        # add road spline to map scene
        spline = data['block_positions']
        curve = {
            'name': 'road_path',
            'closed': True,
            'points': [[p['x'], p['z'], p['y']] for p in spline],
        }
        map_scene.curves.append(curve)

        def get_uvs(alignment):
            uvs = [[0, 1], [1, 1], [1, 0], [0, 0]]
            if str(alignment).startswith('rotate_90'):
                uvs = rotate_list(uvs, 1)
            elif str(alignment).startswith('rotate_180'):
                uvs = rotate_list(uvs, 2)
            elif str(alignment).startswith('rotate_270'):
                uvs = rotate_list(uvs, 3)
            elif alignment == 'flip_h':
                uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
            elif alignment == 'flip_v':
                uvs = [uvs[3], uvs[2], uvs[1], uvs[0]]
            return uvs

        chunks = []
        texture_names = set()
        for block_i, block in enumerate(blocks):
            model = Mesh()
            model.name = f'block_{block_i}'
            pivot = data['block_positions'][block['block_idx']]
            next_pivot = data['block_positions'][
                block['block_idx'] + 1
                if block['block_idx'] < len(blocks) - 1
                else 0
            ]
            model.pivot_offset = (-pivot['x'], -pivot['y'], -pivot['z'])
            vertices = [[v['x'], v['y'], v['z']] for v in block['vertices']]
            for v in vertices[:block['nv8']]:
                v[0] += next_pivot['x'] - pivot['x']
                v[1] += next_pivot['y'] - pivot['y']
                v[2] += next_pivot['z'] - pivot['z']
            # alignments=set()
            for p in block['polygons'][(block['np4'] + block['np2']):]:
                texture_name, texture_alignment = get_texture(p['texture'])
                # alignments.add(str(texture_alignment))
                uvs = get_uvs(texture_alignment)
                base_idx = len(model.vertices)
                for i, v_index in enumerate(p['vertices']):
                    model.vertices.append(vertices[v_index])
                    model.vertex_uvs.append(uvs[i])
                model.polygons.append([base_idx, base_idx + 1, base_idx + 2, base_idx + 3])
                model.texture_ids.append(texture_name)
                texture_names.add(texture_name)
            # model.name += '__' + '_'.join(alignments)
            sub_meshes = model.split_by_texture_ids()

            proxies = [item for sublist in (eb['data_records']['data']
                                            for eb in block['extrablocks']
                                            if eb['type'] in ['props_7', 'props_18'])
                       for item in sublist]
            if len(proxies) > 0:
                proxy_descr_extrablock = next(
                    eb['data_records']['data'] for eb in block['extrablocks'] if eb['type'] == 'prop_descriptions')
                for proxy_i, proxy in enumerate(proxies):
                    if proxy['type'] not in ['static_prop', 'animated_prop']:
                        continue
                    object = proxy_descr_extrablock[proxy['prop_descr_idx']]
                    position = proxy['position']['data'] \
                        if proxy['type'] == 'static_prop' else \
                        proxy['position']['data']['frames'][0]['position']
                    model = Mesh()
                    model.name = f'prop_{block_i}_{proxy_i}'
                    model.pivot_offset = (-position['x'], -position['y'], -position['z'])
                    # alignments=set()
                    for p in object['polygons']:
                        texture_name, texture_alignment = get_texture(p['texture'])
                        # alignments.add(str(texture_alignment))
                        uvs = get_uvs(texture_alignment)
                        base_idx = len(model.vertices)
                        for i, v_index in enumerate(p['vertices']):
                            v = object['vertices'][v_index]
                            model.vertices.append([v['x'], v['y'], v['z']])
                            model.vertex_uvs.append(uvs[i])
                        model.polygons.append([base_idx, base_idx + 1, base_idx + 2, base_idx + 3])
                        model.texture_ids.append(texture_name)
                        texture_names.add(texture_name)
                    # model.name += '__' + '_'.join(alignments)
                    sub_meshes.extend(model.split_by_texture_ids())
            chunks.append([[m for m, _, _ in sub_meshes], (pivot['x'], pivot['y'], pivot['z'])])
        map_scene.mtl_texture_names = list(texture_names)
        for chunk in chunks:
            chunk[1] = (chunk[1][0], chunk[1][2], chunk[1][1])
            for mesh in chunk[0]:
                mesh.pivot_offset = (mesh.pivot_offset[0], mesh.pivot_offset[2], mesh.pivot_offset[1])
                mesh.change_axes(new_z='y', new_y='z')
        if self.settings.maps__save_as_chunked:
            for i, (meshes, chunk_pos) in enumerate(chunks):
                for mesh in meshes:
                    mesh.pivot_offset = (mesh.pivot_offset[0] + chunk_pos[0],
                                         mesh.pivot_offset[1] + chunk_pos[1],
                                         mesh.pivot_offset[2] + chunk_pos[2])
                scene = Scene(name=f'terrain_chunk_{i}',
                              sub_meshes=meshes,
                              obj_name=f'terrain_chunk_{i}',
                              mtl_name='terrain',
                              bake_textures=False,
                              skip_mtl_export=True)
                scenes.append(scene)
        else:
            for (meshes, _) in chunks:
                map_scene.sub_meshes.extend(meshes)

        if self.settings.maps__save_terrain_collisions:
            for scene in scenes:
                scene.extra_script += self.terrain_collisions_script

        # export QFS
        try:
            (shpi_id, shpi_block, shpi_data), _ = require_resource(id[:-4] + '0.QFS__data')
            from serializers import ShpiArchiveSerializer
            ShpiArchiveSerializer().serialize(shpi_data, os.path.join(path, 'textures/'), shpi_id, shpi_block)
        except Exception:
            if self.settings.print_errors:
                traceback.print_exc()

        # export scenes
        export_scenes(scenes, path, self.settings)
