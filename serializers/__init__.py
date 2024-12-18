import settings
from library.read_blocks import DataBlock, DelegateBlock
from library.utils import my_import
from serializers.base import BaseFileSerializer, DelegateBlockSerializer, PlainBinarySerializer
from .archives import ShpiArchiveSerializer, WwwwArchiveSerializer, SoundBankSerializer, BigfArchiveSerializer
from .audios import EacsAudioSerializer, FfmpegSupportedAudioSerializer
from .bitmaps import BitmapSerializer, BitmapWithPaletteSerializer
from .fonts import FfnFontSerializer
from .geometries import OripGeometrySerializer, GeoGeometrySerializer
from .json import JsonSerializer
from .maps import TriMapSerializer, TrkMapSerializer
from .misc_serializers import ShpiTextSerializer
from .palettes import PaletteSerializer
from .videos import FfmpegSupportedVideoSerializer


def get_serializer(block: DataBlock, data) -> BaseFileSerializer:
    if isinstance(block, Exception):
        raise block
    if isinstance(block, DelegateBlock):
        return DelegateBlockSerializer()
    serializer_class_name = settings.SERIALIZER_CLASSES.get(block.__class__.__name__)
    serializer_class = None
    if serializer_class_name:
        try:
            serializer_class = my_import(f'serializers.{serializer_class_name}')
        except ImportError as ex:
            pass
    if not serializer_class_name or not serializer_class:
        raise NotImplementedError(f'Serializer for resource {block.__class__.__name__} not implemented!')
    return serializer_class()
