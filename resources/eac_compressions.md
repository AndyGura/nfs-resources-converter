# EA Games Compression Algorithms

This document describes the compression algorithms used by EA games (NFS 1 - 5, plus JDLZ and HUFF of NFS Underground
1, 2 and Most Wanted). The implementations referenced here live in [resources/eac/compressions](eac/compressions):
each of them both uncompresses and compresses.

## How a compressed file is detected

The game (and this converter) does **not** rely on the file name or extension to pick a decompression algorithm. The
algorithm is chosen purely from the file header. All EA compressed resources used in the first five NFS games share the
same marker: the **second byte of the file equals `0xFB`**. The **first byte** then selects the concrete algorithm:

| First byte         | Second byte | Algorithm                | Implemented |
|--------------------|-------------|--------------------------|:-----------:|
| `0x10`, `0x11`     | `0xFB`      | RefPack (a.k.a. QFS1)    |      ✓      |
| `0x30` - `0x35`    | `0xFB`      | QFS3 (a.k.a. AL1.QFS)    |      ✓      |
| `0x46`, `0x47`     | `0xFB`      | QFS2 (a.k.a. AL2.QFS)    |      ✓      |
| (other, see below) | `0xFB`      | 4th algorithm            |      ✗      |

Because the algorithm depends only on the header, TNFS loads a resource repacked with any of the algorithms above: the
`sys_unpack` of both TNFS DOS (0xaa928) and Win95 SE (0x4a2520) handles RefPack, QFS2 and QFS3. According to the
decompiled TNFS (DOS) code, when a file does not start with a valid QFS header the data is simply consumed **as is**
(uncompressed), so an uncompressed payload is also a valid input (see [Uncompressed data](#uncompressed-data)). Later
games are not checked, and NFS3 / NFS5 ship RefPack files only, so the converter writes a resource back with the
algorithm (and QFS3 delta mode) it was read with, kept as `compression_flags` (the first header byte) in the data of
`EacCompressedBlock`. New data is written as QFS2.

In every algorithm, bit `0x01` of the first byte means a 3-byte compressed size comes right after the magic, before
the uncompressed size. No shipped file uses it, and the compressors don't write it.

[library/loader.py](../library/loader.py) routes any file whose second byte is `0xFB` to `EacCompressedBlock`;
the per-algorithm choice from the first byte is made in
[resources/eac/archives/compressed_block.py](eac/archives/compressed_block.py) (`_detect_compression`).

## RefPack (QFS1)
- **Header**: `0x10FB` or `0x11FB`. First byte is a flags field, second byte is the magic `0xFB`.
  - bit `0x80` ("large files"): the decompressed-size and (optional) compressed-size fields are 4 bytes instead of 3
    (not handled by TNFS nor by this converter).
  - bit `0x01` ("compressed size present"): a 3-byte compressed-size field comes before the decompressed-size field
    (TNFS SE 0x4a823c reads the decompressed size at offset 5 then).
- **Description**: LZ77/LZSS compression format made by Frank Barchard (EA Canada) for the Gimex library. The bitstream
  is a series of 1- to 4-byte commands, each describing a chunk of literal bytes to copy and/or a back-reference
  (length + distance) into the already decompressed output. Decompression ends on a 1-byte "stop" command. P = 0..3
  literal bytes, copied right after the command, before the match; D = distance, L = match length:

  | Command bits                                      | Meaning                          |
  |---------------------------------------------------|----------------------------------|
  | `0DDLLLPP DDDDDDDD`                               | D 1..1024, L 3..10               |
  | `10LLLLLL PPDDDDDD DDDDDDDD`                      | D 1..16384, L 4..67              |
  | `110DLLPP DDDDDDDD DDDDDDDD LLLLLLLL`             | D 1..131072, L 5..1028           |
  | `111NNNNN`, N < 28                                | (N + 1) * 4 literal bytes        |
  | `111111PP`                                        | end of stream, P literal bytes   |

  Stored D and L values are biased: D - 1, L - 3 / 4 / 5.
- **Compression**: hash chains of 3-byte sequences (48 candidates per position), one-byte lazy matching: a few % larger
  than EA's files at most, smaller for some (`356b.crp`).
- **Implementation**: [resources/eac/compressions/ref_pack.py](eac/compressions/ref_pack.py).
- **References**: [niotso wiki](http://wiki.niotso.org/RefPack),
  [sc4devotion wiki](https://www.wiki.sc4devotion.com/index.php?title=DBPF_Compression).

## QFS2 (AL2.QFS)
- **Header**: `0x46FB` (`0x47FB`: a 3-byte compressed size follows the magic). Then come a 3-byte (big-endian)
  decompressed size, a 1-byte escape byte ("value indicator") and a 1-byte pattern count.
- **Description**: Byte pair encoding. The header is followed by a table of patterns, 3 bytes each: id, left byte, right
  byte. The body is a stream of bytes:
  - a pattern id gives its expansion;
  - the escape byte followed by `0x00` ends the stream;
  - the escape byte followed by any other byte gives that byte (this is how pattern ids and the escape byte itself
    are stored);
  - any other byte is itself.

  The game (TNFS DOS 0xa9c24, SE 0x4a96f4) expands both bytes of a pattern recursively, with the **final** tables: a
  byte of a pattern that is an id anywhere in the table expands, also if that id is defined later. A pattern byte can't
  be the escape byte (the game would expand it as a pattern).

  The escape byte can be any value but `0x00` (escape + `0x00` is the end of stream, so a literal `0x00` couldn't be
  escaped). EA's files use `0xFF`, `0xFD`, `0xFC` and `0x55`, always a value the uncompressed data doesn't have.
- **Compression**: escape byte = the least frequent value but `0x00`. Then, up to 255 times, the most frequent pair of
  symbols (escaped bytes don't pair) gets a new id, the least frequent value available. A value that has been a pattern
  byte never becomes an id. Every literal occurrence of a new id gets escaped. Stops when a pattern saves no bytes
  (3 bytes of table + the escaped occurrences of its id). TNFS files come out slightly smaller than EA's.
- **Implementation**: [resources/eac/compressions/qfs2.py](eac/compressions/qfs2.py).

## QFS3 (AL1.QFS)
- **Header**: `0x30FB` - `0x35FB`. The first byte is a flags field, the second byte is the magic `0xFB`:
  - bit `0x01` (first byte `0x31`, `0x33`, `0x35`): a 3-byte (big-endian) compressed-size field follows the magic. It is
    not needed for decoding.
  - `0x32`: after decompression the output is post-processed with a single cumulative sum (delta filter).
  - `0x34`: after decompression the output is post-processed with a double cumulative sum (double-delta filter).
  - `0x30`: no post-processing.

  Then come a 3-byte (big-endian) decompressed size and a 1-byte *escape symbol*. Everything after that is a single
  MSB-first bit stream, not byte-aligned.
- **Description**: Canonical Huffman coding of single bytes, plus an escape symbol for run-length repeats, literals and
  the end marker. The bit stream consists of:
  1. **Code lengths**: for code length 1, 2, 3, ... the number of symbols having that length, one *number* (see below)
     each, until the code space is exhausted (the Kraft sum reaches 1, i.e. the tree is complete). Codes are assigned
     canonically: by length, then in the order the symbols are listed.
  2. **Symbols**: one entry per symbol, in canonical order. Each is a *number* + 1 = distance to the symbol from the
     previous one, counted over byte values **not assigned yet**, cyclic over 0..255 (the walk starts before 0).
  3. **Data**: Huffman codes, each producing one output byte, except the escape symbol, which is followed by a
     *number* N:
     - N > 0: repeat the last output byte N more times;
     - N = 0, next bit 1: end of stream;
     - N = 0, next bit 0: the next 8 bits are a literal byte (this is how the escape byte value itself is emitted).

  **Numbers** use an Elias-gamma-like code: Z zero bits, a one bit, then Z + 2 value bits V;
  number = 2^(Z+2) + V - 4. The smallest numbers 0..3 thus take 3 bits (`1xx`), 4..11 take 5 bits (`01xxx`), etc.

  The decoded output is finally run through the delta filter selected by the header (`0x32`/`0x34`), if any. The
  output length is known from the header, but decoding stops on the end marker, not on the byte count. Code lengths
  are at most 16 bits.
- **Compression**: escape symbol = the least frequent byte value. A run of a byte is repeated by the escape code where
  that takes fewer bits than the byte codes; which runs pay off depends on the code lengths and the other way around,
  so it starts from runs of 8+ repeats and settles in 4 rounds. Code lengths come from a Huffman tree, flattened until
  the longest code fits 16 bits. Without a given delta mode, all three are tried and the shortest result is kept. TNFS
  files come out slightly smaller than EA's in total.
- **Implementation**: [resources/eac/compressions/qfs3.py](eac/compressions/qfs3.py). The original x86 routine was
  ported through the `AsmRunner` emulator; that register-level translation is kept as `Qfs3ASMCompression` in
  [test/resources/eac/archives/test_compressed_block.py](../test/resources/eac/archives/test_compressed_block.py)
  and compared against the pure Python decoder in tests.

## JDLZ (NFS Underground 1, 2, Most Wanted)
- **Header**: 16 bytes: `JDLZ`, `0x02`, `0x10`, 2 zero bytes, uncompressed size (u32 LE), compressed size including
  the header (u32 LE).
- **Description**: LZ77 with two interleaved flag bytes: the first one tells literals from matches, the second one
  short-distance (D 1..16, L 3..4098) from long-distance (D 17..2064, L 3..34) matches. Used by `*.lzc` files,
  compressed bundles and textures. Not an `*FB` algorithm: `NfsuJdlzCompressedBlock` always uses it.
- **Implementation**: [resources/eac/compressions/jdlz.py](eac/compressions/jdlz.py).

## HUFF (NFS Underground 2)
- **Header**: 16 bytes: `HUFF`, `0x01`, `0x10`, 2 zero bytes, uncompressed size (u32 LE), compressed size without the
  header (u32 LE).
- **Description**: a QFS3 stream (`0x30FB`, no delta coding) behind the header. Used by some textures of compressed
  texture packs. The compressor writes plain `0x30` streams only.
- **Implementation**: [resources/eac/compressions/huff.py](eac/compressions/huff.py).

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
