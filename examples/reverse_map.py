import argparse
import inspect
import math
import os
import pathlib
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from resources.eac.maps import TriMap
from library.read_data import ReadData
from library import require_file

# FIXME slants are wrong (CL2). on AL2 looks inversed
# FIXME lane merge/split are broken. Is it possible to fix?
# FIXME tunnel walls are broken. Is it possible to fix?
# FIXME preserve 3D effect from two sided bitmaps (add math.pi to rotation, move base, switch side of side bitmap)
# FIXME opponents have totally broken positioning on open tracks
# FIXME AI speed inadequate
# FIXME render order of props

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()
tri_map: ReadData[TriMap] = require_file(str(args.file))


def rotate_point(origin, point, angle):
    ox, oy = origin
    px, py = point
    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


road_spline_length = len(tri_map.terrain) * 4
# start happens at 18th road spline vertex
new_start_position = tri_map.road_spline[road_spline_length - 19].position
new_start_next_position = tri_map.road_spline[road_spline_length - 20].position
# Y - up; X - left; Z - forward;
y_angle_to_rotate = math.pi - math.atan2(new_start_position.x.value - new_start_next_position.x.value,
                                         new_start_position.z.value - new_start_next_position.z.value)

lane_effects = []
start_x_road_offset = tri_map.road_spline[18].position.x.value
for i, vertex in enumerate(tri_map.road_spline[:road_spline_length]):
    # rotate so road at new start goes forward
    vertex.position.z.value, vertex.position.x.value = rotate_point((0, 0),
                                                                    (vertex.position.z.value, vertex.position.x.value),
                                                                    y_angle_to_rotate)

# translate so new start ==
# -old_start.x (aligning car position for tracks, where road spline located at the side, like CY1)
# 0,
# 6.25 * 18 (average value for start position on original tracks)
position_offset = [
    tri_map.road_spline[road_spline_length - 19].position.x.value + start_x_road_offset,
    tri_map.road_spline[road_spline_length - 19].position.y.value,
    tri_map.road_spline[road_spline_length - 19].position.z.value - 6.25 * 18,
]
for i, vertex in enumerate(tri_map.road_spline[:road_spline_length]):
    vertex.position.x.value -= position_offset[0]
    vertex.position.y.value -= position_offset[1]
    vertex.position.z.value -= position_offset[2]
    # swap left and right
    (vertex.left_verge_distance.value, vertex.right_verge_distance.value) = (
    vertex.right_verge_distance.value, vertex.left_verge_distance.value)
    (vertex.left_barrier_distance.value, vertex.right_barrier_distance.value) = (
    vertex.right_barrier_distance.value, vertex.left_barrier_distance.value)
    # slope/slant are just reversed
    vertex.slope.value = -vertex.slope.value
    vertex.slant_a.value = -vertex.slant_a.value
    vertex.slant_b.value = -vertex.slant_b.value

    vertex.orientation.value += math.pi + y_angle_to_rotate

    if vertex.spline_item_mode.value == 'lane_split':
        vertex.spline_item_mode.value = 'lane_merge'
        lane_effects.append(i)
    elif vertex.spline_item_mode.value == 'lane_merge':
        vertex.spline_item_mode.value = 'lane_split'
        # lane_effects.append(i)

for index in lane_effects:
    tri_map.road_spline[index].spline_item_mode.value, tri_map.road_spline[index - 1].spline_item_mode.value = (
        tri_map.road_spline[index - 1].spline_item_mode.value, tri_map.road_spline[index].spline_item_mode.value)

for chunk in tri_map.terrain:
    (chunk.fence.value.has_left_fence, chunk.fence.value.has_right_fence) = (
    chunk.fence.value.has_right_fence, chunk.fence.value.has_left_fence)
    chunk.texture_ids.value = chunk.texture_ids.value[5:] + chunk.texture_ids.value[:5]
    chunk.rows.value = chunk.rows.value[::-1]
    for i in range(4):
        chunk.rows[i].value = [chunk.rows[i].value[0]] + chunk.rows[i].value[6:] + chunk.rows[i].value[1:6]
        for j in range(11):
            chunk.rows[i][j].z.value, chunk.rows[i][j].x.value = rotate_point((0, 0),
                                                                              (chunk.rows[i][j].z.value,
                                                                               chunk.rows[i][j].x.value),
                                                                              y_angle_to_rotate)

amount_of_instances = [x.reference_road_spline_vertex.value for x in tri_map.proxy_object_instances].index(-1)
for proxy_inst in tri_map.proxy_object_instances[:amount_of_instances]:
    proxy_inst.reference_road_spline_vertex.value = road_spline_length - 1 - proxy_inst.reference_road_spline_vertex.value
    proxy_inst.rotation.value += math.pi
    proxy_inst.position.z.value, proxy_inst.position.x.value = rotate_point((0, 0),
                                                                            (proxy_inst.position.z.value,
                                                                             proxy_inst.position.x.value),
                                                                            y_angle_to_rotate)

tri_map.road_spline.value = tri_map.road_spline.value[:road_spline_length][::-1] + tri_map.road_spline.value[
                                                                                   road_spline_length:]
tri_map.terrain.value = tri_map.terrain.value[::-1]
tri_map.proxy_object_instances.value = (tri_map.proxy_object_instances.value[:amount_of_instances][::-1]
                                        + tri_map.proxy_object_instances.value[amount_of_instances:])

updated_tri = tri_map.to_bytes()
os.makedirs('/'.join(str(args.file).split('/')[:-1]) + '/reversed', exist_ok=True)
f = open('/'.join(str(args.file).split('/')[:-1]) + '/reversed/' + str(args.file).split('/')[-1], 'wb')
f.write(updated_tri)
f.close()
