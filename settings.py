# ======================================================= GENERIC ======================================================
blender_executable = 'blender'
# blender_executable = '/Applications/Blender.app/Contents/MacOS/Blender'
# blender_executable = 'C:\\Program Files\\Blender Foundation\\Blender 3.5\\blender.exe'

ffmpeg_executable = 'ffmpeg'

# amount of processes to be spawned.
# 0 means "use the amount of CPU cores"
multiprocess_processes_count = 0

print_errors = False
print_blender_log = False

# ================================================= CONVERTING OPTIONS =================================================
# classes map, which export blocks data to common formats
SERIALIZER_CLASSES = {
    'Bitmap16Bit0565': 'BitmapSerializer',
    'Bitmap16Bit1555': 'BitmapSerializer',
    'Bitmap24Bit': 'BitmapSerializer',
    'Bitmap32Bit': 'BitmapSerializer',
    'Bitmap4Bit': 'BitmapSerializer',
    'Bitmap8Bit': 'BitmapWithPaletteSerializer',
    'CarPerformanceSpec': 'JsonSerializer',
    'CarSimplifiedPerformanceSpec': 'JsonSerializer',
    'DashDeclarationFile': 'JsonSerializer',
    'FfnFont': 'FfnFontSerializer',
    'Palette16Bit': 'PaletteSerializer',
    'Palette16BitDos': 'PaletteSerializer',
    'Palette24BitDos': 'PaletteSerializer',
    'Palette24Bit': 'PaletteSerializer',
    'Palette32Bit': 'PaletteSerializer',
    'TriMap': 'TriMapSerializer',
    'TrkMap': 'TrkMapSerializer',
    'TrkMapCol': 'JsonSerializer',
    'OripGeometry': 'OripGeometrySerializer',
    'GeoGeometry': 'GeoGeometrySerializer',
    'ShpiBlock': 'ShpiArchiveSerializer',
    'WwwwBlock': 'WwwwArchiveSerializer',
    'BigfBlock': 'BigfArchiveSerializer',
    'FfmpegSupportedVideo': 'FfmpegSupportedVideoSerializer',
    'SoundBank': 'SoundBankSerializer',
    'EacsAudioFile': 'EacsAudioSerializer',
    'AsfAudio': 'FfmpegSupportedAudioSerializer',
    'TnfsConfigDat': 'JsonSerializer',
    'ShpiText': 'ShpiTextSerializer',
    'BytesBlock': 'PlainBinarySerializer',
}

# skip saving palette, image positions
images__save_images_only = False

# for car sfx for engine, honk, additionally export long audio, where the sample repeated 16 times
audio__save_car_sfx_loops = False

# saves each terrain mesh chunk as separate obj/blend file and main file with road path.
# If false builds entire map into single file
maps__save_as_chunked = False
# places boxes with collision, where invisible wall is located
maps__save_invisible_wall_collisions = False  # this one will consume time...
maps__save_terrain_collisions = False
# alongside with horz.png, save spherical.png, suitable to be used as sky spherical texture
maps__save_spherical_skybox_texture = True
# If True, bakes map props to the scene. False puts dummy object to scene with info about what prop should be placed there
# TNFS note: Props will be retrieved from ../ETRACKFM/<map_id>_001.FAM file
# NFS2 note: this option always turned on for NFS2 tracks currently
maps__add_props_to_obj = False

# saves obj file for each 3D scene. obj-s are used under the hood, so if true it is even faster, we do not delete them
geometry__save_obj = True
# saves blender scene for each 3D scene
geometry__save_blend = True
# export to gg-web-engine https://github.com/AndyGura/gg-web-engine
geometry__export_to_gg_web_engine = False
