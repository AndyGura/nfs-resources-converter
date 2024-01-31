from datetime import datetime, timezone

from library.read_blocks import CompoundBlock, ArrayBlock, DataBlock, DelegateBlock
from resources.eac import (archives,
                           bitmaps,
                           fonts,
                           palettes,
                           misc,
                           geometries,
                           maps,
                           audios,
                           configs,
                           car_specs)

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
    ],
    'Physics': [
        car_specs.CarPerformanceSpec(),
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
        palettes.Palette16BitDos(),
    ],
    'Audio': [
        audios.AsfAudio(),
        audios.EacsAudioFile(),
        audios.EacsAudioHeader(),
    ],
    'Misc': [
        configs.TnfsConfigDat(),
        configs.TrackStats(),
        configs.BestRaceRecord(),
        misc.ShpiText(),
    ]
}


def render_value_doc_str(value: str) -> str:
    return str(value).replace('*', '\*')


def render_type(instance: DataBlock) -> str:
    schema = instance.schema
    if isinstance(instance, DelegateBlock):
        return 'One of types:<br/>' + '<br/>'.join(['- ' + render_type(x) for x in instance.possible_blocks])
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
    f.write(f"""# **TNFSSE file specs** #
*Last time updated: {datetime.now(timezone.utc)}*


# **Info by file extensions** #

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
            schema = resource.schema
            f.write(f'\n### **{resource.__class__.__name__.replace("Resource", "")}** ###')
            f.write(f'\n#### **Size**: {render_value_doc_str(resource.size_doc_str)} bytes ####')
            if schema['block_description']:
                f.write(f'\n#### **Description**: {schema["block_description"]} ####')
            f.write(f'\n| Offset | Name | Size (bytes) | Type | Description |')
            f.write(f'\n| --- | --- | --- | --- | --- |')
            offset_int = 0
            offset_lbl = ''
            for key, field in resource.field_blocks:
                extras = resource.field_extras_map[key]
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
                    offset_lbl += ' + ' + field.size_doc_str
    f.write('\n')
