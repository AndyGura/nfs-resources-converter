import os


def path_join(path, *paths) -> str:
    return os.path.join(path, *paths).replace('\\', '/')
