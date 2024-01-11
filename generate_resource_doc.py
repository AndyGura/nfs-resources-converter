from library.read_blocks.array import ArrayBlock
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.literal import LiteralBlock
from library2.read_blocks import CompoundBlock, ArrayBlock, DataBlock
from resources.eac import bitmaps, fonts

EXPORT_RESOURCES = {
    'Archives': [
        # archives.ShpiBlock(),
        # archives.WwwwBlock(),
        # archives.SoundBank(),
    ],
    'Geometries': [
        # geometries.OripGeometry(),
        # geometries.OripPolygon(),
        # geometries.OripTextureName(),
        # geometries.RenderOrderBlock(),
    ],
    'Maps': [
        # maps.TriMap(),
        # maps.RoadSplinePoint(),
        # maps.ProxyObject(),
        # maps.ProxyObjectInstance(),
        # maps.TerrainEntry(),
        # maps.AIEntry(),
        # maps.ModelProxyObjectData(),
        # maps.BitmapProxyObjectData(),
        # maps.TwoSidedBitmapProxyObjectData(),
        # maps.UnknownProxyObjectData(),
    ],
    'Physics': [
        # car_specs.CarPerformanceSpec(),
        # car_specs.EngineTorqueRecord(),
        # car_specs.CarSimplifiedPerformanceSpec(),
    ],
    'Bitmaps': [
        # bitmaps.Bitmap16Bit0565(),
        bitmaps.Bitmap4Bit(),
        # bitmaps.Bitmap8Bit(),
        # bitmaps.Bitmap32Bit(),
        # bitmaps.Bitmap16Bit1555(),
        # bitmaps.Bitmap24Bit(),
    ],
    'Fonts': [
        fonts.FfnFont(),
        fonts.SymbolDefinitionRecord(),
    ],
    'Palettes': [
        # palettes.PaletteReference(),
        # palettes.Palette24BitDos(),
        # palettes.Palette24Bit(),
        # palettes.Palette32Bit(),
        # palettes.Palette16Bit(),
    ],
    'Audio': [
        # audios.AsfAudio(),
        # audios.EacsAudio(),
    ],
    'Misc': [
        # configs.TnfsConfigDat(),
        # configs.TrackStats(),
        # configs.BestRaceRecord(),
    ]
}


def render_value_doc_str(value: str) -> str:
    return str(value).replace('*', '\*')


def render_type(instance: DataBlock) -> str:
    schema = instance.schema
    if isinstance(instance, LiteralBlock):
        return 'One of types:<br/>' + '<br/>'.join(['- ' + render_type(x) for x in instance.possible_resources])
    if not isinstance(instance, CompoundBlock) or schema["inline_description"]:
        descr = schema['block_description']
        if isinstance(instance, ArrayBlock):
            if not isinstance(instance.child, CompoundBlock) or instance.child.schema["inline_description"]:
                size = render_value_doc_str(instance.child.size_doc_str)
                descr += f'<br/>Item size: {size} ' + ('byte' if size == '1' else 'bytes')
            descr += f'<br/>Item type: {render_type(instance.child)}'
        return descr
    name = instance.__class__.__name__.replace("Resource", "")
    return f'[{name}](#{name.lower()})'


with open('resources/README.md', 'w') as f:
    f.write(f"""# **File specs** #


# **Block specs** #""")
    for (heading, resources) in EXPORT_RESOURCES.items():
        f.write(f'\n## **{heading}** ##')
        for resource in resources:
            schema = resource.schema
            collapse_table = len(resource.Fields.fields) > 20
            f.write(f'\n### **{resource.__class__.__name__.replace("Resource", "")}** ###')
            f.write(f'\n#### **Size**: {render_value_doc_str(resource.size_doc_str)} bytes ####')
            if schema['block_description']:
                f.write(f'\n#### **Description**: {schema["block_description"]} ####')
            if collapse_table:
                f.write('\n<details>')
                f.write(f'\n<summary>Click to see block specs ({len(resource.Fields.fields)} fields)</summary>\n')
            f.write(f'\n| Offset | Name | Size (bytes) | Type | Description |')
            f.write(f'\n| --- | --- | --- | --- | --- |')
            offset_int = 0
            offset_lbl = ''
            for key, (field, extras) in resource.Fields.fields:
                if extras.get('custom_offset'):
                    try:
                        offset_int = int(extras.get('custom_offset'))
                        offset_lbl = ''
                    except (ValueError, TypeError):
                        offset_int = 0
                        offset_lbl = extras.get('custom_offset')
                if offset_int == 0 and offset_lbl:
                    offset = offset_lbl
                    if offset.startswith('+'):
                        offset = offset[1:]
                else:
                    offset = str(offset_int) + offset_lbl
                f.write(f'\n| {"-" if False else render_value_doc_str(offset)} | '
                        f'**{key}** | '
                        f'{render_value_doc_str(field.size_doc_str)} | '
                        f'{render_type(field)} | '
                        f'{extras.get("description", "Unknown purpose" if extras.get("is_unknown") else "-")} |')
                try:
                    offset_int += int(field.size_doc_str)
                except (ValueError, TypeError):
                    offset_lbl += '+' + field.size_doc_str
            if collapse_table:
                f.write('\n</details>\n')
