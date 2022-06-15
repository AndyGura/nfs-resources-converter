import argparse
import os
import pathlib

from guess_parser import get_resource_class
from parsers.resources.collections import ResourceDirectory

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()

if os.path.isdir(args.file):
    for subdir, dirs, files in os.walk(args.file):
        res = ResourceDirectory()
        res.read(subdir, files)
        res.save_converted(os.path.join('out', subdir).replace('\\', '/'))
else:
    with args.file.open('rb') as bdata:
        resource = get_resource_class(bdata, bdata.name)
        resource.name = bdata.name.split('/')[-1]
        resource.read(bdata, os.path.getsize(args.file), path=str(args.file))
        resource.save_converted(os.path.join('out', bdata.name).replace('\\', '/'))
