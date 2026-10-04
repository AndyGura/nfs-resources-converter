import os
import re
from collections import defaultdict
from configparser import ConfigParser
from typing import List, Tuple, Dict, Optional

from PIL import Image

from library.exceptions import DataIntegrityException
from library.utils import path_join
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import EacImage
from serializers import BaseFileSerializer
from serializers.common.three_d import SubMesh, Mesh, export_scenes, Scene


class OripGeometrySerializer(BaseFileSerializer):
    default_uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]

    def __init__(self):
        super().__init__(is_dir=True)

    def _setup_vertex(
        self,
        model: SubMesh,
        block_data,
        vertices_file_indices_map,
        index_3D,
        index_2D,
        index_in_polygon,
        textures_shpi_data,
    ):
        try:
            return vertices_file_indices_map[model][index_3D]
        except KeyError:
            pass
        # new vertex creation
        vertex = block_data['vertices']['data'][block_data['vmap'][index_3D]]
        model.vertices.append([vertex['x'], vertex['y'], vertex['z']])
        vertices_file_indices_map[model][index_3D] = len(model.vertices) - 1
        # setup texture coordinate
        if index_2D is None:
            model.vertex_uvs.append([self.default_uvs[index_in_polygon][0], self.default_uvs[index_in_polygon][1]])
        else:
            u_multiplier, v_multiplier = 1, 1
            if model.texture_id:
                try:
                    c = next(x for x in textures_shpi_data['children'] if x['alias'] == model.texture_id)
                    u_multiplier, v_multiplier = (1 / c['item']['data']['width'], 1 / c['item']['data']['height'])

                except StopIteration, ValueError:
                    pass
                except TypeError:
                    print()
            model.vertex_uvs.append(
                [
                    block_data['vertex_uvs'][block_data['vmap'][index_2D]]['u'] * u_multiplier,
                    block_data['vertex_uvs'][block_data['vmap'][index_2D]]['v'] * v_multiplier,
                ]
            )
        return vertices_file_indices_map[model][index_3D]

    def require_shpi(self, id):
        # shpi is always next block
        from library import require_resource

        shpi_id = id.split('/')
        shpi_id[-3] = str(int(shpi_id[-3]) + 1)
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
                sub_model.polygons.append(
                    [
                        self._setup_vertex(
                            sub_model,
                            data,
                            vertices_file_indices_map,
                            offset_3D + offset,
                            (offset_2D + offset) if mapping['use_uv'] else None,
                            offset,
                            textures_shpi_data,
                        )
                        for offset in offsets
                    ]
                )

            if (polygon_type & (0xFF >> 5)) == 3:
                # triangle
                if mapping['two_sided'] or not mapping['flip_normal']:
                    _setup_polygon([0, 1, 2])
                if mapping['two_sided'] or mapping['flip_normal']:
                    _setup_polygon([0, 2, 1])
            elif (polygon_type & (0xFF >> 5)) == 4:
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

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        shpi_id, textures_shpi_block, textures_shpi_data, sub_models = self.build_mesh(data, id)

        scene = Scene()
        scene.sub_meshes = [sm for sm in sub_models.values()]
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.mtl_name = 'material'
        for c in textures_shpi_data['children']:
            texture_block = (
                textures_shpi_block.field_blocks_map['children']
                .child.field_blocks_map['item']
                .possible_blocks[c['item']['choice_index']]
            )
            if isinstance(texture_block, EacImage):
                scene.mtl_texture_names.append(c['alias'])
        scene.mtl_texture_path_func = lambda name: f'assets/{name}.png'

        from serializers import ShpiArchiveSerializer

        ShpiArchiveSerializer().serialize(textures_shpi_data, path_join(path, 'assets/'), shpi_id, textures_shpi_block)
        return export_scenes([scene], path, self.settings)


class GeoGeometrySerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        from library import require_resource

        if 'CARDATA.VIV' in id:
            # NFS2 SE
            local_id = id[id.index('__children/') + 11 :]
            idx = int(local_id[: local_id.index('/')])
            (_, _, viv_data), _ = require_resource(id[: id.find('__children')])
            qfs_name = viv_data['children'][idx]['alias'].upper()
            qfs_id = path_join(id[: id.find('CARDATA.VIV')], f'../../CARMODEL/PC/{qfs_name[:-4]}.QFS')
        else:
            # NFS2
            qfs_id = id[:-4] + '.QFS'
        (shpi_id, textures_shpi_block, textures_shpi_data), _ = require_resource(qfs_id)
        # unwrap QFS
        shpi_id += '__data'
        (textures_shpi_block, textures_shpi_data) = textures_shpi_block.get_child_block_with_data(
            textures_shpi_data, 'data'
        )
        if not textures_shpi_data or not isinstance(textures_shpi_block, ShpiBlock):
            raise DataIntegrityException('Cannot find QFS archive for GEO geometry')
        super().serialize(data, path)
        meshes = []
        for i, part in enumerate(data['parts']):
            if i < 20:
                key = f'part_hp_{i}'
            elif i < 23:
                key = f'part_mp_{i - 20}'
            elif i < 26:
                key = f'part_lp_{i - 23}'
            else:
                key = f'part_res_{i - 26}'
            mesh = Mesh()
            mesh.name = key
            mesh.vertices = [[v['x'], v['y'], v['z']] for v in part['vertices']]
            mesh.vertex_uvs = [[0, 0] for _ in range(len(mesh.vertices))]
            mesh.polygons = [
                p['vertex_indices'] if p['mapping']['flip_normal'] else p['vertex_indices'][::-1]
                for p in part['polygons']
            ]
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

        scene = Scene()
        scene.sub_meshes = meshes
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.mtl_name = 'material'
        for c in textures_shpi_data['children']:
            texture_block = (
                textures_shpi_block.field_blocks_map['children']
                .child.field_blocks_map['item']
                .possible_blocks[c['item']['choice_index']]
            )
            if isinstance(texture_block, EacImage):
                scene.mtl_texture_names.append(c['alias'])
        scene.mtl_texture_path_func = lambda name: f'assets/{name}.png'

        from serializers import ShpiArchiveSerializer

        ShpiArchiveSerializer().serialize(textures_shpi_data, path_join(path, 'assets/'), shpi_id, textures_shpi_block)
        return export_scenes([scene], path, self.settings)


def _read_12_bit_signed(value: int) -> int:
    value &= 0xFFF
    return value - 0x1000 if value & 0x800 else value


def crp_image_atlas_position(image: dict) -> Tuple[int, int]:
    """Position of an NFS5 FSH image inside its texture page: 12-bit signed x and y, packed into the low bits of
    `EacImage.position` (high 4 bits of each coordinate are flags)"""
    return _read_12_bit_signed(image['position']['x']), _read_12_bit_signed(image['position']['y'])


def compose_texture_page(images: List[Tuple[Image.Image, int, int]], width: int = None, height: int = None):
    """Composes images into one texture page. Images are given as (image, x, y). When images overlap (alternate
    versions of the same texture, like "top" and "top1"), the first one wins. If page size is not provided, it is
    the bounding box of all images, rounded up to a power of two"""

    def pow2(x):
        return 1 << max(0, int(x) - 1).bit_length()

    if width is None:
        width = pow2(max([x + img.width for img, x, _ in images] + [1]))
    if height is None:
        height = pow2(max([y + img.height for img, _, y in images] + [1]))
    page = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for img, x, y in reversed(images):
        page.paste(img, (x, y))
    return page


def crp_car_texture_page_sources(fsh_indices: List[int], tpg: ConfigParser = None) -> Dict[int, int]:
    """Maps texture page index (MaterialPartData.tex_page_index) to the index of the FSH part, which content is
    drawn on that page. Uses car's .tpg file if available. Without it, uses the layout all NFS5 cars share:
    FSH part N is file N+1 of .tpg, pages are: exterior (file 1), exterior copy, interior (file 2), extint (file 3),
    glass (file 4), ..., price (file 8). Pages of remaining files (shadow, cabrio, driver suit/head...) are
    taken from global game files, which are not part of the car"""
    res = {}
    if tpg is None:
        for fsh_idx in fsh_indices:
            res[0 if fsh_idx == 0 else fsh_idx + 1] = fsh_idx
        if 0 in res:
            res[1] = res[0]
        return res
    for fsh_idx in fsh_indices:
        section = f'file{fsh_idx + 1}.details'
        if tpg.has_option(section, 'tpage'):
            res[tpg.getint(section, 'tpage') - 1] = fsh_idx
    for section in tpg.sections():
        match = re.fullmatch(r'tpage(\d+)\.details', section)
        if match and tpg.has_option(section, 'sourcetpage'):
            source_page = tpg.getint(section, 'sourcetpage') - 1
            if source_page in res:
                res[int(match.group(1)) - 1] = res[source_page]
    return res


def _find_sibling_file(file_path: str, file_name: str) -> Optional[str]:
    directory = os.path.dirname(file_path) or '.'
    try:
        return next(path_join(directory, x) for x in os.listdir(directory) if x.lower() == file_name.lower())
    except StopIteration, FileNotFoundError:
        return None


def _crp_texture_tag(value: int) -> str:
    return value.to_bytes(4, 'little').decode('latin-1')


class CrpGeometrySerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def _load_car_textures(self, data, path, id, block) -> Dict[int, str]:
        """Exports textures from FSH parts and composes texture pages. Returns texture page index -> name of
        exported page texture"""
        from library.loader import id_to_path
        from serializers import ShpiArchiveSerializer, ImageSerializer

        misc_choice = block.field_blocks_map['common_parts'].child
        fsh_choice_index = misc_choice.get_choice_index_by_class_name('FSHPart')
        shpi_block = ShpiBlock()
        fsh_pages = {}
        for i, x in enumerate(data['common_parts']):
            if x['choice_index'] != fsh_choice_index:
                continue
            fsh_part = x['data']
            assert fsh_part['num_data'] == 1
            fsh_data = fsh_part['data'][0]
            fsh_data_id = join_id(id, 'common_parts', str(i), 'data', 'data', '0')
            ShpiArchiveSerializer().serialize(
                fsh_data, path_join(path, f'textures/{fsh_part["idx"]}/'), fsh_data_id, shpi_block
            )
            images = []
            for child in fsh_data['children']:
                item_block = shpi_block.item_block.possible_blocks[child['item']['choice_index']]
                if not isinstance(item_block, EacImage):
                    continue
                image = ImageSerializer().to_image(
                    child['item']['data'],
                    item_block,
                    join_id(fsh_data_id, 'children', child['alias'], 'item', 'data'),
                )
                images.append((image, *crp_image_atlas_position(child['item']['data'])))
            fsh_pages[fsh_part['idx']] = images

        tpg = None
        if id:
            tpg_path = _find_sibling_file(
                id_to_path(id), os.path.splitext(os.path.basename(id_to_path(id)))[0] + '.tpg'
            )
            if tpg_path:
                tpg = ConfigParser(strict=False)
                try:
                    tpg.read(tpg_path)
                except Exception:
                    tpg = None

        textures = {}
        for page_idx, fsh_idx in crp_car_texture_page_sources(list(fsh_pages.keys()), tpg).items():
            width = height = None
            section = f'tpage{page_idx + 1}.details'
            if tpg is not None and tpg.has_option(section, 'width') and tpg.has_option(section, 'height'):
                width, height = tpg.getint(section, 'width'), tpg.getint(section, 'height')
            name = f'page_{page_idx}'
            compose_texture_page(fsh_pages[fsh_idx], width, height).save(path_join(path, f'textures/{name}.png'))
            textures[page_idx] = name
        return textures

    def _load_track_textures(self, data, path, id, block, tags) -> Dict[int, str]:
        """Exports textures, referenced by materials, from FSH file(s) next to the track CRP. Returns material
        texture tag (as integer) -> name of exported texture"""
        from library import require_resource
        from library.loader import id_to_path
        from serializers import ImageSerializer

        if not id:
            return {}
        misc_choice = block.field_blocks_map['common_parts'].child
        text_choice_index = misc_choice.get_choice_index_by_class_name('TextPart2')
        fsh_names = [x['data']['data'] for x in data['common_parts'] if x['choice_index'] == text_choice_index]
        images = {}
        for fsh_name in fsh_names:
            fsh_path = _find_sibling_file(id_to_path(id), fsh_name)
            if not fsh_path:
                continue
            (fsh_id, shpi_block, shpi_data), _ = require_resource(fsh_path)
            # unwrap compressed file
            while not isinstance(shpi_block, ShpiBlock) and isinstance(shpi_data, dict) and 'choice_index' in shpi_data:
                (fsh_id, shpi_block, shpi_data), _ = require_resource(join_id(fsh_id, 'data'))
            if not isinstance(shpi_block, ShpiBlock):
                continue
            for child in shpi_data['children']:
                item_block = shpi_block.item_block.possible_blocks[child['item']['choice_index']]
                if isinstance(item_block, EacImage) and child['alias'] not in images:
                    images[child['alias']] = (
                        child['item']['data'],
                        item_block,
                        join_id(fsh_id, 'children', child['alias'], 'item', 'data'),
                    )
        textures = {}
        used_names = set()
        for tag in tags:
            alias = _crp_texture_tag(tag)
            if alias not in images:
                continue
            name = re.sub(r'[^0-9A-Za-z_-]', '_', alias.strip()) or 'texture'
            while name in used_names:
                name += '_'
            used_names.add(name)
            image_data, image_block, image_id = images[alias]
            ImageSerializer().to_image(image_data, image_block, image_id).save(path_join(path, f'textures/{name}.png'))
            textures[tag] = name
        return textures

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        os.makedirs(path_join(path, 'textures'), exist_ok=True)

        misc_choice = block.field_blocks_map['common_parts'].child
        material_choice_index = misc_choice.get_choice_index_by_class_name('MaterialPart')
        materials = {
            x['data']['idx']: x['data']['data']
            for x in data['common_parts']
            if x['choice_index'] == material_choice_index
        }
        if data['resource_id'] == 'karT':
            textures = self._load_track_textures(
                data, path, id, block, {m['tex_page_index'] for m in materials.values()}
            )
        else:
            textures = self._load_car_textures(data, path, id, block)

        def material_texture(material_index):
            material = materials.get(material_index)
            return textures.get(material['tex_page_index']) if material else None

        scene = Scene()
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.sub_meshes = []
        scene.mtl_texture_names = list(textures.values())
        scene.mtl_texture_path_func = lambda name: f'textures/{name}.png'

        # Identify choice indexes for part types
        choice = block.field_blocks_map['parts'].child
        vertex_choice_index = choice.get_choice_index_by_class_name('VertexPart')
        uv_choice_index = choice.get_choice_index_by_class_name('UVPart')
        triangle_choice_index = choice.get_choice_index_by_class_name('TrianglePart')
        transform_choice_index = choice.get_choice_index_by_class_name('TransformationPart')
        name_choice_index = choice.get_choice_index_by_class_name('TextPart4')
        triangle_data_block = choice.possible_blocks[triangle_choice_index].field_blocks_map['data']
        info_row_block = triangle_data_block.field_blocks_map['info_rows'].child
        uv_info_row_choice_index = info_row_block.get_choice_index_by_class_name('UVInfoRow')
        vertex_info_row_choice_index = info_row_block.get_choice_index_by_class_name('VertexInfoRow')

        def extract_vertices(part):
            return [[v['position']['x'], v['position']['y'], v['position']['z']] for v in part['data']]

        def extract_triangle_corners(part):
            """Returns list of (vertex index, uv index) for every triangle corner of the triangle part"""
            index_rows = {x['identifier']: x['offset'] for x in part['data']['index_rows']}
            if 'vI' not in index_rows:
                return []
            info_rows = {x['choice_index']: x['data'] for x in part['data']['info_rows']}
            vertex_offset = (
                info_rows[vertex_info_row_choice_index]['offset'] // 16
                if vertex_info_row_choice_index in info_rows
                else 0
            )
            uv_offset = (
                info_rows[uv_info_row_choice_index]['offset'] // 8 if uv_info_row_choice_index in info_rows else 0
            )
            start = index_rows['vI']
            num_data = part['num_data']
            indices = part['data']['index_table'][start : start + num_data]
            uv_indices = part['data']['uv_index_table'][start : start + num_data]
            corners = [(vi + vertex_offset, uvi + uv_offset) for vi, uvi in zip(indices, uv_indices)]
            return corners[: len(corners) - len(corners) % 3]

        for i, article in enumerate(data['articles']):
            names = [x['data'] for x in article['parts'] if x['choice_index'] == name_choice_index]
            if len(names) == 0:
                name = 'article_' + str(i)
            else:
                assert len(names) == 1, f'Inconsistent name parts amount found for part {i}'
                name = names[0]['data']

            v = [x['data'] for x in article['parts'] if x['choice_index'] == vertex_choice_index]
            uv = [x['data'] for x in article['parts'] if x['choice_index'] == uv_choice_index]
            tri = [x['data'] for x in article['parts'] if x['choice_index'] == triangle_choice_index]
            t = [x['data'] for x in article['parts'] if x['choice_index'] == transform_choice_index]

            for vx in v:
                lod_level = vx['part_info']['lod']
                try:
                    transform_matrix = next(x for x in t if x['part_info']['lod'] == lod_level)['data']
                except StopIteration:
                    transform_matrix = None

                mesh_name = f'{name}_LOD{lod_level}_ai{vx["part_info"]["animation_index"]}'
                vertices = extract_vertices(vx)
                if vx['part_info']['damage'] == 8:
                    fix_vertex_pos = next(
                        x
                        for x in v
                        if x['part_info']['lod'] == vx['part_info']['lod']
                        and x['part_info']['animation_index'] == vx['part_info']['animation_index']
                        and x['part_info']['damage'] == 0
                    )
                    fix = extract_vertices(fix_vertex_pos)
                    for j in range(len(vertices)):
                        for k in range(3):
                            vertices[j][k] += fix[j][k]

                try:
                    uvs = [[u['u'], u['v']] for u in next(x for x in uv if x['part_info']['lod'] == lod_level)['data']]
                except StopIteration:
                    uvs = []

                # one sub-mesh per texture
                texture_meshes = {}
                for trix in (x for x in tri if x['part_info']['lod'] == lod_level):
                    texture_id = material_texture(trix['data']['material_index'])
                    if texture_id not in texture_meshes:
                        texture_meshes[texture_id] = (SubMesh(), {})
                    mesh, corner_map = texture_meshes[texture_id]
                    polygon = []
                    for corner in extract_triangle_corners(trix):
                        if corner not in corner_map:
                            vi, uvi = corner
                            if vi >= len(vertices):
                                corner_map[corner] = None
                            else:
                                corner_map[corner] = len(mesh.vertices)
                                mesh.vertices.append(list(vertices[vi]))
                                mesh.vertex_uvs.append(uvs[uvi] if uvi < len(uvs) else [0, 0])
                        polygon.append(corner_map[corner])
                        if len(polygon) == 3:
                            if None not in polygon:
                                mesh.polygons.append(polygon)
                            polygon = []

                for texture_id, (mesh, _) in texture_meshes.items():
                    if not mesh.polygons:
                        continue
                    mesh.name = mesh_name + (f'_{texture_id}' if texture_id else '')
                    if vx['part_info']['damage'] == 8:
                        mesh.name += '_damaged'
                    mesh.texture_id = texture_id
                    if transform_matrix is not None:
                        mesh.apply_transform_matrix(
                            [
                                [transform_matrix[0], transform_matrix[4], transform_matrix[8], transform_matrix[12]],
                                [transform_matrix[1], transform_matrix[5], transform_matrix[9], transform_matrix[13]],
                                [transform_matrix[2], transform_matrix[6], transform_matrix[10], transform_matrix[14]],
                                [transform_matrix[3], transform_matrix[7], transform_matrix[11], transform_matrix[15]],
                            ]
                        )
                    mesh.change_axes(new_y='z', new_z='y')
                    scene.sub_meshes.append(mesh)

        return export_scenes([scene], path, self.settings)


class NfsuBinGeometrySerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)

        scene = Scene()
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.sub_meshes = []

        for c in data['chunks']:
            if c['data']['chunk_id'] != 0x80_13_40_10:
                continue
            mesh_main_chunk = next(x for x in c['data']['sub_chunks'] if x['data']['chunk_id'] == 0x00_13_40_11)
            details_sub_chunk = next(x for x in c['data']['sub_chunks'] if x['data']['chunk_id'] == 0x80_13_41_00)

            mesh_name = mesh_main_chunk['data']['mesh_name']
            vertices = next(
                x for x in details_sub_chunk['data']['sub_chunks'] if x['data']['chunk_id'] == 0x00_13_4B_01
            )['data']['vertices']['data']
            faces = next(x for x in details_sub_chunk['data']['sub_chunks'] if x['data']['chunk_id'] == 0x00_13_4B_03)[
                'data'
            ]['faces']

            mesh = SubMesh()
            mesh.name = mesh_name
            mesh.vertices = [[v['position']['x'], v['position']['y'], v['position']['z']] for v in vertices]
            mesh.polygons = faces
            scene.sub_meshes.append(mesh)

        return export_scenes([scene], path, self.settings)
