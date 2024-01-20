import json
import math
import os
from collections import defaultdict
from copy import deepcopy
from string import Template
from typing import Literal, List, Tuple

from library.helpers.data_wrapper import DataWrapper
from library.helpers.exceptions import DataIntegrityException
from library.read_data import ReadData
from library.utils.blender_scripts import run_blender
from library.utils.meshes import SubMesh
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import AnyBitmapBlock
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer

default_uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]


def _setup_vertex(model: SubMesh, block: ReadData[OripGeometry], vertices_file_indices_map, index_3D, index_2D,
                  index_in_polygon):
    try:
        return vertices_file_indices_map[model][index_3D]
    except KeyError:
        pass
    # new vertex creation
    vertex = block.vertex_block[block.polygon_vertex_map_block[index_3D].value]
    model.vertices.append([vertex.x.value, vertex.y.value, vertex.z.value])
    vertices_file_indices_map[model][index_3D] = len(model.vertices) - 1
    # setup texture coordinate
    if index_2D is None:
        model.scaled_uvs.add(len(model.vertex_uvs))
        uv = DataWrapper({'u': default_uvs[index_in_polygon][0], 'v': default_uvs[index_in_polygon][1]})
    else:
        uv = DataWrapper({
            'u': block.vertex_uvs_block[block.polygon_vertex_map_block[index_2D].value].u.value,
            'v': block.vertex_uvs_block[block.polygon_vertex_map_block[index_2D].value].v.value,
        })
    model.vertex_uvs.append([uv.u, uv.v])
    return vertices_file_indices_map[model][index_3D]


class OripGeometrySerializer(BaseFileSerializer):
    blender_script = Template("""
import json
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath="$obj_file_path", forward_axis='Y', up_axis='Z')

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

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        # shpi is always next block
        from library import require_resource
        textures_shpi_block, _ = require_resource(
            '/'.join(data.id.split('/')[:-1] + [str(int(data.id.split('/')[-1]) + 1)]))
        if not textures_shpi_block or not isinstance(textures_shpi_block.block, ShpiBlock):
            raise DataIntegrityException('Cannot find SHPI archive for ORIP geometry')

        super().serialize(data, path, is_dir=True)
        try:
            is_car = '.CFM__' in data.block_state['id']
        except:
            is_car = False
        vertices_file_indices_map = defaultdict(lambda: dict())
        sub_models = defaultdict(SubMesh)

        for polygon in data.polygons_block:
            polygon_type = polygon.polygon_type.value
            mapping = polygon.mapping.value
            texture_id = data.texture_names_block[polygon.texture_index.value].file_name.value
            sub_model = sub_models[texture_id]
            if not sub_model.name:
                sub_model.name = texture_id
                sub_model.texture_id = texture_id
            offset_3D = polygon.offset_3d.value
            offset_2D = polygon.offset_2d.value

            def _setup_polygon(offsets):
                sub_model.polygons.append([_setup_vertex(sub_model,
                                                         data,
                                                         vertices_file_indices_map,
                                                         offset_3D + offset,
                                                         (offset_2D + offset) if mapping['use_uv'] else None,
                                                         offset)
                                           for offset in offsets])

            if (polygon_type & (0xff >> 5)) == 3:
                # triangle
                if mapping['two_sided'] or not mapping['flip_normal']:
                    _setup_polygon([0, 1, 2])
                if mapping['two_sided'] or mapping['flip_normal']:
                    _setup_polygon([0, 2, 1])
            elif (polygon_type & (0xff >> 5)) == 4:
                # quad
                if mapping['two_sided'] or not mapping['flip_normal']:
                    _setup_polygon([0, 1, 2])
                    _setup_polygon([0, 2, 3])
                if mapping['two_sided'] or mapping['flip_normal']:
                    _setup_polygon([0, 2, 1])
                    _setup_polygon([0, 3, 2])
            elif polygon_type == 2:  # BURNT SIENNA prop. looks good without this polygon
                continue
            else:
                raise NotImplementedError(f'Unknown polygon: {polygon_type}')
        dummies = []
        if is_car:
            if self.settings.geometry__replace_car_wheel_with_dummies:
                # receives wheel vertices (4 items), returns center vertex and radius
                def get_wheel_display_info(vertices: List[List[float]]) -> Tuple[List[float], float]:
                    center = [sum([v[i] for v in vertices]) / len(vertices) for i in range(3)]
                    distances = [math.sqrt(sum((v[i] - center[i]) ** 2 for i in range(3))) for v in vertices]
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
                    if name not in ['tyr4', 'rty4', 'circ', '', 'tyre']:
                        non_wheel_models[name] = model
                        continue
                    if len(model.polygons) > 8:
                        # save non-wheel part of model (F512TR)
                        model_without_wheels = deepcopy(model)
                        model_without_wheels.polygons = [p for p in model_without_wheels.polygons if
                                                         not get_wheel_polygon_key(p)]
                        model_without_wheels.remove_orphaned_vertices()
                        non_wheel_models[name] = model_without_wheels
                        # remove non wheel part from current model to process
                        model.polygons = [p for p in model.polygons if get_wheel_polygon_key(p)]
                        model.remove_orphaned_vertices()
                    wheel_polygons_map = {'fl': [], 'fr': [], 'rl': [], 'rr': []}
                    for polygon in model.polygons:
                        try:
                            wheel_polygons_map[get_wheel_polygon_key(polygon)].append(polygon)
                        except KeyError:
                            pass
                    for key, polygons in wheel_polygons_map.items():
                        vertex_indices = list({x for p in polygons for x in p})
                        if not vertex_indices:
                            continue
                        assert len(vertex_indices) == 4, DataIntegrityException('Wheel square vertices count != 4')
                        (shadow_centers if name == 'circ' else centers)[key] = get_wheel_display_info(
                            [model.vertices[i] for i in vertex_indices])
                if centers and not shadow_centers:
                    # warrior car does not have shadow
                    shadow_centers = {key: ([(p[0] - 0.3 if p[0] > 0 else p[0] + 0.3), p[1], p[2]], radius) for
                                      key, (p, radius) in centers.items()}
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
        with open(os.path.join(path, 'geometry.obj'), 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for sub_model in sub_models.values():
                f.write(sub_model.to_obj(face_index_increment, True, textures_shpi_block))
                face_index_increment += len(sub_model.vertices)
        with open(os.path.join(path, 'material.mtl'), 'w') as f:
            for texture in textures_shpi_block.children:
                if not isinstance(texture, ReadData) or not isinstance(texture.block, AnyBitmapBlock):
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
        if self.settings.geometry__export_to_gg_web_engine:
            from serializers.misc.build_blender_scene import construct_blender_export_script
            script += '\n' + construct_blender_export_script(
                file_name=os.path.join(os.getcwd(), path, 'body'),
                export_materials='EXPORT')
        # skip running blender if it does not save anything
        if self.settings.geometry__export_to_gg_web_engine or self.settings.geometry__save_blend:
            run_blender(path=path,
                        script=script,
                        out_blend_name=os.path.join(os.getcwd(), path, 'body')
                        if self.settings.geometry__save_blend
                        else None)
        if not self.settings.geometry__save_obj:
            os.unlink(os.path.join(path, 'material.mtl'))
            os.unlink(os.path.join(path, 'geometry.obj'))
