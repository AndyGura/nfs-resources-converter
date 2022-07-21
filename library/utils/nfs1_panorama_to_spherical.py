def nfs1_panorama_to_spherical(track_id: str, file_name: str, out_file_name: str):
    from PIL import Image, ImageOps
    from numpy import average
    source = Image.open(file_name)

    out_half_width = 1024
    out_half_height = int(out_half_width / 2)

    scale_x = out_half_width / source.size[0]
    mirror_x = track_id in ['TR3', 'TR7']
    # It is a mystery how NFS decides how to position horizon. I tried everything in {track_id}INFO files,
    # but no stable correlations detected. NFS horizon is not a sphere, it is a separate 2D layer under 3D stage,
    # so output sky texture is approximate for FOV == 65
    scale_y = 2.12
    pos_y = 0
    if track_id in ['TR3', 'TR4']:
        scale_y = 1
    elif track_id == 'TR1':
        scale_y = 1.15
    elif track_id == 'TR2':
        scale_y = 0.86
    elif track_id == 'TR6':
        scale_y = 2.2
    if track_id == 'AL1':
        pos_y = 351
    elif track_id == 'AL2':
        pos_y = 336
    elif track_id == 'AL3':
        pos_y = 365
    elif track_id == 'CL1':
        pos_y = 375
    elif track_id == 'CL2':
        pos_y = 349
    elif track_id == 'CL3':
        pos_y = 374
    elif track_id == 'CY1':
        pos_y = 328
    elif track_id == 'CY2':
        pos_y = 294
    elif track_id == 'CY3':
        pos_y = 343
    elif track_id == 'TR1':
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

    source_scaled = source.resize((int(source.size[0] * scale_x), int(source.size[1] * scale_y)), Image.ANTIALIAS)

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
