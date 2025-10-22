from library.read_blocks import DataBlock
from serializers.base import BaseFileSerializer, DelegateBlockSerializer, PlainBinarySerializer
from .archives import ShpiArchiveSerializer, WwwwArchiveSerializer, SoundBankSerializer, BigfArchiveSerializer
from .audios import EacsAudioSerializer, FfmpegSupportedAudioSerializer
from .bitmaps import BitmapSerializer, BitmapWithPaletteSerializer
from .fonts import FfnFontSerializer
from .geometries import OripGeometrySerializer, GeoGeometrySerializer
from .json import JsonSerializer
from .maps import TriMapSerializer, TrkMapSerializer, FrdMapSerializer
from .misc_serializers import ShpiTextSerializer
from .palettes import PaletteSerializer
from .videos import FfmpegSupportedVideoSerializer


def get_serializer(block: DataBlock, data) -> BaseFileSerializer:
    if isinstance(block, Exception):
        raise block
    serializer_class = block.serializer_class()
    if not serializer_class:
        raise NotImplementedError(f'Serializer for resource {block.__class__.__name__} not implemented!')
    return serializer_class()
