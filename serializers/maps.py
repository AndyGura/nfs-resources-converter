import json
import math
import os
import traceback
from copy import deepcopy
from string import Template
from typing import List, Dict, Optional, Tuple

import config
from library.utils import path_join
from resources.eac.maps import RoadSplinePoint
from resources.eac.utils import rotate_list
from serializers import BaseFileSerializer
from serializers.common.three_d import SubMesh, Mesh, Scene, export_scenes, BarrierPath

general_config = config.general_config()


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
            build_matrix_row = row = (
                build_matrix_row[:vertex_to_remove]
                + build_matrix_row[vertex_to_remove + 1 : vertex_to_duplicate + 1]
                + build_matrix_row[vertex_to_duplicate:]
            )
            # add a tiny offset for duplicated vertex so polygon will be rendered correctly
            row[vertex_to_duplicate - 1] = deepcopy(row[vertex_to_duplicate - 1])
            for i in ['x', 'y', 'z']:
                row[vertex_to_duplicate - 1][i] = (
                    row[vertex_to_duplicate - 1][i] * 0.99 + row[vertex_to_duplicate - 2][i] * 0.01
                )
            # fix vertex position in default matrix to omit holes in chunk connection (second point was removed from build matrix)
            row = com_matrix_row
            distance_to_left_vertex = math.sqrt(
                sum((row[vertex_to_remove][i] - row[vertex_to_remove - 1][i]) ** 2 for i in ['x', 'y', 'z'])
            )
            distance_to_right_vertex = math.sqrt(
                sum((row[vertex_to_remove][i] - row[vertex_to_remove + 1][i]) ** 2 for i in ['x', 'y', 'z'])
            )
            left_right_factor = distance_to_left_vertex / (distance_to_left_vertex + distance_to_right_vertex)
            # now vertex will be located on the straight line between neighbour vertices
            row[vertex_to_remove] = {
                i: row[vertex_to_remove - 1][i] * (1 - left_right_factor)
                + row[vertex_to_remove + 1][i] * left_right_factor
                for i in ['x', 'y', 'z']
            }
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
                        self.build_matrix[3 - row_index], 2, 6, self.matrix[3 - row_index]
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
                        matrix[0], 3, 6, self.next_chunk.build_matrix[3]
                    )
            models = []
            for i in range(10):
                inverted_matrix = [list(x) for x in zip(*matrix)]
                model = SubMesh()
                model.vertices = [[v['x'], v['y'], v['z']] for v in sum(inverted_matrix[i : i + 2], [])]
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
                                inverted_matrix[vertices_matrix_indices[0]][j]['z'],
                            ]
                            model.vertices[j + 5] = [
                                inverted_matrix[vertices_matrix_indices[1]][j]['x'],
                                inverted_matrix[vertices_matrix_indices[1]][j]['y'],
                                inverted_matrix[vertices_matrix_indices[1]][j]['z'],
                            ]
                polygons = [
                    [
                        [i, int(len(model.vertices) / 2) + i, 1 + i],
                        [int(len(model.vertices) / 2) + i, int(len(model.vertices) / 2) + 1 + i, 1 + i],
                    ]
                    for i in range(int(len(model.vertices) / 2) - 1)
                ]
                model.polygons = [item for row in polygons for item in row]
                model.vertex_uvs = [
                    [
                        (x % int(len(model.vertices) / 2)) / 2,
                        (0 if x < int(len(model.vertices) / 2) else 1)
                        if i < int(len(model.vertices) / 2)
                        else (1 if x < int(len(model.vertices) / 2) else 0),
                    ]
                    for x in range(len(model.vertices))
                ]
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
                model.vertices.append(
                    [road_point['x'], road_point['y'] + self.get_fence_height(self.fence_texture_name), road_point['z']]
                )
            for i in range(len(matrix) - 1):
                model.polygons.append([i * 2, i * 2 + 1, i * 2 + 3])
                model.polygons.append([i * 2 + 2, i * 2, i * 2 + 3])
            model.vertex_uvs = [[math.floor(x / 2), 0 if x % 2 == 1 else 1] for x in range(len(model.vertices))]
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
# for obj in bpy.context.selected_objects:
#     obj.rigid_body.collision_shape = 'CONVEX_HULL'
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
            return (
                '0/' + str(math.floor(texture_id / 3)).zfill(2) + hex(10 + texture_id % 3)[2:].upper() + '0'
            )  # zero scale is the biggest and always presented in FAM file

    def _texture_ids(self, tex_id, frame_count, is_opened_track):
        tex_id = math.floor(tex_id / 4)
        return [
            f'{tex_id + i}/0000' if is_opened_track else f'0/{str(tex_id + i).rjust(2, "0")}00'
            for i in range(max(frame_count, 1))
        ]

    def _prop_json(self, data: dict, instance, is_opened_track, use_local_coordinates) -> Dict:
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
            },
        }
        if use_local_coordinates:
            res['position'] = [
                res['position'][0] - data['road_spline'][spline_index - (spline_index % 4)]['position']['x'],
                res['position'][1] - data['road_spline'][spline_index - (spline_index % 4)]['position']['z'],
                res['position'][2] - data['road_spline'][spline_index - (spline_index % 4)]['position']['y'],
            ]
        if prop_definition['type'] == 'model':
            res['properties'] = {**res['properties'], 'model_ref_id': prop_definition['data']['data']['resource_id']}
        elif prop_definition['type'] == 'bitmap':
            res['properties'] = {
                **res['properties'],
                'texture': ';'.join(
                    self._texture_ids(
                        prop_definition['data']['data']['resource_id'],
                        prop_definition['data']['data']['frame_count']
                        if prop_definition['flags']['is_animated']
                        else 1,
                        is_opened_track,
                    )
                ),
                'width': prop_definition['data']['data']['width'],
                'height': prop_definition['data']['data']['height'],
                'animation_interval': prop_definition['data']['data']['animation_interval'],
            }
        elif prop_definition['type'] == 'two_sided_bitmap':
            res['properties'] = {
                **res['properties'],
                'texture': ';'.join(
                    self._texture_ids(prop_definition['data']['data']['resource_id'], 1, is_opened_track)
                ),
                'back_texture': ';'.join(
                    self._texture_ids(prop_definition['data']['data']['resource_id_2'], 1, is_opened_track)
                ),
                'width': prop_definition['data']['data']['width'],
                'back_width': prop_definition['data']['data']['width_2'],
                'height': prop_definition['data']['data']['height'],
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
                mesh.texture_id = (
                    'foreground/' + self._texture_ids(descr['data']['data']['resource_id'], 1, is_opened_track)[0]
                )
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
                    mesh.texture_id = (
                        'foreground/' + self._texture_ids(descr['data']['data']['resource_id_2'], 1, is_opened_track)[0]
                    )
                    meshes.append(mesh)
            else:
                from library import require_resource

                (prop_id, prop_block, prop_data), _ = require_resource(
                    path_join(
                        '/'.join(id.split('/')[:-2]),
                        f'ETRACKFM/{id.split("/")[-1][:3]}_001.FAM__children/3/item/data/children'
                        f'/{descr["data"]["data"]["resource_id"]}/item/data/children/0/item/data',
                    )
                )
                from serializers import OripGeometrySerializer

                _, shpi_block, shpi_data, sub_models = OripGeometrySerializer().build_mesh(prop_data, prop_id)
                for mesh in sub_models.values():
                    mesh.name = f'prop_{i}_' + mesh.name
                    mesh.texture_id = f'props/{descr["data"]["data"]["resource_id"]}/0/assets/' + mesh.texture_id
                    position_mesh(mesh)
                    meshes.append(mesh)
                for ti, child in enumerate(shpi_data['children']):
                    texture_block = shpi_block.item_block.possible_blocks[child['item']['choice_index']]
                    from resources.eac.bitmaps import EacImage

                    if not isinstance(texture_block, EacImage):
                        continue
                    additional_textures.append(
                        f'props/{descr["data"]["data"]["resource_id"]}/0/assets/{child["alias"]}'
                    )
        return (meshes, additional_textures)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        is_opened = data['loop_chunk'] == 0

        map_scene = Scene(
            name='map',
            obj_name='map',
            mtl_name='terrain',
            mtl_texture_path_func=lambda x: f'../../ETRACKFM/{id.split("/")[-1][:3]}_001.FAM/{x}.png',
            skip_obj_export=self.settings.maps__save_as_chunked,
        )
        scenes = [map_scene]

        # add road spline to map scene
        spline = data['road_spline'][: len(data['terrain']) * 4]
        item_mode_names = RoadSplinePoint().field_blocks_map['item_mode'].enum_name_map
        curve = {
            'name': 'road_path',
            'closed': not is_opened,
            'points': [[x['position']['x'], x['position']['z'], x['position']['y']] for x in spline],
            'properties': {
                # 'orientation': [-x['orientation'] for x in spline],
                'slope': [x['slope'] for x in spline],
                'slant': [x['slant'] for x in spline],
                'left_barrier_distance': [x['left_barrier'] for x in spline],
                'right_barrier_distance': [x['right_barrier'] for x in spline],
                'left_verge_distance': [x['left_verge'] for x in spline],
                'right_verge_distance': [x['right_verge'] for x in spline],
                'lanes_backward': [x['num_lanes'][0] for x in spline],
                'lanes_forward': [x['num_lanes'][1] for x in spline],
                # raw byte values, not enum names
                'item_mode': [item_mode_names.index(x['item_mode']) for x in spline],
                'left_shoulder_surface_type': [x['shoulder_surface_type'][0] for x in spline],
                'right_shoulder_surface_type': [x['shoulder_surface_type'][1] for x in spline],
                'left_fence': [x['fence_flag'][0] for x in spline],
                'right_fence': [x['fence_flag'][1] for x in spline],
                'max_ai_speed': [
                    data['ai_info'][math.floor(i / 4)]['top_speed'] for i in range(len(data['terrain']) * 4)
                ],
                'max_traffic_speed': [
                    data['ai_info'][math.floor(i / 4)]['safe_speed'] for i in range(len(data['terrain']) * 4)
                ],
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
        for i, terrain_entry in enumerate(data['terrain']):
            road_path_index = i * 4
            chunk = self.TerrainChunk(id, block, data)
            chunk.read_matrix(terrain_entry['rows'], data['road_spline'][road_path_index : road_path_index + 4])
            if (
                terrain_entry['fence']['texture_id'] != 0
                or terrain_entry['fence']['has_left_fence']
                or terrain_entry['fence']['has_right_fence']
            ):
                fence_texture_id = terrain_entry['fence']['texture_id']
                if is_opened:
                    if id.endswith('AL1.TRI') and fence_texture_id == 16:
                        fence_texture_id = fence_texture_id * 3
                    chunk.fence_texture_name = 'background/' + self._get_texture_name_from_id(
                        is_opened, fence_texture_id
                    )
                else:
                    chunk.fence_texture_name = (
                        'background/0/GA00'
                        if id.split('/')[-1] in ['TR3.TRI', 'TR4.TRI', 'TR5.TRI']
                        else 'background/0/ga00'
                    )
                chunk.has_left_fence = terrain_entry['fence']['has_left_fence']
                chunk.has_right_fence = terrain_entry['fence']['has_right_fence']
                map_scene.mtl_texture_names.append(chunk.fence_texture_name)
            chunks.append(chunk)
        for i, chunk in enumerate(chunks):
            chunk.next_chunk = chunks[i + 1] if (i < len(chunks) - 1) else (None if is_opened else chunks[0])

        # put terrain chunks in scenes
        for i, terrain_entry in enumerate(data['terrain']):
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
                scene = Scene(
                    name=f'terrain_chunk_{i}',
                    sub_meshes=meshes,
                    obj_name=f'terrain_chunk_{i}',
                    mtl_name='terrain',
                    bake_textures=False,
                    skip_mtl_export=True,
                )
                if self.settings.maps__add_props_to_obj:
                    (meshes, txs) = self.render_tnfs_props(id, data, is_opened, i * 4, (i + 1) * 4 - 1, position)
                    scene.sub_meshes.extend(meshes)
                    map_scene.mtl_texture_names.extend(txs)
                else:
                    scene.dummies = [
                        self._prop_json(data, o, is_opened, True)
                        for o in data['props']
                        if (i + 1) * 4 > o['road_point_idx'] >= i * 4
                    ]
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
                prop_dummies = [
                    self._prop_json(data, o, is_opened, False)
                    for o in data['props']
                    if len(data['terrain']) * 4 > o['road_point_idx'] >= 0
                ]
                for i, d in enumerate(prop_dummies):
                    d['name'] += str(i)
                map_scene.dummies.extend(prop_dummies)

        if self.settings.maps__add_props_to_obj:
            resource_ids = [
                x['data']['data']['resource_id']
                for x in data['prop_descr']
                if x['type'] in ['bitmap', 'two_sided_bitmap']
            ]
            resource_ids += [
                x['data']['data']['resource_id_2'] for x in data['prop_descr'] if x['type'] == 'two_sided_bitmap'
            ]
            map_scene.mtl_texture_names.extend(
                [f'foreground/{self._texture_ids(x, 1, is_opened)[0]}' for x in resource_ids]
            )

        if self.settings.maps__save_terrain_collisions:
            for scene in scenes:
                scene.extra_script += self.terrain_collisions_script

        if self.settings.maps__save_invisible_wall_collisions:
            left_barrier_points = BarrierPath(
                [
                    [
                        rp['position']['x'] + rp['left_barrier'] * math.cos(rp['orientation'] + math.pi),
                        rp['position']['y'],
                        rp['position']['z'] - rp['left_barrier'] * math.sin(rp['orientation'] + math.pi),
                    ]
                    for rp in data['road_spline'][: len(data['terrain']) * 4]
                ]
            )
            right_barrier_points = BarrierPath(
                [
                    [
                        rp['position']['x'] + rp['right_barrier'] * math.cos(rp['orientation']),
                        rp['position']['y'],
                        rp['position']['z'] - rp['right_barrier'] * math.sin(rp['orientation']),
                    ]
                    for rp in data['road_spline'][: len(data['terrain']) * 4]
                ]
            )
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

            map_scene.extra_script += self.wall_collisions_script.substitute(
                {
                    'left_barrier': json.dumps(
                        {
                            'points': left_barrier_points.points,
                            'middle_points': left_barrier_points.middle_points,
                            'lengths': left_barrier_points.lengths,
                            'orientations': left_barrier_points.orientations,
                        }
                    ),
                    'right_barrier': json.dumps(
                        {
                            'points': right_barrier_points.points,
                            'middle_points': right_barrier_points.middle_points,
                            'lengths': right_barrier_points.lengths,
                            'orientations': right_barrier_points.orientations,
                        }
                    ),
                }
            )

        # export scenes
        return export_scenes(scenes, path, self.settings)


TERRAIN_COLLISIONS_SCRIPT = """

bpy.ops.object.select_all(action='DESELECT')
is_active_set = False
objects = [x for x in bpy.data.objects if x.name == "terrain_collision_mesh"]
for object in objects:
    object.select_set(True)
    if not is_active_set:
        bpy.context.view_layer.objects.active = object
        is_active_set = True
if len(objects) > 0:
    bpy.ops.rigidbody.objects_add(type='PASSIVE')
for obj in bpy.context.selected_objects:
    obj.rigid_body.collision_shape = 'MESH' 
    obj.hide_render = True
    obj.display_type = 'WIRE'   
 
            """


# Animation delay units per second of NFS2-NFS4 animated props (assumed, not confirmed)
ANIMATION_DELAY_UNITS_PER_SECOND = 64


class TrackProp:
    """A prop placed on a NFS2-NFS4 track. Keyframes are (position, orientation) pairs in game coordinates (Y up), the
    orientation is a quaternion (x, y, z, w) or None. A static prop has one keyframe, an animated prop loops through
    them with `delay` between keyframes. Model vertices are rotated by the orientation, then moved to the position"""

    def __init__(self, model_id: str, keyframes: List[Tuple[tuple, Optional[tuple]]], delay=None, chunk_index=None):
        self.model_id = model_id
        self.keyframes = keyframes
        self.delay = delay
        # None: the chunk nearest to the first keyframe
        self.chunk_index = chunk_index
        # the prop is not confirmed to look like this in game (GUI hides it unless "show hidden fields" is on)
        self.is_unknown = False

    @property
    def is_animated(self):
        return self.delay is not None


def _point(p: dict) -> tuple:
    return p['x'], p['y'], p['z']


def _quaternion(q: dict) -> tuple:
    return q['x'], q['y'], q['z'], q['w']


def _rotate_by_quaternion(q: Optional[tuple], v: list) -> list:
    if q is None:
        return list(v)
    x, y, z, w = q
    # v' = q v q^-1: t = 2 * cross(q.xyz, v), v' = v + w * t + cross(q.xyz, t)
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return [v[0] + w * tx + y * tz - z * ty, v[1] + w * ty + z * tx - x * tz, v[2] + w * tz + x * ty - y * tx]


def _to_export_axes(p) -> list:
    # game coordinates (Y up) to exported ones (Z up), the same as Mesh.change_axes(new_z='y', new_y='z')
    return [p[0], p[2], p[1]]


def _quaternion_to_export_axes(q: Optional[tuple]) -> list:
    # swapping Y and Z axes mirrors the rotation axis and negates the angle. Returns (w, x, y, z), as Blender does
    if q is None:
        return [1, 0, 0, 0]
    x, y, z, w = q
    return [w, -x, -z, -y]


def _alignment_uvs(alignment) -> List[List[float]]:
    # NFS2 COL texture alignment: base UVs for the 4 polygon vertices, rotated or flipped
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


def _add_quads(model: Mesh, polygons: list, vertices: list, get_texture):
    """Adds quad polygons ({'vertices': [4 indexes], ...}) to the model. get_texture(polygon) returns
    (texture name, UVs of the 4 polygon vertices)"""
    for p in polygons:
        texture_name, uvs = get_texture(p)
        base_idx = len(model.vertices)
        for i, v_index in enumerate(p['vertices']):
            model.vertices.append(list(vertices[v_index]))
            model.vertex_uvs.append(uvs[i])
        model.polygons.append([base_idx, base_idx + 1, base_idx + 2, base_idx + 3])
        model.texture_ids.append(texture_name)


def _require_track_sibling(id: str, file_name: str, sub_id: str = ''):
    """Loads a file next to the track one (`<dir>/<file_name>`), ignoring letter case, or its resource `sub_id`"""
    from library import require_resource
    from library.utils.file_utils import find_files_case_insensitive

    dirpath, _, _ = id.rpartition('/')
    path = f'{dirpath}/{file_name}' if dirpath else file_name
    path = next(iter(find_files_case_insensitive([path])), path).replace('\\', '/')
    return require_resource(path + sub_id)


def _shpi_aliases(qfs_data: dict) -> List[str]:
    return [x['alias'] for x in qfs_data['children'] if x['alias']]


def col_props(col_data: dict, get_texture) -> Tuple[List[TrackProp], Dict[str, Mesh]]:
    """Track-wide props of a NFS2/NFS3 COL file: models from its prop_descriptions extrablock, placed by props_7.
    get_texture(texture map index) returns (texture name, alignment)"""
    descriptions = next(
        (x['data_records']['data'] for x in col_data['extrablocks'] if x['type'] == 'prop_descriptions'), []
    )
    records = [r for x in col_data['extrablocks'] if x['type'] == 'props_7' for r in x['data_records']['data']]
    return _prop_records(records, descriptions, 'col_', get_texture, None)


def _deduplicate_models(models: Dict[str, Mesh]) -> Dict[str, str]:
    """Model id -> id of the first model with the same geometry and textures (e.g. the same tree placed many times as
    separate objects)"""
    first_ids = {}
    result = {}
    for model_id, model in models.items():
        key = (
            tuple(tuple(round(c, 4) for c in v) for v in model.vertices),
            tuple(tuple(round(c, 5) for c in uv) for uv in model.vertex_uvs),
            tuple(tuple(p) for p in model.polygons),
            tuple(model.texture_ids),
        )
        result[model_id] = first_ids.setdefault(key, model_id)
    return result


def _prop_description_mesh(description: dict, get_texture) -> Mesh:
    model = Mesh()

    def polygon_texture(p):
        texture_name, alignment = get_texture(p['texture'])
        return texture_name, _alignment_uvs(alignment)

    _add_quads(model, description['polygons'], [_point(v) for v in description['vertices']], polygon_texture)
    return model


def _prop_records(
    records: list, descriptions: list, model_prefix: str, get_texture, chunk_index
) -> Tuple[List[TrackProp], Dict[str, Mesh]]:
    """NFS2/NFS3 prop placements (props_7/props_18 extrablock records) and the models they use"""
    props = []
    models = {}
    for record in records:
        descr_idx = record['prop_descr_idx']
        if descr_idx >= len(descriptions):
            continue
        model_id = f'{model_prefix}{descr_idx}'
        position = record['position']['data']
        if record['type'] in ['static_prop', 'special_prop']:
            point = position['position'] if record['type'] == 'special_prop' else position
            prop = TrackProp(model_id, [(_point(point), None)], chunk_index=chunk_index)
        elif record['type'] == 'animated_prop':
            if not position['frames']:
                continue
            prop = TrackProp(
                model_id,
                [(_point(f['position']), _quaternion(f['orientation'])) for f in position['frames']],
                delay=position['anim_delay'],
                chunk_index=chunk_index,
            )
        else:
            continue
        if model_id not in models:
            models[model_id] = _prop_description_mesh(descriptions[descr_idx], get_texture)
        props.append(prop)
    return props, models


class EacTrackSerializer(BaseFileSerializer):
    """Common export of NFS2 (TRK), NFS3 and NFS4 (FRD) tracks: terrain chunks, props, collision mesh and QFS
    textures"""

    def __init__(self):
        super().__init__(is_dir=True)

    def _prop_meshes(self, model: Mesh, name: str, keyframe) -> List[SubMesh]:
        position, orientation = keyframe
        mesh = Mesh()
        mesh.name = name
        mesh.vertices = [_rotate_by_quaternion(orientation, v) for v in model.vertices]
        mesh.vertex_uvs = list(model.vertex_uvs)
        mesh.polygons = list(model.polygons)
        mesh.texture_ids = list(model.texture_ids)
        mesh.pivot_offset = (-position[0], -position[1], -position[2])
        return [m for m, _, _ in mesh.split_by_texture_ids()]

    def _export_prop_models(self, path: str, models: Dict[str, Mesh]) -> List[str]:
        """Exports every prop model in its own folder "props/<model id>/", like any other single model exported by the
        converter: "geometry.obj" + "material.mtl" (textures from "textures/" of the track), "body.glb" + "body.meta"
        for gg-web-engine (without materials: the game assigns track textures by mesh name "<model>__<texture>",
        like for terrain chunks)"""
        if not models:
            return []
        scenes = []
        for model_id in sorted(models):
            meshes = self._prop_meshes(models[model_id], model_id, ((0, 0, 0), None))
            for mesh in meshes:
                mesh.change_axes(new_z='y', new_y='z')
            scenes.append(
                Scene(
                    name='body',
                    sub_meshes=meshes,
                    obj_name='geometry',
                    mtl_name='material',
                    mtl_texture_names=sorted({m.texture_id for m in meshes if m.texture_id}),
                    mtl_texture_path_func=lambda x: f'../../textures/{x}.png',
                    bake_textures=False,
                    directory=f'{model_id}/',
                )
            )
        props_path = path_join(path, 'props/')
        os.makedirs(props_path, exist_ok=True)
        return export_scenes(scenes, props_path, self.settings)

    def _export_track(
        self,
        path: str,
        map_scene: Scene,
        chunks: List[Tuple[List[SubMesh], tuple]],
        props: List[TrackProp],
        prop_models: Dict[str, Mesh],
        texture_archive,
    ) -> List[str]:
        """
        chunks: (terrain meshes, chunk position) in game coordinates (Y up): world position of a vertex is
        `vertex - mesh.pivot_offset`. Props are baked into the chunk meshes (setting maps__add_props_to_obj), or else
        exported as dummies referencing models in "props/<model id>/" (see `_export_prop_models`). texture_archive is
        a function, which returns the QFS resource (id, block, data), exported to "textures/"
        """
        chunked = self.settings.maps__save_as_chunked
        pivots = [pivot for _, pivot in chunks]
        terrain = [list(meshes) for meshes, _ in chunks]
        prop_meshes = [[] for _ in chunks]
        dummies = [[] for _ in chunks]
        object_properties = [{} for _ in chunks]
        used_models = set()
        canonical_model_ids = _deduplicate_models(prop_models)

        def nearest_chunk(position):
            return min(range(len(pivots)), key=lambda i: sum((pivots[i][k] - position[k]) ** 2 for k in range(3)))

        for prop_i, prop in enumerate(props):
            model = prop_models.get(prop.model_id)
            if model is None or not pivots:
                continue
            model_id = canonical_model_ids[prop.model_id]
            position, orientation = prop.keyframes[0]
            chunk_i = prop.chunk_index if prop.chunk_index is not None else nearest_chunk(position)
            pivot = pivots[chunk_i] if chunked else (0, 0, 0)
            properties = {'is_prop': True, 'type': 'model', 'model_ref_id': model_id}
            if prop.is_unknown:
                properties['is_unknown'] = True
            if prop.is_animated:
                # positions are in the same coordinates as the dummy/mesh position: relative to the chunk position
                # when the track is saved as chunks
                properties['animation'] = json.dumps(
                    {
                        'delay': prop.delay,
                        'frame_duration': max(prop.delay, 1) / ANIMATION_DELAY_UNITS_PER_SECOND,
                        'frames': [
                            {
                                'position': _to_export_axes([p[k] - pivot[k] for k in range(3)]),
                                'quaternion': _quaternion_to_export_axes(q),
                            }
                            for p, q in prop.keyframes
                        ],
                    }
                )
            if self.settings.maps__add_props_to_obj:
                meshes = self._prop_meshes(model, f'prop_{prop_i}', prop.keyframes[0])
                prop_meshes[chunk_i].extend(meshes)
                if prop.is_animated:
                    for mesh in meshes:
                        object_properties[chunk_i][mesh.name] = properties
            else:
                dummies[chunk_i].append(
                    {
                        'name': f'prop_{prop_i}',
                        'position': _to_export_axes([position[k] - pivot[k] for k in range(3)]),
                        'quaternion': _quaternion_to_export_axes(orientation),
                        'properties': properties,
                    }
                )
                used_models.add(model_id)

        for i in range(len(chunks)):
            for mesh in terrain[i] + prop_meshes[i]:
                mesh.pivot_offset = (mesh.pivot_offset[0], mesh.pivot_offset[2], mesh.pivot_offset[1])
                mesh.change_axes(new_z='y', new_y='z')
        map_scene.mtl_texture_names = sorted(
            {m.texture_id for meshes in terrain + prop_meshes for m in meshes if m.texture_id}
        )

        if self.settings.maps__save_terrain_collisions:
            terrain_mesh = SubMesh()
            terrain_mesh.name = 'terrain_collision_mesh'
            for meshes in terrain:
                for mesh in meshes:
                    terrain_mesh.extend(mesh)
            terrain_mesh.collapse_vertices()
            map_scene.sub_meshes.append(terrain_mesh)
            map_scene.extra_script += TERRAIN_COLLISIONS_SCRIPT

        scenes = [map_scene]
        if chunked:
            for i, pivot in enumerate(pivots):
                chunk_pos = _to_export_axes(pivot)
                for mesh in terrain[i] + prop_meshes[i]:
                    mesh.pivot_offset = tuple(mesh.pivot_offset[k] + chunk_pos[k] for k in range(3))
                scenes.append(
                    Scene(
                        name=f'terrain_chunk_{i}',
                        sub_meshes=terrain[i] + prop_meshes[i],
                        obj_name=f'terrain_chunk_{i}',
                        mtl_name='terrain',
                        bake_textures=False,
                        skip_mtl_export=True,
                        dummies=dummies[i],
                        object_properties=object_properties[i],
                    )
                )
        else:
            for i in range(len(chunks)):
                map_scene.sub_meshes.extend(terrain[i] + prop_meshes[i])
                map_scene.dummies.extend(dummies[i])
                map_scene.object_properties.update(object_properties[i])

        exported_files = []
        # export QFS
        try:
            (shpi_id, shpi_block, shpi_data), _ = texture_archive()
            from serializers import ShpiArchiveSerializer

            ShpiArchiveSerializer().serialize(shpi_data, path_join(path, 'textures/'), shpi_id, shpi_block)
        except Exception:
            traceback.print_exc()

        exported_files += self._export_prop_models(path, {model_id: prop_models[model_id] for model_id in used_models})
        # export scenes
        return export_scenes(scenes, path, self.settings) + exported_files


class TrkMapSerializer(EacTrackSerializer):
    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id, block, **kwargs)
        track_name = id.split('/')[-1][:-4]

        col_data = None
        try:
            (_, _, col_data), _ = _require_track_sibling(id, f'{track_name}.COL')
        except Exception:
            traceback.print_exc()

        def texture_archive():
            return _require_track_sibling(id, f'{track_name}0.QFS', '__data')

        try:
            texture_map = col_data['extrablocks'][0]['data_records']['data']
            (_, _, qfs_data), _ = texture_archive()
            shpi_aliases = _shpi_aliases(qfs_data)

            def get_texture(tex):
                try:
                    return shpi_aliases[texture_map[tex]['texture_number']], texture_map[tex]['alignment']
                except IndexError:
                    return f'{tex:04}', 0
        except Exception:
            traceback.print_exc()

            def get_texture(tex):
                return f'{tex:04}', 0

        blocks = []
        for sb in data['superblocks']:
            blocks += sb['blocks']

        map_scene = Scene(
            name='map',
            obj_name='map',
            mtl_name='terrain',
            mtl_texture_path_func=lambda x: f'textures/{x}.png',
            skip_obj_export=self.settings.maps__save_as_chunked and not self.settings.maps__save_terrain_collisions,
        )

        # add road spline to map scene
        spline = data['block_positions']
        curve = {
            'name': 'road_path',
            'closed': True,
            'points': [[p['x'], p['z'], p['y']] for p in spline],
        }
        map_scene.curves.append(curve)

        def polygon_texture(p):
            texture_name, alignment = get_texture(p['texture'])
            return texture_name, _alignment_uvs(alignment)

        chunks = []
        props = []
        prop_models = {}
        for block_i, block in enumerate(blocks):
            model = Mesh()
            model.name = f'block_{block_i}'
            pivot = data['block_positions'][block['block_idx']]
            next_pivot = data['block_positions'][block['block_idx'] + 1 if block['block_idx'] < len(blocks) - 1 else 0]
            model.pivot_offset = (-pivot['x'], -pivot['y'], -pivot['z'])
            vertices = [[v['x'], v['y'], v['z']] for v in block['vertices']]
            for v in vertices[: block['nv8']]:
                v[0] += next_pivot['x'] - pivot['x']
                v[1] += next_pivot['y'] - pivot['y']
                v[2] += next_pivot['z'] - pivot['z']
            _add_quads(model, block['polygons'][(block['np4'] + block['np2']) :], vertices, polygon_texture)
            chunks.append(([m for m, _, _ in model.split_by_texture_ids()], _point(pivot)))

            descriptions = next(
                (eb['data_records']['data'] for eb in block['extrablocks'] if eb['type'] == 'prop_descriptions'), []
            )
            records = [
                r
                for eb in block['extrablocks']
                if eb['type'] in ['props_7', 'props_18']
                for r in eb['data_records']['data']
            ]
            block_props, block_models = _prop_records(records, descriptions, f'block_{block_i}_', get_texture, block_i)
            props += block_props
            prop_models.update(block_models)

        if col_data:
            col_track_props, col_models = col_props(col_data, get_texture)
            props += col_track_props
            prop_models.update(col_models)

        return self._export_track(path, map_scene, chunks, props, prop_models, texture_archive)


# Polygon chunks of a NFS3 FRD track block, which make the visible terrain: high-res track and high-res misc
# (other chunks are lower levels of detail of the same terrain, and lane markings)
FRD_TERRAIN_POLYGON_CHUNKS = [4, 5]


class FrdMapSerializer(EacTrackSerializer):
    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id, block, **kwargs)
        track_name = id.split('/')[-1][:-4]

        def texture_archive():
            return _require_track_sibling(id, f'{track_name}0.QFS', '__data')

        # Unlike NFS2 (TRK/COL), terrain polygon "tex_id" in FRD is not an index into the COL
        # texture map: it directly indexes the FRD file's own "texture_blocks" table, which in
        # turn stores the real index of the texture in the QFS/SHPI archive and UV-s of polygon corners
        texture_blocks = data['texture_blocks']
        shpi_aliases = []
        try:
            (_, _, qfs_data), _ = texture_archive()
            shpi_aliases = _shpi_aliases(qfs_data)
        except Exception:
            traceback.print_exc()

        def texture_name(texture_id):
            return shpi_aliases[texture_id] if texture_id < len(shpi_aliases) else f'{texture_id:04}'

        def polygon_texture(p):
            if p['tex_id'] >= len(texture_blocks):
                return f'{p["tex_id"]:04}', [[0, 1], [1, 1], [1, 0], [0, 0]]
            texture_block = texture_blocks[p['tex_id']]
            corners = texture_block['corners']
            return texture_name(texture_block['texture_id']), [[corners[i * 2], corners[i * 2 + 1]] for i in range(4)]

        blocks = data['blocks']
        map_scene = Scene(
            name='map',
            obj_name='map',
            mtl_name='terrain',
            mtl_texture_path_func=lambda x: f'textures/{x}.png',
            skip_obj_export=self.settings.maps__save_as_chunked and not self.settings.maps__save_terrain_collisions,
        )

        # add road spline to map scene
        spline = [x['position'] for x in blocks]
        curve = {
            'name': 'road_path',
            'closed': True,
            'points': [[p['x'], p['z'], p['y']] for p in spline],
        }
        map_scene.curves.append(curve)

        chunks = []
        for block_i, block in enumerate(blocks):
            polygon_block = data['polygon_blocks'][block_i]
            vertices = [_point(v) for v in block['vertices']]
            model = Mesh()
            model.name = f'block_{block_i}'
            for chunk_i in FRD_TERRAIN_POLYGON_CHUNKS:
                chunk = polygon_block['polygons'][chunk_i]
                if chunk['sz'] != 0:
                    _add_quads(model, chunk['data']['data'], vertices, polygon_texture)
            # static objects of the block (POLYOBJ), their vertices are in the block's vertex table
            objects = Mesh()
            objects.name = f'block_{block_i}_objects'
            for chunk in polygon_block['polyobj']:
                if chunk['sz'] > 0:
                    for obj in chunk['data']['data']:
                        if obj['type'] == 1:
                            _add_quads(objects, obj['data']['data'], vertices, polygon_texture)
            meshes = [m for m, _, _ in model.split_by_texture_ids()]
            if objects.polygons:
                meshes += [m for m, _, _ in objects.split_by_texture_ids()]
            chunks.append((meshes, _point(block['position'])))

        # extra objects (XOBJ): 4 chunks per block, then one with objects not attached to any block
        props = []
        prop_models = {}
        for xobj_chunk_i, xobj_chunk in enumerate(data['extraobject_blocks']):
            block_i = xobj_chunk_i // 4 if xobj_chunk_i // 4 < len(blocks) else None
            for xobj_i, xobj in enumerate(xobj_chunk):
                model_id = f'xobj_{xobj_chunk_i}_{xobj_i}'
                model = Mesh()
                _add_quads(model, xobj['polygons'], [_point(v) for v in xobj['vertices']], polygon_texture)
                prop_models[model_id] = model
                xobj_data = xobj['data']['data']
                if xobj['cross_type'] == 4:
                    props.append(TrackProp(model_id, [(_point(xobj_data['pt_ref']), None)], chunk_index=block_i))
                elif xobj_data['animdata']:
                    props.append(
                        TrackProp(
                            model_id,
                            [(_point(f['pt']), _quaternion(f['orientation'])) for f in xobj_data['animdata']],
                            delay=xobj_data['anim_delay'],
                            chunk_index=block_i,
                        )
                    )

        # track-wide objects from the COL file
        try:
            (_, _, col_data), _ = _require_track_sibling(id, f'{track_name}.COL')
            texture_map = col_data['extrablocks'][0]['data_records']['data']

            def col_texture(tex):
                if tex >= len(texture_map):
                    return f'{tex:04}', 0
                return texture_name(texture_map[tex]['texture_number']), texture_map[tex]['alignment']

            col_track_props, col_models = col_props(col_data, col_texture)
            # Texture numbers of COL models don't match the track QFS in NFS3 (e.g. TR00.COL has an airliner, which
            # gets brick textures), the archive they come from is not known
            for prop in col_track_props:
                prop.is_unknown = True
            props += col_track_props
            prop_models.update(col_models)
        except Exception:
            traceback.print_exc()

        return self._export_track(path, map_scene, chunks, props, prop_models, texture_archive)


# Polygon chunk field names that make up the visible terrain of a NFS4 track block. "lanes" and
# the still-unidentified "misc" chunks 1-4 are deliberately excluded: lanes are non-rendered
# helper polygons and the misc 1-4 chunks' purpose isn't known yet.
NFS4_TERRAIN_POLYGON_CHUNKS = [
    'polygons_low_res_track',
    'polygons_low_res_misc',
    'polygons_med_res_track',
    'polygons_med_res_misc',
    'polygons_high_res_track',
    'polygons_high_res_misc',
]


def _require_nfs4_texture_archive(id):
    # A NFS4 reverse-direction track ("Trn.FRD") doesn't always have its own texture archive -
    # for some tracks (e.g. GT1, GT2, Park) only the forward track's "Tr0.QFS" exists on disk,
    # and the reverse FRD's polygons reference texture indices into that same archive. Try the
    # archive named after this FRD's own basename first, and fall back to the same path with a
    # trailing "n" (the reverse-track marker) stripped before giving up.
    from library import require_resource
    from library.utils.file_utils import find_files_case_insensitive

    dirpath, _, filename = id.rpartition('/')
    prefix = f'{dirpath}/' if dirpath else ''
    basename = filename[:-4]
    candidates = [basename]
    if basename[-1:].lower() == 'n':
        candidates.append(basename[:-1])
    last_error = None
    for candidate in candidates:
        path = f'{prefix}{candidate}0.QFS'
        # Game files' letter case varies ("tr0.qfs", "TRN0.qFS"), which matters on case-sensitive file systems
        path = next(iter(find_files_case_insensitive([path])), path).replace('\\', '/')
        try:
            return require_resource(f'{path}__data')
        except Exception as e:
            last_error = e
    raise last_error


def _is_mirrored_copy(shpi_child) -> bool:
    # Some NFS4 track textures are stored twice in a row under the same name: the original with a
    # "<nonmirrored>" text attachment, then a horizontally mirrored copy tagged "<mirrored>".
    # Polygon texture indices don't count the mirrored copies.
    item = shpi_child['item']['data']
    text = item.get('text') if isinstance(item, dict) else None
    return bool(text) and text['text'].startswith('<mirrored>')


class Nfs4FrdMapSerializer(EacTrackSerializer):
    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id, block, **kwargs)

        def texture_archive():
            return _require_nfs4_texture_archive(id)

        # Unlike NFS3, a NFS4 FRD polygon's texture field indexes the track's QFS/SHPI archive
        # (no local texture table in the FRD itself), and no per-polygon UV corners are
        # stored anywhere - every polygon is UV-mapped to the full 0..1 quad of its texture.
        try:
            (_, _, qfs_data), _ = texture_archive()
            shpi_aliases = [x['alias'] for x in qfs_data['children'] if x['alias'] and not _is_mirrored_copy(x)]
        except Exception:
            traceback.print_exc()
            shpi_aliases = []

        def polygon_texture(p):
            tex = p['texture'] & 0x07FF
            uvs = [[0, 1], [1, 1], [1, 0], [0, 0]]
            if p['tex_flags'] & 0x10:
                uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
            rotate_bits = (p['tex_flags'] >> 7) & 0x3
            if rotate_bits:
                uvs = rotate_list(uvs, rotate_bits)
            return (shpi_aliases[tex] if tex < len(shpi_aliases) else f'{tex:04}'), uvs

        map_scene = Scene(
            name='map',
            obj_name='map',
            mtl_name='terrain',
            mtl_texture_path_func=lambda x: f'textures/{x}.png',
            skip_obj_export=self.settings.maps__save_as_chunked and not self.settings.maps__save_terrain_collisions,
        )

        # add road spline to map scene
        headers = data['blocks_headers']
        curve = {
            'name': 'road_path',
            'closed': True,
            'points': [[h['position']['x'], h['position']['z'], h['position']['y']] for h in headers],
        }
        map_scene.curves.append(curve)

        chunks = []
        props = []
        prop_models = {}

        def add_extra_objects(chunk, model_prefix, chunk_index):
            for i, (header, xobj) in enumerate(zip(chunk['object_headers'], chunk['objects'])):
                model_id = f'{model_prefix}{i}'
                model = Mesh()
                _add_quads(model, xobj['polygons'], [_point(v) for v in xobj['vertices']], polygon_texture)
                prop = nfs4_extra_object_prop(model_id, header, xobj, chunk_index)
                if prop and model.polygons:
                    prop_models[model_id] = model
                    props.append(prop)

        for block_i, (header, trk_block) in enumerate(zip(headers, data['blocks'])):
            model = Mesh()
            model.name = f'block_{block_i}'
            vertices = [_point(v) for v in trk_block['vertices']]
            for chunk_name in NFS4_TERRAIN_POLYGON_CHUNKS:
                _add_quads(model, trk_block[chunk_name], vertices, polygon_texture)
            chunks.append(([m for m, _, _ in model.split_by_texture_ids()], _point(header['position'])))
            for chunk_i in range(4):
                add_extra_objects(trk_block[f'extra_objects_{chunk_i}'], f'xobj_{block_i}_{chunk_i}_', block_i)
        # objects not attached to any block
        for chunk_i in range(2):
            add_extra_objects(data[f'global_objects_{chunk_i}'], f'xobj_global_{chunk_i}_', None)

        return self._export_track(path, map_scene, chunks, props, prop_models, texture_archive)


def nfs4_extra_object_prop(model_id: str, header: dict, xobj: dict, chunk_index) -> Optional[TrackProp]:
    """A NFS4 extra object as a prop. Vertices are relative to the object position; an animated object (type 3) moves
    along keyframes, a special object (type 6, physics prop) is rotated by its transform matrix"""
    if header['type'] == 3 and xobj['anim_data'] and xobj['anim_data']['keyframes']:
        animation = xobj['anim_data']
        return TrackProp(
            model_id,
            [(_point(f['pt']), _quaternion(f['orientation'])) for f in animation['keyframes']],
            delay=animation['delay'],
            chunk_index=chunk_index,
        )
    orientation = None
    if header['type'] == 6 and xobj['special_data']:
        # the matrix rotates vertices as row vectors (v' = v M): transposed for _matrix_to_quaternion
        t = xobj['special_data']['transform']
        orientation = _matrix_to_quaternion([t[0], t[3], t[6], t[1], t[4], t[7], t[2], t[5], t[8]])
    return TrackProp(model_id, [(_point(header['pt']), orientation)], chunk_index=chunk_index)


def _matrix_to_quaternion(m: list) -> tuple:
    """Rotation quaternion (x, y, z, w) of a row-major 3x3 rotation matrix, which transforms a vector as M v"""
    m00, m01, m02, m10, m11, m12, m20, m21, m22 = m
    trace = m00 + m11 + m22
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1)
        q = ((m21 - m12) * s, (m02 - m20) * s, (m10 - m01) * s, 0.25 / s)
    elif m00 > m11 and m00 > m22:
        s = 2 * math.sqrt(1 + m00 - m11 - m22)
        q = (0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    elif m11 > m22:
        s = 2 * math.sqrt(1 + m11 - m00 - m22)
        q = ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    else:
        s = 2 * math.sqrt(1 + m22 - m00 - m11)
        q = ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)
    length = math.sqrt(sum(c * c for c in q)) or 1
    return tuple(c / length for c in q)


def nfs6_route_model_files(level_dir: str) -> List[str]:
    """Model files of NFS6 race route (level folder): compartments listed in "drvpath.ini" ("compNN.o" in the track
    folder, all of them if the list can't be read). "levelG.o" of the route is not included: it is a set of props
    (signs, barrels, spike strips, helicopter) in their own local coordinates, placed by "level.dat" """
    import os
    import re
    from configparser import ConfigParser
    from library.utils.file_utils import find_files_case_insensitive

    track_dir = os.path.dirname(level_dir.rstrip('/\\'))
    compartments = []
    drvpath = find_files_case_insensitive([path_join(level_dir, 'drvpath.ini')])
    if drvpath:
        try:
            ini = ConfigParser(strict=False)
            with open(drvpath[0], encoding='latin-1') as f:
                # sections of the file are indented by tabs
                ini.read_string('\n'.join(line.strip() for line in f))
            for i in range(ini.getint('path', 'nodenum')):
                compartment = ini.getint(f'node{i}', 'compartmentId')
                if compartment not in compartments:
                    compartments.append(compartment)
        except Exception:
            traceback.print_exc()
            compartments = []
    files = []
    if compartments:
        for compartment in compartments:
            files += find_files_case_insensitive([path_join(track_dir, f'comp{compartment:02d}.o')])
    else:
        files = [x for x in find_files_case_insensitive([path_join(track_dir, 'comp*.o')]) if re.search(r'\d\.o$', x)]
    return files


class Nfs6AiPathsSerializer(BaseFileSerializer):
    """NFS6 race route: geometry of route compartments, one terrain chunk per compartment. Chunk
    positions (centers of model bounding boxes, in game coordinates) are saved to "terrain_chunks.json" """

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        import os
        from library import require_resource
        from library.loader import id_to_path, path_to_name
        from resources.eac.geometries.nfs6 import read_eagl_meshes
        from serializers.geometries import (
            eagl_sub_meshes,
            export_fsh_textures,
            find_eagl_texture_archive,
            eagl_texture_archive_name,
        )

        super().serialize(data, path, id, block, **kwargs)
        level_dir = os.path.dirname(id_to_path(id))
        # texture archive name -> (archive, model meshes)
        models = []
        for file_path in nfs6_route_model_files(level_dir):
            try:
                (model_id, _, model_data), _ = require_resource(path_to_name(file_path))
                models.append((model_id, os.path.basename(file_path), read_eagl_meshes(model_data)))
            except Exception:
                traceback.print_exc()
        archives = {}
        texture_names = {}
        alpha_modes = {}
        for model_id, file_name, meshes in models:
            archive_name = eagl_texture_archive_name(file_name)
            if archive_name not in archives:
                archives[archive_name] = (find_eagl_texture_archive(model_id, file_name), set())
            archives[archive_name][1].update(m.main_texture for m in meshes if m.main_texture)
        for archive_name, (archive, aliases) in archives.items():
            # images of different archives have the same names ("0000", "0001", ...)
            names, modes = export_fsh_textures(archive, aliases, path, archive_name[0])
            texture_names[archive_name] = names
            alpha_modes.update(modes)

        map_scene = Scene(
            name='map',
            obj_name='map',
            mtl_name='terrain',
            mtl_texture_names=list(alpha_modes.keys()),
            mtl_texture_path_func=lambda x: f'textures/{x}.png',
            mtl_texture_alpha_modes=alpha_modes,
            skip_obj_export=self.settings.maps__save_as_chunked,
        )
        for graph_name in ['road_paths', 'helicopter_paths']:
            for ai_path in data[graph_name]['paths']:
                map_scene.curves.append(
                    {
                        'name': ai_path['name'],
                        'closed': False,
                        'points': [
                            [p['position']['x'], p['position']['z'], p['position']['y']] for p in ai_path['points']
                        ],
                    }
                )
        scenes = [map_scene]
        chunk_positions = []
        for i, (model_id, file_name, meshes) in enumerate(models):
            vertices = [v for m in meshes for v in m.vertices]
            if not vertices:
                vertices = [(0, 0, 0)]
            pivot = tuple((min(v[k] for v in vertices) + max(v[k] for v in vertices)) / 2 for k in range(3))
            names = texture_names[eagl_texture_archive_name(file_name)]
            sub_meshes = eagl_sub_meshes(meshes, names, f'{file_name.split(".")[0]}_', pivot)
            for mesh in sub_meshes:
                mesh.change_axes(new_z='y', new_y='z')
            if self.settings.maps__save_as_chunked:
                chunk_positions.append({'x': pivot[0], 'y': pivot[1], 'z': pivot[2]})
                scenes.append(
                    Scene(
                        name=f'terrain_chunk_{i}',
                        sub_meshes=sub_meshes,
                        obj_name=f'terrain_chunk_{i}',
                        mtl_name='terrain',
                        bake_textures=False,
                        skip_mtl_export=True,
                    )
                )
            else:
                for mesh in sub_meshes:
                    mesh.pivot_offset = (-pivot[0], -pivot[2], -pivot[1])
                map_scene.sub_meshes.extend(sub_meshes)
        exported = export_scenes(scenes, path, self.settings)
        if self.settings.maps__save_as_chunked:
            chunks_file = path_join(path, 'terrain_chunks.json')
            with open(chunks_file, 'w') as f:
                json.dump(chunk_positions, f)
            exported.append(chunks_file)
        return exported


def nfsu_streaming_sections(bundle_data: dict) -> List[dict]:
    """Streamed sections listed in NFS Underground race bundle or NFSU2 location bundle"""
    for chunk in bundle_data['chunks']:
        if chunk['data'].get('chunk_id') in (0x00034107, 0x00034110) and 'sections' in chunk['data']:
            return chunk['data']['sections']
    return []


def find_nfsu_stream_file(bundle_path: str, sections: List[dict]) -> Optional[str]:
    """STREAM*.BUN file of NFS Underground race bundle (TRACKBnnnn.lzc) in the same folder: the one whose size
    matches the end of the last streamed section. NFSU2 stream file of location bundle LxRA.BUN is STREAMLxRA.BUN
    (padded after the last section)"""
    import os
    from library.utils.file_utils import find_files_case_insensitive

    if not sections:
        return None
    stream_end = max(s['offset'] + s['size'] for s in sections)
    directory = os.path.dirname(bundle_path)
    candidates = find_files_case_insensitive([path_join(directory, 'STREAM*.BUN')])
    for candidate in candidates:
        if os.path.getsize(candidate) == stream_end:
            return candidate
    for candidate in find_files_case_insensitive([path_join(directory, 'STREAM' + os.path.basename(bundle_path))]):
        if os.path.getsize(candidate) >= stream_end:
            return candidate
    return None


def nfsu_section_ranges(sections: List[dict]) -> List[dict]:
    """Sections to read from the stream file. Section "--" is skipped: it spans all other sections in NFSU and is a
    part of section "X0" in NFSU2. So is any other section spanning other sections"""
    sections = [s for s in sections if s['size'] > 0 and s['name'] != '--']
    res = []
    for s in sections:
        spans_other = any(
            o is not s
            and s['offset'] <= o['offset']
            and o['offset'] + o['size'] <= s['offset'] + s['size']
            and (o['offset'], o['size']) != (s['offset'], s['size'])
            for o in sections
        )
        if not spans_other:
            res.append(s)
    return res


class NfsuWorld:
    """Meshes (by mesh id), textures (by name hash: texture info, format, data chunk bytes) and sceneries
    (section number, scenery data) collected from NFS Underground chunk bundles"""

    def __init__(self):
        self.meshes = {}
        self.textures = {}
        self.sceneries = []

    def collect(self, bundle_data: dict):
        import numpy as np
        from serializers.bitmaps import nfsu_texture_pack_textures
        from serializers.geometries import nfsu_geometry_meshes

        for chunk in bundle_data['chunks']:
            chunk_data = chunk['data']
            if not isinstance(chunk_data, dict):
                continue
            if chunk_data.get('header') == 0x80134000:
                for mesh in nfsu_geometry_meshes(chunk_data):
                    if mesh.mesh_id in self.meshes:
                        continue
                    # numpy arrays take a fraction of memory of lists of tuples: a city has tens of thousands meshes
                    mesh.vertices = np.array(mesh.vertices, dtype=np.float64).reshape(-1, 3)
                    mesh.uvs = np.array(mesh.uvs, dtype=np.float64).reshape(-1, 2)
                    mesh.parts = [
                        (texture_id, np.array(triangles, dtype=np.int64).reshape(-1, 3))
                        for texture_id, triangles in mesh.parts
                    ]
                    self.meshes[mesh.mesh_id] = mesh
            elif chunk_data.get('chunk_id') == 0xB3300000:
                for info, d3d_format, data in nfsu_texture_pack_textures(chunk_data):
                    self.textures.setdefault(info['name_hash'], (info, d3d_format, data))
            elif chunk_data.get('chunk_id') == 0x80034100:
                sub_chunks = [x['data'] for x in chunk_data['sub_chunks']]
                header = next((x for x in sub_chunks if x.get('chunk_id') == 0x00034101), None)
                infos = next((x['infos'] for x in sub_chunks if x.get('chunk_id') == 0x00034102), [])
                instances = next((x['instances'] for x in sub_chunks if x.get('chunk_id') == 0x00034103), [])
                self.sceneries.append((header['section_number'] if header else 0, infos, instances))

    def scenery_parts(self, infos: list, instances: list) -> Dict[Optional[int], Tuple[list, list, list]]:
        """World geometry of scenery: texture id -> (vertices, uvs, triangles). Shadow and reflection meshes are
        skipped"""
        import numpy as np

        parts = {}
        for instance in instances:
            if instance['info_index'] >= len(infos):
                continue
            mesh = self.meshes.get(infos[instance['info_index']]['mesh_ids'][0])
            if mesh is None or not len(mesh.vertices) or mesh.name.upper().startswith(('SHD_', 'RFL_', 'SHADOW')):
                continue
            rotation = np.array(instance['rotation'], dtype=np.float64).reshape(3, 3)
            position = np.array([instance['position'][k] for k in 'xyz'], dtype=np.float64)
            world = np.asarray(mesh.vertices, dtype=np.float64) @ rotation + position
            mesh_uvs = np.asarray(mesh.uvs, dtype=np.float64)
            for texture_id, triangles in mesh.parts:
                if not len(triangles):
                    continue
                # only vertices used by this part
                used, remapped = np.unique(np.asarray(triangles, dtype=np.int64), return_inverse=True)
                if used[-1] >= len(world):
                    continue
                vertices, uvs, polygons = parts.setdefault(texture_id, ([], [], []))
                offset = sum(len(x) for x in vertices)
                vertices.append(world[used])
                uvs.append(mesh_uvs[used])
                polygons.append(remapped.reshape(-1, 3) + offset)
        return {
            texture_id: (np.concatenate(vertices), np.concatenate(uvs), np.concatenate(polygons))
            for texture_id, (vertices, uvs, polygons) in parts.items()
        }


class NfsuTrackBundleSerializer(BaseFileSerializer):
    """NFS Underground race world: scenery of every streamed section (from the STREAM*.BUN file next to the race
    bundle) is a terrain chunk; textures are saved to "textures/<texture id>.png". Chunk positions (centers of
    bounding boxes, Y up) are saved to "terrain_chunks.json". Game coordinates are Z up, chunk OBJs keep them"""

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        import os
        import numpy as np
        from library.loader import id_to_path
        from resources.blackbox.maps.nfsu import NfsuChunkBundle
        from serializers.bitmaps import nfsu_texture_to_image
        from serializers.geometries import texture_alpha_mode

        super().serialize(data, path, id, block, **kwargs)
        world = NfsuWorld()
        world.collect(data)
        sections = nfsu_streaming_sections(data)
        stream_path = find_nfsu_stream_file(id_to_path(id), sections)
        if stream_path is None:
            raise FileNotFoundError('Cannot find STREAM*.BUN file of the race next to it')
        bundle_block = NfsuChunkBundle()
        with open(stream_path, 'rb') as f:
            for section in nfsu_section_ranges(sections):
                f.seek(section['offset'])
                try:
                    world.collect(bundle_block.unpack_from_bytes(f.read(section['size'])))
                except Exception:
                    traceback.print_exc()

        # textures
        os.makedirs(path_join(path, 'textures'), exist_ok=True)
        texture_names = {}
        alpha_modes = {}

        def texture_name(texture_id):
            if texture_id not in texture_names:
                texture_names[texture_id] = 'untextured'
                if texture_id in world.textures:
                    try:
                        image = nfsu_texture_to_image(*world.textures[texture_id])
                        name = f'{texture_id:08x}'
                        image.save(path_join(path, f'textures/{name}.png'))
                        texture_names[texture_id] = name
                        alpha_modes[name] = texture_alpha_mode(image)
                    except Exception:
                        traceback.print_exc()
            return texture_names[texture_id]

        chunked = self.settings.maps__save_as_chunked
        map_scene = Scene(
            name='map',
            obj_name='map',
            mtl_name='terrain',
            mtl_texture_path_func=lambda x: f'textures/{x}.png',
            skip_obj_export=chunked,
        )
        scenes = [map_scene]
        chunk_positions = []
        for i, (section_number, infos, instances) in enumerate(world.sceneries):
            parts = world.scenery_parts(infos, instances)
            if not parts:
                continue
            all_vertices = np.concatenate([vertices for (vertices, _, _) in parts.values()])
            pivot = (all_vertices.min(axis=0) + all_vertices.max(axis=0)) / 2 if chunked else np.zeros(3)
            sub_meshes = []
            for k, (texture_id, (vertices, uvs, polygons)) in enumerate(parts.items()):
                sm = SubMesh()
                sm.texture_id = texture_name(texture_id)
                sm.name = f'scenery{section_number}_{k}_{sm.texture_id}'
                # numpy arrays rather than lists: much less memory for a whole city
                sm.vertices = (vertices - pivot).round(3)
                sm.vertex_uvs = uvs.round(5)
                sm.polygons = polygons
                sub_meshes.append(sm)
            if chunked:
                chunk_positions.append({'x': pivot[0], 'y': pivot[2], 'z': pivot[1]})
                scenes.append(
                    Scene(
                        name=f'terrain_chunk_{len(chunk_positions) - 1}',
                        sub_meshes=sub_meshes,
                        obj_name=f'terrain_chunk_{len(chunk_positions) - 1}',
                        mtl_name='terrain',
                        bake_textures=False,
                        skip_mtl_export=True,
                    )
                )
            else:
                map_scene.sub_meshes.extend(sub_meshes)
        map_scene.mtl_texture_names = [x for x in texture_names.values() if x != 'untextured']
        map_scene.mtl_texture_alpha_modes = alpha_modes
        exported = export_scenes(scenes, path, self.settings)
        if chunked:
            chunks_file = path_join(path, 'terrain_chunks.json')
            with open(chunks_file, 'w') as f:
                json.dump([{k: float(v) for k, v in p.items()} for p in chunk_positions], f)
            exported.append(chunks_file)
        return exported
