import os
from collections import defaultdict
from string import Template

import settings
from parsers.resources.common.blender_scripts import run_blender
from parsers.resources.common.meshes import SubMesh
from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.basic.data_wrapper import DataWrapper
from resources.eac.bitmaps import AnyBitmapResource
from resources.eac.geometries import OripGeometry
from serializers import BaseFileSerializer


def _setup_vertex(model: SubMesh, block: OripGeometry, index_3D, index_2D, vertices_file_indices_map,
                  flip_texture=False):
    try:
        return vertices_file_indices_map[model][index_3D]
    except KeyError:
        pass
    # new vertex creation
    vertex = block.vertex_block[block.polygon_vertex_map_block[index_3D] % len(block.vertex_block)]
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
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="$obj_file_path", use_image_search=True)
    """)

    def serialize(self, block: OripGeometry, path: str, wrapper: ReadBlockWrapper):
        super().serialize(block, path, wrapper)

        try:
            is_car = wrapper.parent.name.endswith('.CFM')
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
        # if is_car:
        #     if settings.geometry__skip_car_wheel_polygons:
        #         def is_model_nfs1_wheel(model: SubMesh) -> bool:
        #             if model.name in ['tyr4', 'rty4']:  # TRAFFC.CFM
        #                 return True
        #             if model.name == 'circ':  # wheel shadow
        #                 return True
        #             if model.name == '\x00\x00\x00\x00':  # any other CFM
        #                 if len(model.polygons) == 8:
        #                     return True
        #                 if len(model.polygons) > 8:
        #                     # removing only wheel polygons (F512TR)
        #                     def is_polygon_wheel(polygon):
        #                         vertices = [model.vertices[i] for i in polygon]
        #                         is_match = True
        #                         wheel_key = None
        #                         for vert in vertices:
        #                             key = (None
        #                                    if abs(vert[2]) < 0.1 or abs(vert[0]) < 0.1
        #                                    else f"{'f' if vert[2] > 0 else 'r'}{'l' if vert[0] < 0 else 'r'}")
        #                             if not key or (wheel_key is not None and key != wheel_key):
        #                                 is_match = False
        #                                 break
        #                             wheel_key = key
        #                         return is_match
        #                     model.polygons = [p for p in model.polygons if not is_polygon_wheel(p)]
        #                     removed_vertex_indices = [vi for vi in range(len(model.vertices)) if
        #                                               vi not in [element for sublist in model.polygons for element in
        #                                                          sublist]]
        #                     model.vertices = [v for (i, v) in enumerate(model.vertices) if
        #                                       i not in removed_vertex_indices]
        #                     model.vertex_uvs = [v for (i, v) in enumerate(model.vertex_uvs) if
        #                                         i not in removed_vertex_indices]
        #                     for removed_index in removed_vertex_indices[::-1]:
        #                         for j, p in enumerate(model.polygons):
        #                             model.polygons[j] = [idx if idx <= removed_index else idx - 1 for idx in p]
        #             return False
        #
        #         self.sub_models = {k: v for k, v in self.sub_models.items() if not is_model_nfs1_wheel(v)}

        # not sure why, but seems like Z should be inverted in all geometries
        for sub_model in sub_models.values():
            sub_model.change_axes(new_z='-z')

        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(f'{path}geometry.obj', 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for sub_model in sub_models.values():
                f.write(sub_model.to_obj(face_index_increment, True, wrapper.textures_archive))
                face_index_increment += len(sub_model.vertices)
        with open(f'{path}material.mtl', 'w') as f:
            for texture in wrapper.textures_archive.resources:
                if not isinstance(texture, ReadBlockWrapper) or not isinstance(texture.resource, AnyBitmapResource):
                    continue
                f.write(f"""\n\nnewmtl {texture.name}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd assets/{texture.name}.png""")
        wrapper.textures_archive.save_converted(os.path.join(path, 'assets/'))
        script = self.blender_script.substitute({'obj_file_path': 'geometry.obj', 'is_car': is_car})
        script += '\n' + settings.geometry__additional_exporter(f'{os.getcwd()}/{path}body',
                                                                'car' if is_car else 'prop')
        run_blender(path=path,
                    script=script,
                    out_blend_name=f'{os.getcwd()}/{path}body' if settings.geometry__save_blend else None)
        if not settings.geometry__save_obj:
            os.unlink(f'{path}material.mtl')
            os.unlink(f'{path}geometry.obj')
