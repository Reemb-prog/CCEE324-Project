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

Opcodes 1100–1110 are invalid. Reject any instruction with nonzero unused bits, out-of-range inputs, unknown opcodes, or an uninitialized/out-of-range PC. Shift count is the unsigned 8-bit value in Rt, so shifts >=8 give zero (both directions on 8-bit unsigned data). PC counts instruction **indices**, not byte addresses: PC increments 1 after non-HALT, stays at HALT when stopped; each core can halt independently.

### Shared-memory clock rule

Each CPU `tick()` executes **at most one instruction per non-halted core** against the **same pre-tick snapshot** of data memory. All STORE writes commit at the end of that tick, first core 0, then core 1. If both store to the same address in one tick, core 1's later commit wins. New values become readable **from the next tick**. This simple deterministic policy is a simulation choice, not a physical arbitration model. Register updates are private to each core and are visible to that core's following instruction. An isolated `Core.step(memory)` may execute immediately for single-core tests.

Initial state: all registers and memory zero, PC=0. Test fixtures may initialize registers/data directly; bonus LOADI permits program-based register initialization. Instruction programs are separate read-only sequences; shared **data** memory does not store instructions.
