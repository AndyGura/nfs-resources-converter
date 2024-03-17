from datetime import datetime, timezone

from library.read_blocks import CompoundBlock, ArrayBlock, DataBlock, DelegateBlock, SkipBlock
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


def render_value_doc_str(value: str) -> str:
    return str(value).replace('*', '\*')


def render_type(instance: DataBlock, possible_blocks_filter=None) -> str:
    schema = instance.schema
    if isinstance(instance, DelegateBlock):
        # cleanup: remove SkipBlock and blocks which should be referenced by link but do not exist in documentation
        # for this game. For instance SHPI archive in NFS2 has greater variety of possible image resources than TNFS
        possible_blocks = [x for x in instance.possible_blocks
                           if not isinstance(x, SkipBlock) and (
                                   not possible_blocks_filter
                                   or x.__class__ in possible_blocks_filter
                                   or (not isinstance(x, CompoundBlock) or x.schema["inline_description"]))]
        return 'One of types:<br/>' + '<br/>'.join(['- ' + render_type(x, possible_blocks_filter)
                                                    for x in possible_blocks])
    if not isinstance(instance, CompoundBlock) or schema["inline_description"]:
        descr = schema['block_description']
        if isinstance(instance, ArrayBlock):
            if not isinstance(instance.child, CompoundBlock) or instance.child.schema["inline_description"]:
                size = render_value_doc_str(instance.child.size_doc_str)
                descr += f'<br/>Item size: {size} ' + ('byte' if size == '1' else 'bytes')
            descr += f'<br/>Item type: {render_type(instance.child, possible_blocks_filter)}'
        return descr
    name = instance.__class__.__name__.replace("Resource", "")
    return f'[{name}](#{name.lower()})'


EXPORT_RESOURCES = {
    'tnfsse': {
        'file_name': 'TNFS_SE.md',
        'title': 'TNFSSE (PC) file specs',
        'file_list': f"""**\*INFO** track settings with unknown purpose. That's a plain text file with some values, no problem to edit manually

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

**\*.PBS** car physics. {render_type(car_specs.CarPerformanceSpec())}, **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.PDN** car characteristic for unknown purpose. {render_type(car_specs.CarSimplifiedPerformanceSpec())}, **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.QFS** image archive. {render_type(archives.ShpiBlock())}, **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.TGV** video, I just use ffmpeg to convert it

**\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. {render_type(maps.TriMap())}

**GAMEDATA\CONFIG\CONFIG.DAT** Player name, best times, whether warrior car unlocked etc. {render_type(configs.TnfsConfigDat())}""",
        'blocks': {
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
                maps.PropDescr(),
                maps.MapProp(),
                maps.TerrainEntry(),
                maps.AIEntry(),
                maps.ModelPropDescrData(),
                maps.BitmapPropDescrData(),
                maps.TwoSidedBitmapPropDescrData(),
            ],
            'Physics': [
                car_specs.CarPerformanceSpec(),
                car_specs.CarSimplifiedPerformanceSpec(),
            ],
            'Bitmaps': [
                bitmaps.Bitmap4Bit(),
                bitmaps.Bitmap8Bit(),
            ],
            'Fonts': [
                fonts.FfnFont(),
                fonts.GlyphDefinition(),
            ],
            'Palettes': [
                palettes.PaletteReference(),
                palettes.Palette24BitDos(),
                palettes.Palette24Bit(),
            ],
            'Audio': [
                audios.AsfAudio(),
                audios.EacsAudioFile(),
                audios.SoundBankHeaderEntry(),
                audios.EacsAudioHeader(),
            ],
            'Misc': [
                configs.TnfsConfigDat(),
                configs.TrackStats(),
                configs.BestRaceRecord(),
            ]
        },
    },
    'nfs2': {
        'file_name': 'NFS2.md',
        'title': 'NFS2 file specs',
        'file_list': f"""**\*.GEO** car 3D model. {render_type(geometries.GeoGeometry())}
        
**\*.FFN** bitmap font. {render_type(fonts.FfnFont())}

**\*.FSH** image archive. {render_type(archives.ShpiBlock())}

**\*.MSK** archive with some data. {render_type(archives.BigfBlock())}

**\*.QFS** image archive. {render_type(archives.ShpiBlock())}, **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.UV** video, I just use ffmpeg to convert it

**\*.VIV** archive with some data. {render_type(archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                archives.ShpiBlock(),
                archives.BigfBlock(),
            ],
            'Geometries': [
                geometries.GeoGeometry(),
                geometries.GeoMesh(),
                geometries.GeoPolygon(),
            ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            'Bitmaps': [
                bitmaps.Bitmap4Bit(),
                bitmaps.Bitmap8Bit(),
                bitmaps.Bitmap16Bit0565(),
                bitmaps.Bitmap24Bit(),
                bitmaps.Bitmap32Bit(),
            ],
            'Fonts': [
                fonts.FfnFont(),
                fonts.GlyphDefinition(),
            ],
            'Palettes': [
                palettes.PaletteReference(),
                palettes.Palette24Bit(),
                palettes.Palette32Bit(),
            ],
            # 'Audio': [
            # ],
            'Misc': [
                misc.ShpiText(),
            ]
        },
    },
    'nfs2se': {
        'file_name': 'NFS2_SE.md',
        'title': 'NFS2SE file specs',
        'file_list': f"""**\*.FFN** bitmap font. {render_type(fonts.FfnFont())}

**\*.FSH** image archive. {render_type(archives.ShpiBlock())}

**\*.QFS** image archive. {render_type(archives.ShpiBlock())}, **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.UV** video, I just use ffmpeg to convert it

**\*.VIV** archive with some data. {render_type(archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                archives.ShpiBlock(),
                archives.BigfBlock(),
            ],
            'Geometries': [
                geometries.GeoGeometry(),
                geometries.GeoMesh(),
                geometries.GeoPolygon(),
            ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            'Bitmaps': [
                bitmaps.Bitmap4Bit(),
                bitmaps.Bitmap8Bit(),
                bitmaps.Bitmap16Bit0565(),
                bitmaps.Bitmap16Bit1555(),
                bitmaps.Bitmap24Bit(),
                bitmaps.Bitmap32Bit(),
            ],
            'Fonts': [
                fonts.FfnFont(),
                fonts.GlyphDefinition(),
            ],
            'Palettes': [
                palettes.PaletteReference(),
                palettes.Palette16BitDos(),
                palettes.Palette16Bit(),
                palettes.Palette24Bit(),
                palettes.Palette32Bit(),
            ],
            # 'Audio': [
            # ],
            'Misc': [
                misc.ShpiText(),
            ]
        },
    },
    'nfs3': {
        'file_name': 'NFS3.md',
        'title': 'NFS 3 Hot Pursuit file specs',
        'file_list': f"""**\*.FFN** bitmap font. {render_type(fonts.FfnFont())}

**\*.FSH** image archive. {render_type(archives.ShpiBlock())}

**\*.QFS** image archive. {render_type(archives.ShpiBlock())}, **compressed** (compression algorithms not documented, can be found in resources/eac/compressions/)

**\*.VIV** archive with some data. {render_type(archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                archives.ShpiBlock(),
                archives.BigfBlock(),
            ],
            # 'Geometries': [
            # ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            'Bitmaps': [
                bitmaps.Bitmap4Bit(),
                bitmaps.Bitmap8Bit(),
                bitmaps.Bitmap16Bit0565(),
                bitmaps.Bitmap16Bit1555(),
                bitmaps.Bitmap32Bit(),
                bitmaps.Bitmap24Bit(),
            ],
            'Fonts': [
                fonts.FfnFont(),
                fonts.GlyphDefinition(),
            ],
            'Palettes': [
                palettes.Palette16Bit(),
                palettes.Palette32Bit(),
            ],
            # 'Audio': [
            # ],
            # 'Misc': [
            # ]
        },
    },
}

with open('resources/README.md', 'w') as f:
    f.write(f"# **File specs per game** #\n\n")
    for game in EXPORT_RESOURCES.values():
        f.write(f"- [{game['title']}]({game['file_name']})\n\n")

for game in EXPORT_RESOURCES.values():
    with open('resources/' + game['file_name'], 'w') as f:
        f.write(f"""# **{game['title']}** #

*Last time updated: {datetime.now(timezone.utc)}*


# **Info by file extensions** #

{game['file_list']}

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #""")
        possible_blocks_filter = [res.__class__ for resources in game['blocks'].values() for res in resources]
        for (heading, resources) in game['blocks'].items():
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
                            f'{render_type(field, possible_blocks_filter)} | '
                            f'{extras.get("description", "Unknown purpose" if extras.get("is_unknown") else "-")} |')
                    try:
                        offset_int += int(field.size_doc_str)
                    except (ValueError, TypeError):
                        if '..' in field.size_doc_str and (offset_lbl == '' or '..' in offset_lbl):
                            [fmn, fmx] = field.size_doc_str.split('..')
                            if offset_lbl == '':
                                if offset_int == 0:
                                    offset_lbl = field.size_doc_str
                                else:
                                    try:
                                        mn = str(int(fmn) + offset_int)
                                        mx = str(int(fmx) + offset_int) if fmx != '?' else '?'
                                        offset_int = 0
                                        offset_lbl = f'{mn}..{mx}'
                                    except:
                                        offset_int = 0
                                        offset_lbl = '?'
                            else:
                                [omn, omx] = offset_lbl.split('..')
                                mn = str(int(fmn) + int(omn))
                                mx = str(int(fmx) + int(omx)) if (fmx != '?' and omx != '?') else '?'
                                offset_lbl = f'{mn}..{mx}'
                        else:
                            offset_lbl += ' + ' + field.size_doc_str
        f.write('\n')
