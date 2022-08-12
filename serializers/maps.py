import json
import math
import os
from copy import deepcopy
from string import Template
from typing import List

import settings
from library.helpers.json import resource_to_json
from library.read_data import ReadData
from library.utils.blender_scripts import get_blender_save_script, run_blender
from library.utils.meshes import SubMesh
from library.read_blocks.compound import CompoundBlock
from library.helpers.data_wrapper import DataWrapper
from resources.eac.maps import RoadSplinePoint
from serializers import BaseFileSerializer


class TriMapSerializer(BaseFileSerializer):
    class BarrierPath:
        def __init__(self, points: List[List[float]]) -> None:
            super().__init__()
            self.points = points
            self.is_closed = points[0] == points[-1]
            self.z_up = False

        @property
        def middle_points(self):
            return [[(self.points[i][j] + self.points[i + 1][j]) / 2 for j in range(3)] for i in
                    range(len(self.points) - 1)]

        @property
        def lengths(self):
            return [math.sqrt((self.points[i][0] - self.points[i + 1][0]) ** 2
                              + (self.points[i][1 if self.z_up else 2] - self.points[i + 1][
                1 if self.z_up else 2]) ** 2)
                    for i in range(len(self.points) - 1)]

        @property
        def orientations(self):
            return [math.atan2(self.points[i + 1][0] - self.points[i][0],
                               self.points[i + 1][1 if self.z_up else 2] - self.points[i][1 if self.z_up else 2])
                    for i in range(len(self.points) - 1)]

        def fix_angle(self, angle):
            while angle > math.pi:
                angle -= 2 * math.pi
            while angle <= -math.pi:
                angle += 2 * math.pi
            return angle

        def optimize(self):
            orientations = self.orientations
            lengths = self.lengths
            delta_angles = [abs(math.sin(orientations[i] - orientations[i + 1]) * (lengths[i] + lengths[i + 1]))
                            for i in range(len(orientations) - 1)]
            if self.is_closed:
                # make the most valuable angle as break
                break_delta_angle = abs(self.fix_angle(orientations[-1] - orientations[0]))
                max_delta_angle = max(delta_angles)
                if max_delta_angle > break_delta_angle:
                    index = delta_angles.index(max_delta_angle)
                    self.points = self.points[index + 1:] + self.points[:index + 2]
                    orientations = self.orientations
                    lengths = self.lengths
                    delta_angles = [abs(math.sin(orientations[i] - orientations[i + 1]) * (lengths[i] + lengths[i + 1]))
                                    for i in range(len(orientations) - 1)]
            while True:
                min_delta_angle = min(delta_angles)
                if min_delta_angle > 0.3:  # 30cm threshold
                    break
                index = delta_angles.index(min_delta_angle)
                self.points = self.points[:index + 1] + self.points[index + 2:]
                orientations = self.orientations
                lengths = self.lengths
                delta_angles = [abs(math.sin(orientations[i] - orientations[i + 1]) * (lengths[i] + lengths[i + 1]))
                                for i in range(len(orientations) - 1)]

    class TerrainChunk:

        def get_fence_height(self, fence_texture_name):
            try:
                # TODO determine where to get fence height from resource file
                # resource = self.tri_block.fam.resources[0]
                # for path in fence_texture_name.split('/'):
                #     resource = resource.get_resource_by_name(path)
                if self.tri_block.id.split('/')[-1][:3] in ['TR1', 'TR3']:
                    # TR1 texture height == 64; TR3: 51
                    return 1
                elif self.tri_block.id.split('/')[-1][:3] in ['AL1', 'TR2', 'TR6']:
                    return 2  # TR2 95; TR6: 65; AL1: 64
                elif self.tri_block.id.split('/')[-1][:3] in ['TR7']:
                    return 1.5  # TR7: 47
                # didn't test other tracks
                return 1
            except:
                return 1

        def __init__(self, tri_block):
            self.tri_block = tri_block
            self.next_chunk = None
            self.matrix = None
            self.fence_texture_name = None
            self.has_left_fence = False
            self.left_fence_polygon_index = 3
            # FIXME hardcode
            if self.tri_block.id.split('/')[-1][:3] == 'TR3':
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
            row[vertex_to_remove] = DataWrapper({
                i: row[vertex_to_remove - 1][i] * (1 - left_right_factor) + row[vertex_to_remove + 1][
                    i] * left_right_factor
                for i in ['x', 'y', 'z']})
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
                A0 = rows[row_index][0]
                A0.x += reference_points[row_index].position.x
                A0.y += reference_points[row_index].position.y
                A0.z += reference_points[row_index].position.z

                A15 = [rows[row_index][i + 1] for i in range(5)]
                A610 = [rows[row_index][i + 6] for i in range(5)]
                # Each point is relative to the previous point
                for i in range(5):
                    for j in ['x', 'y', 'z']:
                        A15[i][j] += A0[j] if i == 0 else A15[i - 1][j]
                        A610[i][j] += A0[j] if i == 0 else A610[i - 1][j]
                A610.reverse()
                self.matrix[3 - row_index] = A610 + [A0] + A15
            self.build_matrix = deepcopy(self.matrix)
            for row_index in range(4):
                if reference_points[row_index].spline_item_mode == 'lane_split':
                    self.build_matrix[3 - row_index], self.matrix[3 - row_index] = self._make_vertex_offset(
                        self.build_matrix[3 - row_index],
                        2, 6,
                        self.matrix[3 - row_index]
                    )
                elif reference_points[row_index].spline_item_mode == 'lane_merge':
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
                model.vertices = [[v.x, v.y, v.z] for v in sum(inverted_matrix[i:i + 2], [])]
                # in some cases, first polygon is placed differently (tunnels in Vertigo Ridge and Coastal #2)
                if i == 0:
                    for j in range(5):
                        vertices_matrix_indices = 0, 1
                        # we have 4 points, but 5 items in matrix. last should obey mode of 4th point
                        mode = self.reference_points[min(j, 3)].spline_item_mode
                        if mode == 'left_tunnel_A9_A4':
                            vertices_matrix_indices = 9, 2
                        elif mode == 'left_tunnel_A9_A5':
                            vertices_matrix_indices = 10, 2
                        elif mode == 'right_tunnel_A2_A9':
                            vertices_matrix_indices = 1, 7
                        if vertices_matrix_indices != (0, 1):
                            model.vertices[j] = [
                                inverted_matrix[vertices_matrix_indices[0]][j].x,
                                inverted_matrix[vertices_matrix_indices[0]][j].y,
                                inverted_matrix[vertices_matrix_indices[0]][j].z
                            ]
                            model.vertices[j + 5] = [
                                inverted_matrix[vertices_matrix_indices[1]][j].x,
                                inverted_matrix[vertices_matrix_indices[1]][j].y,
                                inverted_matrix[vertices_matrix_indices[1]][j].z,
                            ]
                model.polygons = [
                    [0, int(len(model.vertices) / 2), 1],
                    [int(len(model.vertices) / 2), int(len(model.vertices) / 2) + 1, 1],
                    [1, int(len(model.vertices) / 2) + 1, 2],
                    [int(len(model.vertices) / 2) + 1, int(len(model.vertices) / 2) + 2, 2],
                ]
                model.polygons = [[i, int(len(model.vertices) / 2) + i, 1 + i] + [int(len(model.vertices) / 2) + i,
                                                                                  int(len(model.vertices) / 2) + 1 + i,
                                                                                  1 + i] for i in
                                  range(int(len(model.vertices) / 2) - 1)]
                model.vertex_uvs = [[
                    (x % int(len(model.vertices) / 2)) / 2,
                    (0 if x < int(len(model.vertices) / 2) else 1) if i < int(len(model.vertices) / 2) else (
                        1 if x < int(len(model.vertices) / 2) else 0)
                ] for x in range(len(model.vertices))]
                model.texture_id = texture_names[i - 5 if i >= 5 else 9 - i]
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
                if self.tri_block.id.split('/')[-1][:3] == 'TR7':
                    neighbour_point = matrix[i][index + 1 if is_left else index - 1]
                    distance = math.sqrt(sum(pow(neighbour_point[c] - road_point[c], 2) for c in ['x', 'y', 'z']))
                    koef = 0.2 / distance
                    road_point = DataWrapper(
                        {c: road_point[c] * (1 - koef) + neighbour_point[c] * koef for c in ['x', 'y', 'z']})
                model.vertices.append([road_point.x, road_point.y, road_point.z])
                model.vertices.append(
                    [road_point.x, road_point.y + self.get_fence_height(self.fence_texture_name), road_point.z])
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

    blender_map_script = Template("""
import bpy
import math
import json
if $new_file:
    bpy.ops.wm.read_factory_settings(use_empty=True)

# create road spline
print('building track spline...')
# create the Curve Datablock
curveData = bpy.data.curves.new('road_path', type='CURVE')
curveData.dimensions = '3D'
curveData.resolution_u = 2

# map coords to spline
polyline = curveData.splines.new('POLY')
coords = [$road_path_points]
polyline.points.add(len(coords) - 1)
for i, coord in enumerate(coords):
    x,y,z = coord
    polyline.points[i].co = (x, y, z, 1)
if not $is_opened_track:
    polyline.use_cyclic_u = True
# create Object
curveOB = bpy.data.objects.new('road_path', curveData)
bpy.context.collection.objects.link(curveOB)
# settings
spline_properties = json.loads('$road_path_settings')
for (key, value) in spline_properties.items():
    curveOB[key] = value

print('creating prop dummies...')
# map chunks dummies
for i in range(int(len(coords) / 4)):
    o = bpy.data.objects.new( f"chunk_{i}", None )
    bpy.context.collection.objects.link(o)
    o.location = coords[i * 4]
    o['is_chunk'] = True
    o['chunk'] = f'terrain_chunk_{i}'
    if i < int(len(coords) / 4) - 1:
        o['children'] = [f'chunk_{i + 1}']
    elif (i == int(len(coords) / 4) - 1) and not $is_opened_track:
        o['children'] = ['chunk_0']

   
# barriers collisions
if $save_collisions:
    print('defining wall collisions...')
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
            cube['invisible'] = True
            wall_cube_names.append(cube.name)
    bpy.ops.object.select_all(action='DESELECT')
    for name in wall_cube_names:
        bpy.data.objects[name].select_set(True)
    bpy.ops.rigidbody.objects_add(type='PASSIVE')
    for obj in bpy.context.selected_objects:
        obj.rigid_body.collision_shape = 'BOX'
    """)

    blender_chunk_script = Template("""
import bpy
import math
import json
from mathutils import Euler

if $new_file:
    bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="$obj_name", use_image_search=True, axis_forward='Y', axis_up='Z')

# create proxy objects
proxy_objects = json.loads('$proxy_objects_json')
for index, proxy_obj in enumerate(proxy_objects):
    o = bpy.data.objects.new( f"proxy_{index}", None )
    bpy.context.collection.objects.link(o)
    o.location = (proxy_obj['x'], proxy_obj['y'], proxy_obj['z'])
    o.rotation_quaternion = Euler((0, 0, proxy_obj['rotation_z']), 'XYZ').to_quaternion()
    o['is_prop'] = True
    o['type'] = proxy_obj['type']
    if 'model_ref_id' in proxy_obj:
        o['model_ref_id'] = proxy_obj['model_ref_id']
    if 'texture' in proxy_obj:
        o['texture'] = proxy_obj['texture']
    if 'back_texture' in proxy_obj:
        o['back_texture'] = proxy_obj['back_texture']
    o['width'] = proxy_obj['width']
    o['height'] = proxy_obj['height']
    
def find_terrain_chunks():
    import re
    pattern = re.compile(f"^terrain_chunk")
    return [x for x in bpy.data.objects if pattern.match(x.name)]
    
# terrain collisions
if $save_collisions:
    bpy.ops.object.select_all(action='DESELECT')
    is_active_set = False
    objects = find_terrain_chunks()
    for object in objects:
        object.select_set(True)
        if not is_active_set:
            bpy.context.view_layer.objects.active = object
            is_active_set = True
    bpy.ops.rigidbody.objects_add(type='PASSIVE')
    # for obj in bpy.context.selected_objects:
    #     obj.rigid_body.collision_shape = 'CONVEX_HULL'
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

    def _save_mtl(self, terrain_data, path: str, name):
        with open(f'{path}terrain.mtl', 'w') as f:
            texture_names = list(set(
                sum([x['texture_names'] for x in terrain_data], [])
                + [x['chunk'].fence_texture_name for x in terrain_data if x['chunk'].fence_texture_name]
            ))
            texture_names.sort()
            for texture_name in texture_names:
                f.write(f"""\n\nnewmtl {texture_name}
        Ka 1.000000 1.000000 1.000000
        Kd 1.000000 1.000000 1.000000
        Ks 0.000000 0.000000 0.000000
        illum 1
        Ns 0.000000
        map_Kd ../../ETRACKFM/{name[:3]}_001.FAM/background/{texture_name}.png""")

    def serialize(self, data: ReadData, path: str):
        super().serialize(data, path)
        is_opened_track = math.sqrt(
            (data.road_spline[0].position.x.value - data.road_spline[len(data.terrain) * 4 - 1].position.x.value) ** 2
            + (data.road_spline[0].position.y.value - data.road_spline[len(data.terrain) * 4 - 1].position.y.value) ** 2
            + (data.road_spline[0].position.z.value - data.road_spline[len(data.terrain) * 4 - 1].position.z.value) ** 2
        ) > 100

        terrain_data = []
        for terrain_entry in data.terrain:
            res = dict()
            res['texture_names'] = [self._get_texture_name_from_id(is_opened_track, tid.value) for tid in
                                    terrain_entry.texture_ids]
            road_path_index = len(terrain_data) * 4
            res['chunk'] = self.TerrainChunk(data)
            res['chunk'].read_matrix(DataWrapper.wrap(resource_to_json(terrain_entry.rows)),
                                     DataWrapper.wrap(resource_to_json(data.road_spline[road_path_index:road_path_index + 4])))
            if terrain_entry.fence.texture_id != 0 or terrain_entry.fence.has_left_fence or terrain_entry.fence.has_right_fence:
                fence_texture_id = terrain_entry.fence.texture_id
                if is_opened_track:
                    if data.id.endswith('AL1.TRI') and fence_texture_id == 16:
                        fence_texture_id = fence_texture_id * 3
                    res['chunk'].fence_texture_name = self._get_texture_name_from_id(is_opened_track, fence_texture_id)
                else:
                    res['chunk'].fence_texture_name = ('0/GA00'
                                                       if data.id.split('/')[-1] in ['TR3.TRI', 'TR4.TRI', 'TR5.TRI']
                                                       else '0/ga00')
                res['chunk'].has_left_fence = terrain_entry.fence.has_left_fence
                res['chunk'].has_right_fence = terrain_entry.fence.has_right_fence
            terrain_data.append(res)
        for i, terrain_data_entry in enumerate(terrain_data):
            terrain_data_entry['chunk'].next_chunk = terrain_data[i + 1]['chunk'] if (
                    i < len(terrain_data) - 1) else (None
                                                     if is_opened_track
                                                     else terrain_data[0]['chunk'])
            terrain_data_entry['meshes'] = terrain_data_entry['chunk'].build_models(i,
                                                                                    terrain_data_entry['texture_names'])

        if settings.maps__save_collisions:
            left_barrier_points = self.BarrierPath(
                [[rp.position.x.value + rp.left_barrier_distance.value * math.cos(rp.orientation.value + math.pi),
                  rp.position.y.value,
                  rp.position.z.value - rp.left_barrier_distance.value * math.sin(rp.orientation.value + math.pi)
                  ] for rp in data.road_spline[:len(data.terrain) * 4]])
            right_barrier_points = self.BarrierPath(
                [[rp.position.x.value + rp.right_barrier_distance.value * math.cos(rp.orientation.value),
                  rp.position.y.value,
                  rp.position.z.value - rp.right_barrier_distance.value * math.sin(rp.orientation.value)
                  ] for rp in data.road_spline[:len(data.terrain) * 4]])
            if not is_opened_track:
                left_barrier_points.points += [left_barrier_points.points[0]]
                right_barrier_points.points += [right_barrier_points.points[0]]
                left_barrier_points.is_closed = right_barrier_points.is_closed = True
            left_barrier_points.optimize()
            right_barrier_points.optimize()

        # I use Z-up. Did not test exporter with Y-up, also prop rotations will not work, that's why it doesn't have
        # own settings option. Also correct rotation is (new_z='y', new_y='-z'), but looks like NFS loads map mirrored
        # So since we change y and z, we need to invert Y-rotation as well
        for i, terrain_chunk in enumerate(terrain_data):
            for sub_model in terrain_chunk['meshes']:
                sub_model.change_axes(new_z='y', new_y='z')
        for obj in data.proxy_object_instances:
            (obj.position.z, obj.position.y) = (obj.position.y, obj.position.z)
            obj.rotation.value = -obj.rotation.value
        for spline_point in data.road_spline[:len(data.terrain) * 4]:
            (spline_point.position.z, spline_point.position.y) = (spline_point.position.y, spline_point.position.z)
            spline_point.orientation.value = -spline_point.orientation.value
        if settings.maps__save_collisions:
            if right_barrier_points:
                right_barrier_points.points = [[p[0], p[2], p[1]] for p in right_barrier_points.points]
                right_barrier_points.z_up = True
            if left_barrier_points:
                left_barrier_points.points = [[p[0], p[2], p[1]] for p in left_barrier_points.points]
                left_barrier_points.z_up = True

        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        save_path = os.getcwd().replace('\\', '/')
        self._save_mtl(terrain_data, path, data.id.split('/')[-1])
        blender_script = "import bpy\nbpy.ops.wm.read_factory_settings(use_empty=True)"
        if settings.maps__save_as_chunked:
            for i, terrain_chunk in enumerate(terrain_data):
                with open(f'{path}/terrain_chunk_{i}.obj', 'w') as f:
                    face_index_increment = 1
                    for sub_model in terrain_chunk['meshes']:
                        f.write(sub_model.to_obj(face_index_increment, mtllib='terrain.mtl', pivot_offset=(
                            data.road_spline[i * 4].position.x.value,
                            data.road_spline[i * 4].position.y.value,
                            data.road_spline[i * 4].position.z.value,
                        )))
                        face_index_increment = face_index_increment + len(sub_model.vertices)
                blender_script += '\n\n\n' + self.blender_chunk_script.substitute({
                    'new_file': True,
                    'save_collisions': settings.maps__save_collisions,
                    'obj_name': f'terrain_chunk_{i}.obj',
                    'proxy_objects_json': json.dumps(
                        [{'x': o.position.x.value + data.road_spline[
                            o.reference_road_spline_vertex.value].position.x.value - data.road_spline[i * 4].position.x.value,
                          'y': o.position.y.value + data.road_spline[
                              o.reference_road_spline_vertex.value].position.y.value - data.road_spline[
                                   i * 4].position.y.value,
                          'z': o.position.z.value + data.road_spline[
                              o.reference_road_spline_vertex.value].position.z.value - data.road_spline[
                                   i * 4].position.z.value,
                          'rotation_z': o.rotation.value + data.road_spline[
                              o.reference_road_spline_vertex.value].orientation.value,
                          'type': data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].type.value,
                          'model_ref_id': data.proxy_objects[
                              o.proxy_object_index.value % len(
                                  data.proxy_objects)].resource_id.value,
                          'texture': ';'.join(self._texture_ids(data.proxy_objects[
                                                                    o.proxy_object_index.value % len(
                                                                        data.proxy_objects)].resource_id.value,
                                                                data.proxy_objects[
                                                                    o.proxy_object_index.value % len(
                                                                        data.proxy_objects)].frame_count.value,
                                                                is_opened_track)),
                          'back_texture': ';'.join(self._texture_ids(
                              data.proxy_objects[o.proxy_object_index.value % len(
                                  data.proxy_objects)].resource_2_id.value,
                              data.proxy_objects[o.proxy_object_index.value % len(
                                  data.proxy_objects)].frame_count.value, is_opened_track)),
                          'width': data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].width.value,
                          'height': data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].height.value,
                          'animation_interval': 250,
                          }
                         for o in data.proxy_object_instances
                         if (i + 1) * 4 > o.reference_road_spline_vertex.value >= i * 4]),
                })
                if settings.geometry__save_blend:
                    blender_script += get_blender_save_script(out_blend_name=f'{save_path}/{path}terrain_chunk_{i}')
                blender_script += '\n' + settings.geometry__additional_exporter(f'{save_path}/{path}terrain_chunk_{i}',
                                                                                'terrain_chunk')
        else:
            with open(f'{path}/terrain.obj', 'w') as f:
                face_index_increment = 1
                for i, terrain_chunk in enumerate(terrain_data):
                    for sub_model in terrain_chunk['meshes']:
                        f.write(sub_model.to_obj(face_index_increment, mtllib='terrain.mtl'))
                        face_index_increment = face_index_increment + len(sub_model.vertices)
            blender_script += '\n\n\n' + self.blender_chunk_script.substitute({
                'new_file': False,
                'save_collisions': settings.maps__save_collisions,
                'obj_name': 'terrain.obj',
                'proxy_objects_json': json.dumps(
                    [{'x': o.position.x.value + data.road_spline[o.reference_road_spline_vertex.value].position.x.value,
                      'y': o.position.y.value + data.road_spline[o.reference_road_spline_vertex.value].position.y.value,
                      'z': o.position.z.value + data.road_spline[o.reference_road_spline_vertex.value].position.z.value,
                      'rotation_z': o.rotation.value + data.road_spline[o.reference_road_spline_vertex.value].orientation.value,
                      'type': data.proxy_objects[o.proxy_object_index.value % len(data.proxy_objects)].type.value,
                      'model_ref_id': data.proxy_objects[
                          o.proxy_object_index.value % len(data.proxy_objects)].resource_id.value,
                      'texture': ';'.join(self._texture_ids(
                          data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].resource_id.value,
                          data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].frame_count.value, is_opened_track)),
                      'back_texture': ';'.join(self._texture_ids(
                          data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].resource_2_id.value,
                          data.proxy_objects[
                              o.proxy_object_index.value % len(data.proxy_objects)].frame_count.value, is_opened_track)),
                      'width': data.proxy_objects[
                          o.proxy_object_index.value % len(data.proxy_objects)].width.value,
                      'height': data.proxy_objects[
                          o.proxy_object_index.value % len(data.proxy_objects)].height.value,
                      'animation_interval': 250,
                      } for o in data.proxy_object_instances
                     if len(data.terrain) * 4 > o.reference_road_spline_vertex.value >= 0]),
            })
        blender_script += '\n\n\n\n' + self.blender_map_script.substitute({
            'new_file': settings.maps__save_as_chunked,
            'save_collisions': settings.maps__save_collisions,
            'road_path_points': ', '.join(
                [f'({block.position.x.value}, {block.position.y.value}, {block.position.z.value})' for block in
                 data.road_spline[:len(data.terrain) * 4]]),
            'road_path_settings': json.dumps({
                'slope': [block.slope.value for block in data.road_spline[:len(data.terrain) * 4]],
                'slant': [block.slant_a.value for block in data.road_spline[:len(data.terrain) * 4]],
            }),
            'is_opened_track': is_opened_track,
            'left_barrier': json.dumps({
                'points': left_barrier_points.points,
                'middle_points': left_barrier_points.middle_points,
                'lengths': left_barrier_points.lengths,
                'orientations': left_barrier_points.orientations,
            }) if settings.maps__save_collisions else 'null',
            'right_barrier': json.dumps({
                'points': right_barrier_points.points,
                'middle_points': right_barrier_points.middle_points,
                'lengths': right_barrier_points.lengths,
                'orientations': right_barrier_points.orientations,
            }) if settings.maps__save_collisions else 'null',
        })
        blender_script += '\n' + settings.geometry__additional_exporter(f'{save_path}/{path}map', 'map')
        run_blender(path=path,
                    script=blender_script,
                    out_blend_name=f'{save_path}/{path}map' if settings.geometry__save_blend else None)
        if not settings.geometry__save_obj:
            if settings.maps__save_as_chunked:
                for i in range(len(terrain_data)):
                    os.unlink(f'{path}/terrain_chunk_{i}.obj')
            else:
                os.unlink(f'{path}/terrain.obj')
            os.unlink(f'{path}terrain.mtl')
