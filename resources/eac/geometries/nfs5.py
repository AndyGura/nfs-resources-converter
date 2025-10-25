from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 BytesBlock)


class Article(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(required_value='itrA', length=4),
                       {'description': 'Resource ID'})
        header_info = (IntegerBlock(length=4, required_value=0x1A),
                       {'is_unknown': True})
        len_parttable = (IntegerBlock(length=4),
                         {'description': 'Length of Parttable pointed to (* 16)'})
        offset = (IntegerBlock(length=4),
                  {'description': 'Offset (Relative from current Article offset * 16)'})


class MiscPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=4),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'description': 'Offset (Relative from current MiscPart offset)'})


class MaterialPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        index = (IntegerBlock(length=2),
                 {'description': 'Index'})
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("tm"/"mt")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'description': 'Offset (Relative from current MaterialPart offset)'})


class FSHPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        index = (IntegerBlock(length=2),
                 {'description': 'Index'})
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("fs"/"sf")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        num_fsh = (IntegerBlock(length=4),
                   {'description': 'Number of FSH files'})
        offset = (IntegerBlock(length=4),
                  {'description': 'Offset (Relative from current FSHPart offset)'})


class CrpGeometry(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(required_value=' raC', length=4),
                       {'description': 'Resource ID'})
        header_info = (IntegerBlock(length=4, programmatic_value=lambda ctx: 0x1A | (len(ctx.data('articles')) << 5)),
                       {'description': 'Header info: 5 bits: unknown (always seems to be 0x1A), '
                                       '27 bits: number of parts'})
        num_miscdata = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('misc_parts'))),
                        {'description': 'Number of misc data blocks'})
        articles_offset = (IntegerBlock(length=4, required_value=1),
                           {'description': 'Offset to articles block'})
        articles = (ArrayBlock(child=Article(), length=lambda ctx: ctx.data('header_info') >> 5),
                    {'description': 'Array of articles'})
        misc_parts = (ArrayBlock(child=MiscPart(), length=lambda ctx: ctx.data('num_miscdata')),
                      {'description': 'Array of misc parts'})
        unk = (BytesBlock(length=128),
               {'is_unknown': True})
