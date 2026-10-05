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

# size of FCE3 header. Offsets of all data tables are relative to it
FCE3_HEADER_SIZE = 0x1F04

FCE3_PART_NAMES = [
    'High body',
    'Left front wheel',
    'Right front wheel',
    'Left rear wheel',
    'Right rear wheel',
    'Medium body',
    'Medium right front wheel',
    'Medium left front wheel',
    'Medium right rear wheel',
    'Medium left rear wheel',
    'Low body',
    'Tiny body',
    'High headlights',
]


class FceColor(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Car color in HSB. Every component is 0..255: hue = degrees / 360 * 255, '
            'saturation = percent / 100 * 255, brightness = percent / 100 * 255',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        hue = (IntegerBlock(length=4), {'description': 'Hue'})
        saturation = (IntegerBlock(length=4), {'description': 'Saturation'})
        brightness = (IntegerBlock(length=4), {'description': 'Brightness'})
        transparency = (IntegerBlock(length=4), {'description': 'Transparency'})


class Fce3Triangle(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A single triangle of FCE mesh'}

    class Fields(DeclarativeCompoundBlock.Fields):
        tex_page = (
            IntegerBlock(length=4),
            {
                'description': 'Texture page index. 0 for car models (texture car00.tga), other values are used '
                'by multi-texture models like police officers'
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
                flag_names=[(0, 'matte'), (1, 'high_chrome'), (2, 'no_cull'), (3, 'semi_transparent')],
            ),
            {
                'description': 'Triangle flags. "matte": no environment reflection (underbody), "high_chrome": '
                'strong reflection (windows), "no_cull": triangle is visible from both sides, "semi_transparent": '
                'translucent triangle (windows). Triangle is visible behind a semi-transparent triangle only if it '
                'has smaller index'
            },
        )
        u = (
            ArrayBlock(child=DecimalBlock(length=4), length=3),
            {'description': 'Texture U coordinates of 3 vertices, 0..1'},
        )
        v = (
            ArrayBlock(child=DecimalBlock(length=4), length=3),
            {'description': 'Texture V coordinates of 3 vertices, 0..1, from bottom to top'},
        )


def _standard_offset(ctx, table: str) -> int:
    num_vertices = len(ctx.data('vertices'))
    num_triangles = len(ctx.data('triangles'))
    offsets = {
        'vertices': 0,
        'normals': 12 * num_vertices,
        'triangles': 24 * num_vertices,
        'reserve1': 24 * num_vertices + 56 * num_triangles,
        'reserve2': 56 * num_vertices + 56 * num_triangles,
        'reserve3': 68 * num_vertices + 56 * num_triangles,
    }
    return offsets[table]


class Fce3Geometry(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'FCE 3D model, version 3 (NFS3: Hot Pursuit). Used for cars (car.fce in '
            'car.viv), police officers, menu models. Consists of up to 64 parts, each of them is a separate mesh '
            'with own position, and up to 16 "dummies": named points, which are used for lights. Coordinate system: '
            'X points right, Y up, Z forward. The unit is meter. Texture is a TGA image car00.tga, which is located '
            'next to car.fce in car.viv',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
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
        vertices_offset = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, 'vertices')),
            {
                'usage': 'io,doc',
                'description': 'Offset of vertices table, relative to header end (0x1F04). Tables go one after another '
                'in order: vertices, normals, triangles, reserved areas 1-3',
            },
        )
        normals_offset = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, 'normals')),
            {'usage': 'io,doc', 'description': 'Offset of normals table, relative to header end'},
        )
        triangles_offset = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, 'triangles')),
            {'usage': 'io,doc', 'description': 'Offset of triangles table, relative to header end'},
        )
        reserve1_offset = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, 'reserve1')),
            {'usage': 'io,doc', 'description': 'Offset of reserved area 1, relative to header end'},
        )
        reserve2_offset = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, 'reserve2')),
            {'usage': 'io,doc', 'description': 'Offset of reserved area 2, relative to header end'},
        )
        reserve3_offset = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: _standard_offset(ctx, 'reserve3')),
            {'usage': 'io,doc', 'description': 'Offset of reserved area 3, relative to header end'},
        )
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
        num_primary_colors = (IntegerBlock(length=4), {'description': 'Number of primary car colors, 0..16'})
        primary_colors = (
            ArrayBlock(child=FceColor(), length=16),
            {'description': 'Primary car colors. Only first `num_primary_colors` are used'},
        )
        num_secondary_colors = (IntegerBlock(length=4), {'description': 'Number of secondary car colors, 0..16'})
        secondary_colors = (
            ArrayBlock(child=FceColor(), length=16),
            {'description': 'Secondary car colors. Only first `num_secondary_colors` are used'},
        )
        dummy_names = (
            ArrayBlock(child=UTF8Block(length=64), length=16),
            {
                'description': 'Names of dummies. The name defines what the dummy is: first letter is the kind '
                '("H": headlight, "T": taillight, "M": siren), third letter is the side ("L"/"R"), fourth letter '
                'is a flashing mode ("O"/"E" for odd/even flashing, "N" for no flashing)'
            },
        )
        part_names = (
            ArrayBlock(child=UTF8Block(length=64), length=64),
            {
                'description': 'Names of parts. For car models, the role of the part is defined by its index, '
                'not by name: ' + ', '.join(f'{i}: {x}' for i, x in enumerate(FCE3_PART_NAMES))
            },
        )
        unk1 = (BytesBlock(length=256), {'is_unknown': True})
        vertices = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=lambda ctx: ctx.data('num_vertices')),
            {'description': 'Vertex positions, relative to position of their part'},
        )
        normals = (
            ArrayBlock(child=Point3D(child=DecimalBlock(length=4)), length=lambda ctx: ctx.data('num_vertices')),
            {'description': 'Vertex normals'},
        )
        triangles = (
            ArrayBlock(child=Fce3Triangle(), length=lambda ctx: ctx.data('num_triangles')),
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

    def serializer_class(self):
        from serializers import Fce3GeometrySerializer

        return Fce3GeometrySerializer
