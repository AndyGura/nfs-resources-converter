---
name: asm-runner-porting
description: Use when a game routine (decompressor, codec, checksum, packer) must be understood and ported to Python from an executable's disassembly (IDA/Ghidra), or when verifying such a port. Explains how to drive library/utils/asm_runner.py — the in-repo x86 snippet interpreter — to execute the original ASM basic blocks from Python, progressively replace them with real Python, and keep the ASM-driven version as a regression test. NOT for describing file layouts with read_blocks — use nfs-resource-formats for that.
---

# Porting game routines with the ASM runner

> Keep this file in sync with the codebase: if something here is wrong, stale, or missing, fix it
> as part of your change. Describe only the current state, dry and reference-like — never
> change-log prose.

Some game logic (compression, audio codecs, checksums) can't be described as a data layout — it has
to be re-implemented. The source is the game executable, disassembled with IDA or Ghidra.
`library/utils/asm_runner.py` (`AsmRunner`, built on `virtual_asm_registers.py` and
`virtual_asm_flags.py`) is a tiny 32-bit x86 interpreter that executes IDA-syntax instruction
snippets against emulated registers, flags and a flat virtual memory. It lets you run the *original*
instructions from Python, compare against known-good output, and swap blocks for Python one at a
time without ever having the whole algorithm "in your head" at once.

Existing ports done this way (all decompressors in `resources/eac/compressions/`):

| Pure Python (production) | ASM-driven twin (tests only) |
|---|---|
| `resources/eac/compressions/ref_pack.py` `RefPackCompression` | `RefPackASMCompression` in `test/resources/eac/archives/test_compressed_block.py` |
| `resources/eac/compressions/qfs2.py` `Qfs2Compression` | `Qfs2ASMCompression`, same file |
| `resources/eac/compressions/qfs3.py` `Qfs3Compression` | `Qfs3ASMCompression`, same file (hybrid: register-level Python + virtual memory for the stack tables) |

Each twin is compared byte-for-byte against the pure Python version on `test/samples/*` files
(`test_*_asm_decompression`), which doubles as the regression suite for the runner itself.
Runner instruction semantics have their own unit tests in `test/test_asm_runner.py`.

## Workflow

1. **Get the disassembly.** In IDA: select the function, copy the listing text. In Ghidra: use the
   Listing window's *Copy Special → Assembly* (or export). The runner expects **IDA operand syntax**:
   lowercase registers, immediates as decimal or hex with an `h` suffix (`0FFh`, `31Ch` — `0x10`
   is *not* parsed), memory operands like `[esp+31Ch+var_14]`, `[edx+eax]`, `[ebx*4+esi]`,
   `byte ptr [edi+esi]`, `ds:dword_53034C`. Normalize Ghidra output to this form (registers to
   lowercase, `0x..` to `..h`, `dword ptr [ESP + 0x10]` to `[esp+10h]`). Keep IDA's stack
   variable names (`var_14`, `arg_0`) — they become named variables (see below). Ghidra's
   decompiler output is a useful *reading* aid for structuring loops, but the runner executes
   assembly, not C.

2. **Set up the harness.** Subclass `AsmRunner` (plus the domain base class, e.g.
   `BaseCompressionAlgorithm`). In the entry method (`uncompress(buffer, input_length)` for
   compressions):
   - `super().__init__(asm_virtual_memory_size=...)` — default is 1 MB; the memory must hold
     input, output and the stack, so size it for the biggest sample.
   - Copy the input into virtual memory with `memstore(offset, byte, size=1)`; pick an output
     region far from it.
   - Set `self.esp` to a stack top with room below it for the function's locals (`sub esp, 30Ch`
     in the prologue tells you how much).
   - Declare IDA stack variables and arguments with `define_variable(name, offset, size)`, e.g.
     `define_variable('var_14', -0x14, 4)`, `define_variable('arg_0', 8, 4)`. The offset is what
     IDA shows (`var_14 = -14h`); the *size* is the element size accessed through it (1 for byte
     tables, 4 for dwords) — it determines the width of `[esp+...+var_14]` loads and stores.
     Store argument values at `[esp+4]`, `[esp+8]`, ... with `memstore`.
   - Globals (`ds:dword_53034C`) and any scratch value you want to name can also be
     `define_variable`d; they then behave like memory-less named registers.
   `define_variable` raises if a name is already defined, so runner instances are **one-shot**:
   create a new one per decoded file.

3. **Translate basic blocks, not instructions.** One Python method per IDA label
   (`loc_4A96E4`, or a descriptive name once you understand it), whose body is a single
   `self.run_block("""...""")` containing the block's instructions up to and including its
   terminating jump. `run_block` returns `True` if the final conditional/unconditional jump would
   be taken, `False` if execution falls through, `None` if the block has no jump. Jump *targets*
   are ignored — you rebuild the control flow in Python (`if not self.loc_A(): ...`,
   `while self.loc_B(): ...`). A block may contain at most one jump, and it must be last.
   `call name` invokes the Python method `name` on the runner (pushing/popping a dummy return
   address), so recursive helpers translate naturally.

4. **Verify early.** Feed a real file (`test/samples/`, or the gitignored `games/<game>/` folders)
   and compare the output region of `asm_virtual_memory` against the known-good result
   (uncompressed twin file, other tools, in-game behaviour). Only once the ASM-driven version is
   byte-exact do you have a trustworthy oracle for the rewrite.

5. **Rewrite progressively.** Replace blocks with plain Python that reads/writes the same registers
   (`self.eax`, `self.al`, `self.esi` ... stay available as attributes with proper 32/16/8-bit
   wrapping) and re-run the comparison after each step. Name things as their meaning becomes
   clear (`unk_table_2` → code-length table). Stop when only the algorithm's *idea* remains, then
   write the pure Python class from scratch with proper names and a docstring describing the
   format (see `Qfs3Compression` for the target shape).

6. **Keep the oracle.** Move the ASM-driven / hybrid class into the test module next to the
   existing twins, add a `test_<algo>_asm_decompression` comparing it with the pure Python
   implementation on a couple of samples (keep them small — the runner decodes roughly 10–100 KB/s of output depending on instruction density),
   and keep the sample-vs-expected-output tests on the pure Python class.

## Runner reference

- **Registers**: `eax ebx ecx edx esi edi esp ebp` (32-bit) with views `ax..dx`, `ah..dh`,
  `al..dl` that alias the parent register; every assignment wraps to the register width.
  `get_register_signed_value('esi')` gives the two's-complement value for signed comparisons in
  hybrid Python code.
- **Flags**: `CF ZF SF OF PF AF DF` attributes, updated by arithmetic/logic/`cmp`/`test`.
- **Memory**: `memstore(offset, value, size)`, `memread(offset, size)`, `_push`/`_pop` (via
  `esp`). `get_value(expr)` / `set_value(expr, value, size=None)` accept the same operand syntax as
  instructions (registers, immediates, `[...]` pointers, named variables, `byte ptr`). Pointer
  width for `[...]` comes from the declared size of a named variable inside the brackets,
  otherwise defaults to 4.
- **Instructions implemented** in `run_command`: `mov movzx lea push pop add sub inc dec neg
  and or xor test cmp shl shr rol call`, `rep movsb`/`rep movsd` (honours `DF`), and jumps
  `jmp jb jnb jz jnz jbe jl jge jle js jns`. Anything else (`ja`, `jg`, `jne`/`je` spellings,
  `sar`, `ror`, `mul`/`imul`/`div`, `sbb`/`adc`, `movsx`, `xchg`, `setcc`, `loop`, `cmovcc`, ...)
  raises `Unknown command` — add it to `run_command` with a unit test in
  `test/test_asm_runner.py` (mirror the Intel manual's flag behaviour, see `shl`/`rol` for the
  pattern) rather than rewriting the block by hand before you understand it.
- **Diagnostics**: uncomment the `print` at the top of `run_command` to trace every instruction;
  `self.calldict` counts flag-setting mnemonics executed.

## Pitfalls

- Wrong `define_variable` size is the classic silent bug: a byte table declared with size 4 makes
  `mov al, [esp+eax+var_11C]` read 4 bytes and truncate — the result *looks* right most of the
  time. Match the size to the access width seen in the listing.
- `mov` between operands of different widths trusts the destination width; `movzx` is treated the
  same. Check high bytes when something drifts.
- Unbounded Python ints can hide in hybrid code (e.g. an accumulator that is never masked); rely
  on register attributes, which wrap, when emulating registers.
- Reads past the input in the emulated memory return zeros, matching the game's behaviour of
  prefetching past the end — keep that in mind when deciding termination conditions for the pure
  Python version (it should not depend on `input_length` being exact).
- The runner is slow (interpreted, regex-parsed per instruction). Never use it in production
  code paths; it exists for tests and for the porting session itself.
