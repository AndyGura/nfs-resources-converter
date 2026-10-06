import os
import re
import traceback
from collections import defaultdict
from configparser import ConfigParser, Error as ConfigParserError
from typing import List, Tuple, Dict, Optional

from PIL import Image

from library.exceptions import DataIntegrityException
from library.utils import path_join
from library.utils.id import join_id
from resources.eac.archives import ShpiBlock
from resources.eac.bitmaps import EacImage
from serializers import BaseFileSerializer
from serializers.common.three_d import SubMesh, Mesh, export_scenes, Scene
from serializers.misc.path_utils import escape_chars


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


def compose_texture_page(
    images: List[Tuple[Image.Image, int, int]], width: int = None, height: int = None, keep_alpha: bool = True
):
    """Composes images into one texture page. Images are given as (image, x, y). When images overlap, the first one
    wins. If page size is not provided, it is the bounding box of all images, rounded up to a power of two.
    Without keep_alpha, images are drawn opaque, so alpha of the page only tells which pixels are covered by any
    image"""

    def pow2(x):
        return 1 << max(0, int(x) - 1).bit_length()

    if width is None:
        width = pow2(max([x + img.width for img, x, _ in images] + [1]))
    if height is None:
        height = pow2(max([y + img.height for img, _, y in images] + [1]))
    page = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for img, x, y in reversed(images):
        if not keep_alpha:
            img = img.copy()
            img.putalpha(255)
        page.paste(img, (x, y))
    return page


def texture_alpha_mode(image: Image.Image) -> str:
    """Alpha mode of a texture for `Scene.mtl_texture_alpha_modes`: "blend" for translucent textures (glass, smoke:
    more than 10% of pixels have partial alpha), "cutout" for others (alpha is 0 or 255 except anti-aliased edges)"""
    histogram = image.getchannel('A').histogram()
    return 'blend' if sum(histogram[17:240]) > 0.1 * image.width * image.height else 'cutout'


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


def crp_car_default_style(tpg: ConfigParser) -> Dict[Tuple[str, int], int]:
    """Variant selection of car's default style (the lowest-numbered [styleN] section of .tpg): maps
    (slot kind, slot index) to variant type, e.g. ('geometry', 8) -> 3. Slots, not listed in the style, use type 0"""
    styles = sorted(int(m.group(1)) for m in (re.fullmatch(r'style(\d+)', x) for x in tpg.sections()) if m is not None)
    if not styles:
        return {}
    return dict(_crp_tpg_variant_entries(tpg, f'style{styles[0]}'))


def _crp_tpg_variant_entries(tpg: ConfigParser, section: str) -> List[Tuple[Tuple[str, int], int]]:
    """Reads (slot, type) entries of .tpg section, like "geometry1=5 type1=0" -> (('geometry', 5), 0)"""
    res = []
    for key, value in tpg.items(section):
        match = re.fullmatch(r'(geometry|texture)(\d+)', key)
        if match is None or not tpg.has_option(section, f'type{match.group(2)}'):
            continue
        res.append(((match.group(1), int(value)), tpg.getint(section, f'type{match.group(2)}')))
    return res


def crp_car_is_image_used(tpg: ConfigParser, file_index: int, alias: str, style: Dict[Tuple[str, int], int]) -> bool:
    """Whether the image of car's FSH file (1-based .tpg file index) is drawn on the texture page for given style.
    Images, described in .tpg section [file<N>.<alias>], are alternative variants: an image is used if any of its
    (slot, type) entries is selected by the style. Showroom (frontend=1) variants are preferred over in-race ones,
    race decals are skipped"""
    section = f'file{file_index}.{alias.strip()}'
    if not tpg.has_section(section):
        return True
    if tpg.has_option(section, 'frontend') and tpg.getint(section, 'frontend') != 1:
        return False
    if tpg.has_option(section, 'testdrive') and tpg.getint(section, 'testdrive') != 0:
        return False
    if tpg.has_option(section, 'racedecal') and tpg.getint(section, 'racedecal') != 0:
        return False
    entries = _crp_tpg_variant_entries(tpg, section)
    if not entries:
        return True
    return any(style.get(slot, 0) == variant for slot, variant in entries)


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

    def _load_car_textures(self, data, path, id, block) -> Dict[int, Tuple[list, Optional[int], Optional[int]]]:
        """Exports textures from FSH parts and prepares texture pages. Returns texture page index ->
        (images with positions, page width, page height)"""
        from library.loader import id_to_path
        from serializers import ShpiArchiveSerializer, ImageSerializer

        tpg = None
        if id:
            tpg_path = _find_sibling_file(
                id_to_path(id), os.path.splitext(os.path.basename(id_to_path(id)))[0] + '.tpg'
            )
            if tpg_path:
                tpg = ConfigParser(strict=False, interpolation=None)
                try:
                    tpg.read(tpg_path)
                except Exception:
                    tpg = None

        misc_choice = block.field_blocks_map['common_parts'].child
        fsh_choice_index = misc_choice.get_choice_index_by_class_name('FSHPart')
        shpi_block = ShpiBlock()
        # FSH part index -> (alias, image, x, y) of every image
        fsh_images = {}
        for i, x in enumerate(data['common_parts']):
            if x['choice_index'] != fsh_choice_index:
                continue
            fsh_part = x['data']
            assert fsh_part['num_data'] == 1
            fsh_data = fsh_part['data'][0]
            fsh_data_id = join_id(id, 'common_parts', str(i), 'data', 'data', '0')
            textures_path = path_join(path, f'textures/{fsh_part["idx"]}/')
            exported_files = set(ShpiArchiveSerializer().serialize(fsh_data, textures_path, fsh_data_id, shpi_block))
            aliases = [child['alias'] for child in fsh_data['children']]
            images = []
            for child in fsh_data['children']:
                item_block = shpi_block.item_block.possible_blocks[child['item']['choice_index']]
                if not isinstance(item_block, EacImage):
                    continue
                # reuse the image, exported by archive serializer, if its file name is unambiguous
                png_path = escape_chars(path_join(textures_path, child['alias'].replace('/', '_'))) + '.png'
                try:
                    if png_path in exported_files and aliases.count(child['alias']) == 1:
                        with Image.open(png_path) as png:
                            image = png.convert('RGBA')
                    else:
                        image = ImageSerializer().to_image(
                            child['item']['data'],
                            item_block,
                            join_id(fsh_data_id, 'children', child['alias'], 'item', 'data'),
                        )
                except Exception:
                    # the page is composed without images which cannot be converted
                    traceback.print_exc()
                    continue
                images.append((child['alias'], image, *crp_image_atlas_position(child['item']['data'])))
            fsh_images[fsh_part['idx']] = images

        def build_pages(tpg):
            style = crp_car_default_style(tpg) if tpg is not None else {}
            pages = {}
            for page_idx, fsh_idx in crp_car_texture_page_sources(list(fsh_images.keys()), tpg).items():
                width = height = None
                section = f'tpage{page_idx + 1}.details'
                if tpg is not None and tpg.has_option(section, 'width') and tpg.has_option(section, 'height'):
                    width, height = tpg.getint(section, 'width'), tpg.getint(section, 'height')
                images = [
                    (image, x, y)
                    for alias, image, x, y in fsh_images[fsh_idx]
                    if tpg is None or crp_car_is_image_used(tpg, fsh_idx + 1, alias, style)
                ]
                pages[page_idx] = (images, width, height)
            return pages

        if tpg is not None:
            try:
                return build_pages(tpg)
            except ValueError, ConfigParserError:
                # malformed .tpg: use the default layout
                traceback.print_exc()
        return build_pages(None)

    def _load_track_textures(self, data, path, id, block, tags) -> Tuple[Dict[int, str], Dict[str, str]]:
        """Exports textures, referenced by materials, from FSH file(s) next to the track CRP. Returns material
        texture tag (as integer) -> name of exported texture, and name of exported texture -> its alpha mode"""
        from library import require_resource
        from library.loader import id_to_path, path_to_name
        from serializers import ImageSerializer

        if not id:
            return {}, {}
        misc_choice = block.field_blocks_map['common_parts'].child
        text_choice_index = misc_choice.get_choice_index_by_class_name('TextPart2')
        fsh_names = [x['data']['data'] for x in data['common_parts'] if x['choice_index'] == text_choice_index]
        images = {}
        for fsh_name in fsh_names:
            fsh_path = _find_sibling_file(id_to_path(id), fsh_name)
            if not fsh_path:
                continue
            (fsh_id, shpi_block, shpi_data), _ = require_resource(path_to_name(fsh_path))
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
        alpha_modes = {}
        for tag in tags:
            alias = _crp_texture_tag(tag)
            if alias not in images:
                continue
            image_data, image_block, image_id = images[alias]
            try:
                image = ImageSerializer().to_image(image_data, image_block, image_id)
            except Exception:
                # meshes with a texture which cannot be converted stay untextured
                traceback.print_exc()
                continue
            name = re.sub(r'[^0-9A-Za-z_-]', '_', alias.strip()) or 'texture'
            while name in alpha_modes:
                name += '_'
            image.save(path_join(path, f'textures/{name}.png'))
            textures[tag] = name
            alpha_modes[name] = texture_alpha_mode(image)
        return textures, alpha_modes

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
        if data['resource_id'] == 'karT' and self.settings.maps__save_as_chunked:
            # the track viewer textures chunks from the track's FSH file itself: material name is the FSH alias
            def material_texture(material_index):
                material = materials.get(material_index)
                if not material:
                    return None
                # no "_" in the name: the track viewer takes the material from the last "_"-separated part of mesh name
                return re.sub(r'[^0-9A-Za-z-]', '-', _crp_texture_tag(material['tex_page_index']).strip()) or None

            return self._serialize_track_chunks(data, path, block, material_texture)

        if data['resource_id'] == 'karT':
            textures, alpha_modes = self._load_track_textures(
                data, path, id, block, {m['tex_page_index'] for m in materials.values()}
            )

            def material_texture(material_index):
                material = materials.get(material_index)
                return textures.get(material['tex_page_index']) if material else None

        else:
            pages = self._load_car_textures(data, path, id, block)
            textures = {}
            alpha_modes = {}

            def material_texture(material_index):
                material = materials.get(material_index)
                if not material or material['tex_page_index'] not in pages:
                    return None
                page_idx = material['tex_page_index']
                # alpha channel of car textures means transparency only for wheels and windows. For other
                # materials it is something else (probably a paint/reflection mask), so their page is drawn opaque
                desc = material['desc'].split('\x00')[0]
                keep_alpha = any(x in desc for x in ('Wheel', 'Window'))
                name = f'page_{page_idx}' + ('_alpha' if keep_alpha else '')
                if (page_idx, keep_alpha) not in textures:
                    images, width, height = pages[page_idx]
                    page = compose_texture_page(images, width, height, keep_alpha=keep_alpha)
                    page.save(path_join(path, f'textures/{name}.png'))
                    textures[(page_idx, keep_alpha)] = name
                    alpha_modes[name] = texture_alpha_mode(page) if keep_alpha else 'cutout'
                if 'Window' in desc:
                    # glass is translucent, even when it takes a small part of the page
                    alpha_modes[name] = 'blend'
                return name

        scene = Scene()
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.sub_meshes = []
        scene.mtl_texture_path_func = lambda name: f'textures/{name}.png'
        for *_, sub_mesh in self._build_article_meshes(data, block, material_texture):
            sub_mesh.change_axes(new_y='z', new_z='y')
            scene.sub_meshes.append(sub_mesh)

        scene.mtl_texture_names = sorted({m.texture_id for m in scene.sub_meshes if m.texture_id != 'untextured'})
        scene.mtl_texture_alpha_modes = alpha_modes
        return export_scenes([scene], path, self.settings)

    def _build_article_meshes(self, data, block, material_texture):
        """Yields (article index, article name, vertex part info, sub-mesh) of every vertex part and texture of each
        article. Sub-mesh is in CRP coordinates (Y up), with the article transformation applied"""
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
            index_rows = part['data']['index_rows']
            if not index_rows:
                return []
            # parts without a vertex index row use the offset of their first row
            start = next((x['offset'] for x in index_rows if x['identifier'] in ('vI', 'Iv')), index_rows[0]['offset'])
            info_rows = {x['choice_index']: x['data'] for x in part['data']['info_rows']}
            vertex_offset = (
                info_rows[vertex_info_row_choice_index]['offset'] // 16
                if vertex_info_row_choice_index in info_rows
                else 0
            )
            uv_offset = (
                info_rows[uv_info_row_choice_index]['offset'] // 8 if uv_info_row_choice_index in info_rows else 0
            )
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
                mesh = Mesh()
                mesh.name = mesh_name
                corner_map = {}
                for trix in (x for x in tri if x['part_info']['lod'] == lod_level):
                    # explicit material for untextured polygons, otherwise OBJ readers keep using the previous
                    # mesh's material
                    texture_id = material_texture(trix['data']['material_index']) or 'untextured'
                    corners = extract_triangle_corners(trix)
                    for j in range(0, len(corners), 3):
                        triangle = corners[j : j + 3]
                        if any(vi >= len(vertices) for vi, _ in triangle):
                            continue
                        for corner in triangle:
                            if corner not in corner_map:
                                vi, uvi = corner
                                corner_map[corner] = len(mesh.vertices)
                                mesh.vertices.append(list(vertices[vi]))
                                mesh.vertex_uvs.append(uvs[uvi] if uvi < len(uvs) else [0, 0])
                        mesh.polygons.append([corner_map[corner] for corner in triangle])
                        mesh.texture_ids.append(texture_id)
                if not mesh.polygons:
                    continue

                for sub_mesh, _, _ in mesh.split_by_texture_ids():
                    sub_mesh.name = mesh_name + (
                        f'_{sub_mesh.texture_id}' if sub_mesh.texture_id != 'untextured' else ''
                    )
                    if vx['part_info']['damage'] == 8:
                        sub_mesh.name += '_damaged'
                    if transform_matrix is not None:
                        sub_mesh.apply_transform_matrix(
                            [
                                [transform_matrix[0], transform_matrix[4], transform_matrix[8], transform_matrix[12]],
                                [transform_matrix[1], transform_matrix[5], transform_matrix[9], transform_matrix[13]],
                                [transform_matrix[2], transform_matrix[6], transform_matrix[10], transform_matrix[14]],
                                [transform_matrix[3], transform_matrix[7], transform_matrix[11], transform_matrix[15]],
                            ]
                        )
                    yield i, name, vx['part_info'], sub_mesh

    # track article name: <RD|CNK|OBJ><4-digit road piece number><L|C|R> (<section> <description>)
    _TRACK_ARTICLE_NAME_REGEX = re.compile(r'^(RD|CNK|OBJ)(\d{4})[LCR]\s*\((\d+)\s')

    def _serialize_track_chunks(self, data, path, block, material_texture) -> List[str]:
        """Track viewer output: one `terrain_chunk_<i>.obj` per road piece of the main road section, pivoted at the
        road piece center, plus `track_layout.json` with chunk positions (in CRP coordinates, Y up), road headings and
        whether the road is a loop. Only LOD 0, not animated, not damaged meshes are exported. Articles of the main
        section go to the chunk of their road piece number, all other articles to the chunk with the nearest center"""
        import bisect
        import json
        import math

        articles = defaultdict(list)
        names = {}
        for article_index, name, part_info, sub_mesh in self._build_article_meshes(data, block, material_texture):
            if part_info['lod'] != 0 or part_info['animation_index'] != 0 or part_info['damage'] != 0:
                continue
            articles[article_index].append(sub_mesh)
            names[article_index] = name

        def center(meshes):
            vertices = [v for m in meshes for v in m.vertices]
            return tuple(sum(v[k] for v in vertices) / len(vertices) for k in range(3))

        parsed = {i: self._TRACK_ARTICLE_NAME_REGEX.match(names[i]) for i in articles}
        sections = defaultdict(int)
        for m in parsed.values():
            if m and m.group(1) == 'RD':
                sections[m.group(3)] += 1
        main_section = max(sections, key=sections.get) if sections else None
        road_pieces = sorted(
            (int(m.group(2)), i) for i, m in parsed.items() if m and m.group(1) == 'RD' and m.group(3) == main_section
        )
        # several articles of the same road piece are merged into one chunk
        piece_numbers = sorted({n for n, _ in road_pieces})
        chunk_positions = [
            center([sm for n, i in road_pieces if n == number for sm in articles[i]]) for number in piece_numbers
        ]
        if not chunk_positions:
            chunk_positions = [center([sm for meshes in articles.values() for sm in meshes])] if articles else []
        chunks = [[] for _ in chunk_positions]
        for i, meshes in articles.items():
            m = parsed[i]
            if m and m.group(3) == main_section and piece_numbers:
                chunk_index = max(bisect.bisect_right(piece_numbers, int(m.group(2))) - 1, 0)
            else:
                c = center(meshes)
                chunk_index = min(range(len(chunk_positions)), key=lambda k: math.dist(chunk_positions[k], c))
            chunks[chunk_index].extend(meshes)

        def heading(k):
            if len(chunk_positions) < 2:
                return 0
            a, b = (
                (chunk_positions[k], chunk_positions[k + 1]) if k < len(chunk_positions) - 1 else chunk_positions[-2:]
            )
            return math.atan2(b[0] - a[0], b[2] - a[2])

        steps = [math.dist(chunk_positions[k], chunk_positions[k + 1]) for k in range(len(chunk_positions) - 1)]
        is_closed = bool(steps) and math.dist(chunk_positions[0], chunk_positions[-1]) < 2 * max(steps)

        scenes = []
        for k, meshes in enumerate(chunks):
            position = chunk_positions[k]
            for j, sub_mesh in enumerate(meshes):
                sub_mesh.change_axes(new_y='z', new_z='y')
                sub_mesh.pivot_offset = (position[0], position[2], position[1])
                sub_mesh.name = f'terrain_chunk_{k}_{j}_{sub_mesh.texture_id}'
            scenes.append(
                Scene(
                    name=f'terrain_chunk_{k}',
                    sub_meshes=meshes,
                    obj_name=f'terrain_chunk_{k}',
                    mtl_name=None,
                    bake_textures=False,
                )
            )
        exported = export_scenes(scenes, path, self.settings)
        layout_path = path_join(path, 'track_layout.json')
        with open(layout_path, 'w') as f:
            json.dump(
                {
                    'closed': is_closed,
                    'chunks': [
                        {'position': {'x': p[0], 'y': p[1], 'z': p[2]}, 'orientation': heading(k)}
                        for k, p in enumerate(chunk_positions)
                    ],
                },
                f,
            )
        return exported + [layout_path]


class NfsuBinGeometrySerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)

        scene = Scene()
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.sub_meshes = []

        for nfsu_mesh in nfsu_geometry_meshes(data):
            mesh = SubMesh()
            mesh.name = nfsu_mesh.name
            mesh.vertices = [list(v) for v in nfsu_mesh.vertices]
            mesh.vertex_uvs = [list(uv) for uv in nfsu_mesh.uvs]
            mesh.polygons = [list(t) for (_, triangles) in nfsu_mesh.parts for t in triangles]
            scene.sub_meshes.append(mesh)

        return export_scenes([scene], path, self.settings)


def fce_part_lod_prefix(part_index: int) -> str:
    """Level of detail of a car.fce part, by its index: "hp" (high-poly), "mp" (medium-poly), "lp" (low-poly) or
    "tp" (tiny)"""
    if part_index in (0, 1, 2, 3, 4, 12):
        return 'hp'
    if 5 <= part_index <= 9:
        return 'mp'
    if part_index == 10:
        return 'lp'
    if part_index == 11:
        return 'tp'
    return 'part'


def fce4_part_lod_prefix(part_name: str) -> str:
    """Level of detail of a FCE4 car.fce part, by its name (":HB", ":MLFW", ...): "hp" (high-poly), "mp"
    (medium-poly), "lp" (low-poly) or "tp" (tiny). Optional parts ":O*" (interior, driver, mirrors etc.) belong to
    high-poly model"""
    name = part_name.upper()
    if not name.startswith(':'):
        return 'part'
    if name.startswith(':O'):
        return 'hp'
    return {'H': 'hp', 'M': 'mp', 'L': 'lp', 'T': 'tp'}.get(name[1:2], 'part')


def _find_fce_siblings(id: str) -> Tuple[Optional[str], List[Tuple[str, bytes]]]:
    """Finds file name of FCE model and its TGA textures: TGA items of the same BIGF archive (car.viv), or TGA files
    next to FCE file. Returns (FCE file name, list of (texture name without extension, TGA bytes) sorted by name)"""
    from library import require_resource
    from library.loader import id_to_path

    if not id:
        return None, []
    file_name = None
    textures = []
    match = re.fullmatch(r'(.*?)(?:__|/)children/(\d+)/item/data', id)
    if match:
        (_, _, archive_data), _ = require_resource(match.group(1))
        children = (archive_data or {}).get('children', [])
        if int(match.group(2)) < len(children):
            file_name = children[int(match.group(2))]['alias']
        for child in children:
            alias = child['alias'] or ''
            item_data = (child['item'] or {}).get('data')
            if alias.lower().endswith('.tga') and isinstance(item_data, bytes):
                textures.append((alias[:-4], item_data))
    elif '__' not in id:
        file_path = id_to_path(id)
        file_name = os.path.basename(file_path)
        directory = os.path.dirname(file_path) or '.'
        for sibling in sorted(os.listdir(directory)) if os.path.isdir(directory) else []:
            if sibling.lower().endswith('.tga'):
                with open(path_join(directory, sibling), 'rb') as f:
                    textures.append((sibling[:-4], f.read()))
    return file_name, sorted(textures, key=lambda x: x[0].lower())


class Fce3GeometrySerializer(BaseFileSerializer):
    # FCE3 texture V goes from bottom to top of the texture, FCE4 from top to bottom
    v_from_bottom = True

    def __init__(self):
        super().__init__(is_dir=True)

    def _part_prefix(self, part_index: int, part_name: str, is_car: bool) -> str:
        # role of car.fce part is defined by its index
        return fce_part_lod_prefix(part_index) if is_car else 'part'

    def _vertex_tables(self, data: dict) -> List[Tuple[str, str]]:
        """Mesh variants to export: list of (mesh name suffix, name of vertex positions table)"""
        return [('', 'vertices')]

    def _transparency_mask(self, image: Image.Image) -> Image.Image:
        """Alpha channel of exported texture. FCE3 textures are opaque"""
        return Image.new('L', image.size, 255)

    def _export_textures(self, path: str, textures: List[Tuple[str, bytes]]) -> List[str]:
        """Exports TGA textures to PNG. Returns texture name for every texture page, in the given order"""
        from io import BytesIO

        names = []
        for name, tga_bytes in textures:
            name = re.sub(r'[^0-9A-Za-z_-]', '_', name) or 'texture'
            try:
                image = Image.open(BytesIO(tga_bytes)).convert('RGBA')
            except Exception:
                traceback.print_exc()
                continue
            # alpha channel of car textures is not transparency, but a paint mask: the less alpha, the more car
            # color is applied. Kept in a separate file for GUI preview
            image.save(path_join(path, f'assets/{name}_paint_mask.png'))
            image.putalpha(self._transparency_mask(image))
            image.save(path_join(path, f'assets/{name}.png'))
            names.append(name)
        return names

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        os.makedirs(path_join(path, 'assets'), exist_ok=True)
        file_name, textures = _find_fce_siblings(id)
        # texture page N of model <name>.fce is <name>0N.tga (car.fce: car00.tga, car1.fce: car100.tga, dash.fce:
        # dash00.tga). If there are no such files, all TGA files in alphabetical order are texture pages
        stem = re.escape((file_name or '').rsplit('.', 1)[0])
        own_textures = [x for x in textures if stem and re.fullmatch(stem + r'\d\d', x[0], re.IGNORECASE)]
        texture_pages = self._export_textures(path, own_textures or textures)
        # NFS4 car.viv has a model per upgrade level: car.fce, car1.fce, car2.fce, car3.fce
        is_car = re.fullmatch(r'car\d*\.fce', (file_name or '').lower()) is not None

        scene = Scene()
        scene.name = 'body'
        scene.obj_name = 'geometry'
        scene.mtl_name = 'material'
        alpha_modes = {}
        vertex_tables = self._vertex_tables(data)

        for part_index in range(min(data['num_parts'], 64)):
            part_name = data['part_names'][part_index].split('\x00')[0]
            mesh_name = f'{self._part_prefix(part_index, part_name, is_car)}_{part_index}'
            sanitized_name = re.sub(r'[^0-9A-Za-z-]+', '_', part_name).strip('_')
            if sanitized_name:
                mesh_name += f'_{sanitized_name}'
            first_vertex = data['part_first_vertex'][part_index]
            first_triangle = data['part_first_triangle'][part_index]
            triangles = data['triangles'][first_triangle : first_triangle + data['part_num_triangles'][part_index]]
            position = data['part_positions'][part_index]
            for name_suffix, vertex_table in vertex_tables:
                vertices = data[vertex_table][first_vertex : first_vertex + data['part_num_vertices'][part_index]]
                mesh = Mesh()
                mesh.name = mesh_name
                mesh.pivot_offset = (-position['x'], -position['y'], -position['z'])
                corner_map = {}
                for triangle in triangles:
                    if any(vi < 0 or vi >= len(vertices) for vi in triangle['vertex_indices']):
                        continue
                    page = triangle['tex_page']
                    texture_id = texture_pages[page] if 0 <= page < len(texture_pages) else 'untextured'
                    if triangle['flags']['semi_transparent'] and texture_id != 'untextured':
                        texture_id += '_translucent'
                        alpha_modes[texture_id] = 'blend'
                    polygon = []
                    for vi, u, v in zip(triangle['vertex_indices'], triangle['u'], triangle['v']):
                        key = (vi, u, v)
                        if key not in corner_map:
                            corner_map[key] = len(mesh.vertices)
                            vertex = vertices[vi]
                            mesh.vertices.append([vertex['x'], vertex['y'], vertex['z']])
                            mesh.vertex_uvs.append([u, 1 - v if self.v_from_bottom else v])
                        polygon.append(corner_map[key])
                    mesh.polygons.append(polygon)
                    mesh.texture_ids.append(texture_id)
                    if triangle['flags']['no_cull']:
                        mesh.polygons.append(polygon[::-1])
                        mesh.texture_ids.append(texture_id)
                if not mesh.polygons:
                    continue
                for sub_mesh, _, _ in mesh.split_by_texture_ids():
                    sub_mesh.name = (
                        mesh_name
                        + (f'__{sub_mesh.texture_id}' if sub_mesh.texture_id != 'untextured' else '')
                        + name_suffix
                    )
                    sub_mesh.change_axes(new_y='z', new_z='y')
                    px, py, pz = sub_mesh.pivot_offset
                    sub_mesh.pivot_offset = (px, pz, py)
                    scene.sub_meshes.append(sub_mesh)

        for dummy_index in range(min(data['num_dummies'], 16)):
            position = data['dummy_positions'][dummy_index]
            scene.dummies.append(
                {
                    'name': data['dummy_names'][dummy_index].split('\x00')[0] or f'dummy_{dummy_index}',
                    'position': [position['x'], position['z'], position['y']],
                }
            )

        scene.mtl_texture_names = sorted({m.texture_id for m in scene.sub_meshes if m.texture_id != 'untextured'})
        scene.mtl_texture_path_func = lambda name: f'assets/{name.removesuffix("_translucent")}.png'
        scene.mtl_texture_alpha_modes = {name: alpha_modes.get(name, 'cutout') for name in scene.mtl_texture_names}
        return export_scenes([scene], path, self.settings)


class Fce4GeometrySerializer(Fce3GeometrySerializer):
    v_from_bottom = False

    def _transparency_mask(self, image: Image.Image) -> Image.Image:
        # texture alpha 0 is transparency (wheel rims, steering wheel), other values are paint mask
        return image.getchannel('A').point(lambda a: 0 if a == 0 else 255)

    def _part_prefix(self, part_index: int, part_name: str, is_car: bool) -> str:
        # role of car.fce part is defined by its name
        return fce4_part_lod_prefix(part_name) if is_car else 'part'

    def _vertex_tables(self, data: dict) -> List[Tuple[str, str]]:
        # crashed car model is exported as a copy of every mesh, "<mesh>_damaged"
        if data['damaged_vertices'] != data['vertices']:
            return [('', 'vertices'), ('_damaged', 'damaged_vertices')]
        return [('', 'vertices')]


def eagl_texture_archive_name(model_file_name: str) -> str:
    """FSH file with textures of NFS6 EAGL model: "<x>g.o" uses "<x>.fsh" ("levelG.o" -> "level.fsh", "skyg.o" ->
    "sky.fsh"), track compartments ("compNN.o") use "track.fsh", car models ("car.o", "carRigid.o", "carM.o", "shadow.o"
    in car.viv) use "car.fsh" """
    name = os.path.basename(model_file_name or '').lower()
    if name.startswith('car') or name == 'shadow.o':
        return 'car.fsh'
    if name.endswith('g.o') and not name.startswith('comp'):
        return name[:-3] + '.fsh'
    return 'track.fsh'


def _find_bigf_child(archive_id: str, alias: str) -> Optional[str]:
    from library import require_resource

    (_, _, archive_data), _ = require_resource(archive_id)
    for i, child in enumerate((archive_data or {}).get('children', [])):
        if (child['alias'] or '').lower() == alias.lower():
            return join_id(archive_id, 'children', str(i), 'item', 'data')
    return None


def find_eagl_texture_archive(id: str, model_file_name: str = None) -> Optional[Tuple[str, ShpiBlock, dict]]:
    """Finds FSH file with textures of NFS6 EAGL model with given resource id: in the same BIGF archive (models in
    "persist.viv"), next to the model file, or in "persist.viv" next to the model or in the parent folder (track
    compartments in track folder, "levelG.o" in "levelNN" sub-folder). Returns (id, block, data) of SHPI or None"""
    from library import require_resource
    from library.loader import id_to_path, path_to_name

    if not id:
        return None
    candidates = []
    match = re.fullmatch(r'(.*?)(?:__|/)children/(\d+)/item/data', id)
    if match:
        (_, _, archive_data), _ = require_resource(match.group(1))
        children = (archive_data or {}).get('children', [])
        if model_file_name is None and int(match.group(2)) < len(children):
            model_file_name = children[int(match.group(2))]['alias']
        fsh_name = eagl_texture_archive_name(model_file_name)
        candidates.append(lambda: _find_bigf_child(match.group(1), fsh_name))
        file_path = id_to_path(id)
    else:
        file_path = id_to_path(id)
        fsh_name = eagl_texture_archive_name(model_file_name or file_path)
    directory = os.path.dirname(file_path)
    candidates.append(lambda: (lambda p: path_to_name(p) if p else None)(_find_sibling_file(file_path, fsh_name)))
    for folder in [directory, os.path.dirname(directory)]:
        candidates.append(
            lambda folder=folder: (lambda p: _find_bigf_child(path_to_name(p), fsh_name) if p else None)(
                _find_sibling_file(path_join(folder, 'persist.viv'), 'persist.viv')
            )
        )
    for candidate in candidates:
        try:
            fsh_id = candidate()
            if not fsh_id:
                continue
            (fsh_id, shpi_block, shpi_data), _ = require_resource(fsh_id)
            while not isinstance(shpi_block, ShpiBlock) and isinstance(shpi_data, dict) and 'choice_index' in shpi_data:
                (fsh_id, shpi_block, shpi_data), _ = require_resource(join_id(fsh_id, 'data'))
            if isinstance(shpi_block, ShpiBlock):
                return fsh_id, shpi_block, shpi_data
        except Exception:
            traceback.print_exc()
    return None


def export_fsh_textures(
    archive: Optional[Tuple[str, ShpiBlock, dict]], aliases, path: str, name_prefix: str = ''
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Saves images with given aliases from SHPI archive to "<path>/textures/<name_prefix><alias>.png". Returns
    alias -> texture name and texture name -> alpha mode"""
    from serializers import ImageSerializer

    if archive is None:
        return {}, {}
    fsh_id, shpi_block, shpi_data = archive
    images = {}
    for child in shpi_data['children']:
        item_block = shpi_block.item_block.possible_blocks[child['item']['choice_index']]
        if isinstance(item_block, EacImage) and child['alias'] not in images:
            images[child['alias']] = (child['item']['data'], item_block, join_id(fsh_id, 'children', child['alias']))
    os.makedirs(path_join(path, 'textures'), exist_ok=True)
    names, alpha_modes = {}, {}
    for alias in aliases:
        if alias not in images:
            continue
        image_data, image_block, image_id = images[alias]
        try:
            image = ImageSerializer().to_image(image_data, image_block, image_id)
        except Exception:
            traceback.print_exc()
            continue
        name = name_prefix + re.sub(r'[^0-9A-Za-z-]', '-', alias.strip())
        image.save(path_join(path, f'textures/{name}.png'))
        names[alias] = name
        alpha_modes[name] = texture_alpha_mode(image)
    return names, alpha_modes


def eagl_sub_meshes(meshes, texture_names: Dict[str, str], mesh_name_prefix: str, pivot=(0, 0, 0)) -> List[SubMesh]:
    """One SubMesh per EAGL mesh, textured with its main texture, in game coordinates relative to `pivot`. Mesh
    names end with "_<texture name>" (texture names have no "_")"""
    sub_meshes = []
    for i, m in enumerate(meshes):
        if not m.triangles:
            continue
        sm = SubMesh()
        sm.texture_id = texture_names.get(m.main_texture) or 'untextured'
        sm.name = f'{mesh_name_prefix}{i}_{sm.texture_id}'
        sm.vertices = [[v[0] - pivot[0], v[1] - pivot[1], v[2] - pivot[2]] for v in m.vertices]
        uvs = m.main_uvs
        sm.vertex_uvs = [[u, v] for (u, v) in uvs] if uvs else [[0, 0]] * len(m.vertices)
        sm.polygons = [list(t) for t in m.triangles]
        sub_meshes.append(sm)
    return sub_meshes


class EaglModelSerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        from resources.eac.geometries.nfs6 import read_eagl_meshes

        super().serialize(data, path)
        meshes = read_eagl_meshes(data)
        if is_nfs6_car_model(meshes):
            return self._serialize_car(data, meshes, path, id)
        archive = find_eagl_texture_archive(id)
        texture_names, alpha_modes = export_fsh_textures(
            archive, {m.main_texture for m in meshes if m.main_texture}, path
        )
        scene = Scene(
            name='model',
            obj_name='geometry',
            mtl_name='material',
            sub_meshes=eagl_sub_meshes(meshes, texture_names, 'mesh_'),
            mtl_texture_names=list(texture_names.values()),
            mtl_texture_path_func=lambda name: f'textures/{name}.png',
            mtl_texture_alpha_modes=alpha_modes,
        )
        for mesh in scene.sub_meshes:
            # game Y up -> Z up
            mesh.change_axes(new_z='y', new_y='z')
        return export_scenes([scene], path, self.settings)

    def _serialize_car(self, data: dict, meshes, path: str, id) -> List[str]:
        import json

        scene, skins = nfs6_car_scene(data, meshes, path, id)
        # game axes: X right, Y up, car front at -Z. Exported: X right, Y forward, Z up
        for mesh in scene.sub_meshes:
            mesh.change_axes(new_y='-z', new_z='y')
            mesh.polygons = [p[::-1] for p in mesh.polygons]
        for dummy in scene.dummies:
            x, y, z = dummy['position']
            dummy['position'] = [x, -z, y]
        paths = export_scenes([scene], path, self.settings)
        skins_path = path_join(path, 'skins.json')
        with open(skins_path, 'w') as f:
            json.dump(skins, f, indent=2)
        return paths + [skins_path]


def _eagl_model_location(id: str) -> Tuple[Optional[str], Optional[str], str]:
    """(BIGF archive id or None, model file name, path of the file on disk) of NFS6 model with given resource id"""
    from library import require_resource
    from library.loader import id_to_path

    match = re.fullmatch(r'(.*?)(?:__|/)children/(\d+)/item/data', id or '')
    if not match:
        return None, os.path.basename(id_to_path(id or '')), id_to_path(id or '')
    (_, _, archive_data), _ = require_resource(match.group(1))
    children = (archive_data or {}).get('children', [])
    alias = children[int(match.group(2))]['alias'] if int(match.group(2)) < len(children) else None
    return match.group(1), alias, id_to_path(id)


def is_nfs6_car_model(meshes) -> bool:
    """NFS6 car models (car.o, carRigid.o etc.) are drawn with "EASVehicle*" microcodes"""
    return any(m.shader.startswith('EASVehicle') for m in meshes)


def nfs6_car_part_lod_prefix(geometry_name: str) -> str:
    """Level of detail of NFS6 car geometry, by its name: "hp" (high-poly) for full-detail parts, "mp" (medium-poly)
    for "MIDLOD_Shape" and "*_LOD_WHEEL_*" wheels, "lp" (low-poly) for other "*LOD*" geometries
    ("ALPHA_OPAQUE_LODShape"). Game's geomdata.ini has the same as distances: hp is drawn from 100 to 65, mp from 65
    to 50 (wheels to 10), lp below 50"""
    name = (geometry_name or '').upper()
    if 'MIDLOD' in name or 'LOD_WHEEL' in name:
        return 'mp'
    if 'LOD' in name:
        return 'lp'
    return 'hp'


def find_nfs6_car_skins(id: str) -> List[Tuple[str, str, Tuple[str, ShpiBlock, dict]]]:
    """Skins of NFS6 car: FSH files of "skin.viv" next to car's "car.viv" ("skin00.fsh", ..., "skinhp.fsh" for the
    hot pursuit version), each has a "skin" image. Returns list of (skin name, label, (FSH id, block, data)), label is
    "color_id" of [skinNN] section of "vehicle.ini" next to car.viv ("red", "silver", ...) or skin name"""
    from library import require_resource
    from library.loader import path_to_name

    _, _, file_path = _eagl_model_location(id)
    skin_viv = _find_sibling_file(file_path, 'skin.viv')
    if not skin_viv:
        return []
    labels = {}
    vehicle_ini = _find_sibling_file(file_path, 'vehicle.ini')
    if vehicle_ini:
        ini = ConfigParser(strict=False, interpolation=None, comment_prefixes=("'", '//', ';', '#'))
        try:
            with open(vehicle_ini, encoding='latin-1') as f:
                ini.read_string(f.read())
            labels = {x.lower(): ini.get(x, 'color_id') for x in ini.sections() if ini.has_option(x, 'color_id')}
        except ConfigParserError:
            traceback.print_exc()
    skins = []
    try:
        (archive_id, _, archive_data), _ = require_resource(path_to_name(skin_viv))
        for i, child in enumerate((archive_data or {}).get('children', [])):
            alias = child['alias'] or ''
            if not alias.lower().endswith('.fsh'):
                continue
            (fsh_id, fsh_block, fsh_data), _ = require_resource(join_id(archive_id, 'children', str(i), 'item', 'data'))
            while not isinstance(fsh_block, ShpiBlock) and isinstance(fsh_data, dict) and 'choice_index' in fsh_data:
                (fsh_id, fsh_block, fsh_data), _ = require_resource(join_id(fsh_id, 'data'))
            if isinstance(fsh_block, ShpiBlock):
                name = alias[:-4]
                skins.append((name, labels.get(name.lower(), name), (fsh_id, fsh_block, fsh_data)))
    except Exception:
        traceback.print_exc()
    return skins


def _find_nfs6_car_skeleton(id: str):
    """Bones of "skeleton.o" in the same car.viv as the car model, or next to the model file"""
    from library import require_resource
    from library.loader import path_to_name
    from resources.eac.geometries.nfs6 import read_eagl_skeleton

    archive_id, _, file_path = _eagl_model_location(id)
    try:
        skeleton_id = _find_bigf_child(archive_id, 'skeleton.o') if archive_id else None
        if skeleton_id is None:
            skeleton_path = _find_sibling_file(file_path, 'skeleton.o')
            skeleton_id = path_to_name(skeleton_path) if skeleton_path else None
        if skeleton_id is None:
            return []
        (_, _, skeleton_data), _ = require_resource(skeleton_id)
        return read_eagl_skeleton(skeleton_data) if skeleton_data else []
    except Exception:
        traceback.print_exc()
        return []


def _save_opaque(file_path: str):
    image = Image.open(file_path).convert('RGBA')
    image.putalpha(255)
    image.save(file_path)


def _tinted_texture(image: Image.Image, color: int) -> Image.Image:
    """Texture multiplied by vertex diffuse color 0xRRGGBBAA, as Direct3D modulates them"""
    from PIL import ImageChops

    tint = Image.new(
        'RGBA', image.size, ((color >> 24) & 0xFF, (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
    )
    return ImageChops.multiply(image.convert('RGBA'), tint)


def nfs6_car_scene(data: dict, meshes, path: str, id: str) -> Tuple[Scene, List[dict]]:
    """Scene of NFS6 car model with its textures in "<path>/textures": car.fsh images by alias, "skin.png" is the
    first skin, every skin is also saved as "skins/<skin name>-skin.png". Car textures are saved opaque: their alpha is
    a reflection mask. Glass is drawn black with vertex alpha, so meshes with one vertex color other than white get a
    tinted copy of their texture "<texture>-<RRGGBBAA>", which is translucent. Mesh names are
    "<lod>_<geometry index>_<geometry name>", dummies are the bones of car's skeleton.o. Returns the scene (game
    axes) and the skins: list of {"name", "label", "texture"}"""
    texture_path = path_join(path, 'textures')
    os.makedirs(path_join(texture_path, 'skins'), exist_ok=True)
    texture_names, _ = export_fsh_textures(
        find_eagl_texture_archive(id),
        {m.main_texture for m in meshes if m.main_texture and m.main_texture != 'skin'},
        path,
    )
    for texture_name in texture_names.values():
        _save_opaque(path_join(texture_path, f'{texture_name}.png'))
    skins = []
    for name, label, archive in find_nfs6_car_skins(id):
        file_name = re.sub(r'[^0-9A-Za-z-]', '-', name)
        names, _ = export_fsh_textures(archive, ['skin'], path, name_prefix=f'skins/{file_name}-')
        if 'skin' not in names:
            continue
        _save_opaque(path_join(texture_path, f'{names["skin"]}.png'))
        skins.append({'name': name, 'label': label, 'texture': f'textures/{names["skin"]}.png'})
        if 'skin' not in texture_names:
            Image.open(path_join(path, skins[-1]['texture'])).save(path_join(texture_path, 'skin.png'))
            texture_names['skin'] = 'skin'
    alpha_modes = {name: 'cutout' for name in texture_names.values()}
    images = {}
    sub_meshes = []
    for i, m in enumerate(meshes):
        if not m.triangles:
            continue
        sm = SubMesh()
        sm.texture_id = texture_names.get(m.main_texture) or 'untextured'
        colors = set(m.colors)
        if sm.texture_id != 'untextured' and len(colors) == 1 and next(iter(colors)) != 0xFFFFFFFF:
            color = next(iter(colors))
            tinted_id = f'{sm.texture_id}-{color:08x}'
            if tinted_id not in alpha_modes:
                if sm.texture_id not in images:
                    images[sm.texture_id] = Image.open(path_join(texture_path, f'{sm.texture_id}.png'))
                _tinted_texture(images[sm.texture_id], color).save(path_join(texture_path, f'{tinted_id}.png'))
                alpha_modes[tinted_id] = 'blend'
            sm.texture_id = tinted_id
        geometry = re.sub(r'[^0-9A-Za-z]+', '_', (m.geometry_name or '').split('~')[0]).strip('_') or 'mesh'
        sm.name = f'{nfs6_car_part_lod_prefix(m.geometry_name)}_{i}_{geometry}'
        sm.vertices = [list(v) for v in m.vertices]
        uvs = m.main_uvs
        sm.vertex_uvs = [[u, v] for (u, v) in uvs] if uvs else [[0, 0]] * len(m.vertices)
        sm.polygons = [list(t) for t in m.triangles]
        sub_meshes.append(sm)
    dummies = [
        {'name': bone.name, 'position': list(bone.position)}
        for bone in _find_nfs6_car_skeleton(id)
        if not re.match(r'(Root|false_?root\d*|joint\d+|DAMAGE\d+)$', bone.name, re.IGNORECASE)
    ]
    scene = Scene(
        name='body',
        obj_name='geometry',
        mtl_name='material',
        sub_meshes=sub_meshes,
        mtl_texture_names=sorted({m.texture_id for m in sub_meshes if m.texture_id != 'untextured'}),
        mtl_texture_path_func=lambda name: f'textures/{name}.png',
        mtl_texture_alpha_modes=alpha_modes,
        dummies=dummies,
    )
    return scene, skins


class NfsuMesh:
    """Mesh of NFS Underground geometry pack, in its local coordinates: vertex positions, UVs and triangles per
    texture id (hash of texture name)"""

    def __init__(self, mesh_id: int, name: str):
        self.mesh_id = mesh_id
        self.name = name
        self.vertices: List[Tuple[float, float, float]] = []
        self.uvs: List[Tuple[float, float]] = []
        self.parts: List[Tuple[Optional[int], List[List[int]]]] = []


def _nfsu_sub_chunk_data(chunks: list, chunk_id: int):
    return next(
        (x['data'] for x in chunks if isinstance(x['data'], dict) and x['data'].get('chunk_id') == chunk_id), None
    )


def nfsu_geometry_meshes(geometry_data: dict) -> List[NfsuMesh]:
    """Meshes of NFS Underground geometry pack (NfsuBinGeometry data)"""
    meshes = []
    for c in geometry_data['chunks']:
        if c['data'].get('chunk_id') != 0x80_13_40_10:
            continue
        sub_chunks = c['data']['sub_chunks']
        header = _nfsu_sub_chunk_data(sub_chunks, 0x00_13_40_11)
        container = _nfsu_sub_chunk_data(sub_chunks, 0x80_13_41_00)
        if header is None or container is None:
            continue
        texture_ids = _nfsu_sub_chunk_data(sub_chunks, 0x00_13_40_12)
        texture_ids = [x['value'] for x in texture_ids['items']] if texture_ids else []
        vertices_chunk = _nfsu_sub_chunk_data(container['sub_chunks'], 0x00_13_4B_01)
        faces_chunk = _nfsu_sub_chunk_data(container['sub_chunks'], 0x00_13_4B_03)
        materials_chunk = _nfsu_sub_chunk_data(container['sub_chunks'], 0x00_13_4B_02)
        if vertices_chunk is None or faces_chunk is None or not isinstance(vertices_chunk['vertices']['data'], list):
            continue
        mesh = NfsuMesh(header['mesh_id'], header['mesh_name'])
        vertices = vertices_chunk['vertices']['data']
        mesh.vertices = [(v['position']['x'], v['position']['y'], v['position']['z']) for v in vertices]
        mesh.uvs = [(v['u'], v['v']) for v in vertices]
        faces = faces_chunk['faces']
        materials = materials_chunk['materials'] if materials_chunk else []
        if not materials:
            mesh.parts.append((texture_ids[0] if texture_ids else None, faces))
        for material in materials:
            start = material['indices_offset'] // 3
            end = start + material['indices_amount'] // 3
            texture_index = material['texture_index']
            mesh.parts.append(
                (texture_ids[texture_index] if 0 <= texture_index < len(texture_ids) else None, faces[start:end])
            )
        meshes.append(mesh)
    return meshes
