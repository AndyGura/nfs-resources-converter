import argparse
import inspect
import os
import pathlib
import sys
from math import cos, sin, pi

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from library.read_data import ReadData
from library import require_file

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()
tri_map: ReadData = require_file(str(args.file))
for i, terrain_chunk in enumerate(tri_map.terrain):
    for j in range(4):
        terrain_chunk.rows[j][0].y.value = 0.0
        # rotate terrain mesh around first point
        angle = tri_map.road_spline[i * 4 + j].orientation.value
        cosine = cos(angle)
        sine = sin(angle)
        for k in range(1, 11):
            terrain_chunk.rows[j][k].x.value -= terrain_chunk.rows[j][0].x.value
            terrain_chunk.rows[j][k].z.value -= terrain_chunk.rows[j][0].z.value
            x_new = terrain_chunk.rows[j][k].x.value * cosine - terrain_chunk.rows[j][k].z.value * sine
            z_new = terrain_chunk.rows[j][k].x.value * sine + terrain_chunk.rows[j][k].z.value * cosine
            terrain_chunk.rows[j][k].x.value = x_new + terrain_chunk.rows[j][0].x.value
            terrain_chunk.rows[j][k].z.value = z_new + terrain_chunk.rows[j][0].z.value
# fix props
for prop in tri_map.proxy_object_instances:
    road_vertex = tri_map.road_spline[prop.reference_road_spline_vertex.value]
    prop.rotation.value -= road_vertex.orientation.value
    if prop.rotation.value < 0:
        prop.rotation.value += 2 * pi
    sine, cosine = sin(road_vertex.orientation.value), cos(road_vertex.orientation.value)
    prop.position.x.value, prop.position.z.value = (prop.position.x.value * cosine - prop.position.z.value * sine,
                                                    prop.position.x.value * sine + prop.position.z.value * cosine)

for i, road_vertex in enumerate(tri_map.road_spline[:len(tri_map.terrain) * 4]):
    road_vertex.position.x.value = road_vertex.position.y.value = 0
    road_vertex.position.z.value = i * 6.25
    road_vertex.orientation.value = 0
    road_vertex.orientation_x.value = road_vertex.orientation_y.value = 0x7FFF  # for some reason, nfs crashes if set all rotation fields to zero (exception divide by zero)
    road_vertex.slope.value = 0
    road_vertex.slant_a.value = 0
    road_vertex.slant_b.value = 0

updated_tri = tri_map.to_bytes()
f = open(str(args.file)[:-4] + '_SUPERFLAT.TRI', 'wb')
f.write(updated_tri)
f.close()
# serializer = get_serializer(tri_map)
# serializer.serialize(tri_map, f'{str(args.file)}_exported')
