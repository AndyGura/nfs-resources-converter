# EA Games Compression Algorithms

This document describes the compression algorithms used by EA games (NFS 1 - 5). The implementations referenced
here live in [resources/eac/compressions](eac/compressions).

## How a compressed file is detected

The game (and this converter) does **not** rely on the file name or extension to pick a decompression algorithm. The
algorithm is chosen purely from the file header. All EA compressed resources used in the first five NFS games share the
same marker: the **second byte of the file equals `0xFB`**. The **first byte** then selects the concrete algorithm:

| First byte         | Second byte | Algorithm                | Implemented |
|--------------------|-------------|--------------------------|:-----------:|
| `0x10`, `0x11`     | `0xFB`      | RefPack (a.k.a. QFS1)    |      ✓      |
| `0x30` - `0x35`    | `0xFB`      | QFS3 (a.k.a. AL1.QFS)    |      ✓      |
| `0x46`             | `0xFB`      | QFS2 (a.k.a. AL2.QFS)    |      ✓      |
| (other, see below) | `0xFB`      | 4th algorithm            |      ✗      |

Because the algorithm depends only on the header, a resource can be repacked with any of the algorithms (or left
uncompressed) and the game will still load it. According to the decompiled TNFS (DOS) code, when a file does not start
with a valid QFS header the data is simply consumed **as is** (uncompressed), so an uncompressed payload is also a valid
input (see [Uncompressed data](#uncompressed-data)).

The header detection logic used by this converter can be found in [library/loader.py](../library/loader.py).

## RefPack (QFS1)
- **Header**: `0x10FB` or `0x11FB`. First byte is a flags field, second byte is the magic `0xFB`.
  - bit `0x80` ("large files"): the decompressed-size and (optional) compressed-size fields are 4 bytes instead of 3.
  - bit `0x01` ("compressed size present"): a compressed-size field is present right after the decompressed-size field.
- **Description**: LZ77/LZSS compression format made by Frank Barchard (EA Canada) for the Gimex library. The bitstream
  is a series of 1- to 4-byte commands, each describing a chunk of literal bytes to copy and/or a back-reference
  (length + distance) into the already decompressed output. Decompression ends on a 1-byte "stop" command.
- **Implementation**: [resources/eac/compressions/ref_pack.py](eac/compressions/ref_pack.py).
- **References**: [niotso wiki](http://wiki.niotso.org/RefPack),
  [sc4devotion wiki](https://www.wiki.sc4devotion.com/index.php?title=DBPF_Compression).

## QFS2 (AL2.QFS)
- **Header**: `0x46FB`. After the magic comes a 3-byte (big-endian) decompressed size, a 1-byte "value indicator" and a
  1-byte pattern count.
- **Description**: A dictionary/pattern based scheme. The header is followed by a table of patterns; each pattern maps a
  single-byte id to a pair of values, where every value is either a raw byte or a reference to a previously defined
  pattern (recursive expansion). The body is then a stream of bytes: a byte equal to the "value indicator" escapes the
  next byte as a literal, every other byte is expanded through the pattern table (or emitted as-is when it is not a
  pattern id).
- **Implementation**: [resources/eac/compressions/qfs2.py](eac/compressions/qfs2.py).

## QFS3 (AL1.QFS)
- **Header**: `0x30FB` - `0x35FB`. The high bits of the first byte encode options:
  - `0x100` bit (i.e. first byte `0x31`, `0x33`, `0x35`): a compressed-size field is present in the header.
  - `0x32FB`: after decompression the output is post-processed with a single cumulative sum (delta filter).
  - `0x34FB`: after decompression the output is post-processed with a double cumulative sum (double-delta filter).
- **Description**: A Huffman + LZ scheme. The header is followed by Huffman code tables built from a bit-accurate
  reader; the decoder then emits literals and back-references decoded through those tables. This implementation is a
  Python translation of the original x86 assembly and is executed through a small register/memory emulator
  (`AsmRunner`).
- **Implementation**: [resources/eac/compressions/qfs3.py](eac/compressions/qfs3.py).

## 4th algorithm (not implemented)
- **Description**: A fourth `*FB` compression branch was found in the decompiled TNFS (DOS) executable. No resource in
  the first 5 NFS games (`TNFS`, `NFS2`, `NFS2 SE`, `NFS3`, `NFS4`, `NFS5`) was found to actually use it, so
  it is **not implemented** in this converter. It is documented here only for completeness of the `*FB` compression
  family.

## Uncompressed data
- **Description**: A compressed header is not mandatory. According to the decompiled TNFS (DOS) code, when a file does
  not start with a valid QFS header (second byte is not `0xFB`, or the first byte is not a recognized algorithm id), the
  game passes the data through **as is**, treating it as already uncompressed. This means a resource can be repacked
  uncompressed and will still be loaded correctly by the game.
