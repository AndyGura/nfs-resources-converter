def nfs1_panorama_to_spherical(track_id: str, file_name: str, out_file_name: str, pivot_y: int):
    from PIL import Image, ImageOps
    from numpy import average
    source = Image.open(file_name)

    out_half_width = 1024
    out_half_height = int(out_half_width / 2)

    scale_x = out_half_width / source.size[0]
    mirror_x = track_id in ['TR3', 'TR5', 'TR7', 'TR8']

    # when putting NTRACKFM/TR1_T01.FAM into ETRACKFM/TR1_001.FAM, the game does not mirror image as it does when selecting custom time of a day
    # so mirror info is not located in FAM file, it's in the MISC/*INFO, TRI file or hardcoded in the game executable
    if 'T01' in file_name:
        mirror_x = track_id in ['CL3', 'TR1', 'TR2', 'TR6', 'TR7']

    # NFS horizon is not a sphere, it is a separate 2D layer under 3D stage,
    # so output sky texture is approximate for FOV == 65

    # TODO it is not exactly clear how game decides how to draw horizon: it's scale, mirroring and position
    scale_y = 2.12
    if track_id in ['TR3', 'TR4']:
        scale_y = 1
    elif track_id == 'TR1':
        scale_y = 1.15
    elif track_id == 'TR2':
        scale_y = 0.86
    elif track_id == 'TR6':
        scale_y = 2.2

    pos_y = out_half_height - pivot_y * scale_y
    if track_id == 'TR1':
        pos_y = 324
    elif track_id == 'TR2':
        pos_y = 308
    elif track_id == 'TR3':
        pos_y = 367
    elif track_id == 'TR6':
        pos_y = 369
    elif track_id == 'TR7':
        pos_y = 342
    elif track_id == 'TR4':
        pos_y = 300

    scale_y = scale_y * out_half_width / 1024
    pos_y = int(pos_y * out_half_width / 1024)

    source_scaled = source.resize((int(source.size[0] * scale_x), int(source.size[1] * scale_y)), Image.LANCZOS)

    # INFO files have some values for top and bottom color, but I don't understand what exactly colors do they mean
    top_line_color = tuple([int(x)
                            for x in average(average(source.crop((0, 0, source.size[0], 1)), axis=0), axis=0)])
    bottom_line_color = tuple([int(x)
                               for x in average(average(source.crop((0,
                                                                     source.size[1] - 1,
                                                                     source.size[0],
                                                                     source.size[1])), axis=0), axis=0)])

    spherical = Image.new(source_scaled.mode, (out_half_width * 2, out_half_height * 2), 0xff000000)
    spherical.paste(top_line_color, [0, 0,
                                     spherical.size[0], int(pos_y + source_scaled.size[1] / 2)])
    spherical.paste(bottom_line_color, [0, int(pos_y + source_scaled.size[1] / 2),
                                        spherical.size[0], spherical.size[1]])
    spherical.paste(source_scaled, (out_half_width, pos_y))
    if mirror_x:
        source_scaled = ImageOps.mirror(source_scaled)
    spherical.paste(source_scaled, (out_half_width - source_scaled.size[0], pos_y))

    spherical.save(out_file_name)
