import argparse
import inspect
import os
import pathlib
import sys
from math import cos, sin, pi

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from library import require_file

from resources.eac.maps import TriMap

from serializers import get_serializer

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()
tri_map: TriMap = require_file(str(args.file))
for i, terrain_chunk in enumerate(tri_map.terrain):
    for j in range(4):
        terrain_chunk.rows[j][0].y = 0.0
        # rotate terrain mesh around first point
        angle = tri_map.road_spline[i * 4 + j].orientation
        cosine = cos(angle)
        sine = sin(angle)
        for k in range(1, 11):
            terrain_chunk.rows[j][k].x -= terrain_chunk.rows[j][0].x
            terrain_chunk.rows[j][k].z -= terrain_chunk.rows[j][0].z
            x_new = terrain_chunk.rows[j][k].x * cosine - terrain_chunk.rows[j][k].z * sine
            z_new = terrain_chunk.rows[j][k].x * sine + terrain_chunk.rows[j][k].z * cosine
            terrain_chunk.rows[j][k].x = x_new + terrain_chunk.rows[j][0].x
            terrain_chunk.rows[j][k].z = z_new + terrain_chunk.rows[j][0].z
# fix props
for prop in tri_map.proxy_object_instances:
    road_vertex = tri_map.road_spline[prop.reference_road_spline_vertex]
    prop.rotation -= road_vertex.orientation
    if prop.rotation < 0:
        prop.rotation += 2 * pi
    sine, cosine = sin(road_vertex.orientation), cos(road_vertex.orientation)
    prop.position.x, prop.position.z = (prop.position.x * cosine - prop.position.z * sine,
                                        prop.position.x * sine + prop.position.z * cosine)

for i, road_vertex in enumerate(tri_map.road_spline[:len(tri_map.terrain) * 4]):
    road_vertex.position.x = road_vertex.position.y = 0
    road_vertex.position.z = i * 6.25
    road_vertex.orientation = 0
    road_vertex.orientation_x = road_vertex.orientation_y = 0x7FFF  # for some reason, nfs crashes if set all rotation fields to zero (exception divide by zero)
    road_vertex.slope = 0
    road_vertex.slant_a = 0
    road_vertex.slant_b = 0

updated_tri = tri_map.to_raw_value()
f = open(str(args.file)[:-4] + '_SUPERFLAT.TRI', 'wb')
f.write(updated_tri)
f.close()
# serializer = get_serializer(tri_map)
# serializer.serialize(tri_map, f'{str(args.file)}_exported')
