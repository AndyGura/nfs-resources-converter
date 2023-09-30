from library.read_blocks.array import ArrayBlock
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.data_block import DataBlock
from library.read_blocks.detached import DetachedBlock
from library.read_blocks.literal import LiteralBlock
from resources.eac import palettes, bitmaps, fonts, car_specs, maps, geometries, audios, archives, configs

EXPORT_RESOURCES = {
    'Archives': [
        archives.ShpiBlock(),
        archives.WwwwBlock(),
        archives.SoundBank(),
    ],
    'Geometries': [
        geometries.OripGeometry(),
        geometries.OripPolygon(),
        geometries.OripTextureName(),
        geometries.RenderOrderBlock(),
    ],
    'Maps': [
        maps.TriMap(),
        maps.RoadSplinePoint(),
        maps.ProxyObject(),
        maps.ProxyObjectInstance(),
        maps.TerrainEntry(),
        maps.AIEntry(),
        maps.ModelProxyObjectData(),
        maps.BitmapProxyObjectData(),
        maps.TwoSidedBitmapProxyObjectData(),
        maps.UnknownProxyObjectData(),
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
    ],
    'Audio': [
        audios.AsfAudio(),
        audios.EacsAudio(),
    ],
    'Misc': [
        configs.TnfsConfigDat(),
        configs.OpenTrackStats(),
        configs.ClosedTrackStats(),
        configs.BestRaceRecord(),
    ]
}


def render_range(field, min: int, max: int, render_hex: bool) -> str:
    if field is not None and isinstance(field, ArrayBlock) and field.length_label is not None:
        if field.child.get_size({}) == 1:
            return field.length_label
        if field.child.get_size({}) is None:
            return '?'
        return f'{field.child.get_size({})} * ({field.length_label})'
    if min == max:
        return hex(min) if render_hex else str(min)
    label = f'{hex(min) if render_hex else str(min)}..{hex(max) if render_hex else str(max)}'.replace('inf', '?')
    if label == '?..?':
        label = '?'
    return label


def render_type(instance: DataBlock) -> str:
    if isinstance(instance, LiteralBlock):
        return 'One of types:<br/>' + '<br/>'.join(['- ' + render_type(x) for x in instance.possible_resources])
    if not isinstance(instance, CompoundBlock) or instance.inline_description:
        descr = instance.block_description
        if isinstance(instance, ArrayBlock):
            if not isinstance(instance.child, CompoundBlock) or instance.child.inline_description:
                size = render_range(None, instance.child.get_min_size({}), instance.child.get_max_size({}), False)
                descr += f'<br/>Item size: {size} ' + ('byte' if size == '1' else 'bytes')
            descr += f'<br/>Item type: {render_type(instance.child)}'
        return descr
    name = instance.__class__.__name__.replace("Resource", "")
    return f'[{name}](#{name.lower()})'


with open('resources/README.md', 'w') as f:
    f.write(f"""# **File specs** #

**\*INFO** track settings with unknown purpose. That's a plain text file with some values, no problem to edit manually

**\*.AS4**, **\*.ASF**, **\*.EAS** audio + loop settings. {render_type(audios.AsfAudio())}

**\*.BNK** sound bank. {render_type(archives.SoundBank())}

**\*.CFM** car 3D model. {render_type(archives.WwwwBlock())} with 4 entries:
- {render_type(geometries.OripGeometry())} high-poly 3D model
- {render_type(archives.ShpiBlock())} textures for high-poly model
- {render_type(geometries.OripGeometry())} low-poly 3D model
- {render_type(archives.ShpiBlock())} textures for low-poly model

**\*.FAM** track textures, props, skybox. {render_type(archives.WwwwBlock())} with 4 entries:
- {render_type(archives.WwwwBlock())} (background) contains few {render_type(archives.ShpiBlock())} items, terrain textures
- {render_type(archives.WwwwBlock())} (foreground) contains few {render_type(archives.ShpiBlock())} items, prop textures
- {render_type(archives.ShpiBlock())} (skybox) contains horizon texture
- {render_type(archives.WwwwBlock())} (props) contains a series of consecutive {render_type(geometries.OripGeometry())} + {render_type(archives.ShpiBlock())} items, 3D props

**\*.FFN** bitmap font. {render_type(fonts.FfnFont())}

**\*.FSH** image archive. {render_type(archives.ShpiBlock())}

**\*.PBS** car physics. {render_type(car_specs.CarPerformanceSpec())}, **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.PDN** car characteristic for unknown purpose. {render_type(car_specs.CarSimplifiedPerformanceSpec())}, **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.QFS** image archive. {render_type(archives.ShpiBlock())}, **compressed** (compression algorithms not docummented, can be found in resources/eac/compressions/)

**\*.TGV** video, I just use ffmpeg to convert it

**\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. {render_type(maps.TriMap())}

**GAMEDATA\CONFIG\CONFIG.DAT** Player name, best times, whether warrior car unlocked etc. {render_type(configs.TnfsConfigDat())}


# **Block specs** #""")
    for (heading, resources) in EXPORT_RESOURCES.items():
        f.write(f'\n## **{heading}** ##')
        for resource in resources:
            collapse_table = len(resource.Fields.fields) > 20
            f.write(f'\n### **{resource.__class__.__name__.replace("Resource", "")}** ###')
            f.write(f'\n#### **Size**: {render_range(None, resource.get_min_size({}), resource.get_max_size({}), False)} bytes ####')
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
                f.write(f'\n| {"-" if isinstance(field, DetachedBlock) else render_range(None, offset_min, offset_max, False)} | '
                        f'**{key}**{" (optional)" if key in resource.Fields.optional_fields else ""} | '
                        f'{render_range(field, field.get_min_size({}), field.get_max_size({}), False)} | '
                        f'{render_type(field)} | '
                        f'{field.description or ("Unknown purpose" if key in resource.Fields.unknown_fields else "-")} |')
                if not isinstance(field, DetachedBlock):
                    offset_min += field.get_min_size({}) or 0
                    offset_max += field.get_max_size({}) or float('inf')
            if collapse_table:
                f.write('\n</details>\n')
