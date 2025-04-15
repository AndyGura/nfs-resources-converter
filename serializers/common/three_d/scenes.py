import json
import os
from string import Template
from typing import Callable
from typing import List

from library.utils import path_join
from .blender_scripts import get_blender_save_script, run_blender
from .build_blender_scene import construct_blender_export_script
from .mesh import SubMesh


class Scene:
    def __init__(self,
                 name: str = 'scene',
                 sub_meshes: List[SubMesh] = None,
                 obj_name: str = 'geometry',
                 mtl_name: str = 'material',
                 bake_textures: bool = True,
                 mtl_texture_names: List[str] = None,
                 mtl_texture_path_func: Callable[[str], str] = lambda x: x,
                 dummies: List[dict] = None,
                 curves: List[dict] = None,
                 extra_script: str = None,
                 skip_obj_export: bool = False,
                 skip_mtl_export: bool = False):
        self.name = name
        self.sub_meshes = sub_meshes or []
        self.obj_name = obj_name
        self.mtl_name = mtl_name
        self.bake_textures = bake_textures
        self.mtl_texture_names = mtl_texture_names or []
        self.mtl_texture_path_func = mtl_texture_path_func
        self.dummies = dummies or []
        self.curves = curves or []
        self.extra_script = extra_script or ""
        self.skip_obj_export = skip_obj_export
        self.skip_mtl_export = skip_mtl_export


def export_scenes(scenes: List[Scene], output_path: str, settings):
    mtl_entry_template = Template("""

newmtl $texture_name
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd $texture_path""")

    script_base = """
import json
from mathutils import Euler

def load_obj_extra(path):
    try:
        with open(path) as f:
            extras = json.load(f)
            for dummy in extras.get('dummies', []):
                o = bpy.data.objects.new( dummy['name'], None )
                bpy.context.scene.collection.objects.link(o)
                o.location = dummy.get('position', [0, 0, 0])
                o.rotation_mode = 'QUATERNION'
                o.rotation_quaternion = Euler(tuple(dummy.get('rotation', [0, 0, 0])), 'XYZ').to_quaternion()
                dummy_props = dummy.get('properties', {})
                for key, value in dummy_props.items():
                    o[key] = value
            
            for curve in extras.get('curves', []):
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
    except FileNotFoundError:
        pass

    """

    import_template = Template("""
bpy.ops.wm.read_factory_settings(use_empty=True)
if "$obj_file_path":
    bpy.ops.wm.obj_import(filepath="$obj_file_path", forward_axis='Y', up_axis='Z')
if "$extras_file_path":
    load_obj_extra("$extras_file_path")
        
$extra_script
    """)

    for scene in scenes:
        if not scene.skip_obj_export:
            with open(path_join(output_path, f'{scene.obj_name}.obj'), 'w') as f:
                if scene.mtl_name:
                    f.write(f'mtllib {scene.mtl_name}.mtl')
                face_index_increment = 1
                for sub_model in scene.sub_meshes:
                    obj, fii = sub_model.to_obj(face_index_increment)
                    f.write(obj)
                    face_index_increment += fii
        if scene.dummies or scene.curves:
            with open(path_join(output_path, f'{scene.obj_name}_extra.json'), 'w') as f:
                f.write(json.dumps({
                    'dummies': scene.dummies,
                    'curves': scene.curves
                }, indent=4, sort_keys=True))
        if scene.mtl_name and not scene.skip_mtl_export:
            with open(path_join(output_path, f'{scene.mtl_name}.mtl'), 'w') as f:
                for texture_name in sorted(list({x for x in scene.mtl_texture_names})):
                    f.write(mtl_entry_template.substitute({
                        'texture_name': texture_name,
                        'texture_path': scene.mtl_texture_path_func(texture_name),
                    }))

    if settings.geometry__export_to_gg_web_engine or settings.geometry__save_blend:
        script = script_base
        for scene in scenes:
            script += '\n\n' + import_template.substitute({
                'obj_file_path': f'{scene.obj_name}.obj' if not scene.skip_obj_export else '',
                'extras_file_path': f'{scene.obj_name}_extra.json',
                'extra_script': scene.extra_script,
            })
            if settings.geometry__export_to_gg_web_engine:
                script += '\n' + construct_blender_export_script(
                    file_name=path_join(os.getcwd(), output_path, scene.name),
                    export_materials='EXPORT' if scene.bake_textures else 'NONE')
            if settings.geometry__save_blend:
                script += '\n\n' + get_blender_save_script(
                    out_blend_name=path_join(os.getcwd(), output_path, scene.name))
        run_blender(path=output_path, script=script)

    if not settings.geometry__save_obj:
        for scene in scenes:
            if not scene.skip_obj_export:
                os.unlink(path_join(output_path, scene.obj_name + '.obj'))
            try:
                os.unlink(path_join(output_path, scene.obj_name + '_extra.json'))
            except:
                pass
            if scene.mtl_name and not scene.skip_mtl_export:
                os.unlink(path_join(output_path, scene.mtl_name + '.mtl'))
