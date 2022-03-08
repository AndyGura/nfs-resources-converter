import json
import math
import os
from copy import deepcopy
from io import BufferedReader, SEEK_CUR
from string import Template
from typing import List

import settings
from buffer_utils import (
    read_int,
    read_signed_int,
    read_byte,
    read_short,
    read_utf_bytes,
    read_vector3_as_list,
    read_signed_short
)
from parsers.resources.base import BaseResource
from parsers.resources.common.blender_scripts import get_blender_save_script, run_blender
from parsers.resources.geometries import SubMesh


class SceneryFlags:
    none = 0
    Unk1 = 1
    Animated = 4


class SceneryType:
    Model = 1
    Bitmap = 4
    TwoSidedBitmap = 6


class RoadSplineItem:

    # calculated as average for closed tracks with known length: 0.0000118444
    # tested with screenshots, last value appears to be too small
    scale_multiplier = 0.000016

    def __init__(self):
        self.is_empty = True
        self.left_verge_distance = 0
        self.right_verge_distance = 0
        self.left_barrier_distance = 0
        self.right_barrier_distance = 0
        self.node_property = 0
        self.slope = 0
        self.slant_a = 0
        self.orientation = 0
        self.orientation_y = 0
        self.slant_b = 0
        self.orientation_x = 0
        self.x = 0
        self.y = 0
        self.z = 0

    def read(self, buffer):
        self.left_verge_distance = read_byte(buffer)
        self.right_verge_distance = read_byte(buffer)
        self.left_barrier_distance = read_byte(buffer) * 16 * 0.0077  # 16 * terrain scale, accurate at least for TR3
        self.right_barrier_distance = read_byte(buffer) * 16 * 0.0077
        buffer.seek(3, SEEK_CUR)  # maybe index of polygon for adding fence?
        self.node_property = read_byte(buffer)
        self.x = read_signed_int(buffer) * self.scale_multiplier
        self.z = read_signed_int(buffer) * self.scale_multiplier
        self.y = read_signed_int(buffer) * self.scale_multiplier
        self.slope = read_short(buffer)
        self.slant_a = read_short(buffer)
        self.orientation = ((read_short(buffer) & 0x3FFF) / 0x4000) * (math.pi * 2)
        buffer.seek(2, SEEK_CUR)
        self.orientation_y = ((read_short(buffer) & 0x3FFF) / 0x4000) * (math.pi * 2)
        self.slant_b = read_short(buffer)
        self.orientation_x = ((read_short(buffer) & 0x3FFF) / 0x4000) * (math.pi * 2)
        buffer.seek(2, SEEK_CUR)
        self.is_empty = self.left_verge_distance == self.right_verge_distance == self.x == self.y == self.z == 0


class BarrierPath:
    def __init__(self, points: List[List[float]]) -> None:
        super().__init__()
        self.points = points
        self.is_closed = points[0] == points[-1]

    @property
    def middle_points(self):
        return [[(self.points[i][j] + self.points[i + 1][j]) / 2 for j in range(3)] for i in
                range(len(self.points) - 1)]

    @property
    def lengths(self):
        return [math.sqrt((self.points[i][0] - self.points[i + 1][0]) ** 2
                          + (self.points[i][1] - self.points[i + 1][1]) ** 2)
                for i in range(len(self.points) - 1)]

    @property
    def orientations(self):
        return [math.atan2(self.points[i + 1][0] - self.points[i][0], self.points[i + 1][1] - self.points[i][1])
                for i in range(len(self.points) - 1)]

    def fix_angle(self, angle):
        while angle > math.pi:
            angle -= 2*math.pi
        while angle <= -math.pi:
            angle += 2*math.pi
        return angle

    def optimize(self):
        orientations = self.orientations
        lengths = self.lengths
        delta_angles = [abs(math.sin(orientations[i] - orientations[i+1]) * (lengths[i] + lengths[i+1]))
                        for i in range(len(orientations) - 1)]
        if self.is_closed:
            # make the most valuable angle as break
            break_delta_angle = abs(self.fix_angle(orientations[-1] - orientations[0]))
            max_delta_angle = max(delta_angles)
            if max_delta_angle > break_delta_angle:
                index = delta_angles.index(max_delta_angle)
                self.points = self.points[index+1:] + self.points[:index+2]
                orientations = self.orientations
                lengths = self.lengths
                delta_angles = [abs(math.sin(orientations[i] - orientations[i+1]) * (lengths[i] + lengths[i+1]))
                                for i in range(len(orientations) - 1)]
        while True:
            min_delta_angle = min(delta_angles)
            if min_delta_angle > 0.3:  # 30cm threshold
                break
            index = delta_angles.index(min_delta_angle)
            self.points = self.points[:index+1] + self.points[index+2:]
            orientations = self.orientations
            lengths = self.lengths
            delta_angles = [abs(math.sin(orientations[i] - orientations[i+1]) * (lengths[i] + lengths[i+1]))
                            for i in range(len(orientations) - 1)]


class TerrainChunk:
    # not tested
    fence_height = 1

    def __init__(self):
        self.next_chunk = None
        self.matrix = None
        self.fence_texture_name = None
        self.has_left_fence = False
        self.has_right_fence = False

    def read_matrix(self, buffer, reference_points: List[RoadSplineItem], scale):
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
        self.matrix = [None] * 4
        for row_index in range(4):
            A0 = read_vector3_as_list(buffer, scale)
            A0[0] += reference_points[row_index].x
            A0[1] += reference_points[row_index].y
            A0[2] += reference_points[row_index].z

            A15 = [read_vector3_as_list(buffer, scale) for _ in range(5)]
            A610 = [read_vector3_as_list(buffer, scale) for _ in range(5)]
            # Each point is relative to the previous point
            for i in range(5):
                for j in range(3):
                    A15[i][j] += A0[j] if i == 0 else A15[i - 1][j]
                    A610[i][j] += A0[j] if i == 0 else A610[i - 1][j]
            A610.reverse()
            self.matrix[3 - row_index] = A610 + [A0] + A15

    def build_models(self, counter, texture_names):
        matrix = deepcopy(self.matrix)
        if self.next_chunk:
            matrix = [self.next_chunk.matrix[-1]] + matrix
        models = []
        inverted_matrix = [list(x) for x in zip(*matrix)]
        for i in range(10):
            model = SubMesh()
            model.vertices = sum(inverted_matrix[i:i + 2], [])
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
            models.append(self.build_fence(counter, True))
        if self.has_right_fence:
            models.append(self.build_fence(counter, False))
        return models

    def build_fence(self, counter, is_left):
        matrix = deepcopy(self.matrix)
        if self.next_chunk:
            matrix = [self.next_chunk.matrix[-1]] + matrix
        model = SubMesh()
        index = 3 if is_left else 7
        for i in range(len(matrix)):
            road_point = matrix[i][index]
            model.vertices.append(road_point)
            model.vertices.append([road_point[0], road_point[1], road_point[2] + self.fence_height])
        for i in range(len(matrix) - 1):
            model.polygons.append([i * 2, i * 2 + 1, i * 2 + 3])
            model.polygons.append([i * 2 + 2, i * 2, i * 2 + 3])
        model.vertex_uvs = [[
            (x % int(len(model.vertices) / 2)) / 2,
            0 if x % 2 == 1 else 1
        ] for x in range(len(model.vertices))]
        model.texture_id = self.fence_texture_name
        model.name = f'terrain_chunk_{counter}_{"left" if is_left else "right"}fence_{self.fence_texture_name}'
        return model


class ProxyObjectDescriptor:

    def __init__(self, index, terrain_position_scale, scenery_objects_size_scale):
        self.index = index
        self.terrain_position_scale = terrain_position_scale
        self.scenery_objects_size_scale = scenery_objects_size_scale
        self.flags = 0
        self.type = 0
        self.width = 0
        self.height = 0
        self.resource_id = 0
        self.resource_2_id = 0
        self.animation_frame_count = 1

    def read(self, buffer):
        # https://github.com/jeff-1amstudios/OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202
        pos = buffer.tell()
        self.flags = read_byte(buffer)
        self.type = read_byte(buffer)
        self.resource_id = read_byte(buffer)
        if self.type == SceneryType.TwoSidedBitmap:
            self.resource_2_id = read_byte(buffer)
        buffer.seek(pos + 6)
        self.width = read_short(
            buffer) * self.terrain_position_scale * self.scenery_objects_size_scale
        if (self.flags & SceneryFlags.Animated) == SceneryFlags.Animated:
            self.animation_frame_count = read_byte(buffer)
        buffer.seek(pos + 14)
        self.height = read_short(
            buffer) * self.terrain_position_scale * self.scenery_objects_size_scale

    def get_export_data(self, is_opened_track):
        res = {}
        res['type'] = self.type
        res['width'] = self.width
        res['height'] = self.height
        if self.type == SceneryType.Model:
            res['model_ref_id'] = self.resource_id
        else:
            tex_id = math.floor(self.resource_id / 4)
            res['texture'] = ';'.join(
                [f"{tex_id + i}/0000" if is_opened_track else f"0/{str(tex_id + i).rjust(2, '0')}00"
                 for i in range(self.animation_frame_count)])
            if self.type == SceneryType.TwoSidedBitmap:
                tex_id = math.floor(self.resource_2_id / 4)
                res['back_texture'] = ';'.join(
                    [f"{tex_id + i}/0000" if is_opened_track else f"0/{str(tex_id + i).rjust(2, '0')}00"
                     for i in range(self.animation_frame_count)])
            if self.animation_frame_count > 1:
                res['animation_interval'] = 250  # TODO maybe NFS defines it somewhere?
        return res


class TriMapResource(BaseResource):

    # scale of terrain vertices. Tested with comparing screenshots on CY1 initial position. Looks very accurate
    # TODO looks like the same as car mesh scale?
    terrain_position_scale = 0.0077
    # scale of scenery object positions (aproximated to terrain_position_scale) TODO not too accurate
    scenery_objects_position_scale = 0.5
    # scale of scenery object width/height Looks ok but not tested properly
    scenery_objects_size_scale = 135

    def __init__(self, id=None, length=None, save_binary_file=True):
        super().__init__()
        self.first_node_coordinates = (0, 0, 0)
        self.scenery_data_length = 0
        self.road_path: List[RoadSplineItem] = []
        self.objects: List[dict] = []
        self.object_descriptors: List[ProxyObjectDescriptor] = []
        self.terrain_data: List[dict] = []

    def _get_texture_name_from_id(self, texture_id):
        if self.is_opened_track:
            return f'{math.floor(texture_id / 3)}/{hex(10 + texture_id % 3)[2:].upper()}000'
        else:
            return ('0/' + str(math.floor(texture_id / 3)).zfill(2)
                    + hex(10 + texture_id % 3)[2:].upper()
                    + '0')  # zero scale is the biggest and always presented in FAM file

    def _read_object_record(self, buffer):
        res = dict()
        res['reference_road_path_vertex'] = read_signed_int(buffer)  # % len(self.road_path)
        if res['reference_road_path_vertex'] < 0 or res['reference_road_path_vertex'] >= len(self.road_path):
            buffer.seek(12, SEEK_CUR)
            return None
        res['descriptor'] = self.object_descriptors[read_byte(buffer) % len(self.object_descriptors)]
        res['rotation_z'] = -((read_byte(buffer) / 256) * (math.pi * 2)
                              + self.road_path[res['reference_road_path_vertex']].orientation)
        res['flags'] = read_int(buffer)
        res['x'] = read_signed_short(
            buffer) * self.terrain_position_scale * self.scenery_objects_position_scale + \
                   self.road_path[res['reference_road_path_vertex']].x
        res['z'] = read_signed_short(
            buffer) * self.terrain_position_scale * self.scenery_objects_position_scale + \
                   self.road_path[res['reference_road_path_vertex']].z
        res['y'] = read_signed_short(
            buffer) * self.terrain_position_scale * self.scenery_objects_position_scale + \
                   self.road_path[res['reference_road_path_vertex']].y
        return res

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start_offset = buffer.tell()
        buffer.seek(12, SEEK_CUR)
        (x, z, y) = (
            read_signed_int(buffer),
            read_signed_int(buffer),
            read_signed_int(buffer)
        )
        self.first_node_coordinates = (x, y, z)
        buffer.seek(12, SEEK_CUR)
        self.scenery_data_length = read_int(buffer)
        buffer.seek(4, SEEK_CUR)
        # skip second index tables
        # jump directly to road path
        buffer.seek(start_offset + 0x98C)
        while 1:
            path_record = RoadSplineItem()
            path_record.read(buffer)
            if path_record.is_empty:
                break
            self.road_path.append(path_record)
        self.is_opened_track = math.sqrt(
            (self.road_path[0].x - self.road_path[-1].x) ** 2
            + (self.road_path[0].y - self.road_path[-1].y) ** 2
            + (self.road_path[0].z - self.road_path[-1].z) ** 2
        ) > 100
        if len(self.road_path) < 2400:
            # skip remaining
            buffer.seek(0x24 * (2400 - len(self.road_path) - 1), SEEK_CUR)
        # objects data starts here:
        buffer.seek(0x708, SEEK_CUR)

        object_descriptor_count = read_int(buffer)
        objects_count = read_int(buffer)
        check_header_text = read_utf_bytes(buffer, 4)
        if check_header_text != 'SJBO':
            raise Exception('OBJS block not found')
        buffer.seek(0x8, SEEK_CUR)
        for i in range(object_descriptor_count):
            descr = ProxyObjectDescriptor(len(self.object_descriptors), self.terrain_position_scale, self.scenery_objects_size_scale)
            descr.read(buffer)
            self.object_descriptors.append(descr)
        for i in range(objects_count):
            record = self._read_object_record(buffer)
            if record:
                self.objects.append(record)
        # jump to end of objects
        buffer.seek(1600, SEEK_CUR)
        # blank space
        buffer.seek(492, SEEK_CUR)

        # terrain data
        buffer.seek(start_offset + 0x1A4A8)
        try:
            index = -1
            while buffer.tell() < length:
                index += 1
                res = dict()
                id = read_utf_bytes(buffer, 4)
                if id != 'TRKD':
                    raise Exception(f'Expected TRKD in scenery data, found: {id}')
                res['block_length'] = read_int(buffer)
                res['block_number'] = read_int(buffer)
                # always zero ?
                read_byte(buffer)
                # fence type: [lrtttttt]
                # l - flag is add left fence
                # r - flag is add right fence
                # tttttt - texture id
                fence_type = read_byte(buffer)
                res['texture_names'] = [self._get_texture_name_from_id(read_byte(buffer)) for _ in range(10)]
                road_path_index = len(self.terrain_data) * 4
                res['chunk'] = TerrainChunk()
                res['chunk'].read_matrix(buffer, self.road_path[road_path_index:road_path_index + 4],
                                         self.terrain_position_scale)
                if fence_type != 0:
                    # Ignore the top 2 bits to find the texture to use
                    fence_texture_id = fence_type & (0xff >> 2)
                    if self.is_opened_track:
                        if self.name == 'AL1.TRI' and fence_texture_id == 16:
                            fence_texture_id = fence_texture_id * 3
                        res['chunk'].fence_texture_name = self._get_texture_name_from_id(fence_texture_id)
                    else:
                        res['chunk'].fence_texture_name = ('0/GA00'
                                                           if self.name in ['TR3.TRI', 'TR4.TRI', 'TR5.TRI']
                                                           else '0/ga00')
                    res['chunk'].has_left_fence = (fence_type & (0x1 << 7)) != 0
                    res['chunk'].has_right_fence = (fence_type & (0x1 << 6)) != 0
                self.terrain_data.append(res)
        except:
            pass
        # build terrain models
        for i, terrain_data in enumerate(self.terrain_data):
            terrain_data['chunk'].next_chunk = self.terrain_data[i + 1]['chunk'] if (
                    i < len(self.terrain_data) - 1) else (None
                                                          if self.is_opened_track
                                                          else self.terrain_data[0]['chunk'])
            terrain_data['meshes'] = terrain_data['chunk'].build_models(i, terrain_data['texture_names'])
        # barriers
        road_path = self.road_path.copy()
        if not self.is_opened_track:
            road_path += [road_path[0]]
        self.left_barrier_points = BarrierPath([[rp.x + rp.left_barrier_distance * math.cos(rp.orientation + math.pi),
                                                 rp.y - rp.left_barrier_distance * math.sin(rp.orientation + math.pi),
                                                 rp.z] for rp in road_path])
        self.left_barrier_points.optimize()
        self.right_barrier_points = BarrierPath([[rp.x + rp.right_barrier_distance * math.cos(rp.orientation),
                                                  rp.y - rp.right_barrier_distance * math.sin(rp.orientation),
                                                  rp.z] for rp in road_path])
        self.right_barrier_points.optimize()
        return length

    def save_converted(self, path: str):
        if not settings.save_obj and not settings.save_glb and not settings.save_blend:
            return
        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)

        with open(f'{path}terrain.mtl', 'w') as f:
            texture_names = list(set(
                sum([x['texture_names'] for x in self.terrain_data], [])
                + [x['chunk'].fence_texture_name for x in self.terrain_data if x['chunk'].fence_texture_name]
            ))
            texture_names.sort()
            for texture_name in texture_names:
                f.write(f"""\n\nnewmtl {texture_name}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd ../../ETRACKFM/{self.name[:3]}_001.FAM/background/{texture_name}.png""")

        chunks_blender_script = ""
        for i, terrain_chunk in enumerate(self.terrain_data):
            with open(f'{path}/terrain_chunk_{i}.obj', 'w') as f:
                face_index_increment = 1
                for sub_model in terrain_chunk['meshes']:
                    f.write(sub_model.to_obj(face_index_increment, mtllib='terrain.mtl', pivot_offset=(
                        self.road_path[i * 4].x,
                        self.road_path[i * 4].y,
                        self.road_path[i * 4].z,
                    )))
                    face_index_increment = face_index_increment + len(sub_model.vertices)
            chunks_blender_script += '\n\n\n' + self.blender_chunk_script.substitute({
                'chunk_index': i,
                'proxy_objects_json': json.dumps([{**o,
                                                   'x': o['x'] - self.road_path[i * 4].x,
                                                   'y': o['y'] - self.road_path[i * 4].y,
                                                   'z': o['z'] - self.road_path[i * 4].z,
                                                   'descriptor': None,
                                                   **(o['descriptor'].get_export_data(self.is_opened_track))}
                                                  for o in self.objects
                                                  if (i + 1) * 4 > o['reference_road_path_vertex'] >= i * 4]),
            }) + get_blender_save_script(out_glb_name=f'terrain_chunk_{i}' if settings.save_glb else None,
                                         export_materials='NONE',
                                         out_blend_name=f'terrain_chunk_{i}' if settings.save_blend else None)
        run_blender(path=path, script=chunks_blender_script)
        run_blender(path=path,
                    script=self.blender_map_script.substitute({
                        'road_path_points': ', '.join(
                            [f'({block.x}, {block.y}, {block.z})' for block in self.road_path]),
                        'is_opened_track': self.is_opened_track,
                        'left_barrier': json.dumps({
                            'points': self.left_barrier_points.points,
                            'middle_points': self.left_barrier_points.middle_points,
                            'lengths': self.left_barrier_points.lengths,
                            'orientations': self.left_barrier_points.orientations,
                        }),
                        'right_barrier': json.dumps({
                            'points': self.right_barrier_points.points,
                            'middle_points': self.right_barrier_points.middle_points,
                            'lengths': self.right_barrier_points.lengths,
                            'orientations': self.right_barrier_points.orientations,
                        }),
                    }),
                    out_glb_name='map' if settings.save_glb else None,
                    export_materials='EXPORT',
                    out_blend_name='map' if settings.save_blend else None)
        if not settings.save_obj:
            for i in range(len(self.terrain_data)):
                os.unlink(f'{path}/terrain_chunk_{i}.obj')
            os.unlink(f'{path}terrain.mtl')

    blender_map_script = Template("""
import bpy
import math
import json

bpy.ops.wm.read_factory_settings(use_empty=True)

# create road spline

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
left_barrier = json.loads('$left_barrier')
right_barrier = json.loads('$right_barrier')
for barrier in [left_barrier, right_barrier]:
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
        bpy.ops.object.select_all(action='DESELECT')
        cube.select_set(True)
        bpy.ops.rigidbody.objects_add()
        cube.rigid_body.type='PASSIVE'
        cube.rigid_body.collision_shape = 'BOX'
        cube['invisible'] = True
    """)

    blender_chunk_script = Template("""
import bpy
import math
import json
from mathutils import Euler

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="terrain_chunk_$chunk_index.obj", use_image_search=True, axis_forward='Y', axis_up='Z')

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
    
def find_subchunk(index):
    import re
    pattern = re.compile(f"^terrain_chunk_\d+_{index}_")
    for ob in bpy.data.objects:
        if pattern.match(ob.name):
            return ob
    return None
    
# terrain collisions
for subchunk_index in list(range(2, 8)) + ['leftfence', 'rightfence']:
    object = find_subchunk(subchunk_index)
    if object is not None:
        bpy.ops.object.select_all(action='DESELECT')
        object.select_set(True)
        bpy.context.view_layer.objects.active = object
        bpy.ops.rigidbody.objects_add()
        object.rigid_body.type='PASSIVE'
        object.rigid_body.collision_shape = 'CONVEX_HULL'
    """)
