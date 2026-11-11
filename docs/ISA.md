# Fixed instruction-set contract (instructor brief + documented decisions)

**Required (PDF):** 2 cores; data width = 8 bits; 8 registers R0..R7 per core; one 16-bit instruction word; shared data memory = 256 x 8 bits; 11 required instructions (8 ALU operations, LOAD, STORE, HALT). **Bonus** (the PDF allows extra instructions): LOADI and NOT (stage 05), plus SLT, SLTI, BEQ, BNE and J (stage 07, human-approved extension). All numbers in registers/memory are 0..255. ALU results wrap via `& 0xFF` (8-bit two's complement bit patterns, not signed Python integers).

**R0 is hard-wired to zero for instructions**, like MIPS `$zero`: it always reads 0, and an instruction's write to it is discarded. `RegisterFile.write(0, v)` still works as a direct test-setup path (the stage-01 register-file test uses it).

## Instruction formats (MSB at left)

The three format families are the lecture's R, I and J. The exact bit placements are **project design decisions**: the brief gives the widths and the instruction list but no field map.

| Format | Bit fields | Used by |
|---|---|---|
| R | `[15:12]=opcode [11:9]=Rd [8:6]=Rs [5:3]=Rt [2:0]=000` | ADD SUB AND OR XOR NOR SLL SRL, SLT; NOT (Rt field = 000) |
| I (imm8) | `[15:12]=opcode [11:9]=Reg [8:1]=imm8 [0]=0` | LOAD (Reg=Rd), STORE (Reg=Rs), LOADI (Reg=Rd) |
| I (imm6) | `[15:12]=1110 [11:9]=Rd [8:6]=Rs [5:0]=imm6` | SLTI |
| I (branch) | `[15:12]=1100 [11:10]=kind [9:7]=Rs [6:4]=Rt [3:0]=offset4` | BEQ (kind 01), BNE (kind 10) |
| J | `[15:12]=1100 [11:10]=11 [9:8]=00 [7:0]=target` | J |
| HALT | `[15:12]=1111 [11:0]=0` | HALT |

The imm8 instructions have no Rs field, so their base register is R0. LOAD, STORE and LOADI compute `R0 + imm8` in the ALU, like MIPS `lw $t0, 100($zero)` and `addi $t0, $zero, 5`. So the memory address is effectively absolute (0..255).

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
| 1000 | LOAD | `Rd = shared_memory[R0 + imm8]` |
| 1001 | STORE | `shared_memory[R0 + imm8] = Rs` |
| 1010 | LOADI | `Rd = R0 + imm8` **BONUS** |
| 1011 | NOT | `Rd = ~Rs & 0xFF` **BONUS** |
| 1100 kind 01 | BEQ | if `Rs == Rt`: `PC = PC + 1 + offset`, else `PC = PC + 1` **BONUS** |
| 1100 kind 10 | BNE | if `Rs != Rt`: `PC = PC + 1 + offset`, else `PC = PC + 1` **BONUS** |
| 1100 kind 11 | J | `PC = target` (absolute instruction index 0..255) **BONUS** |
| 1101 | SLT | `Rd = 1 if Rs < Rt else 0` (unsigned) **BONUS** |
| 1110 | SLTI | `Rd = 1 if Rs < imm6 else 0`, imm6 = 0..63 (unsigned) **BONUS** |
| 1111 | HALT | stop core and freeze PC |

## Rules

- **Strict decoding.** Reject any word with nonzero unused bits, out-of-range inputs or an unknown opcode with `ValueError`. Kind `00` in opcode 1100 is invalid, so the all-zero word `0xC000` stays illegal. For J, bits `[9:8]` must be zero.
- **Shifts.** The shift count is the unsigned 8-bit value in Rt, so a shift of 8 or more gives zero.
- **Unsigned comparisons.** SLT/SLTI compare unsigned values, like MIPS `sltu`: `200 < 5` is false.
- **Branches.** BEQ/BNE compute `Rs − Rt` in the ALU and test for a zero result, as the lecture's `beq` does. They write no register and touch no memory.
- **Branch offsets.** `offset4` is a 4-bit two's-complement number (−8..+7), counted in instructions from the **next** instruction (PC+1). This is the index version of MIPS `PC + 4 + (offset << 2)`.
- **PC.** The PC counts instruction **indices**, not byte addresses. It advances by 1 after an ordinary instruction (not MIPS PC+4) and stays on HALT once stopped. Each core halts independently.
- **Bad PC.** An uninitialized or out-of-range PC is an error: fetching outside the program raises `RuntimeError`. That covers running off the end without HALT and a branch or jump to a missing index. Infinite loops are stopped by `run(max_cycles)`.

### Shared-memory clock rule

Each CPU `tick()` executes **at most one instruction per non-halted core**, against the **same pre-tick snapshot** of data memory.

- All STORE writes commit at the end of the tick: core 0 first, then core 1. If both cores store to the same address in one tick, core 1's later commit wins.
- New values become readable **from the next tick**.
- This is a simple, deterministic simulation policy, not a model of physical memory arbitration.
- Register updates are private to each core and visible to that core's next instruction.
- An isolated `Core.step(memory)` runs immediately, for single-core tests.

**Initial state.** All registers and memory are zero, and PC = 0. Test fixtures may set registers or data directly, and bonus LOADI lets a program set its own registers. Instruction programs are separate, read-only sequences: the shared **data** memory does not hold instructions.
