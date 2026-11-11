# Final technical report: a simplified dual-core 8-bit processor (Python simulator)

CCEE 324 Computer Organization, Fall 2026 project.

## 1. Goal and approach

The brief asks for a two-core processor that runs arithmetic and logical instructions. Each core fetches, decodes and executes on its own, and the two cores communicate through a shared data memory. We built a **Python simulator** (one of the allowed tools) using only the standard library. Each module is one block of the single-cycle datapath from the lectures, so the code can be explained block by block.

**(PDF)** marks a rule from the instructor brief. **(design choice)** marks a decision we made where the brief leaves the choice open; these are fixed in `docs/ISA.md`. Our baseline is the lecture's MIPS single-cycle datapath and control table. We depart from it only where the 8-bit data and 16-bit instructions force us to; `docs/DESIGN_REVIEW.md` lists every such departure.

## 2. Architecture / block diagram (deliverable 1)

`docs/ARCHITECTURE.md` contains the dual-core block diagram and the single-core datapath (PC + 1 adder, register file, ALUSrc mux, ALU, data memory, MemtoReg mux, branch adder, PCSrc and Jump muxes). Each core contains a **PC**, an instruction program, a decoder, a **control** unit, a **register** file and an **ALU** (PDF). Only the data memory is **shared** (PDF).

| Block | File | Hardware meaning |
|---|---|---|
| Decoder / encoder | `dualcore/isa.py` | splits a 16-bit word into fields |
| Register file | `dualcore/registers.py` | 8 × 8-bit registers, one set per core |
| Control unit | `dualcore/control.py` | opcode → control signals |
| ALU | `dualcore/alu.py` | 8 required operations, plus bonus NOT and SLT |
| Data memory | `dualcore/memory.py` | 256 × 8-bit, shared |
| Core | `dualcore/core.py` | PC + the blocks above, one instruction per step |
| Processor | `dualcore/processor.py` | two cores, one clock, shared memory |
| Demo | `dualcore/demo.py` | terminal demonstration |

## 3. Instruction set and instruction format (deliverables 2–3)

**Specification (PDF):** 8-bit data, 8 registers R0–R7 per core, 16-bit instructions, 256 × 8 data memory, and 11 basic instructions (8 ALU operations, LOAD, STORE, HALT) with clock-based execution.

The brief allows extra instructions as a **bonus**, and we added seven:

- LOADI and NOT, for constants and one more logical operation;
- SLT, SLTI, BEQ, BNE and J, so programs can express `if` and `while`.

The brief gives the opcodes and widths but not the field positions. We use the lecture's three format families (design choice for the exact bits):

| Format | Bit fields | Used by |
|---|---|---|
| R | `opcode[15:12] Rd[11:9] Rs[8:6] Rt[5:3] 000` | ADD SUB AND OR XOR NOR SLL SRL, SLT; NOT (Rt = 000) |
| I (imm8) | `opcode[15:12] Reg[11:9] imm8[8:1] 0` | LOAD (Reg = Rd), STORE (Reg = Rs), LOADI |
| I (imm6) | `1110 Rd[11:9] Rs[8:6] imm6[5:0]` | SLTI |
| I (branch) | `1100 kind[11:10] Rs[9:7] Rt[6:4] offset4[3:0]` | BEQ (kind 01), BNE (kind 10) |
| J | `1100 11 00 target[7:0]` | J |
| HALT | `1111 000000000000` | HALT |

**Opcodes:**

- 0000–0111 are the ALU operations, in the PDF's order (PDF).
- 1000 LOAD, 1001 STORE and 1111 HALT (PDF).
- Bonus opcodes: 1010 LOADI, 1011 NOT, 1101 SLT and 1110 SLTI.
- Only three opcodes were left for five new instructions. So 1100 is a group, and bits [11:10] choose BEQ, BNE or J. Kind 00 is invalid, so `0xC000` stays illegal.

**Example:** `ADD R1, R2, R3` = `0000 001 010 011 000` = `0x0298`.

**Illegal words:** the decoder raises `ValueError` for:

- unknown opcodes;
- words with unused bits set;
- values outside 0–65535.

This is like hardware raising an illegal-instruction exception.

**R0 is hard-wired to zero**, like MIPS `$zero` (design choice). The imm8 instructions have no Rs field, so they use R0 as their base:

- LOAD/STORE address = R0 + imm8, like `lw $t0, 100($zero)`, so addresses are effectively absolute;
- LOADI computes Rd = R0 + imm8, like `addi $t0, $zero, 5`.

## 4. ALU design (deliverable 4)

`alu_execute(op, a, b)` performs ADD, SUB, AND, OR, XOR, NOR, SLL and SRL (PDF), plus the bonus operations NOT and SLT. All values are unsigned 8-bit, and every result is masked with `& 0xFF`, the way an 8-bit result bus drops extra bits:

- `250 + 10 = 4`: the carry out of bit 7 is lost.
- `3 − 5 = 254`: subtraction is two's-complement addition, `3 + (~5 + 1)`, and `11111110` is −2 read as signed.
- Shifts use the value in Rt. A shift of 8 or more gives 0. SRL is logical, so zeros come in from the left.
- `NOT 47 = 208` (`00101111 → 11010000`). SLT returns 1 if a < b, comparing unsigned values (like `sltu`).

There is no flag register. Branches use the ALU's **Zero** output directly in the same cycle, as in the lecture datapath.

## 5. Register-file design (deliverable 5)

Each `RegisterFile` object owns a private list of eight 8-bit values, all starting at 0. Bad indices or out-of-range values raise `ValueError`. Every core builds its own object, so both cores can use "R1" while they are **different physical registers** (PDF example). The core reads R0 as 0 and discards instruction writes to it, which hard-wires R0 to zero.

## 6. Control-unit design (deliverable 6)

The control unit uses the signals and values of the lecture's single-cycle control table. `X` means "don't care" and is stored as `None`.

| Signal | R-type | LOAD | STORE | HALT | LOADI | NOT | SLT | SLTI | BEQ | BNE | J |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RegDst | 1 | 1 | X | X | 1 | 1 | 1 | 1 | X | X | X |
| ALUSrc | 0 | 1 | 1 | X | 1 | X | 0 | 1 | 0 | 0 | X |
| MemtoReg | 0 | 1 | X | X | 0 | 0 | 0 | 0 | X | X | X |
| RegWrite | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| MemRead | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MemWrite | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Branch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 |
| BranchNe | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| Jump | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| ALUOp | operation | ADD | ADD | X | ADD | NOT | SLT | SLT | SUB | SUB | X |

The LOAD, STORE and BEQ columns are the lecture's lw, sw and beq columns. There are three differences, all explained in `docs/ARCHITECTURE.md`:

- **RegDst is always 1**, because every destination register sits in bits 11–9.
- **ALUOp names the operation directly**, because there is no `funct` field.
- **Two extra signals.** **Jump** is the textbook's extension for `j`. **BranchNe** is the only signal we invented: it inverts the Zero test for BNE.

## 7. Single-core implementation (deliverable 7)

`Core.step(memory)` runs exactly one instruction through the lecture's single-cycle path:

1. **Fetch** the word at `program[PC]`. A PC outside the program raises `RuntimeError` (for example, a missing HALT).
2. **Decode** the word and generate the control signals.
3. **Register read**: read Rs (R0 for imm8 instructions) and Rt.
4. **ALU**: input B is Rt when ALUSrc = 0, or the immediate when ALUSrc = 1. The ALU then executes `ALUOp`.
5. **Memory**: LOAD reads the address computed by the ALU when MemRead is set; STORE writes it when MemWrite is set.
6. **Writeback** to Rd through the MemtoReg mux: memory data if MemtoReg = 1, otherwise the ALU result.
7. **Next PC**: one of three values.
   - Normally PC + 1.
   - For a branch, PC + 1 + offset if Zero (BEQ) or not Zero (BNE). The offset is a 4-bit signed number, −8 to +7.
   - For J, the absolute target.

The PC indexes a list of 16-bit instructions, so it advances by **1, not MIPS PC + 4** (design choice). For the same reason the branch target has no `<< 2`. On **HALT** the core sets `halted`, the PC stays on the HALT instruction, and later steps do nothing (PDF: "stop when HALT is encountered").

## 8. Dual-core implementation (deliverable 8)

`DualCoreProcessor` creates two separate `Core` objects. Each has its own PC, registers, control unit and program; only the memory object is passed to both.

Each `tick()` is one conceptual clock cycle, in which every non-halted core executes one instruction. The cores are stepped one after the other in plain Python, with no threads. This models "the same cycle" for teaching; it is not real parallel hardware.

"Two PCs" means two separate state variables, not two different numbers. In the scripted demo both PCs are 0–4 during ticks 1–5. Then core 0 freezes at 4 when it halts, while core 1 continues to 9. `run(max_cycles)` raises `RuntimeError` if the cores never halt.

## 9. Shared-memory implementation (deliverable 9)

Both cores use the same 256-byte `SharedMemory` (PDF). To make simultaneous access deterministic, we use a clock rule (design choice):

1. At the start of a tick, take a snapshot of memory.
2. Both cores **LOAD** from that snapshot.
3. **STORE**s are buffered, then committed at the end of the tick: core 0 first, then core 1.

So a value stored in tick *n* becomes visible from tick *n + 1*. If both cores store to the same address in one tick, core 1's value remains. This mirrors the lecture idea that state changes on the clock edge. It is a teaching simplification, not a model of a real bus, arbiter or cache.

## 10. Bonus instructions

- **LOADI Rd, imm8** lets a program create its own constants, so register values no longer have to come from Python setup or memory. It introduces the immediate operand: imm8 → ALUSrc = 1 → ALU (R0 + imm8) → MemtoReg = 0 → Rd.
- **NOT Rd, Rs** adds one more bitwise ALU function at minimal cost.
- **SLT / SLTI** set Rd to 1 when Rs is less than Rt, or less than imm6 (0–63).
- **BEQ / BNE** follow the lecture's beq column: ALUSrc = 0, ALUOp = Subtract, Branch = 1, and the ALU's Zero output drives the PCSrc mux. BranchNe inverts that Zero test for BNE.
- **J** loads an absolute target into the PC, for loops and jumps that are too far for a 4-bit offset.

R0 being zero makes `BEQ Rx, R0, label` a direct "branch if Rx is zero". Together these instructions express `if/else` and `while`.

## 11. Simulation results and test evidence (deliverable 10)

The automated **test** suite has 33 unit tests across seven stages and runs with `python scripts/harness.py verify`. Before running, the harness checks the hashes of 14 protected test and spec files. The observed results and the full demo outputs are copied in `docs/RESULTS.md`. The tests cover:

- encoding, decoding and rejection of invalid words;
- register isolation and the hard-wired R0;
- all ALU operations with masking;
- PC advance and the HALT freeze;
- independent cores and the cycle count;
- memory bounds, next-tick visibility and the same-address conflict;
- the bonus instructions, `if`, `while`, backward loops and out-of-program targets;
- a cross-core spin-wait with an exact tick count;
- the presence of these deliverables.

**Scripted demo** (`python -m dualcore.demo`): 9 PASS checks.

- Core 0 computes 25 + 17 = 42 and STOREs it in tick 4.
- Core 1's LOAD in tick 4 still reads 0, and its LOAD in tick 5 reads 42.
- Core 1 then writes 47 and NOT 47 = 208 to memory.

**Branch demo** (`python -m dualcore.demo -b`): 5 PASS checks.

- Core 0's `while` loop sums 1..5 = 15.
- Core 1 spin-waits on a ready flag (LOAD + BEQ) until it becomes visible.
- Core 1 then runs an SLTI `if/else`.

## 12. Live demonstration (deliverable 12)

`docs/DEMO_SCRIPT.md` gives a short presentation sequence:

1. Run the tests.
2. Run the scripted demo, pointing out the separate PCs and registers and the STORE→LOAD hand-off.
3. Run the branch demo.
4. Try expressions such as `"200 + 100" "3 - 5"` to show 8-bit wrap-around and two's complement live, with the control signals printed for each step.

## 13. Limitations

- It is a simulator, not HDL hardware: there is no timing or gate-level detail.
- The course scope excludes flags, interrupts, pipelining, hazards and cache.
- Control flow is limited to BEQ/BNE (offsets −8 to +7) and J. There are no procedure calls and no stack.
- Within a tick the cores run one after the other, not truly in parallel. The snapshot/commit rule replaces real memory arbitration.
- Programs are written in Python with the encoder functions; there is no assembler.
