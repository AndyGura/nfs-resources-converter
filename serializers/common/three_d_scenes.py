import json
import math
import os
from abc import ABC, abstractmethod
from string import Template
from typing import Callable
from typing import Tuple, List

from library.utils.blender_scripts import run_blender, get_blender_save_script


class BaseMesh(ABC):
    def __init__(self):
        self.name = None
        self.vertices = []
        self.polygons = []
        self.vertex_uvs = []
        self.pivot_offset = (0, 0, 0)

    def rotate_z(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        self.vertices = [[p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]]
                         for p in self.vertices]

    @abstractmethod
    def to_obj(self, face_index_increment, mtllib=None, pivot_offset=None) -> Tuple[str, int]:
        raise NotImplementedError

    def change_axes(self, new_x='x', new_y='y', new_z='z'):
        map = {
            'x': 0,
            'y': 1,
            'z': 2,
        }

        def get_value_from_vertex_list(vertex: list[int], coordinate: str) -> int:
            value = vertex[map[coordinate[-1]]]
            if coordinate[0] == '-':
                value = -value
            return value

        self.vertices = [[
            get_value_from_vertex_list(v, new_x),
            get_value_from_vertex_list(v, new_y),
            get_value_from_vertex_list(v, new_z),
        ] for v in self.vertices]

    # after deleting polygons should call this function
    def remove_orphaned_vertices(self):
        orphans = [vi for vi in range(len(self.vertices)) if
                   vi not in [element for sublist in self.polygons for element in sublist]]
        self.vertices = [v for (i, v) in enumerate(self.vertices) if i not in orphans]
        self.vertex_uvs = [v for (i, v) in enumerate(self.vertex_uvs) if i not in orphans]
        for removed_index in orphans[::-1]:
            for j, p in enumerate(self.polygons):
                self.polygons[j] = [idx if idx <= removed_index else idx - 1 for idx in p]


# Mesh with one single texture
class SubMesh(BaseMesh):
    def __init__(self):
        super().__init__()
        self.texture_id = None

    def to_obj(self, face_index_increment, mtllib=None, pivot_offset=None) -> Tuple[str, int]:
        if pivot_offset is None:
            pivot_offset = self.pivot_offset
        res = f'\n\no {self.name}'
        if mtllib is not None:
            res += f'\nmtllib {mtllib}'
        res += '\n' + '\n'.join(['v ' + ' '.join(
            [str(coordinates[i] - pivot_offset[i]) for i in range(3)]
        ) for coordinates in self.vertices])
        res += '\n' + '\n'.join([f'vt {uv[0]} {1 - uv[1]}' for uv in self.vertex_uvs])
        if self.texture_id:
            res += '\nusemtl ' + self.texture_id
        res += '\n' + '\n'.join(
            ['f ' + ' '.join([f'{x + face_index_increment}/{x + face_index_increment}' for x in polygon]) for polygon in
             self.polygons])
        return res, len(self.vertices)


# Mesh with multiple textures
class Mesh(BaseMesh):
    def __init__(self):
        super().__init__()
        self.texture_ids = []

    # splits mesh to few single-texture meshes. Returns list of tuples: ( mesh, vertex index map, polygon index map )
    def split_by_texture_ids(self) -> List[Tuple[SubMesh, List[int], List[int]]]:
        texture_ids = list({x for x in self.texture_ids})
        texture_ids.sort()
        if len(texture_ids) == 1:
            sm = SubMesh()
            sm.name = self.name
            sm.pivot_offset = self.pivot_offset
            sm.texture_id = texture_ids[0]
            sm.vertices = self.vertices
            sm.vertex_uvs = self.vertex_uvs
            sm.polygons = self.polygons
            return [(sm, list(range(len(self.vertices))), list(range(len(self.polygons))))]
        res = []
        for texture_id in texture_ids:
            sm = SubMesh()
            sm.name = (self.name or 'None') + '__' + (texture_id or 'None')
            sm.pivot_offset = self.pivot_offset
            sm.texture_id = texture_id
            vertex_indices = []
            polygon_indices = []
            for i, p in enumerate(self.polygons):
                if self.texture_ids[i] != texture_id:
                    continue
                polygon_indices.append(i)
                new_polygon = []
                for idx in p:
                    try:
                        new_idx = vertex_indices.index(idx)
                    except ValueError:
                        new_idx = len(vertex_indices)
                        vertex_indices.append(idx)
                    new_polygon.append(new_idx)
                sm.polygons.append(new_polygon)
            for v_idx in vertex_indices:
                sm.vertices.append(self.vertices[v_idx])
                sm.vertex_uvs.append(self.vertex_uvs[v_idx])
            res.append((sm, vertex_indices, polygon_indices))
        return res

    def to_obj(self, face_index_increment, mtllib=None, pivot_offset=None) -> Tuple[str, int]:
        sub_meshes = self.split_by_texture_ids()
        if len(sub_meshes) == 1:
            return sub_meshes[0][0].to_obj(face_index_increment, mtllib, pivot_offset)
        obj_texts = []
        for (sub_model, _, _) in sub_meshes:
            obj, fii = sub_model.to_obj(face_index_increment, mtllib, pivot_offset)
            obj_texts.append(obj)
            face_index_increment += fii
        return '\n\n'.join(obj_texts), face_index_increment


class Scene:
    sub_meshes: List[SubMesh] = []
    name: str = 'scene'
    obj_name: str = 'geometry'
    mtl_name: str = 'material'
    external_mtl: bool = False
    mtl_texture_names: List[str] = []
    mtl_texture_path_func: Callable[[str], str] = lambda x: x
    dummies = []


# TODO support existing map export logic here and use it
def export_scenes(scenes: List[Scene], output_path: str, settings):
    mtl_entry_template = Template("""
    
newmtl $texture_name
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd $texture_path""")

    import_template = Template("""
import json
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="$obj_file_path", axis_forward='Y', axis_up='Z')

dummies = json.loads('$dummies') or []
for dummy in dummies:
    o = bpy.data.objects.new( dummy['name'], None )
    bpy.context.scene.collection.objects.link(o)
    o.location = dummy.get('position', [0, 0, 0])
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Euler(tuple(dummy.get('rotation', [0, 0, 0])), 'XYZ').to_quaternion()
    dummy_props = dummy.get('properties', {})
    for key, value in dummy_props.items():
        o[key] = value

curves = json.loads('$curves') or []
for curve in curves:
    curveData = bpy.data.curves.new(curve['name'], type='CURVE')
    curveData.dimensions = '3D'
    curveData.resolution_u = 2
    polyline = curveData.splines.new('POLY')
    polyline.points.add(len(curve['points']) - 1)
    for i, [x,y,z] in enumerate(curve['points']):
        polyline.points[i].co = (x, y, z, 1)
    polyline.use_cyclic_u = curve.get('closed', False)
    curveOB = bpy.data.objects.new(curve['name'], curveData)
    bpy.context.collection.objects.link(curveOB)
    curve_props = curve.get('properties', {})
    for (key, value) in curve_props.items():
        curveOB[key] = value
    """)

    for scene in scenes:
        with open(os.path.join(output_path, f'{scene.obj_name}.obj'), 'w') as f:
            if scene.mtl_name:
                f.write(f'mtllib {scene.mtl_name}.mtl')
            face_index_increment = 1
            for sub_model in scene.sub_meshes:
                obj, fii = sub_model.to_obj(face_index_increment)
                f.write(obj)
                face_index_increment += fii
        if scene.mtl_name and not scene.external_mtl:
            with open(os.path.join(output_path, f'{scene.mtl_name}.mtl'), 'w') as f:
                for texture_name in scene.mtl_texture_names:
                    f.write(mtl_entry_template.substitute({
                        'texture_name': texture_name,
                        'texture_path': scene.mtl_texture_path_func(texture_name),
                    }))

    if settings.geometry__export_to_gg_web_engine or settings.geometry__save_blend:
        script = ''
        for scene in scenes:
            script += '\n\n' + import_template.substitute({
                'obj_file_path': f'{scene.obj_name}.obj',
                'dummies': json.dumps(scene.dummies),
                'curves': json.dumps([]),
            })
            if settings.geometry__export_to_gg_web_engine:
                from serializers.misc.build_blender_scene import construct_blender_export_script
                script += '\n' + construct_blender_export_script(
                    file_name=os.path.join(os.getcwd(), output_path, scene.name),
                    export_materials='EXPORT')
            if settings.geometry__save_blend:
                script += '\n\n' + get_blender_save_script(
                    out_blend_name=os.path.join(os.getcwd(), output_path, scene.name))
        run_blender(path=output_path, script=script)

    if not settings.geometry__save_obj:
        for scene in scenes:
            os.unlink(os.path.join(output_path, scene.obj_name + '.obj'))
            if scene.mtl_name and not scene.external_mtl:
                os.unlink(os.path.join(output_path, scene.mtl_name + '.mtl'))
