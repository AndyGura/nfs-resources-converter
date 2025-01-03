import json
import os
from collections import defaultdict
from os.path import join
from string import Template

from library.exceptions import DataIntegrityException
from library.utils.blender_scripts import run_blender
from library.utils.meshes import SubMesh, Mesh
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import AnyBitmapBlock
from serializers import BaseFileSerializer


class ObjExporter:
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

    def handle_obj(self, settings, path, obj_name='geometry.obj', mtl_name='material.mtl', dummies=None):
        if dummies is None:
            dummies = []
        script = self.blender_script.substitute({'obj_file_path': obj_name,
                                                 'dummies': json.dumps(dummies)})
        if settings.geometry__export_to_gg_web_engine:
            from serializers.misc.build_blender_scene import construct_blender_export_script
            script += '\n' + construct_blender_export_script(
                file_name=os.path.join(os.getcwd(), path, 'body'),
                export_materials='EXPORT')
        # skip running blender if it does not save anything
        if settings.geometry__export_to_gg_web_engine or settings.geometry__save_blend:
            run_blender(path=path,
                        script=script,
                        out_blend_name=os.path.join(os.getcwd(), path, 'body')
                        if settings.geometry__save_blend
                        else None)
        if not settings.geometry__save_obj:
            os.unlink(os.path.join(path, mtl_name))
            os.unlink(os.path.join(path, obj_name))


class OripGeometrySerializer(BaseFileSerializer):
    default_uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]

    def __init__(self):
        super().__init__(is_dir=True)

    def _setup_vertex(self,
                      model: SubMesh,
                      block_data,
                      vertices_file_indices_map,
                      index_3D,
                      index_2D,
                      index_in_polygon,
                      textures_shpi_data):
        try:
            return vertices_file_indices_map[model][index_3D]
        except KeyError:
            pass
        # new vertex creation
        vertex = block_data['vertices'][block_data['vmap'][index_3D]]['data']
        model.vertices.append([vertex['x'], vertex['y'], vertex['z']])
        vertices_file_indices_map[model][index_3D] = len(model.vertices) - 1
        # setup texture coordinate
        if index_2D is None:
            model.vertex_uvs.append([self.default_uvs[index_in_polygon][0],
                                     self.default_uvs[index_in_polygon][1]])
        else:
            u_multiplier, v_multiplier = 1, 1
            if model.texture_id:
                try:
                    idx = textures_shpi_data['children_aliases'].index(model.texture_id)
                    u_multiplier, v_multiplier = (1 / textures_shpi_data['children'][idx]['data']['width'],
                                                  1 / textures_shpi_data['children'][idx]['data']['height'])

                except ValueError:
                    pass
            model.vertex_uvs.append([block_data['vertex_uvs'][block_data['vmap'][index_2D]]['u'] * u_multiplier,
                                     block_data['vertex_uvs'][block_data['vmap'][index_2D]]['v'] * v_multiplier])
        return vertices_file_indices_map[model][index_3D]

    def require_shpi(self, id):
        # shpi is always next block
        from library import require_resource
        shpi_id = id.split('/')
        shpi_id[-2] = str(int(shpi_id[-2]) + 1)
        (shpi_id, textures_shpi_block, textures_shpi_data), _ = require_resource('/'.join(shpi_id))
        if not textures_shpi_data or not isinstance(textures_shpi_block, ShpiBlock):
            raise DataIntegrityException('Cannot find SHPI archive for ORIP geometry')
        return (shpi_id, textures_shpi_block, textures_shpi_data)

    def build_mesh(self, data: dict, id=None):
        (shpi_id, textures_shpi_block, textures_shpi_data) = self.require_shpi(id)
        vertices_file_indices_map = defaultdict(lambda: dict())
        sub_models = defaultdict(SubMesh)

        for pi, polygon in enumerate(data['polygons']):
            polygon_type = polygon['polygon_type']
            mapping = polygon['mapping']
            texture_id = data['tex_ids'][polygon['texture_index']]['file_name']
            label = ([x['name'] for x in filter(lambda y: y['index'] == pi, data['labels'])] or [None])[0]
            fx_name = ([x['name'] for x in filter(lambda y: y['index'] == pi, data['fx_polys'])] or [None])[0]
            sub_model_parts = []
            if label:
                sub_model_parts.append('lbl__' + label)
            if fx_name:
                sub_model_parts.append('fx__' + fx_name)
            if texture_id:
                sub_model_parts.append(texture_id)
            sub_model_id = '__'.join(sub_model_parts)
            sub_model = sub_models[sub_model_id]
            if not sub_model.name:
                sub_model.name = sub_model_id
                sub_model.texture_id = texture_id
            offset_3D = polygon['offset_3d']
            offset_2D = polygon['offset_2d']

            def _setup_polygon(offsets):
                sub_model.polygons.append([self._setup_vertex(sub_model,
                                                              data,
                                                              vertices_file_indices_map,
                                                              offset_3D + offset,
                                                              (offset_2D + offset) if mapping['use_uv'] else None,
                                                              offset,
                                                              textures_shpi_data)
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
        # not sure why, but seems like Z should be inverted in all geometries
        for sub_model in sub_models.values():
            sub_model.change_axes(new_z='y', new_y='z')
        return shpi_id, textures_shpi_block, textures_shpi_data, sub_models

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        shpi_id, textures_shpi_block, textures_shpi_data, sub_models = self.build_mesh(data, id)
        with open(os.path.join(path, 'geometry.obj'), 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for sub_model in sub_models.values():
                obj, fii = sub_model.to_obj(face_index_increment)
                f.write(obj)
                face_index_increment += fii
        with open(os.path.join(path, 'material.mtl'), 'w') as f:
            for i, texture_name in enumerate(textures_shpi_data['children_aliases']):
                texture_block = textures_shpi_block.field_blocks_map['children'].child.possible_blocks[
                    textures_shpi_data['children'][i]['choice_index']]
                if not isinstance(texture_block, AnyBitmapBlock):
                    continue
                f.write(f"""\n\nnewmtl {texture_name}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd assets/{texture_name}.png""")
        from serializers import ShpiArchiveSerializer
        shpi_serializer = ShpiArchiveSerializer()
        shpi_serializer.serialize(textures_shpi_data, os.path.join(path, 'assets/'), shpi_id, textures_shpi_block)
        ObjExporter().handle_obj(settings=self.settings, path=path)


class GeoGeometrySerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        from library import require_resource
        if 'CARDATA.VIV' in id:
            # NFS2 SE
            local_id = id[id.index('__children/') + 11:]
            idx = int(local_id[:local_id.index('/')])
            (_, _, viv_data), _ = require_resource(id[:id.find('__children')])
            qfs_name = viv_data['children_aliases'][idx].upper()
            qfs_id = join(id[:id.find('CARDATA.VIV')], f'../../CARMODEL/PC/{qfs_name[:-4]}.QFS')
        else:
            # NFS2
            qfs_id = id[:-4] + '.QFS'
        (shpi_id, textures_shpi_block, textures_shpi_data), _ = require_resource(qfs_id)
        # unwrap QFS
        shpi_id += '__data'
        (textures_shpi_block, textures_shpi_data) = textures_shpi_block.get_child_block_with_data(textures_shpi_data,
                                                                                                  'data')
        if not textures_shpi_data or not isinstance(textures_shpi_block, ShpiBlock):
            raise DataIntegrityException('Cannot find QFS archive for GEO geometry')
        super().serialize(data, path)
        meshes = []
        for key, part in data.items():
            if not key.startswith('part') or not part['num_plgn']:
                continue
            mesh = Mesh()
            mesh.name = key
            mesh.vertices = [[v['x'], v['y'], v['z']] for v in part['vertices']]
            mesh.vertex_uvs = [[0, 0] for _ in range(len(mesh.vertices))]
            mesh.polygons = [p['vertex_indices']
                             if p['mapping']['flip_normal']
                             else p['vertex_indices'][::-1]
                             for p in part['polygons']]
            mesh.texture_ids = [p['texture_name'] for p in part['polygons']]
            mesh.pivot_offset = (-part['pos']['x'], -part['pos']['y'], -part['pos']['z'])

            sub_meshes = mesh.split_by_texture_ids()
            for submesh, _, polygon_idx_map in sub_meshes:
                double_side_polygons = []
                for i, polygon in enumerate(submesh.polygons):
                    p_part = part['polygons'][polygon_idx_map[i]]
                    if p_part['mapping']['is_triangle']:
                        if p_part['mapping']['uv_flip']:
                            uvs = [[0, 0], [1, 0], [1, 1], [1, 1]]
                        else:
                            uvs = [[0, 1], [1, 1], [1, 0], [1, 0]]
                    else:
                        if p_part['mapping']['uv_flip']:
                            uvs = [[0, 1], [1, 1], [1, 0], [0, 0]]
                        else:
                            uvs = [[0, 0], [1, 0], [1, 1], [0, 1]]
                    # flip normal flag does not change uv-s, it's required for our exported obj, because in order to
                    # achieve negated normal, we inverted list of vertex indices in the polygon
                    if not p_part['mapping']['flip_normal']:
                        uvs = uvs[::-1]
                    for i, vi in enumerate(polygon):
                        submesh.vertex_uvs[vi] = uvs[i]
                    if p_part['mapping']['double_sided']:
                        double_side_polygons.append(polygon[::-1])
                submesh.polygons.extend(double_side_polygons)
                meshes.append(submesh)
        for mesh in meshes:
            mesh.change_axes(new_z='y', new_y='z')
            px, py, pz = mesh.pivot_offset
            mesh.pivot_offset = (px, pz, py)
        with open(os.path.join(path, 'geometry.obj'), 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for mesh in meshes:
                obj, fii = mesh.to_obj(face_index_increment)
                f.write(obj)
                face_index_increment += fii
        with open(os.path.join(path, 'material.mtl'), 'w') as f:
            for i, texture_name in enumerate(textures_shpi_data['children_aliases']):
                texture_block = textures_shpi_block.field_blocks_map['children'].child.possible_blocks[
                    textures_shpi_data['children'][i]['choice_index']]
                if not isinstance(texture_block, AnyBitmapBlock):
                    continue
                f.write(f"""\n\nnewmtl {texture_name}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd assets/{texture_name}.png""")
        from serializers import ShpiArchiveSerializer
        shpi_serializer = ShpiArchiveSerializer()
        shpi_serializer.serialize(textures_shpi_data, os.path.join(path, 'assets/'), shpi_id, textures_shpi_block)
        ObjExporter().handle_obj(settings=self.settings, path=path)
