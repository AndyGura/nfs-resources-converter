import os
import shutil
import subprocess
import sys


def start_file(filename):
    if sys.platform == 'win32':
        os.startfile(filename)
    else:
        opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
        subprocess.call([opener, filename])


def remove_file_or_directory(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            pass
    except Exception as e:
        print(f"An error occurred while removing '{path}': {str(e)}")
        pass


def _resolve_dir_case_insensitive(directory: str):
    # Returns the existing directory matching `directory` with any letter case per path component,
    # or None. Game files ship with inconsistent case ("Tr0.QFS" vs "tr0.qfs") and case-sensitive
    # file systems need this to find them.
    if directory == '' or os.path.isdir(directory):
        return directory
    parent, name = os.path.split(directory.rstrip('/\\'))
    if parent == directory or not name:
        return None
    parent = _resolve_dir_case_insensitive(parent)
    if parent is None:
        return None
    try:
        entries = os.listdir(parent or '.')
    except OSError:
        return None
    for entry in entries:
        if entry.lower() == name.lower() and os.path.isdir(os.path.join(parent, entry)):
            return os.path.join(parent, entry)
    return None


def find_files_case_insensitive(patterns: list) -> list:
    """
    Finds existing files matching any of the given glob patterns (wildcards allowed in the file name
    only), ignoring letter case. Results keep the order of the patterns, sorted by name within one
    pattern, without duplicates.
    """
    from fnmatch import fnmatch

    result = []
    for pattern in patterns:
        directory, name_pattern = os.path.split(pattern)
        resolved_dir = _resolve_dir_case_insensitive(directory)
        if resolved_dir is None:
            continue
        try:
            entries = sorted(os.listdir(resolved_dir or '.'))
        except OSError:
            continue
        for entry in entries:
            path = os.path.join(resolved_dir, entry) if resolved_dir else entry
            if fnmatch(entry.lower(), name_pattern.lower()) and os.path.isfile(path) and path not in result:
                result.append(path)
    return result
