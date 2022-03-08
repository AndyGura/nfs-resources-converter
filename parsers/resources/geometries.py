import json
import os
from collections import defaultdict
from io import BufferedReader, SEEK_CUR
from string import Template
from typing import List

import settings
from buffer_utils import read_int, read_utf_bytes, read_byte, read_signed_int
from parsers.resources.base import BaseResource
from parsers.resources.bitmaps import BaseBitmap
from parsers.resources.collections import ArchiveResource
from parsers.resources.common.blender_scripts import run_blender
from parsers.resources.common.meshes import SubMesh


class Block:
    POLYGON = 0
    VERTEX_UV = 1
    TEXTURE_NAME = 2
    TEXTURE_NUMBER_MAP = 3
    UNK4 = 4
    UNK5 = 5
    LABEL = 6
    VERTEX = 7
    POLYGON_VERTEX_MAP = 8


class OripGeometryResource(BaseResource):

    # means which part of meter equivalent to one unit of coordinates. Calculated from LDIABLO
    car_model_size_koeff = 0.00767546
    # means which part of meter equivalent to one unit of coordinates. Calculated approximately
    prop_model_size_koeff = car_model_size_koeff * 7

    bounding_box = None

    @property
    def is_car(self):
        from parsers.resources.archives import WwwwArchive
        return isinstance(self.parent, WwwwArchive) and self.parent.name[-4:] == '.CFM'

    @property
    def model_size_koeff(self):
        return self.car_model_size_koeff if self.is_car else self.prop_model_size_koeff

    def __init__(self):
        super().__init__()
        self._record_power: List[int] = [12, 8, 20, 20, 28, 12, 12, 12, 4]
        self._record_count: List[int] = [0] * 9
        self._offsets: List[int] = [0] * 9
        self.textures_archive: ArchiveResource = None
        self.sub_models = defaultdict(SubMesh)
        self.vertices_file_indices_map = defaultdict(lambda: dict())

    def _get_texture_name(self, buffer: BufferedReader, index: int) -> str:
        pointer = buffer.tell()
        buffer.seek(self._offsets[Block.TEXTURE_NAME] + index * self._record_power[Block.TEXTURE_NAME] + 8)
        name = read_utf_bytes(buffer, 4)
        buffer.seek(pointer)
        return name

    def _read_flags(self, buffer: BufferedReader, start_offset: int, length: int):
        buffer.seek(16, SEEK_CUR)
        self._record_count[Block.VERTEX] = read_int(buffer)
        buffer.seek(4, SEEK_CUR)
        self._offsets[Block.VERTEX] = start_offset + read_int(buffer)
        self._record_count[Block.VERTEX_UV] = read_int(buffer)
        self._offsets[Block.VERTEX_UV] = start_offset + read_int(buffer)
        self._record_count[Block.POLYGON] = read_int(buffer)
        self._offsets[Block.POLYGON] = start_offset + read_int(buffer)
        identifier = read_utf_bytes(buffer, 12)
        self._record_count[Block.TEXTURE_NAME] = read_int(buffer)
        self._offsets[Block.TEXTURE_NAME] = start_offset + read_int(buffer)
        self._record_count[Block.TEXTURE_NUMBER_MAP] = read_int(buffer)
        self._offsets[Block.TEXTURE_NUMBER_MAP] = start_offset + read_int(buffer)
        self._record_count[Block.UNK4] = read_int(buffer)
        self._offsets[Block.UNK4] = start_offset + read_int(buffer)
        self._offsets[Block.POLYGON_VERTEX_MAP] = start_offset + read_int(buffer)
        self._record_count[Block.POLYGON_VERTEX_MAP] = int((length - self._offsets[Block.POLYGON_VERTEX_MAP] + start_offset) / self._record_power[Block.POLYGON_VERTEX_MAP])
        self._record_count[Block.UNK5] = read_int(buffer)
        self._offsets[Block.UNK5] = start_offset + read_int(buffer)
        self._record_count[Block.LABEL] = read_int(buffer)
        self._offsets[Block.LABEL] = start_offset + read_int(buffer)

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start_offset = buffer.tell()
        self._read_flags(buffer, start_offset, length)
        self.sub_models.clear()
        for i in range(0, self._record_count[Block.POLYGON]):
            buffer.seek(start_offset + i * self._record_power[Block.POLYGON] + 112)
            polygon_type = read_byte(buffer) & 255
            normal = read_byte(buffer)
            texture_id = self._get_texture_name(buffer, read_byte(buffer))
            sub_model = self.sub_models[texture_id]
            if not sub_model.name:
                sub_model.name = texture_id
                sub_model.texture_id = texture_id
            buffer.seek(1, SEEK_CUR)
            offset_3D = read_int(buffer)
            offset_2D = read_int(buffer)
            is_triangle = (polygon_type & (0xff >> 5)) == 3
            is_quad = (polygon_type & (0xff >> 5)) == 4
            if is_triangle:
                if normal in [17, 19]:
                    # two sided polygon
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 1, 2)
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 2, 1)
                elif normal in [18, 2, 3, 48, 50]:
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 1, 2, flip_texture=True)
                elif normal in [0, 1, 16]:
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 2, 1)
                else:
                    raise NotImplementedError(f'Unknown normal: {normal}, polygon type: {polygon_type}')
            elif is_quad:
                if normal in [17, 19]:
                    # two sided polygon
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 1, 3)
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 1, 2, 3)
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 3, 1)
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 1, 3, 2)
                elif normal in [18, 2, 3, 48, 50]:
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 1, 3, flip_texture=True)
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 1, 2, 3, flip_texture=True)
                elif normal in [0, 1, 16]:
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 0, 3, 1)
                    self._setup_polygon(sub_model, texture_id, buffer, offset_3D, offset_2D, 1, 3, 2)
                else:
                    # TODO Unknown normal: 10 nfs1/SIMDATA/ETRACKFM/CY1_001.FAM/props/0xcd59c/0xcd5ac
                    raise NotImplementedError(f'Unknown normal: {normal}, polygon type: {polygon_type}')
            elif polygon_type == 2:  # BURNT SIENNA prop. looks good without this polygon
                continue
            else:
                raise NotImplementedError(f'Unknown polygon: {polygon_type}')
        if self.is_car:
            for model in self.sub_models.values():
                model.change_axes(new_y='-z', new_z='y')
            # FIXME how the NFS knows the dimensions of car? Looks like it uses box collision as well
            self.bounding_box = {'min': [9999999, 9999999, 9999999], 'max': [-9999999, -9999999, -9999999]}
            # omit wheel + shadow polygons
            for model in [x for (key, x) in self.sub_models.items() if key not in ['\x00\x00\x00\x00', 'shad', 'circ', 'wing']]:
                for v in model.vertices:
                    for i in range(3):
                        self.bounding_box['min'][i] = min(self.bounding_box['min'][i], v[i])
                        self.bounding_box['max'][i] = max(self.bounding_box['max'][i], v[i])
            # extra 5cm clearance
            self.bounding_box['min'][2] += 0.05
        return length

    def save_converted(self, path: str):
        if not settings.save_obj and not settings.save_glb and not settings.save_blend:
            return
        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(f'{path}geometry.obj', 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for sub_model in self.sub_models.values():
                f.write(sub_model.to_obj(face_index_increment, True, self.textures_archive))
                face_index_increment += len(sub_model.vertices)
        with open(f'{path}material.mtl', 'w') as f:
            for texture in self.textures_archive.resources:
                if not isinstance(texture, BaseBitmap):
                    continue
                f.write(f"""\n\nnewmtl {texture.name}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd assets/{texture.name}.png""")
        self.textures_archive.save_converted(os.path.join(path, 'assets/'))
        run_blender(path=path,
                    # FIXME hardcoded car mass
                    script=self.blender_script.substitute({'obj_file_path': 'geometry.obj', 'is_car': self.is_car,
                                                           'bounding_box': json.dumps(self.bounding_box),
                                                           'mass': 1500}),
                    out_glb_name='body' if settings.save_glb else None,
                    export_materials='EXPORT',
                    out_blend_name='body' if settings.save_blend else None)
        if not settings.save_obj:
            os.unlink(f'{path}material.mtl')
            os.unlink(f'{path}geometry.obj')

    def _setup_polygon(self, model: SubMesh, texture_id: str, buffer: BufferedReader, offset_3D, offset_2D, *offsets,
                       flip_texture=False):
        model.polygons.append([self._setup_vertex(model, buffer, offset_3D + offset, offset_2D + offset, flip_texture)
                               for offset in offsets])

    def _setup_vertex(self, model: SubMesh, buffer: BufferedReader, index_3D, index_2D, flip_texture=False):
        try:
            return self.vertices_file_indices_map[model][index_3D]
        except KeyError:
            pass
        # new vertex creation
        buffer.seek(self._offsets[Block.POLYGON_VERTEX_MAP] + index_3D * self._record_power[Block.POLYGON_VERTEX_MAP])
        buffer.seek(self._offsets[Block.VERTEX] + read_int(buffer) * self._record_power[Block.VERTEX])
        # z inverted
        vertex = [
            read_signed_int(buffer) * self.model_size_koeff,
            read_signed_int(buffer) * self.model_size_koeff,
            -read_signed_int(buffer) * self.model_size_koeff
        ]
        model.vertices.append(vertex)
        self.vertices_file_indices_map[model][index_3D] = len(model.vertices) - 1
        # setup texture coordinate
        buffer.seek(self._offsets[Block.POLYGON_VERTEX_MAP] + index_2D * self._record_power[Block.POLYGON_VERTEX_MAP])
        uv_vertex_index = read_int(buffer)
        if uv_vertex_index < self._record_count[Block.VERTEX_UV]:
            buffer.seek(self._offsets[Block.VERTEX_UV] + uv_vertex_index * self._record_power[Block.VERTEX_UV])
            model.vertex_uvs.append([read_signed_int(buffer) for _ in range(0, 2)])
        else:
            model.scaled_uvs.add(len(model.vertex_uvs))
            uv = [
                1 if len(model.vertex_uvs) % 4 > 1 else 0,
                1 if len(model.vertex_uvs) % 2 == 1 else 0
            ]
            if flip_texture:
                uv = [uv[1], uv[0]]
            model.vertex_uvs.append(uv)
        return self.vertices_file_indices_map[model][index_3D]

    blender_script = Template("""
import bpy
import math
import json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="$obj_file_path", use_image_search=True, axis_up='Z', axis_forward='Y')

if $is_car:

    def get_wheel_vertex_key(vert):
        if abs(vert.co.y) < 0.1 or abs(vert.co.x) < 0.1:
            # not a wheel vertex
            return None, vert.co.x, vert.co.y, vert.co.z
        key = 'f' if vert.co.y > 0 else 'r'
        key += 'l' if vert.co.x < 0 else 'r'
        return key, vert.co.x, vert.co.y, vert.co.z
    
    if bpy.data.objects.get('circ') is not None:
        circ_mesh = bpy.data.objects['circ'].data
        from collections import defaultdict
        import bmesh
        wheel_vertices = defaultdict(list)
        for vert in circ_mesh.vertices:
            (key, x, y, z) = get_wheel_vertex_key(vert)
            wheel_vertices[key].append((x, y, z))
        wheel_centers = ({ 
            key: {
                'coordinates': (
                    sum([x for (x, y, z) in vertices_list])/len(vertices_list),
                    sum([y for (x, y, z) in vertices_list])/len(vertices_list),
                    sum([z for (x, y, z) in vertices_list])/len(vertices_list),
                ),
                'radius': 0.4,
                'width': 0.3,
            } for (key, vertices_list) in wheel_vertices.items() 
        })
        print(f'wheel_centers: {wheel_centers}')
        for (key, wheel_center) in wheel_centers.items():
            distances = [math.sqrt(
                (x - wheel_center['coordinates'][0])**2 +
                (y - wheel_center['coordinates'][1])**2 +
                (z - wheel_center['coordinates'][2])**2
            ) for (x, y, z) in wheel_vertices[key]]
            wheel_center['radius'] =  (sum(distances) / len(distances)) / math.sqrt(2)
            wheels_mesh = bpy.data.objects['Mesh'].data
            wheel_face_vertex_indices = []        
            for polygon in wheels_mesh.polygons:
                vertices = [wheels_mesh.vertices[v] for v in polygon.vertices]
                is_match = True
                for vert in vertices:
                    (vert_key, x, y, z) = get_wheel_vertex_key(vert)
                    if vert_key != key:
                        is_match = False
                        break
                if is_match:
                    wheel_face_vertex_indices += polygon.vertices
            wheel_face_vertex_indices = list(dict.fromkeys(wheel_face_vertex_indices))
            wheel_face_vertices = [
                (wheels_mesh.vertices[i].co.x, wheels_mesh.vertices[i].co.y, wheels_mesh.vertices[i].co.z) 
                for i in wheel_face_vertex_indices
            ]
            bm = bmesh.new()
            bm.from_mesh(wheels_mesh)
            bm.verts.ensure_lookup_table()
            vertices_to_remove = [bm.verts[x] for x in wheel_face_vertex_indices]
            for bmv in vertices_to_remove:
                bm.verts.remove(bmv)
            bm.to_mesh(wheels_mesh)
            wheels_mesh.update()
            wheel_face_center = (
                sum([x for (x, y, z) in wheel_face_vertices])/len(wheel_face_vertices),
                sum([y for (x, y, z) in wheel_face_vertices])/len(wheel_face_vertices),
                sum([z for (x, y, z) in wheel_face_vertices])/len(wheel_face_vertices),
            )
            wheel_center['width'] = math.sqrt(
                (wheel_center['coordinates'][0] - wheel_face_center[0])**2 +
                (wheel_center['coordinates'][1] - wheel_face_center[1])**2 +
                (wheel_center['coordinates'][2] - wheel_face_center[2])**2
            )
        for wheel_key in wheel_centers.keys():
            o = bpy.data.objects.new( f"wheel_{wheel_key}", None )
            bpy.context.scene.collection.objects.link(o)
            o.location = wheel_centers[wheel_key]['coordinates']
            o['tyre_radius'] = wheel_centers[wheel_key]['radius']
            o['tyre_width'] = wheel_centers[wheel_key]['width']
        bpy.data.objects.remove(bpy.data.objects['circ'])
        bpy.data.meshes.remove(circ_mesh)
        
    bounding_box = json.loads('$bounding_box')
    bpy.ops.mesh.primitive_cube_add(location=(
                                        (bounding_box['min'][0] + bounding_box['max'][0]) / 2,
                                        (bounding_box['min'][1] + bounding_box['max'][1]) / 2,
                                        (bounding_box['min'][2] + bounding_box['max'][2]) / 2),
                                    scale=(
                                        (bounding_box['min'][0] - bounding_box['max'][0]) / 2,
                                        (bounding_box['min'][1] - bounding_box['max'][1]) / 2,
                                        (bounding_box['min'][2] - bounding_box['max'][2]) / 2))
    cube = bpy.data.objects['Cube']
    cube.name = "chassis_collision"
    bpy.ops.rigidbody.objects_add()
    cube.rigid_body.type='ACTIVE'
    print(cube.rigid_body)
    cube.rigid_body.collision_shape = 'BOX'
    cube.rigid_body.mass=$mass
    cube['invisible'] = True
    """)
