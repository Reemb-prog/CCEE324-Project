# `dualcore` package

A dual-core 8-bit processor simulator. Each module is one block of the lecture's single-cycle datapath.

| File | Block |
|---|---|
| `isa.py` | Instruction formats (R / I / J / HALT): encoder and strict decoder |
| `registers.py` | Register file: 8 × 8-bit registers, one per core |
| `control.py` | Control unit: lecture signals, plus Jump (textbook) and BranchNe (for BNE) |
| `alu.py` | ALU: ADD SUB AND OR XOR NOR SLL SRL, plus bonus NOT and SLT; 8-bit wrap |
| `memory.py` | 256 × 8-bit shared data memory, with a private per-tick snapshot/commit port |
| `core.py` | One core: PC, fetch → decode → ALU → memory → writeback → next PC; R0 hard-wired to 0 |
| `processor.py` | Two cores on one clock tick, sharing the data memory |
| `demo.py` | Terminal demo: `python -m dualcore.demo [-b | -i | "expr" ["expr"] | -h]` |

The specifications are in `docs/ISA.md` and `docs/INTERFACES.md`. `tests/` is the fixed acceptance contract; run it with `python scripts/harness.py verify`.
