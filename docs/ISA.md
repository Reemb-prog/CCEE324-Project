# Fixed instruction-set contract (instructor brief + documented decisions)

**Required:** 2 cores; data width = 8 bits; 8 independently held registers R0..R7 per core; one 16-bit instruction word; shared data memory = 256 x 8 bits; 11 required instructions. Additional two **bonus** instructions are LOADI, NOT. All numbers in registers/memory are 0..255. ALU results wrap via `& 0xFF` (8-bit two's complement bit patterns, not signed Python integers). Every register is writable including R0.

## Exact encoding (MSB at left)

| Form | Bit fields | Usage |
|---|---|---|
| R | `[15:12]=opcode [11:9]=Rd [8:6]=Rs [5:3]=Rt [2:0]=000` | Eight ALU operations |
| M | `[15:12]=opcode [11:9]=Reg [8:1]=address [0]=0` | LOAD (Reg=Rd), STORE (Reg=Rs) |
| I | `[15:12]=opcode [11:9]=Rd [8:1]=immediate [0]=0` | Bonus LOADI |
| U | `[15:12]=opcode [11:9]=Rd [8:6]=Rs [5:0]=000000` | Bonus NOT |
| H | `[15:12]=1111 [11:0]=0` | HALT |

These exact field placements are **project design decisions** because the brief specifies widths/opcodes but not a full field map. They need not match MIPS formats.

| opcode | mnemonic | result / effect |
|---|---|---|
| 0000 | ADD | `Rd = (Rs + Rt) & 0xFF` |
| 0001 | SUB | `Rd = (Rs - Rt) & 0xFF` |
| 0010 | AND | `Rd = Rs & Rt` |
| 0011 | OR | `Rd = Rs \| Rt` |
| 0100 | XOR | `Rd = Rs ^ Rt` |
| 0101 | NOR | `Rd = ~(Rs \| Rt) & 0xFF` |
| 0110 | SLL | `Rd = (Rs << Rt) & 0xFF` |
| 0111 | SRL | `Rd = Rs >> Rt` (logical, unsigned) |
| 1000 | LOAD | `Rd = shared_memory[address]` |
| 1001 | STORE | `shared_memory[address] = Rs` |
| 1010 | LOADI | `Rd = immediate` **BONUS** |
| 1011 | NOT | `Rd = ~Rs & 0xFF` **BONUS** |
| 1111 | HALT | stop core and freeze PC |

Opcodes 1100–1110 are invalid through stage 06 (stage 07 assigns them; see the extension section at the end). Reject any instruction with nonzero unused bits, out-of-range inputs, unknown opcodes, or an uninitialized/out-of-range PC. Shift count is the unsigned 8-bit value in Rt, so shifts >=8 give zero (both directions on 8-bit unsigned data). PC counts instruction **indices**, not byte addresses: PC increments 1 after non-HALT, stays at HALT when stopped; each core can halt independently.

### Shared-memory clock rule

Each CPU `tick()` executes **at most one instruction per non-halted core** against the **same pre-tick snapshot** of data memory. All STORE writes commit at the end of that tick, first core 0, then core 1. If both store to the same address in one tick, core 1's later commit wins. New values become readable **from the next tick**. This simple deterministic policy is a simulation choice, not a physical arbitration model. Register updates are private to each core and are visible to that core's following instruction. An isolated `Core.step(memory)` may execute immediately for single-core tests.

Initial state: all registers and memory zero, PC=0. Test fixtures may initialize registers/data directly; bonus LOADI permits program-based register initialization. Instruction programs are separate read-only sequences; shared **data** memory does not store instructions.

## Stage 07 extension: SLT, SLTI, BEQ, BNE, J (human-approved addition)

Added after the six original stages at the team's request, so programs can express `if` and `while`. The PDF allows extra instructions as a bonus; this section is a **project design decision**, not part of the original brief. All earlier encodings and rules above are unchanged.

| Form | Bit fields | Usage |
|---|---|---|
| R | `[15:12]=1101 [11:9]=Rd [8:6]=Rs [5:3]=Rt [2:0]=000` | SLT |
| S | `[15:12]=1110 [11:9]=Rd [8:6]=Rs [5:0]=imm6` | SLTI |
| B | `[15:12]=1100 [11:10]=kind [9:7]=Rs [6:4]=Rt [3:0]=offset4` | BEQ (kind 01), BNE (kind 10) |
| J | `[15:12]=1100 [11:10]=11 [9:8]=00 [7:0]=target` | J |

| opcode | mnemonic | result / effect |
|---|---|---|
| 1101 | SLT | `Rd = 1 if Rs < Rt else 0` (unsigned 8-bit compare) |
| 1110 | SLTI | `Rd = 1 if Rs < imm6 else 0`, imm6 = 0..63 (unsigned) |
| 1100 kind 01 | BEQ | if `Rs == Rt`: `PC = PC + 1 + offset`, else `PC = PC + 1` |
| 1100 kind 10 | BNE | if `Rs != Rt`: `PC = PC + 1 + offset`, else `PC = PC + 1` |
| 1100 kind 11 | J | `PC = target` (absolute instruction index 0..255) |

Rules:
- `offset4` is a 4-bit two's-complement number, −8..+7, counted in instructions relative to the **next** instruction (PC+1). This is the index-based analogue of MIPS `PC + 4 + (offset << 2)`.
- Kind `00` in opcode 1100 is invalid, so the all-zero word `0xC000` remains illegal. For J, bits `[9:8]` must be zero. SLT bits `[2:0]` must be zero. Any other nonzero unused bit or out-of-range field is rejected with `ValueError`.
- Comparisons are **unsigned**, consistent with the rest of this ISA (like MIPS `sltu`): `200 < 5` is false.
- BEQ/BNE compare by computing `Rs − Rt` in the ALU and testing for a zero result. They write no register and touch no memory.
- A branch or jump to an index outside the program is not an error by itself. The next fetch raises `RuntimeError`, exactly like running off the end without HALT. Infinite loops are stopped by `run(max_cycles)`.
- **R0 is hard-wired to zero for instructions** (like MIPS `$zero`; a later stage-07 revision): an instruction's write to R0 is discarded, so R0 always reads 0 in programs and `BEQ Rx, R0, …` tests for zero directly. This revises the earlier rule "Every register is writable including R0" for program execution only: `RegisterFile.write(0, v)` still works as a direct test-setup path, which keeps the stage-01 register-file test valid.
