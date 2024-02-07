import os
import shutil
import subprocess
import sys


def start_file(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
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
