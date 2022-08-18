import argparse
import inspect
import os
import pathlib
import sys

import eel

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from library import require_file
from library.read_data import ReadData

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()

eel.init('frontend/dist/gui')

current_file = None


def serialize(data: ReadData) -> dict:
    if not isinstance(data, ReadData):
        return data
    return data.serialize()


@eel.expose
def open_file(path: str):
    current_file = require_file(path)
    return serialize(current_file)


@eel.expose
def on_angular_ready():
    eel.open_file(str(args.file))


eel.start('index.html')
