# Scope boundary: what has been covered

Sources consulted: CCEE 324 Modules 01–04 and the Modules 01–03 solving session (RHU), plus the five-page instructor project brief included under `reference/`.

**Aligned concepts:** architecture vs organization / ISA; binary instruction encodings and instruction formats; binary, hexadecimal and two's-complement; register operands and writeback; MIPS `add`, `sub`, logical operators, `lw`, `sw`; PC, instruction memory, register file, ALU, multiplexing, control signals, data memory; combinational operation vs state updated on clock edges; step-by-step fetch/decode/execute traces; separate cores sharing memory.

**Simplifications, not MIPS:** instructor explicitly specifies an 8-bit data path, 8 registers per core, 16-bit instruction words, 256 bytes of shared data memory. Unlike MIPS's 32-bit byte-addressed instructions and PC+4, this teaching model indexes a list of 16-bit instructions with PC+1. Its LOAD and STORE use an 8-bit **absolute byte address**, not base+offset addressing. It is a simulator, not electronic HDL hardware.

**Deliberate exclusions:** pipelining, hazards and forwarding, cache/coherence, virtual memory, true parallel execution, flags/interrupts, branch/jump instructions, division/multiplication, MIPS assembler, GUI, network, external dependencies. These are not needed for this assignment and would distract from tested topics. Bonus uses `LOADI` and `NOT` only.
