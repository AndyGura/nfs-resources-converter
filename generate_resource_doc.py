import os

from resources.eac import palettes, bitmaps
from resources.fields import ReadBlock, ResourceField, ArrayField

EXPORT_RESOURCES = {
    'Bitmaps': [
        bitmaps.Bitmap16Bit1555(),
    ],
    'Palettes': [
        palettes.Palette24BitDosResource(),
        palettes.Palette24BitResource(),
        palettes.Palette32BitResource(),
        palettes.Palette16BitResource(),
    ]
}


def render_range(min: int, max: int, render_hex: bool) -> str:
    if min == max:
        return hex(min) if render_hex else str(min)
    return f'{hex(min) if render_hex else str(min)}..{hex(max) if render_hex else str(max)}'


def render_type(instance: ReadBlock) -> str:
    if isinstance(instance, ResourceField):
        descr = instance.block_description
        if isinstance(instance, ArrayField):
            if isinstance(instance.child, ResourceField):
                size = render_range(instance.child.min_size, instance.child.max_size, False)
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
            f.write(f'\n### **{resource.__class__.__name__.replace("Resource", "")}** ###')
            f.write(f'\n#### **Size**: {render_range(resource.min_size, resource.max_size, False)} bytes ####')
            if resource.block_description:
                f.write(f'\n#### **Description**: {resource.block_description} ####')
            f.write(f'\n| Offset | Name | Size (bytes) | Type | Description |')
            f.write(f'\n| --- | --- | --- | --- | --- |')
            offset_min = 0
            offset_max = 0
            for key, field in resource.Fields.fields:
                f.write(f'\n| {render_range(offset_min, offset_max, False)} | **{key}** | {render_range(field.min_size, field.max_size, False)} | {render_type(field)} | {field.description or "-"} |')
                offset_min += field.min_size
                offset_max += field.max_size
