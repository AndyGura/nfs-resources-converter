import inspect
import os
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from library.read_blocks.array import ArrayBlock
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.literal import LiteralBlock
from library.read_blocks.read_block import ReadBlock
from resources.eac import palettes, bitmaps, fonts, car_specs, maps, geometries

EXPORT_RESOURCES = {
    'Geometries': [
        geometries.OripGeometry(),
        geometries.OripPolygon(),
    ],
    'Maps': [
        maps.TriMap(),
        maps.RoadSplinePoint(),
        maps.ProxyObject(),
        maps.ProxyObjectInstance(),
        maps.TerrainEntry(),
    ],
    'Physics': [
        car_specs.CarPerformanceSpec(),
        car_specs.EngineTorqueRecord(),
        car_specs.CarSimplifiedPerformanceSpec(),
    ],
    'Bitmaps': [
        bitmaps.Bitmap16Bit0565(),
        bitmaps.Bitmap4Bit(),
        bitmaps.Bitmap8Bit(),
        bitmaps.Bitmap32Bit(),
        bitmaps.Bitmap16Bit1555(),
        bitmaps.Bitmap24Bit(),
    ],
    'Fonts': [
        fonts.FfnFont(),
        fonts.SymbolDefinitionRecord(),
    ],
    'Palettes': [
        palettes.PaletteReference(),
        palettes.Palette24BitDos(),
        palettes.Palette24Bit(),
        palettes.Palette32Bit(),
        palettes.Palette16Bit(),
    ]
}


def render_range(field, min: int, max: int, render_hex: bool) -> str:
    if field is not None and isinstance(field, ArrayBlock) and field.length_label is not None:
        if field.child.size == 1:
            return field.length_label
        return f'{field.child.size} * ({field.length_label})'
    if min == max:
        return hex(min) if render_hex else str(min)
    label = f'{hex(min) if render_hex else str(min)}..{hex(max) if render_hex else str(max)}'.replace('inf', '?')
    if label == '?..?':
        label = '?'
    return label


def render_type(instance: ReadBlock) -> str:
    if isinstance(instance, LiteralBlock):
        return 'One of types:<br/>' + '<br/>'.join([render_type(x) for x in instance.possible_resources])
    if not isinstance(instance, CompoundBlock) or instance.inline_description:
        descr = instance.block_description
        if isinstance(instance, ArrayBlock):
            if not isinstance(instance.child, CompoundBlock) or instance.child.inline_description:
                size = render_range(None, instance.child.min_size, instance.child.max_size, False)
                descr += f'<br/>Item size: {size} ' + ('byte' if size == '1' else 'bytes')
            descr += f'<br/>Item type: {render_type(instance.child)}'
        return descr
    name = instance.__class__.__name__.replace("Resource", "")
    return f'[{name}](#{name.lower()})'


script_path = os.path.realpath(__file__)
md_name = script_path.replace('generate_resource_doc.py', 'resources/README.md')

with open(md_name, 'w') as f:
    f.write('# **File specs** #')
    for (heading, resources) in EXPORT_RESOURCES.items():
        f.write(f'\n## **{heading}** ##')
        for resource in resources:
            collapse_table = len(resource.Fields.fields) > 16
            f.write(f'\n### **{resource.__class__.__name__.replace("Resource", "")}** ###')
            f.write(f'\n#### **Size**: {render_range(None, resource.min_size, resource.max_size, False)} bytes ####')
            if resource.block_description:
                f.write(f'\n#### **Description**: {resource.block_description} ####')
            if collapse_table:
                f.write('\n<details>')
                f.write(f'\n<summary>Click to see block specs ({len(resource.Fields.fields)} fields)</summary>\n')
            f.write(f'\n| Offset | Name | Size (bytes) | Type | Description |')
            f.write(f'\n| --- | --- | --- | --- | --- |')
            offset_min = 0
            offset_max = 0
            for key, field in resource.Fields.fields:
                f.write(f'\n| {render_range(None, offset_min, offset_max, False)} | '
                        f'**{key}**{" (optional)" if key in resource.Fields.optional_fields else ""} | '
                        f'{render_range(field, field.min_size, field.max_size, False)} | '
                        f'{render_type(field)} | '
                        f'{field.description or "-"} |')
                offset_min += field.min_size
                offset_max += field.max_size
            if collapse_table:
                f.write('\n</details>\n')
