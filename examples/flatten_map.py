import argparse
import inspect
import os
import pathlib
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from library import require_file

from resources.eac.maps import TriMap

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()
tri_map: TriMap = require_file(str(args.file))
for i, road_vertex in enumerate(tri_map.road_spline):
    road_vertex.position.x = road_vertex.position.y = 0
    road_vertex.position.z = i * 6.25
    road_vertex.orientation = 0
    road_vertex.orientation_x = road_vertex.orientation_y = 6.28  # for some reason, nfs crashes if set all rotation fields to zero (exception divide by zero)
    road_vertex.slope = 0
    road_vertex.slant_a = 0
    road_vertex.slant_b = 0
updated_tri = tri_map.to_raw_value()
os.rename(str(args.file), str(args.file) + '.bak')
f = open(str(args.file), 'wb')
f.write(updated_tri)
f.close()
