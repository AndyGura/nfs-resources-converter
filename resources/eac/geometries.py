from math import floor
from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 BytesBlock,
                                 DelegateBlock,
                                 BitFlagsBlock)
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.fields.misc import Point3D


class OripPolygon(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A geometry polygon',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_type = (IntegerBlock(length=1),
                        {'description': "Huh, that's a srange field. From my tests, if it is xxx0_0011, the "
                                        "polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only "
                                        "one polygon for entire TNFS with type == 2 in burnt sienna props. If "
                                        "ignore this polygon everything still looks great"})
        mapping = (BitFlagsBlock(flag_names=[(0, 'two_sided'),
                                             (1, 'flip_normal'),
                                             (4, 'use_uv')]),
                   {'description': 'Rendering properties of the polygon'})
        texture_index = (IntegerBlock(length=1),
                         {'description': "The index of item in ORIP's tex_ids block"})
        unk = (IntegerBlock(length=1),
               {'is_unknown': True})
        offset_3d = (IntegerBlock(length=4),
                     {'description': "The index in vmap ORIP's table. This index "
                                     "represents first vertex of this polygon, so in order to determine all "
                                     "vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. "
                                     "Look at vmap description for more info"})
        offset_2d = (IntegerBlock(length=4),
                     {'description': "The same as offset_3d, also points to vmap, but used "
                                     "for texture coordinates. Look at vmap description "
                                     "for more info"})


class OripVertexUV(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Texture coordinates for vertex, where each coordinate is: '
                                 + IntegerBlock(length=4).schema['block_description']
                                 + '. The unit is a pixels amount of assigned texture. So it should be changed when selecting '
                                   'texture with different size',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        u = IntegerBlock(length=4, is_signed=True)
        v = IntegerBlock(length=4, is_signed=True)


class OripTextureName(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A settings of the texture. From what is known, contains name of bitmap (not always a correct UTF-8)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        type = BytesBlock(length=8)
        file_name = (UTF8Block(length=4),
                     {'description': 'Name of bitmap in SHPI block'})
        unknown = (BytesBlock(length=8),
                   {'is_unknown': True})


class RenderOrderBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=8),
                      {'description': "identifier ('NON-SORT', 'inside', 'surface', 'outside')"})
        unk0 = (IntegerBlock(length=4),
                {'description': "0x8 for 'NON-SORT' or 0x1 for the others"})
        polygons_amount = (IntegerBlock(length=4),
                           {'description': "Polygons amount (3DO). For TNFSSE sometimes too big value"})
        polygon_sum = (IntegerBlock(length=4),
                       {'description': "0 for 'NON-SORT'; block’s 10 size for 'inside'; equals block’s 10 size "
                                       "+ number of polygons from ‘inside’ = XXX for 'surface'; equals XXX + "
                                       "number of polygons from 'surface' for 'outside'; (Description for 3DO "
                                       "orip file, TNFSSE version has only 9 blocks!)"})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=4),
                {'is_unknown': True})


class NamedIndex(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': '12-bytes record, first 8 bytes is null-terminated UTF-8 string, last'
                                 ' 4 bytes is an unsigned integer (little-endian)',
            'inline_description': True,
        }

    @property
    def size_doc_str(self):
        return '12'

    class Fields(DeclarativeCompoundBlock.Fields):
        name = NullTerminatedUTF8Block(length=8)
        offset = (ArrayBlock(child=IntegerBlock(length=1),
                             length=(lambda ctx: 8 - ctx.buffer.tell() + ctx.read_start_offset, '7 - len(name)')), {
                      'programmatic_value': lambda ctx: [0] * (7 - len(ctx.data('name')))
                  })
        index = IntegerBlock(length=4)


# TODO check additional info in http://3dodev.com/documentation/file_formats/games/nfs
class OripGeometry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Geometry block for 3D model with few materials',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(required_value='ORIP', length=4),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=4),
                      {'description': 'Total ORIP block size'})
        unk0 = (IntegerBlock(length=4, required_value=0x02BC),
                {'description': 'Looks like always 0x01F4 in 3DO version and 0x02BC in PC TNFSSE. ORIP type?',
                 'is_unknown': True})
        unk1 = (IntegerBlock(length=4, required_value=0),
                {'is_unknown': True})
        num_vrtx = (IntegerBlock(length=4),
                    {'description': 'Amount of vertices',
                     'programmatic_value': lambda ctx: len(ctx.data('vertices'))})
        unk2 = (BytesBlock(length=4),
                {'is_unknown': True})
        vrtx_ptr = (IntegerBlock(length=4),
                    {'description': 'An offset to vertices',
                     'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(),
                                                                                             'vertices')})
        num_uvs = (IntegerBlock(length=4),
                   {'description': 'Amount of vertex UV-s (texture coordinates)',
                    'programmatic_value': lambda ctx: len(ctx.data('vertex_uvs'))})
        uvs_ptr = (IntegerBlock(length=4),
                   {'description': 'An offset to vertex_uvs. Always equals to `112 + num_polygons*12`',
                    'programmatic_value': lambda ctx: 112 + len(ctx.data('polygons')) * 12})
        num_polygons = (IntegerBlock(length=4),
                        {'description': 'Amount of polygons',
                         'programmatic_value': lambda ctx: len(ctx.data('polygons'))})
        polygons_ptr = (IntegerBlock(length=4, is_signed=False, required_value=112),
                        {'description': 'An offset to polygons block'})
        identifier = (UTF8Block(length=12),
                      {'description': 'Some ID of geometry, don\'t know the purpose',
                       'is_unknown': True})
        num_tex_ids = (IntegerBlock(length=4),
                       {'description': 'Amount of texture names',
                        'programmatic_value': lambda ctx: len(ctx.data('tex_ids'))})
        tex_ids_ptr = (IntegerBlock(length=4),
                       {'description': 'An offset to texture names block. Always equals to '
                                       '`112 + num_polygons*12 + num_uvs*8`',
                        'programmatic_value': lambda ctx: 112 + len(ctx.data('polygons')) * 12
                                                          + len(ctx.data('vertex_uvs')) * 8})
        num_tex_nmb = (IntegerBlock(length=4),
                       {'description': 'Amount of texture numbers',
                        'programmatic_value': lambda ctx: len(ctx.data('tex_nmb'))})
        tex_nmb_ptr = (IntegerBlock(length=4),
                       {'description': 'An offset to texture numbers block'})
        num_ren_ord = (IntegerBlock(length=4),
                       {'description': 'Amount of items in render_order block',
                        'programmatic_value': lambda ctx: len(ctx.data('render_order'))})
        ren_ord_ptr = (IntegerBlock(length=4),
                       {'description': 'Offset of render_order block. Always equals to `tex_nmb_ptr + num_tex_nmb*20`',
                        'programmatic_value': lambda ctx: ctx.data('tex_nmb_ptr')
                                                          + len(ctx.data('tex_nmb')) * 20})
        vmap_ptr = (IntegerBlock(length=4),
                    {'description': 'Offset of polygon_vertex_map block',
                     'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(),
                                                                                             'vmap')})
        num_fxp = (IntegerBlock(length=4),
                   {'description': 'Amount of items in fx_polys block',
                    'programmatic_value': lambda ctx: len(ctx.data('fx_polys'))})
        fxp_ptr = (IntegerBlock(length=4),
                   {'description': 'Offset of fx_polys block. Always equals to `tex_nmb_ptr + num_tex_nmb*20 + '
                                   'num_ren_ord*28`',
                    'programmatic_value': lambda ctx: ctx.data('tex_nmb_ptr')
                                                      + len(ctx.data('tex_nmb')) * 20
                                                      + len(ctx.data('render_order')) * 28})
        num_lbl = (IntegerBlock(length=4),
                   {'description': 'Amount of items in labels block',
                    'programmatic_value': lambda ctx: len(ctx.data('labels'))})
        lbl_ptr = (IntegerBlock(length=4),
                   {'description': 'Offset of labels block. Always equals to `tex_nmb_ptr'
                                   ' + num_tex_nmb*20 + num_ren_ord*28 + num_fxp*12`',
                    'programmatic_value': lambda ctx: ctx.data('tex_nmb_ptr')
                                                      + len(ctx.data('tex_nmb')) * 20
                                                      + len(ctx.data('render_order')) * 28
                                                      + len(ctx.data('fx_polys')) * 12})
        unknowns1 = (BytesBlock(length=12),
                     {'is_unknown': True})
        polygons = (ArrayBlock(child=OripPolygon(),
                               length=lambda ctx: ctx.data('num_polygons')),
                    {'description': 'A block with polygons of the geometry. Probably should be a start point when '
                                    'building model from this file'})
        vertex_uvs = (ArrayBlock(child=OripVertexUV(),
                                 length=lambda ctx: ctx.data('num_uvs')),
                      {'description': 'A table of texture coordinates. Items are retrieved by index, located in vmap',
                       'custom_offset': 'uvs_ptr'})
        tex_ids = (ArrayBlock(child=OripTextureName(),
                              length=lambda ctx: ctx.data('num_tex_ids')),
                   {'description': 'A table of texture references. Items are retrieved by index, located in '
                                   'polygon item',
                    'custom_offset': 'tex_ids_ptr'})
        offset = (BytesBlock(
            length=(lambda ctx: ctx.read_start_offset + ctx.data('tex_nmb_ptr') - ctx.buffer.tell(),
                    'space up to offset `tex_nmb_ptr`'),
            allow_negative_length=True),
                  {'description': 'In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in'
                                  ' case of DIABLO.CFM it\'s length is equal to -3, meaning that last 3 bytes from '
                                  'texture names block are reused by next block'})
        tex_nmb = (ArrayBlock(child=ArrayBlock(child=IntegerBlock(length=1), length=20),
                              length=lambda ctx: ctx.data('num_tex_nmb')),
                   {'is_unknown': True,
                    'custom_offset': 'tex_nmb_ptr'})
        render_order = (ArrayBlock(child=RenderOrderBlock(),
                                   length=lambda ctx: ctx.data('num_ren_ord')),
                        {'description': 'Render order. The exact mechanism how it works is unknown',
                         'custom_offset': 'ren_ord_ptr'})
        fx_polys = (ArrayBlock(child=NamedIndex(),
                               length=lambda ctx: ctx.data('num_fxp')),
                    {'description': 'Indexes of polygons which participate in visual effects such as engine smoke, '
                                    'dust particles, tyre trails? Presented in car CFM-s. ',
                     'custom_offset': 'fxp_ptr'})
        labels = (ArrayBlock(child=NamedIndex(),
                             length=lambda ctx: ctx.data('num_lbl')),
                  {'description': 'Marks special polygons for the game, where it should change texture on runtime such '
                                  'as tyres, tail lights',
                   'custom_offset': 'lbl_ptr'})
        vertices = (ArrayBlock(child=DelegateBlock(possible_blocks=[Point3D(child_length=4, fraction_bits=7),
                                                                    Point3D(child_length=4, fraction_bits=4)],
                                                   choice_index=lambda ctx, **_: (
                                                       0 if ctx.buffer.name.endswith('.CFM')
                                                       else 1)),
                               length=lambda ctx: ctx.data('num_vrtx')),
                    {'description': 'A table of mesh vertices 3D coordinates. For cars uses 32:7 points, else 32:4. '
                                    'The unit is meter',
                     'custom_offset': 'vrtx_ptr'})
        vmap = (ArrayBlock(child=IntegerBlock(length=4),
                           length=(lambda ctx: floor(
                               (ctx.data('block_size') + ctx.read_start_offset - ctx.buffer.tell()) / 4), '?')),
                {'description': "A LUT for both 3D and 2D vertices. Every item is an index of either item in "
                                "vertices or vertex_uvs. When building 3D vertex, polygon defines offset_3d, "
                                "a lookup to this table, and value from here is an index of item in vertices. "
                                "When building UV-s, polygon defines offset_2d, a lookup to this table, and "
                                "value from here is an index of item in vertex_uvs",
                 'custom_offset': 'vmap_ptr'})


class GeoPolygon(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A single polygon of the mesh. Texture coordinates seem to be hardcoded in game:'
                                     'for triangles `[[0, 0], [1, 0], [1, 1]]` if "uv_flip" else '
                                     '`[[0, 1], [1, 1], [1, 0]]`, for quads `[[0, 1], [1, 1], [1, 0], [0, 0]]` if '
                                     '"uv_flip" else `[[0, 0], [1, 0], [1, 1], [0, 1]]`'}

    class Fields(DeclarativeCompoundBlock.Fields):
        mapping = (BitFlagsBlock(flag_names=[(0, 'is_triangle'),
                                             (1, 'uv_flip'),
                                             (2, 'flip_normal'),
                                             (4, 'double_sided')]),
                   {'description': 'Polygon properties. "is_triangle" means that 3th and 4th vertices in the polygon '
                                   'are the same, "uv_flip" changes texture coordinates, "flip normal" inverts normal '
                                   'vector of the polygon, "double-sided" makes polygon visible from the other side.'})
        unk0 = (IntegerBlock(length=3),
                {'is_unknown': True})
        vertex_indices = (ArrayBlock(child=IntegerBlock(length=1), length=4),
                          {'description': 'Indexes of vertices'})
        texture_name = (UTF8Block(length=4),
                        {'description': 'ID of texture from neighbouring QFS file'})


class GeoMesh(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A single mesh, can use multiple textures'}

    class Fields(DeclarativeCompoundBlock.Fields):
        num_vrtx = (IntegerBlock(length=4),
                    {'description': 'number of vertices in block'})
        num_plgn = (IntegerBlock(length=4),
                    {'description': 'number of polygons in block'})
        pos = (Point3D(child_length=4, fraction_bits=16),
               {'description': 'position of part in 3d space. The unit is meter'})
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=8, required_value=0),
                {'is_unknown': True})
        unk3 = (IntegerBlock(length=8, required_value=1),
                {'is_unknown': True})
        unk4 = (IntegerBlock(length=8, required_value=1),
                {'is_unknown': True})
        vertices = (ArrayBlock(length=lambda ctx: ctx.data('num_vrtx'),
                               child=Point3D(child_length=2, fraction_bits=8)),
                    {'description': 'Vertex coordinates. The unit is meter'})
        offset = (BytesBlock(length=(lambda ctx: 0 if ctx.data('num_vrtx') % 2 == 0 else 6, '(num_vrtx % 2) ? 6 : 0')),
                  {'description': 'Data offset, happens when `num_vrtx` is odd'})
        polygons = (ArrayBlock(length=lambda ctx: ctx.data('num_plgn'),
                               child=GeoPolygon()),
                    {'description': 'Array of mesh polygons',
                     'custom_offset': '52 + ceil(num_vrtx/2)*12'})


class GeoGeometry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A set of 3D meshes, used for cars and props. Contains multiple meshes with '
                                     'high details, medium and low LOD-s. Below `part_hp_x` is a high-poly part, '
                                     '`part_mp_x` and `part_lp_x` are medium and low-poly parts respectively'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk1 = (ArrayBlock(child=IntegerBlock(length=4), length=32),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=8, required_value=0),
                {'is_unknown': True})
        part_hp_0 = (GeoMesh(),
                     {'description': 'High-Poly Additional Body Part'})
        part_hp_1 = (GeoMesh(),
                     {'description': 'High-Poly Main Body Part'})
        part_hp_2 = (GeoMesh(),
                     {'description': 'High-Poly Ground Part'})
        part_hp_3 = (GeoMesh(),
                     {'description': 'High-Poly Front Part'})
        part_hp_4 = (GeoMesh(),
                     {'description': 'High-Poly Back Part'})
        part_hp_5 = (GeoMesh(),
                     {'description': 'High-Poly Left Side Part'})
        part_hp_6 = (GeoMesh(),
                     {'description': 'High-Poly Right Side Part'})
        part_hp_7 = (GeoMesh(),
                     {'description': 'High-Poly Additional Left Side Part'})
        part_hp_8 = (GeoMesh(),
                     {'description': 'High-Poly Additional Right Side Part'})
        part_hp_9 = (GeoMesh(),
                     {'description': 'High-Poly Spoiler Part'})
        part_hp_10 = (GeoMesh(),
                      {'description': 'High-Poly Additional Part'})
        part_hp_11 = (GeoMesh(),
                      {'description': 'High-Poly Backlights'})
        part_hp_12 = (GeoMesh(),
                      {'description': 'High-Poly Front Right Wheel'})
        part_hp_13 = (GeoMesh(),
                      {'description': 'High-Poly Front Right Wheel Part'})
        part_hp_14 = (GeoMesh(),
                      {'description': 'High-Poly Front Left Wheel'})
        part_hp_15 = (GeoMesh(),
                      {'description': 'High-Poly Front Left Wheel Part'})
        part_hp_16 = (GeoMesh(),
                      {'description': 'High-Poly Rear Right Wheel'})
        part_hp_17 = (GeoMesh(),
                      {'description': 'High-Poly Rear Right Wheel Part'})
        part_hp_18 = (GeoMesh(),
                      {'description': 'High-Poly Rear Left Wheel'})
        part_hp_19 = (GeoMesh(),
                      {'description': 'High-Poly Rear Left Wheel Part'})
        part_mp_0 = (GeoMesh(),
                     {'description': 'Medium-Poly Additional Body Part'})
        part_mp_1 = (GeoMesh(),
                     {'description': 'Medium-Poly Main Body Part'})
        part_mp_2 = (GeoMesh(),
                     {'description': 'Medium-Poly Ground Part'})
        part_lp_0 = (GeoMesh(),
                     {'description': 'Low-Poly Wheel Part'})
        part_lp_1 = (GeoMesh(),
                     {'description': 'Low-Poly Main Part'})
        part_lp_2 = (GeoMesh(),
                     {'description': 'Low-Poly Side Part'})
        part_res_0 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_1 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_2 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_3 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_4 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_5 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
