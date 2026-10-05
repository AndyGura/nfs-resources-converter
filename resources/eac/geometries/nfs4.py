from typing import Dict

from library.read_blocks import (
    DeclarativeCompoundBlock,
    UTF8Block,
    IntegerBlock,
    ArrayBlock,
    BitFlagsBlock,
    BytesBlock,
    DecimalBlock,
)
from resources.eac.fields.misc import Point3D
from resources.eac.geometries.nfs3 import FceColor

# size of FCE4 header. Offsets of all data tables are relative to it
FCE4_HEADER_SIZE = 0x2038

# first 4 bytes of FCE4 file: NFS4: High Stakes, Motor City Online
FCE4_VERSION = 0x00101014
FCE4M_VERSION = 0x00101015

FCE4_PART_NAMES = [
    (':HB', 'high body'),
    (':MB', 'medium body'),
    (':LB', 'low body'),
    (':TB', 'tiny body'),
    (':OT', 'top of convertible'),
    (':OL', 'pop-up headlights'),
    (':OS', 'optional spoiler'),
    (':OLB', 'left front brake'),
    (':ORB', 'right front brake'),
    (':OLM', 'left mirror'),
    (':ORM', 'right mirror'),
    (':OC', 'interior'),
    (':ODL', 'dashboard when lit'),
    (':OH', 'driver head'),
    (':OD', 'driver holding steering wheel'),
    (':OND', 'chair and steering wheel without driver'),
    (
        ':HLFW',
        'high left front wheel ("M" instead of "H" for medium wheels, "R" instead of "L" for right, '
        '"M"/"R" instead of "F" for middle/rear)',
    ),
]


class Fce4Color(FceColor):
    """The same as FCE3 color, but every component is 1 byte"""

    class Fields(DeclarativeCompoundBlock.Fields):
        hue = (IntegerBlock(length=1), {'description': 'Hue'})
        saturation = (IntegerBlock(length=1), {'description': 'Saturation'})
        brightness = (IntegerBlock(length=1), {'description': 'Brightness'})
        transparency = (IntegerBlock(length=1), {'description': 'Transparency'})


class Fce4Triangle(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A single triangle of FCE4 mesh'}

    class Fields(DeclarativeCompoundBlock.Fields):
        tex_page = (
            IntegerBlock(length=4),
            {
                'description': 'Texture page index. 0 for car models (texture car00.tga), other values are used '
                'by multi-texture models like police officers and pursuit road objects'
            },
        )
        vertex_indices = (
            ArrayBlock(child=IntegerBlock(length=4), length=3),
            {
                'description': 'Vertex indices, local to the part: add `part_first_vertex` of the part to get index '
                'in `vertices`'
            },
        )
        unk0 = (ArrayBlock(child=IntegerBlock(length=4), length=3), {'is_unknown': True})
        flags = (
            BitFlagsBlock(
                length=4,
                flag_names=[
                    (0, 'matte'),
                    (1, 'high_chrome'),
                    (2, 'no_cull'),
                    (3, 'semi_transparent'),
                    (5, 'window'),
                    (6, 'front_window'),
                    (7, 'left_window'),
                    (8, 'back_window'),
                    (9, 'right_window'),
                    (10, 'broken_window'),
                ],
            ),
            {
                'description': 'Triangle flags. "matte": no environment reflection (underbody), "high_chrome": '
                'strong reflection (windows), "no_cull": triangle is visible from both sides, "semi_transparent": '
                'translucent triangle (windows). Triangle is visible behind a semi-transparent triangle only if it '
                'has smaller index. "window" is set for all car windows, together with one of "front_window", '
                '"left_window", "back_window", "right_window". "broken_window" marks a texture of broken glass, '
                'which replaces the window after crash'
            },
        )
        u = (
            ArrayBlock(child=DecimalBlock(length=4), length=3),
            {'description': 'Texture U coordinates of 3 vertices, 0..1'},
        )
        v = (
            ArrayBlock(child=DecimalBlock(length=4), length=3),
            {'description': 'Texture V coordinates of 3 vertices, 0..1, from top to bottom'},
        )


# tables of FCE4 file in their usual order: (name, size per vertex, size per triangle)
FCE4_TABLES = [
    ('vertices', 12, 0),
    ('normals', 12, 0),
    ('triangles', 0, 56),
    ('reserve1', 32, 0),
    ('reserve2', 12, 0),
    ('reserve3', 12, 0),
    ('undamaged_vertices', 12, 0),
    ('undamaged_normals', 12, 0),
    ('damaged_vertices', 12, 0),
    ('damaged_normals', 12, 0),
    ('reserve4', 4, 0),
    ('animation_flags', 4, 0),
    ('reserve5', 4, 0),
    ('reserve6', 0, 12),
]


def _standard_offset(ctx, table: str) -> int:
    num_vertices = len(ctx.data('vertices'))
    num_triangles = len(ctx.data('triangles'))
    offset = 0
    for name, vertex_size, triangle_size in FCE4_TABLES:
        if name == table:
            return offset
        offset += vertex_size * num_vertices + triangle_size * num_triangles
    raise ValueError(table)


def _vector_table(description: str):
    return (
        ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=lambda ctx: ctx.data('num_vertices')),
        {'description': description},
    )


def _offset_field(table: str, description: str):
    return (
        IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, table)),
        {'usage': 'io,doc', 'description': description},
    )


class Fce4Geometry(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'FCE 3D model, version 4 (NFS4: High Stakes, Motor City Online). Used for cars '
            '(car.fce in car.viv), dashboards (dash.fce), police officers, helicopter, menu models. Consists of up '
            'to 64 parts, each of them is a separate mesh with own position, and up to 16 "dummies": named points, '
            'which are used for lights, license plates, smoke and water effects. In addition to FCE3, every vertex '
            'has a "damaged" position, used when car is crashed. Coordinate system: X points right, Y up, Z '
            'forward. The unit is meter. Texture is a TGA image car00.tga, which is located next to car.fce in '
            'car.viv. Alpha channel of the texture defines which car color is applied to the pixel: 224 primary, '
            '164 interior, 96 secondary, 32 driver hair color',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        version = (
            IntegerBlock(length=4),
            {'description': 'Format version. 0x00101014 in NFS4, 0x00101015 in Motor City Online (FCE4M)'},
        )
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        num_triangles = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('triangles'))),
            {'usage': 'io,doc', 'description': 'Number of triangles in the model'},
        )
        num_vertices = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('vertices'))),
            {'usage': 'io,doc', 'description': 'Number of vertices in the model'},
        )
        num_arts = (
            IntegerBlock(length=4),
            {'description': 'Number of "arts" (texture pages?). 1, unless triangles use non-zero `tex_page`'},
        )
        vertices_offset = _offset_field(
            'vertices',
            'Offset of vertices table, relative to header end (0x2038). Tables go one after another in order: '
            'vertices, normals, triangles, reserved areas 1-3, undamaged vertices, undamaged normals, damaged '
            'vertices, damaged normals, reserved area 4, animation flags, reserved areas 5-6',
        )
        normals_offset = _offset_field('normals', 'Offset of normals table, relative to header end')
        triangles_offset = _offset_field('triangles', 'Offset of triangles table, relative to header end')
        reserve1_offset = _offset_field('reserve1', 'Offset of reserved area 1, relative to header end')
        reserve2_offset = _offset_field('reserve2', 'Offset of reserved area 2, relative to header end')
        reserve3_offset = _offset_field('reserve3', 'Offset of reserved area 3, relative to header end')
        undamaged_vertices_offset = _offset_field(
            'undamaged_vertices', 'Offset of undamaged vertices table, relative to header end'
        )
        undamaged_normals_offset = _offset_field(
            'undamaged_normals', 'Offset of undamaged normals table, relative to header end'
        )
        damaged_vertices_offset = _offset_field(
            'damaged_vertices', 'Offset of damaged vertices table, relative to header end'
        )
        damaged_normals_offset = _offset_field(
            'damaged_normals', 'Offset of damaged normals table, relative to header end'
        )
        reserve4_offset = _offset_field('reserve4', 'Offset of reserved area 4, relative to header end')
        animation_flags_offset = _offset_field(
            'animation_flags', 'Offset of vertex animation flags table, relative to header end'
        )
        reserve5_offset = _offset_field('reserve5', 'Offset of reserved area 5, relative to header end')
        reserve6_offset = _offset_field('reserve6', 'Offset of reserved area 6, relative to header end')
        half_size = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Half-size of the whole model (bounding box, used for collisions)'},
        )
        num_dummies = (IntegerBlock(length=4), {'description': 'Number of used dummies, 0..16'})
        dummy_positions = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=16),
            {'description': 'Positions of dummies. Only first `num_dummies` are used'},
        )
        num_parts = (IntegerBlock(length=4), {'description': 'Number of used parts, 0..64'})
        part_positions = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=64),
            {
                'description': 'Positions of parts. Vertices of the part are relative to it. Only first `num_parts` '
                'are used'
            },
        )
        part_first_vertex = (
            ArrayBlock(child=IntegerBlock(length=4), length=64),
            {'description': 'Index of first vertex of each part'},
        )
        part_num_vertices = (
            ArrayBlock(child=IntegerBlock(length=4), length=64),
            {'description': 'Number of vertices in each part'},
        )
        part_first_triangle = (
            ArrayBlock(child=IntegerBlock(length=4), length=64),
            {'description': 'Index of first triangle of each part'},
        )
        part_num_triangles = (
            ArrayBlock(child=IntegerBlock(length=4), length=64),
            {'description': 'Number of triangles in each part'},
        )
        num_colors = (
            IntegerBlock(length=4),
            {
                'description': 'Number of car colors, 0..16. Every color is a set of 4 colors with the same index in '
                'tables below'
            },
        )
        primary_colors = (
            ArrayBlock(child=Fce4Color(), length=16),
            {'description': 'Primary car colors (car body). Only first `num_colors` are used'},
        )
        interior_colors = (
            ArrayBlock(child=Fce4Color(), length=16),
            {'description': 'Interior colors. Only first `num_colors` are used'},
        )
        secondary_colors = (
            ArrayBlock(child=Fce4Color(), length=16),
            {'description': 'Secondary car colors. Only first `num_colors` are used'},
        )
        driver_hair_colors = (
            ArrayBlock(child=Fce4Color(), length=16),
            {'description': 'Driver hair colors. Only first `num_colors` are used'},
        )
        unk1 = (BytesBlock(length=260), {'is_unknown': True})
        dummy_names = (
            ArrayBlock(child=UTF8Block(length=64), length=16),
            {
                'description': 'Names of dummies. The name defines what the dummy is. Special names: ":LICENSE", '
                '":LICMED", ":LICLOW" (license plate in high/medium/low LOD), ":LICENSE_EURO" (long license plate), '
                '":SMOKE" (smoke when shifting gears), ":WATER" (water generator). Other dummies are lights, where '
                'every letter is a property: 1st is kind ("H": headlight, "T": taillight, "B": brake light, "R": '
                'reverse light, "P": direction indicator, "S": siren), 2nd is color ("W": white, "R": red, "B": blue, '
                '"O": orange, "Y": yellow), 3rd is "Y"/"N" for breakable or not, 4th is flashing mode ("O"/"E" for '
                'odd/even flashing, "N" for no flashing), 5th is intensity 0..9, 6th and 7th are flashing time and '
                'delay 0..9'
            },
        )
        part_names = (
            ArrayBlock(child=UTF8Block(length=64), length=64),
            {
                'description': 'Names of parts. For car models, the role of the part is defined by its name: '
                + ', '.join(f'"{name}": {description}' for name, description in FCE4_PART_NAMES)
            },
        )
        unk2 = (BytesBlock(length=528), {'is_unknown': True})
        vertices = _vector_table('Vertex positions, relative to position of their part')
        normals = _vector_table('Vertex normals')
        triangles = (
            ArrayBlock(child=Fce4Triangle(), length=lambda ctx: ctx.data('num_triangles')),
            {'description': 'Triangles'},
        )
        reserve1 = (
            BytesBlock(length=(lambda ctx: 32 * ctx.data('num_vertices'), '32 * num_vertices')),
            {'is_unknown': True},
        )
        reserve2 = (
            BytesBlock(length=(lambda ctx: 12 * ctx.data('num_vertices'), '12 * num_vertices')),
            {'is_unknown': True},
        )
        reserve3 = (
            BytesBlock(length=(lambda ctx: 12 * ctx.data('num_vertices'), '12 * num_vertices')),
            {'is_unknown': True},
        )
        undamaged_vertices = _vector_table('Undamaged vertex positions, a copy of `vertices`')
        undamaged_normals = _vector_table('Undamaged vertex normals, a copy of `normals`')
        damaged_vertices = _vector_table('Vertex positions of crashed car, relative to position of their part')
        damaged_normals = _vector_table('Vertex normals of crashed car')
        reserve4 = (
            BytesBlock(length=(lambda ctx: 4 * ctx.data('num_vertices'), '4 * num_vertices')),
            {'is_unknown': True},
        )
        animation_flags = (
            ArrayBlock(child=IntegerBlock(length=4), length=lambda ctx: ctx.data('num_vertices')),
            {
                'description': 'Vertex animation flags. Used by driver part ":OD": vertex with value 4 does not '
                'move, vertex with value 0 rotates together with steering wheel'
            },
        )
        reserve5 = (
            BytesBlock(length=(lambda ctx: 4 * ctx.data('num_vertices'), '4 * num_vertices')),
            {'is_unknown': True},
        )
        reserve6 = (
            BytesBlock(
                length=(
                    lambda ctx: (
                        12 * ctx.data('num_triangles')
                        + (ctx.data('num_vertices') if ctx.data('version') == FCE4M_VERSION else 0)
                    ),
                    '12 * num_triangles (+ num_vertices in FCE4M)',
                )
            ),
            {'is_unknown': True},
        )

    def serializer_class(self):
        from serializers import Fce4GeometrySerializer

        return Fce4GeometrySerializer
