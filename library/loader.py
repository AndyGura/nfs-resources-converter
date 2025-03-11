from io import BufferedReader, BytesIO, SEEK_CUR
from os.path import getsize
from typing import Tuple


# this looks like a mess, but it is intended to be like that: by using local imports we dramatically increase
# performance, because we spawn process per file, and it doesn't need to load all those classes every time
def _find_block_class(file_path: str, header_str: str, header_bytes: bytes):
    if file_path:
        # test resource
        if file_path.endswith('nfsrc_test_resource.bin'):
            from resources.test_resource import TestResource
            return TestResource
        elif file_path.endswith('.BNK'):
            from resources.eac.archives import SoundBank
            return SoundBank
        elif file_path.endswith('.PBS_UNCOMPRESSED'):
            from resources.eac.car_specs import CarPerformanceSpec
            return CarPerformanceSpec
        elif file_path.endswith('.PDN_UNCOMPRESSED'):
            from resources.eac.car_specs import CarSimplifiedPerformanceSpec
            return CarSimplifiedPerformanceSpec
        elif file_path.endswith('CONFIG.DAT'):
            from resources.eac.configs import TnfsConfigDat
            return TnfsConfigDat
        elif file_path.upper().endswith('.GEO'):
            from resources.eac.geometries import GeoGeometry
            return GeoGeometry
        elif file_path.upper().endswith('.FRD'):
            from resources.eac.maps.nfs3 import FrdMap
            return FrdMap
    if header_str:
        if file_path and header_str == '#ver' and file_path.endswith('INFO'):
            from resources.eac.misc import DashDeclarationFile
            return DashDeclarationFile
        elif header_str == '1SNh':
            from resources.eac.audios import AsfAudio
            return AsfAudio
        elif header_str in ['kVGT', 'SCHl']:
            from resources.eac.videos import FfmpegSupportedVideo
            return FfmpegSupportedVideo
        elif header_str == 'SHPI':
            from resources.eac.archives import ShpiBlock
            return ShpiBlock
        elif header_str == 'wwww':
            from resources.eac.archives import WwwwBlock
            return WwwwBlock
        elif header_str == 'FNTF':
            from resources.eac.fonts import FfnFont
            return FfnFont
        elif header_str == 'ORIP':
            from resources.eac.geometries import OripGeometry
            return OripGeometry
        elif header_str == 'EACS':
            from resources.eac.audios import EacsAudioFile
            return EacsAudioFile
        elif header_str == 'BIGF':
            from resources.eac.archives import BigfBlock
            return BigfBlock
        elif header_str == 'TRAC':
            from resources.eac.maps import TrkMap
            return TrkMap
        elif header_str == 'COLL':
            from resources.eac.maps import TrkMapCol
            return TrkMapCol
    try:
        resource_id = header_bytes[0]
        if resource_id == 0x22:
            from resources.eac.palettes import Palette24BitDos
            return Palette24BitDos
        elif resource_id == 0x24:
            from resources.eac.palettes import Palette24Bit
            return Palette24Bit
        elif resource_id == 0x29:
            from resources.eac.palettes import Palette16BitDos
            return Palette16BitDos
        elif resource_id == 0x2A:
            from resources.eac.palettes import Palette32Bit
            return Palette32Bit
        elif resource_id == 0x2D:
            # TODO colors 15-0 ? found here https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
            from resources.eac.palettes import Palette16Bit
            return Palette16Bit
        # TODO PIXEL_PAL4_PSP https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
        # elif resource_id == 0x5C:
        #     pass
        # TODO PIXEL_P32_PSP https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
        # elif resource_id == 0x3B:
        #     pass
        # TODO PIXEL_4444_PSP https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
        # elif resource_id == 0x59:
        #     pass
        # TODO PIXEL_PAL8_PSP https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
        # elif resource_id == 0x5D:
        #     pass
        # TODO BitmapDXT1
        # elif resource_id == 0x60:
        #     pass
        # TODO BitmapDXT3
        # elif resource_id == 0x61:
        #     pass
        # TODO BitmapDXT5
        # elif resource_id == 0x62:
        #     pass
        # TODO Bitmap24Bit6666
        # elif resource_id == 0x66:
        #     pass
        # TODO Bitmap16Bit484
        # elif resource_id == 0x68:
        #     pass
        # TODO Bitmap32Bit1010102
        # elif resource_id == 0x6A:
        #     pass
        # TODO Bitmap16Bit4444
        # elif resource_id == 0x6D:
        #     pass
        elif resource_id == 0x6F:
            from resources.eac.misc import ShpiText
            return ShpiText
        elif resource_id == 0x78:
            from resources.eac.bitmaps import Bitmap16Bit0565
            return Bitmap16Bit0565
        # TODO Bitmap4Bit (with palette)
        # elif resource_id == 0x79:
        #     pass
        elif resource_id == 0x7A:
            from resources.eac.bitmaps import Bitmap4Bit
            return Bitmap4Bit
        elif resource_id == 0x7B:
            from resources.eac.bitmaps import Bitmap8Bit
            return Bitmap8Bit
        elif resource_id == 0x7C:
            from resources.eac.palettes import PaletteReference
            return PaletteReference
        elif resource_id == 0x7D:
            from resources.eac.bitmaps import Bitmap32Bit
            return Bitmap32Bit
        elif resource_id == 0x7E:
            from resources.eac.bitmaps import Bitmap16Bit1555
            return Bitmap16Bit1555
        elif resource_id == 0x7F:
            from resources.eac.bitmaps import Bitmap24Bit
            return Bitmap24Bit
        # QFS1
        # if resource_id & 0b0001_0000:
        elif header_bytes[1] == 0xfb and (resource_id & 0b1111_1110) == 0x10:
            from resources.eac.archives import RefPackBlock
            return RefPackBlock
        # AL2.QFS
        elif header_bytes[1] == 0xfb and resource_id == 0b0100_0110:
            from resources.eac.archives import Qfs2Block
            return Qfs2Block
        # AL1.QFS
        elif header_bytes[1] == 0xfb and resource_id in [0b0011_0000, 0b0011_0010, 0b0011_0100, 0b0011_0001,
                                                         0b0011_0011,
                                                         0b0011_0101]:
            from resources.eac.archives import Qfs3Block
            return Qfs3Block
        elif resource_id == 0x11:
            from resources.eac.maps import TriMap
            return TriMap
    except IndexError:
        pass
    return None


def probe_block_class(binary_file: [BufferedReader, BytesIO], file_path: str = None, resources_to_pick=None):
    header_bytes = binary_file.read(4)
    binary_file.seek(-len(header_bytes), SEEK_CUR)
    try:
        header_str = header_bytes.decode('utf8')
    except UnicodeDecodeError:
        header_str = None
    block_class = _find_block_class(file_path, header_str, header_bytes)
    if block_class and (not resources_to_pick or block_class in resources_to_pick):
        return block_class
    raise NotImplementedError('Don`t have parser for such resource')


def path_to_name(path: str) -> str:
    return path.replace('\\', '/').replace(':', '---DRIVE')


def id_to_path(id: str) -> str:
    return id.split('__')[0].replace('---DRIVE', ':')


# id example: /media/data/nfs/SIMDATA/CARFAMS/LDIABL.CFM__1/frnt
def require_resource(id: str) -> Tuple[Tuple[str, "DataBlock", dict], Tuple[str, "DataBlock", dict]]:
    file_path = id_to_path(id)
    (file_id, block, data) = require_file(file_path)
    if not data:
        return (id, None, None), (file_id, None, None)
    if file_path == id:
        return (file_id, block, data), (file_id, block, data)
    resource_path = [x for x in id.split('__')[1].split('/') if x]
    (res_block, res) = (block, data)
    for key in resource_path:
        (res_block, res) = res_block.get_child_block_with_data(res, key)
    return (id, res_block, res), (file_id, block, data)


# not shared between processes: in most cases if file requires another resource, it is in the same file, or it
# requires one external file multiple times. It will be more time-consuming to serialize/deserialize it for sharing
# between processes than load some file multiple times. + we avoid potential memory leaks
files_cache = {}


def clear_file_cache(path: str):
    try:
        name = path_to_name(path)
        del files_cache[name]
        from library.read_blocks import DataBlock
        DataBlock.root_read_ctx.children = [c for c in DataBlock.root_read_ctx.children if c.name != name]
    except KeyError:
        pass


def require_file(path: str) -> Tuple[str, "DataBlock", dict]:
    name = path_to_name(path)
    (block, data) = files_cache.get(name, (None, None))
    if block is None or data is None:
        with open(path, 'rb', buffering=100 * 1024 * 1024) as bdata:
            block_class = probe_block_class(bdata, path)
            block = block_class()
            data = block.unpack(bdata, name=name, read_bytes_amount=getsize(path))
            files_cache[name] = (block, data)
    return name, block, data
