import json
import math
import os
from collections import defaultdict
from copy import deepcopy
from string import Template
from typing import Literal, List, Tuple

import settings
from library.utils.blender_scripts import run_blender
from library.utils.meshes import SubMesh
from library.helpers.data_wrapper import DataWrapper
from library.helpers.exceptions import BlockIntegrityException
from resources.eac.bitmaps import AnyBitmapBlock
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer


def _setup_vertex(model: SubMesh, block: OripGeometry, index_3D, index_2D, vertices_file_indices_map,
                  flip_texture=False):
    try:
        return vertices_file_indices_map[model][index_3D]
    except KeyError:
        pass
    # new vertex creation
    vertex = block.vertex_block[block.polygon_vertex_map_block[index_3D]]
    model.vertices.append([vertex.x, vertex.y, vertex.z])
    vertices_file_indices_map[model][index_3D] = len(model.vertices) - 1
    # setup texture coordinate
    try:
        uv = block.vertex_uvs_block[block.polygon_vertex_map_block[index_2D]]
    except IndexError:
        model.scaled_uvs.add(len(model.vertex_uvs))
        uv = DataWrapper({
            'u': 1 if len(model.vertex_uvs) % 4 > 1 else 0,
            'v': 1 if len(model.vertex_uvs) % 2 == 1 else 0
        })
        if flip_texture:
            uv = DataWrapper({'u': uv.v, 'v': uv.u})
    model.vertex_uvs.append([uv.u, uv.v])
    return vertices_file_indices_map[model][index_3D]


def _setup_polygon(model: SubMesh, block: OripGeometry, vertices_file_indices_map, offset_3D, offset_2D, *offsets,
                   flip_texture=False):
    model.polygons.append(
        [_setup_vertex(model, block, offset_3D + offset, offset_2D + offset, vertices_file_indices_map, flip_texture)
         for offset in offsets])


class OripGeometrySerializer(BaseFileSerializer):

    blender_script = Template("""
import bpy
import json
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="$obj_file_path", use_image_search=True, axis_forward='Y', axis_up='Z')

dummies = json.loads('$dummies')
for dummy in dummies:
    o = bpy.data.objects.new( dummy['name'], None )
    bpy.context.scene.collection.objects.link(o)
    o.location = dummy['position']
    for key, value in dummy.items():
        if key in ['position', 'name']:
            continue
        o[key] = value

    """)

    def serialize(self, block: OripGeometry, path: str):
        # shpi is always next block
        from library import require_resource
        textures_shpi_block = require_resource('/'.join(block.id.split('/')[:-1] + [str(int(block.id.split('/')[-1]) + 1)]))
        if not textures_shpi_block:
            raise BlockIntegrityException('Cannot find SHPI archive for ORIP geometry')

        super().serialize(block, path)
        try:
            is_car = '.CFM__' in block.id
        except:
            is_car = False
        vertices_file_indices_map = defaultdict(lambda: dict())
        sub_models = defaultdict(SubMesh)

        for polygon in block.polygons_block:
            polygon_type = polygon.polygon_type
            normal = polygon.normal
            texture_id = block.texture_names_block[polygon.texture_index].file_name
            sub_model = sub_models[texture_id]
            if not sub_model.name:
                sub_model.name = texture_id
                sub_model.texture_id = texture_id
            offset_3D = polygon.offset_3d
            offset_2D = polygon.offset_2d
            is_triangle = (polygon_type & (0xff >> 5)) == 3
            is_quad = (polygon_type & (0xff >> 5)) == 4
            if is_triangle:
                if normal in [17, 19]:
                    # two sided polygon
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 1, 2)
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 2, 1)
                elif normal in [18, 2, 3, 48, 50]:
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 1, 2, flip_texture=True)
                elif normal in [0, 1, 16]:
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 2, 1)
                else:
                    raise NotImplementedError(f'Unknown normal: {normal}, polygon type: {polygon_type}')
            elif is_quad:
                if normal in [17, 19]:
                    # two sided polygon
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 1, 3)
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 1, 2, 3)
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 3, 1)
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 1, 3, 2)
                elif normal in [18, 2, 3, 48, 50, 10, 6]:  # 10, 6 are unknown. Placed here for testing and looks good
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 1, 3, flip_texture=True)
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 1, 2, 3, flip_texture=True)
                elif normal in [0, 1, 16]:
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 0, 3, 1)
                    _setup_polygon(sub_model, block, vertices_file_indices_map, offset_3D, offset_2D, 1, 3, 2)
                else:
                    raise NotImplementedError(f'Unknown normal: {normal}, polygon type: {polygon_type}')
            elif polygon_type == 2:  # BURNT SIENNA prop. looks good without this polygon
                continue
            else:
                raise NotImplementedError(f'Unknown polygon: {polygon_type}')
        dummies = []
        if is_car:
            if settings.geometry__replace_car_wheel_with_dummies:
                # receives wheel vertices (4 items), returns center vertex and radius
                def get_wheel_display_info(vertices: List[List[float]]) -> Tuple[List[float], float]:
                    center = [sum([v[i] for v in vertices])/len(vertices) for i in range(3)]
                    distances = [math.sqrt(sum((v[i] - center[i])**2 for i in range(3))) for v in vertices]
                    return center, (sum(distances) / len(distances)) / math.sqrt(2)

                def get_wheel_polygon_key(polygon) -> Literal['fl', 'fr', 'rl', 'rr', None]:
                    vertices = [model.vertices[i] for i in polygon]
                    wheel_key = None
                    for vert in vertices:
                        key = (None
                               if abs(vert[2]) < 0.1 or abs(vert[0]) < 0.1
                               else f"{'f' if vert[2] > 0 else 'r'}{'l' if vert[0] < 0 else 'r'}")
                        if not key or (wheel_key is not None and key != wheel_key):
                            return None
                        wheel_key = key
                    return wheel_key

                non_wheel_models = {}
                centers = {}
                shadow_centers = {}
                for name, model in sub_models.items():
                    if name not in ['tyr4', 'rty4', 'circ', '\x00\x00\x00\x00', 'tyre']:
                        non_wheel_models[name] = model
                        continue
                    if len(model.polygons) > 8:
                        # save non-wheel part of model (F512TR)
                        model_without_wheels = deepcopy(model)
                        model_without_wheels.polygons = [p for p in model_without_wheels.polygons if not get_wheel_polygon_key(p)]
                        model_without_wheels.remove_orphaned_vertices()
                        non_wheel_models[name] = model_without_wheels
                        # remove non wheel part from current model to process
                        model.polygons = [p for p in model.polygons if get_wheel_polygon_key(p)]
                        model.remove_orphaned_vertices()
                    wheel_polygons_map = { 'fl': [], 'fr': [], 'rl': [], 'rr': [] }
                    for polygon in model.polygons:
                        try:
                            wheel_polygons_map[get_wheel_polygon_key(polygon)].append(polygon)
                        except KeyError:
                            pass
                    for key, polygons in wheel_polygons_map.items():
                        vertex_indices = list({ x for p in polygons for x in p })
                        if not vertex_indices:
                            continue
                        assert len(vertex_indices) == 4, BlockIntegrityException('Wheel square vertices count != 4')
                        (shadow_centers if name == 'circ' else centers)[key] = get_wheel_display_info([model.vertices[i] for i in vertex_indices])
                if centers and not shadow_centers:
                    # warrior car does not have shadow
                    shadow_centers = { key: ([(p[0] - 0.3 if p[0] > 0 else p[0] + 0.3), p[1], p[2]], radius) for key, (p, radius) in centers.items() }
                dummies = [{
                    'name': f'wheel_{key}',
                    'position': position,
                    'radius': centers[key][1],
                    'width': abs(position[0] - centers[key][0][0])
                } for (key, (position, radius)) in shadow_centers.items()]
                sub_models = non_wheel_models
        # not sure why, but seems like Z should be inverted in all geometries
        for sub_model in sub_models.values():
            sub_model.change_axes(new_z='y', new_y='z')
        for dummy in dummies:
            dummy['position'] = [dummy['position'][0], dummy['position'][2], dummy['position'][1]]

        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(f'{path}geometry.obj', 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for sub_model in sub_models.values():
                f.write(sub_model.to_obj(face_index_increment, True, textures_shpi_block))
                face_index_increment += len(sub_model.vertices)
        with open(f'{path}material.mtl', 'w') as f:
            for texture in textures_shpi_block.children:
                if not isinstance(texture, AnyBitmapBlock):
                    continue
                f.write(f"""\n\nnewmtl {texture.id.split('/')[-1]}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd assets/{texture.id.split('/')[-1]}.png""")
        from serializers import ShpiArchiveSerializer
        shpi_serializer = ShpiArchiveSerializer()
        shpi_serializer.serialize(textures_shpi_block, os.path.join(path, 'assets/'))
        script = self.blender_script.substitute({'obj_file_path': 'geometry.obj',
                                                 'is_car': is_car,
                                                 'dummies': json.dumps(dummies)})
        script += '\n' + settings.geometry__additional_exporter(f'{os.getcwd()}/{path}body',
                                                                'car' if is_car else 'prop')
        run_blender(path=path,
                    script=script,
                    out_blend_name=f'{os.getcwd()}/{path}body' if settings.geometry__save_blend else None)
        if not settings.geometry__save_obj:
            os.unlink(f'{path}material.mtl')
            os.unlink(f'{path}geometry.obj')
