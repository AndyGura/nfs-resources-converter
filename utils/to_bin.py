# For converting DosBOX memdump file to binary
import argparse
import pathlib

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()

out = bytearray()

with args.file.open('r') as f:
    while True:
        line = f.readline()
        if not line:
            break
        bytes = line.split(' ')[3:-1]
        for byte in bytes:
            value = int(byte, 16)
            out.extend(value.to_bytes(1, 'little'))
            

with open(f'out.bin', 'w+b') as file:
        file.write(out)
