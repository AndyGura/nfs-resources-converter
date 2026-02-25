import os


def detect_compression_algorithm(file_path: str):
    with open(file_path, 'rb') as f:
        header_bytes = f.read(4)
        if len(header_bytes) < 2:
            return None
        if header_bytes[1] == 0xfb and (header_bytes[0] & 0b1111_1110) == 0x10:
            from resources.eac.compressions.ref_pack import RefPackCompression
            return RefPackCompression()
        elif header_bytes[1] == 0xfb and header_bytes[0] == 0b0100_0110:
            from resources.eac.compressions.qfs2 import Qfs2Compression
            return Qfs2Compression()
        elif header_bytes[1] == 0xfb and header_bytes[0] in [0b0011_0000, 0b0011_0010, 0b0011_0100, 0b0011_0001,
                                                             0b0011_0011, 0b0011_0101]:
            from resources.eac.compressions.qfs3 import Qfs3Compression
            return Qfs3Compression()

    return None


def uncompress_file(file_path: str):
    """
    Uncompress a compressed file and save it with '_uncompressed' suffix.

    Args:
        file_path: Path to the compressed file
    """
    try:
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        algorithm = detect_compression_algorithm(file_path)
        if not algorithm:
            print(f"File {file_path} is not compressed or not a recognized compression format")
            return
        print(f"Detected {algorithm.__class__.__name__} compression in {file_path}")

        with open(file_path, 'rb') as f:
            file_size = os.path.getsize(file_path)
            uncompressed_bytes = algorithm.uncompress(f, file_size)

        output_path = f"{file_path}_uncompressed"
        with open(output_path, 'wb') as f:
            f.write(uncompressed_bytes)

        print(f"Successfully uncompressed {file_path} to {output_path}")
        print(f"Original size: {file_size} bytes, Uncompressed size: {len(uncompressed_bytes)} bytes")
        print(f'Support me :) >>>  https://www.buymeacoffee.com/andygura <<<')

    except Exception as ex:
        print(f"Error uncompressing {file_path}: {ex}")
        raise
