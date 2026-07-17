import re
from datetime import datetime, timezone

from library.read_blocks import (CompoundBlock,
                                 ArrayBlock,
                                 DataBlock,
                                 DelegateBlock,
                                 Padding,
                                 EnumLookupDelegateBlock,
                                 LengthPrefixedArrayBlock,
                                 OptionalBlock)
from library.read_blocks.strings import LengthPrefixedUtf8Block, UTF8Block
from library.utils.docs import add_doc_numbers
from resources import eac, blackbox

def render_value_doc_str(value: str) -> str:
    return str(value).replace('*', '\\*')


def render_type(instance: DataBlock, possible_blocks_filter=None) -> str:
    schema = instance.schema
    if isinstance(instance, DelegateBlock):
        possible_blocks = [x for x in instance.possible_blocks
                           if (not possible_blocks_filter
                               or x.__class__ in possible_blocks_filter
                               or (not isinstance(x, CompoundBlock) or x.schema["inline_description"]))]
        if isinstance(instance, EnumLookupDelegateBlock):
            description = f'Type according to enum `{instance.enum_field}`:<br/>'
        else:
            description = f'One of types:<br/>'
        return description + '<br/>'.join(['- ' + render_type(x, possible_blocks_filter) for x in possible_blocks])
    if not isinstance(instance, CompoundBlock) or schema["inline_description"]:
        descr = schema['block_description']
        if isinstance(instance, OptionalBlock):
            return f'Optional (if {schema["criteria"]}): {render_type(instance.child, possible_blocks_filter)}'
        if isinstance(instance, ArrayBlock):
            if isinstance(instance, LengthPrefixedArrayBlock) or isinstance(instance, LengthPrefixedUtf8Block):
                descr += f'<br/>Length field type: {instance.length_block.schema["block_description"]}'
            if not isinstance(instance.child, CompoundBlock) or instance.child.schema["inline_description"]:
                size = render_value_doc_str(instance.child.size_doc_str)
                descr += f'<br/>Item size: {size} ' + ('byte' if size == '1' else 'bytes')
            descr += f'<br/>Item type: {render_type(instance.child, possible_blocks_filter)}'
        return descr
    name = instance.__class__.__name__.replace("Resource", "")
    if possible_blocks_filter and instance.__class__ not in possible_blocks_filter:
        print(f"WARNING: Block class {instance.__class__.__name__} is referenced but not presented in the file")
    return f'[{name}](#{name.lower()})'


def render_description(extras):
    description = extras.get("description", "Unknown purpose" if extras.get("is_unknown") else "-")
    # find parts in description like "<br/>- [GeoGeometry](#geogeometry)" and filter them with possible_blocks_filter
    if possible_blocks_filter:
        possible_block_class_names = [x.__name__.replace("Resource", "") for x in possible_blocks_filter]
        block_ref_pattern = re.compile(r'<br/>\s*-\s*\[([A-Za-z0-9_]+)\]\(#.*?\)')

        def remove_if_filtered_out(match):
            if match.group(1) not in possible_block_class_names:
                return ''
            return match.group(0)

        return block_ref_pattern.sub(remove_if_filtered_out, description)
    return description


EXPORT_RESOURCES = {
    'tnfsse': {
        'file_name': 'TNFS_SE.md',
        'title': 'TNFSSE (PC) file specs',
        'file_list': f"""**\\*INFO** track settings with unknown purpose. That's a plain text file with some values, no problem to edit manually

**\\*.AS4**, **\\*.ASF**, **\\*.EAS** audio + loop settings. {render_type(eac.audios.AsfAudio())}

**\\*.BNK** sound bank. {render_type(eac.archives.SoundBank())}

**\\*.CFM** car 3D model. {render_type(eac.archives.WwwwBlock())} with 4 entries:
- {render_type(eac.geometries.OripGeometry())} high-poly 3D model
- {render_type(eac.archives.ShpiBlock())} textures for high-poly model
- {render_type(eac.geometries.OripGeometry())} low-poly 3D model
- {render_type(eac.archives.ShpiBlock())} textures for low-poly model

**\\*.FAM** track textures, props, skybox. {render_type(eac.archives.WwwwBlock())} with 4 entries:
- {render_type(eac.archives.WwwwBlock())} (background) contains few {render_type(eac.archives.ShpiBlock())} items, terrain textures
- {render_type(eac.archives.WwwwBlock())} (foreground) contains few {render_type(eac.archives.ShpiBlock())} items, prop textures
- {render_type(eac.archives.ShpiBlock())} (skybox) contains horizon texture
- {render_type(eac.archives.WwwwBlock())} (props) contains a series of consecutive {render_type(eac.geometries.OripGeometry())} + {render_type(eac.archives.ShpiBlock())} items, 3D props

**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.PBS** car physics. {render_type(eac.car_specs.CarPerformanceSpec())}, [compressed](eac_compressions.md)

**\\*.PDN** car characteristic for unknown purpose. {render_type(eac.car_specs.CarSimplifiedPerformanceSpec())}, [compressed](eac_compressions.md)

**\\*.QFS** image archive. {render_type(eac.archives.ShpiBlock())}, [compressed](eac_compressions.md)

**\\*.TGV** video, I just use ffmpeg to convert it

**\\*.TRI** track path, terrain geometry, prop positions, various track properties, used by physics engine, camera work etc. {render_type(eac.maps.TriMap())}

**GAMEDATA\\CONFIG\\CONFIG.DAT** Player name, best times, whether warrior car unlocked etc. {render_type(eac.configs.TnfsConfigDat())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.PaletteReference(),
                eac.archives.WwwwBlock(),
                eac.archives.SoundBank(),
            ],
            'Geometries': [
                eac.geometries.OripGeometry(),
                eac.geometries.OripPolygon(),
                eac.geometries.OripTextureName(),
                eac.geometries.RenderOrderBlock(),
            ],
            'Maps': [
                eac.maps.TriMap(),
                eac.maps.RoadSplinePoint(),
                eac.maps.PropDescr(),
                eac.maps.MapProp(),
                eac.maps.TerrainEntry(),
                eac.maps.AIEntry(),
                eac.maps.ModelPropDescrData(),
                eac.maps.BitmapPropDescrData(),
                eac.maps.TwoSidedBitmapPropDescrData(),
            ],
            'Physics': [
                eac.car_specs.CarPerformanceSpec(),
                eac.car_specs.CarSimplifiedPerformanceSpec(),
            ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            'Audio': [
                eac.audios.AsfAudio(),
                eac.audios.EacsAudioFile(),
                eac.audios.SoundBankHeaderEntry(),
                eac.audios.EacsAudioHeader(),
            ],
            'Misc': [
                eac.configs.TnfsConfigDat(),
                eac.configs.TrackStats(),
                eac.configs.BestRaceRecord(),
            ]
        },
    },
    'nfs2': {
        'file_name': 'NFS2.md',
        'title': 'NFS2 file specs',
        'file_list': f"""**\\*.COL** track additional data. {render_type(eac.maps.MapColFile())}
        
**\\*.GEO** car 3D model. {render_type(eac.geometries.GeoGeometry())}
        
**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.MSK** archive with some data. {render_type(eac.archives.BigfBlock())}

**\\*.QFS** image archive. {render_type(eac.archives.ShpiBlock())}, [compressed](eac_compressions.md)

**\\*.TRK** main track file. {render_type(eac.maps.TrkMap())}

**\\*.UV** video, I just use ffmpeg to convert it

**\\*.VIV** archive with some data. {render_type(eac.archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.PaletteReference(),
                eac.archives.BigfBlock(),
                eac.archives.BigfItemDescriptionBlock(),
            ],
            'Geometries': [
                eac.geometries.GeoGeometry(),
                eac.geometries.GeoMesh(),
                eac.geometries.GeoPolygon(),
            ],
            'Maps': [
                # TRK
                eac.maps.TrkMap(),
                eac.maps.TrkSuperBlock(),
                eac.maps.TrkBlock(),
                # COL
                eac.maps.MapColFile(),
                eac.maps.ColExtraBlock(),
                eac.maps.TexturesMapExtraDataRecord(),
                eac.maps.PolygonMapExtraDataRecord(),
                eac.maps.MedianExtraDataRecord(),
                eac.maps.AnimatedPropPosition(),
                eac.maps.AnimatedPropPositionFrame(),
                eac.maps.PropExtraDataRecord(),
                eac.maps.PropDescriptionExtraDataRecord(),
                eac.maps.LanesExtraDataRecord(),
                eac.maps.RoadVectorsExtraDataRecord(),
                eac.maps.CollisionExtraDataRecord(),
                eac.maps.ColPolygon(),
            ],
            # 'Physics': [
            # ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            # 'Audio': [
            # ],
            'Misc': [
                eac.misc.ShpiText(),
            ]
        },
    },
    'nfs2se': {
        'file_name': 'NFS2_SE.md',
        'title': 'NFS2SE file specs',
        'file_list': f"""**\\*.COL** track additional data. {render_type(eac.maps.MapColFile())}
        
**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.QFS** image archive. {render_type(eac.archives.ShpiBlock())}, [compressed](eac_compressions.md)

**\\*.TRK** main track file. {render_type(eac.maps.TrkMap())}

**\\*.UV** video, I just use ffmpeg to convert it

**\\*.VIV** archive with some data. {render_type(eac.archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.PaletteReference(),
                eac.archives.BigfBlock(),
                eac.archives.BigfItemDescriptionBlock(),
            ],
            'Geometries': [
                eac.geometries.GeoGeometry(),
                eac.geometries.GeoMesh(),
                eac.geometries.GeoPolygon(),
            ],
            'Maps': [
                # TRK
                eac.maps.TrkMap(),
                eac.maps.TrkSuperBlock(),
                eac.maps.TrkBlock(),
                # COL
                eac.maps.MapColFile(),
                eac.maps.ColExtraBlock(),
                eac.maps.TexturesMapExtraDataRecord(),
                eac.maps.PolygonMapExtraDataRecord(),
                eac.maps.MedianExtraDataRecord(),
                eac.maps.AnimatedPropPosition(),
                eac.maps.AnimatedPropPositionFrame(),
                eac.maps.PropExtraDataRecord(),
                eac.maps.PropDescriptionExtraDataRecord(),
                eac.maps.LanesExtraDataRecord(),
                eac.maps.RoadVectorsExtraDataRecord(),
                eac.maps.CollisionExtraDataRecord(),
                eac.maps.ColPolygon(),
            ],
            # 'Physics': [
            # ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            # 'Audio': [
            # ],
            'Misc': [
                eac.misc.ShpiText(),
            ]
        },
    },
    'nfs3': {
        'file_name': 'NFS3.md',
        'title': 'NFS 3 Hot Pursuit file specs',
        'file_list': f"""**\\*.COL** track additional data. {render_type(eac.maps.MapColFile())}
        
**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FRD** main track file. {render_type(eac.maps.FrdMap())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.QFS** image archive. {render_type(eac.archives.ShpiBlock())}, [compressed](eac_compressions.md)

**\\*.VIV** archive with some data. {render_type(eac.archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.BigfBlock(),
                eac.archives.BigfItemDescriptionBlock(),
            ],
            # 'Geometries': [
            # ],
            'Maps': [
                # FRD
                eac.maps.FrdMap(),
                eac.maps.FrdBlock(),
                eac.maps.FrdPositionBlock(),
                eac.maps.FrdBlockPolygonData(),
                eac.maps.FrdBlockVroadData(),
                eac.maps.FrdPolyBlock(),
                eac.maps.FrdPolygonsBlock(),
                eac.maps.FrdPolygonRecord(),
                eac.maps.FrdPolyObjBlock(),
                eac.maps.FrdPolyObjPolygonsBlock(),
                eac.maps.ExtraObjectBlock(),
                eac.maps.ExtraObjectDataCrossType1(),
                eac.maps.AnimData(),
                eac.maps.ExtraObjectDataCrossType4(),
                eac.maps.TextureBlock(),
                # COL
                eac.maps.MapColFile(),
                eac.maps.ColExtraBlock(),
                eac.maps.TexturesMapExtraDataRecord(),
                eac.maps.PolygonMapExtraDataRecord(),
                eac.maps.MedianExtraDataRecord(),
                eac.maps.AnimatedPropPosition(),
                eac.maps.AnimatedPropPositionFrame(),
                eac.maps.PropExtraDataRecord(),
                eac.maps.PropDescriptionExtraDataRecord(),
                eac.maps.LanesExtraDataRecord(),
                eac.maps.RoadVectorsExtraDataRecord(),
                eac.maps.CollisionExtraDataRecord(),
                eac.maps.ColPolygon(),
            ],
            # 'Physics': [
            # ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            # 'Audio': [
            # ],
            # 'Misc': [
            # ]
        },
    },
    'nfs4': {
        'file_name': 'NFS4.md',
        'title': 'NFS 4 High Stakes file specs',
        'file_list': f"""**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}
        
**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.QFS** image archive. {render_type(eac.archives.ShpiBlock())}, [compressed](eac_compressions.md)

**\\*.VIV** archive with some data. {render_type(eac.archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.BigfBlock(),
                eac.archives.BigfItemDescriptionBlock(),
            ],
            # 'Geometries': [
            # ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            # 'Audio': [
            # ],
            # 'Misc': [
            # ]
        },
    },
    'nfs5': {
        'file_name': 'NFS5.md',
        'title': 'NFS 5 Porsche Unleashed file specs',
        'file_list': f"""**\\*.crp** geometry file. {render_type(eac.geometries.CrpGeometry())}, [compressed](eac_compressions.md)
        
**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.ENV** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.VIV** archive with some data. {render_type(eac.archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.BigfBlock(),
                eac.archives.BigfItemDescriptionBlock(),
            ],
            'Geometries': [
                eac.geometries.nfs5.CrpGeometry(),

                eac.geometries.nfs5.ArticlePart(),
                eac.geometries.nfs5.TextPart2(),
                eac.geometries.nfs5.TextPart4(),
                eac.geometries.nfs5.MaterialPart(),
                eac.geometries.nfs5.FSHPart(),
                eac.geometries.nfs5.CullingPart(),
                eac.geometries.nfs5.EffectPart(),
                eac.geometries.nfs5.NormalPart(),
                eac.geometries.nfs5.TrianglePart(),
                eac.geometries.nfs5.TransformationPart(),
                eac.geometries.nfs5.UVPart(),
                eac.geometries.nfs5.VertexPart(),
                eac.geometries.nfs5.UnkPart2(),
                eac.geometries.nfs5.UnkPart4(),

                eac.geometries.nfs5.MaterialPartData(),
                eac.geometries.nfs5.CullingPartData(),
                eac.geometries.nfs5.CullingInfoRow(),

                eac.geometries.nfs5.EffectPartData(),

                eac.geometries.nfs5.NormalPartData(),
                eac.geometries.nfs5.NormalInfoRow(),

                eac.geometries.nfs5.TrianglePartData(),
                eac.geometries.nfs5.TriangleInfoRowBase(),
                eac.geometries.nfs5.IndexRow(),

                eac.geometries.nfs5.UVData(),
                eac.geometries.nfs5.UVInfoRow(),

                eac.geometries.nfs5.VertexData(),
                eac.geometries.nfs5.VertexInfoRow(),
            ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            # 'Audio': [
            # ],
            # 'Misc': [
            # ]
        },
    },
    'nfs6': {
        'file_name': 'NFS6.md',
        'title': 'NFS 6 Hot Pursuit 2 file specs',
        'file_list': f"""**\\*.FFN** bitmap font. {render_type(eac.fonts.FfnFont())}

**\\*.FSH** image archive. {render_type(eac.archives.ShpiBlock())}

**\\*.VIV** archive with some data. {render_type(eac.archives.BigfBlock())}""",
        'blocks': {
            'Archives': [
                eac.archives.ShpiBlock(),
                eac.archives.BigfBlock(),
                eac.archives.BigfItemDescriptionBlock(),
            ],
            # 'Geometries': [
            # ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            'Images': [
                eac.bitmaps.EacImage(),
                eac.bitmaps.EacPalette(),
            ],
            'Fonts': [
                eac.fonts.FfnFont(),
                eac.fonts.GlyphDefinition(),
                eac.fonts.KerningItem(),
            ],
            # 'Audio': [
            # ],
            # 'Misc': [
            # ]
        },
    },
    'nfsu': {
        'file_name': 'NFSU.md',
        'title': 'NFS Underground file specs',
        'file_list': f"""Cars\\**\\GEOMETRY.BIN** car geometry. {render_type(blackbox.geometries.NfsuBinGeometry())}""",
        'blocks': {
            # 'Archives': [
            # ],
            'Geometries': [
                blackbox.geometries.NfsuBinGeometry(),
                blackbox.geometries.ZeroChunk(),
                blackbox.geometries.UnknownChunk(),
                blackbox.geometries.Chunk80034020(),
                blackbox.geometries.NfsuMeshChunk(),
                blackbox.geometries.NfsuMeshFacesChunk(),
                blackbox.geometries.Chunk00134BXX(),
                blackbox.geometries.Chunk80134100(),
                blackbox.geometries.Chunk00134002(),
                blackbox.geometries.Chunk00134003(),
                blackbox.geometries.Chunk00134011(),
                blackbox.geometries.Chunk00134012(),
                blackbox.geometries.Chunk00134013(),
                blackbox.geometries.Chunk001340XX(),
                blackbox.geometries.Chunk80134008(),
                blackbox.geometries.NfsuMeshDescriptorChunk(),
                blackbox.geometries.Chunk80134001(),
                blackbox.geometries.Chunk80134020(),
                blackbox.geometries.NfsuVec3(),
            ],
            # 'Maps': [
            # ],
            # 'Physics': [
            # ],
            # 'Images': [
            # ],
            # 'Fonts': [
            # ],
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
    old_contents = open('resources/' + game['file_name'], 'r').read()
    new_contents = f"""# **{game['title']}** #

*Last time updated: {datetime.now(timezone.utc)}*


# **Info by file extensions** #

{game['file_list']}

Did not find what you need or some given data is wrong? Please submit an
[issue](https://github.com/AndyGura/nfs-resources-converter/issues/new)


# **Block specs** #"""
    possible_blocks_filter = [res.__class__ for resources in game['blocks'].values() for res in resources]
    for (heading, resources) in game['blocks'].items():
        new_contents += f'\n## **{heading}** ##'
        for resource in resources:
            schema = resource.schema
            new_contents += f'\n### **{resource.__class__.__name__.replace("Resource", "")}** ###'
            new_contents += f'\n#### **Size**: {render_value_doc_str(resource.size_doc_str)} bytes ####'
            if schema['block_description']:
                new_contents += f'\n#### **Description**: {schema["block_description"]} ####'
            new_contents += f'\n| Offset | Name | Size (bytes) | Type | Description |'
            new_contents += f'\n| --- | --- | --- | --- | --- |'
            offset = '0'


            def render_field(offset, key, field, extras):
                return (f'\n| {render_value_doc_str(offset)} | '
                        f'**{key}** | '
                        f'{render_value_doc_str(field.size_doc_str)} | '
                        f'{render_type(field, possible_blocks_filter)} | '
                        f'{render_description(extras)} |')


            for key, field in resource.field_blocks:
                extras = resource.field_extras_map[key]
                usage = extras.get('usage', 'everywhere')
                if usage != 'everywhere' and 'doc' not in usage:
                    continue
                if extras.get('custom_offset'):
                    offset = extras.get('custom_offset')
                if isinstance(field, LengthPrefixedArrayBlock):
                    new_contents += render_field(offset, f'num_{key}', field.length_block,
                                                 {"description": f"Length of {key} array"})
                    offset = add_doc_numbers(offset, field.length_block.size_doc_str)
                    tmp_arr_field = ArrayBlock(child=field.child, length=lambda ctx: ctx.data(f"num_{key}"))
                    new_contents += render_field(offset, key, tmp_arr_field, extras)
                    offset = add_doc_numbers(offset, tmp_arr_field.size_doc_str)
                elif isinstance(field, LengthPrefixedUtf8Block):
                    new_contents += render_field(offset, f'len_{key}', field.length_block,
                                                 {"description": f"Length of '{key}' utf8 block"})
                    offset = add_doc_numbers(offset, field.length_block.size_doc_str)
                    tmp_utf_field = UTF8Block(length=lambda ctx: ctx.data(f"len_{key}"))
                    new_contents += render_field(offset, key, tmp_utf_field, extras)
                    offset = add_doc_numbers(offset, tmp_utf_field.size_doc_str)
                elif isinstance(field, Padding):
                    new_contents += render_field(offset, key, field, extras)
                    offset = field.to_descr
                else:
                    new_contents += render_field(offset, key, field, extras)
                    offset = add_doc_numbers(offset, field.size_doc_str)
    new_contents += '\n'

    if old_contents.split('\n')[3:] == new_contents.split('\n')[3:]:
        print('Skip writing ' + game['file_name'] + ': no changes')
    else:
        with open('resources/' + game['file_name'], 'w') as f:
            f.write(new_contents)
