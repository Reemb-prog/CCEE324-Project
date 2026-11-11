# Final technical report: a simplified dual-core 8-bit processor (Python simulator)

CCEE 324 Computer Organization, Fall 2026 project.

## 1. Goal and approach

The brief asks for a two-core processor that runs arithmetic and logical instructions, where each core fetches, decodes and executes on its own and the two cores talk through a shared data memory. We built a **Python simulator** (one of the allowed tools), using only the standard library, in the four instructor milestones plus a bonus step. Each module matches a hardware block from the single-cycle datapath in the lectures, so the code can be explained block by block.

Where this report says **(PDF)**, the rule comes from the instructor brief. **(design choice)** marks a decision we made because the brief leaves it open; these are fixed in `docs/ISA.md`.

## 2. Architecture / block diagram (deliverable 1)

The Mermaid block diagram and a single-core flow are in `docs/ARCHITECTURE.md`. Each core contains a **PC**, an instruction program, a decoder, a **control** unit, a **register** file and an **ALU** (PDF). Only the data memory is **shared** (PDF).

| Block | File | Hardware meaning |
|---|---|---|
| Decoder / encoder | `dualcore/isa.py` | splits a 16-bit word into fields |
| Register file | `dualcore/registers.py` | 8 × 8-bit registers, one per core |
| Control unit | `dualcore/control.py` | opcode → control signals |
| ALU | `dualcore/alu.py` | 8 operations plus bonus NOT |
| Data memory | `dualcore/memory.py` | 256 × 8-bit, shared |
| Core | `dualcore/core.py` | PC + the blocks above, one instruction per step |
| Processor | `dualcore/processor.py` | two cores, one clock, shared memory |
| Demo | `dualcore/demo.py` | terminal demonstration |

## 3. Instruction set and instruction format (deliverables 2–3)

Specification (PDF): 8-bit data, 8 registers R0–R7 per core, 16-bit instructions, 256 × 8 data memory, 11 basic instructions (8 ALU, LOAD, STORE, HALT), clock-based execution.

The brief gives the opcodes and widths but not where each field sits, so the bit layout is a **design choice**:

| Form | Bits 15–12 | 11–9 | 8–6 | 5–3 | 2–0 | Used by |
|---|---|---|---|---|---|---|
| R | opcode | Rd | Rs | Rt | 000 | ADD SUB AND OR XOR NOR SLL SRL |
| M | opcode | Reg | address [8:1] | | bit 0 = 0 | LOAD (Reg = Rd), STORE (Reg = Rs) |
| I | opcode | Rd | immediate [8:1] | | bit 0 = 0 | bonus LOADI |
| U | opcode | Rd | Rs | 000000 | | bonus NOT |
| H | 1111 | all zero | | | | HALT |

Opcodes 0000–0111 are the ALU operations in the PDF's order, then 1000 LOAD, 1001 STORE, 1111 HALT (PDF), plus bonus 1010 LOADI and 1011 NOT. Example: `ADD R1, R2, R3` = `0000 001 010 011 000` = `0x0298`. The decoder rejects unknown opcodes (1100–1110), words with unused bits set, and values outside 0–65535 by raising `ValueError`, much as hardware raises an illegal-instruction exception. LOAD/STORE use an **absolute** 8-bit address, not MIPS base + offset (design choice).

## 4. ALU design (deliverable 4)

`alu_execute(op, a, b)` handles ADD, SUB, AND, OR, XOR, NOR, SLL and SRL (PDF). All values are unsigned 8-bit and every result is masked with `& 0xFF`, the way an 8-bit result bus drops extra bits:

- `250 + 10 = 4`: the carry out of bit 7 is lost.
- `3 − 5 = 254`: subtraction is two's-complement addition, `3 + (~5 + 1)`, and `11111110` is −2 read as signed.
- Shifts use the value in Rt; a shift of 8 or more gives 0. SRL is logical, so zeros come in from the left.

There is no flag register (no carry or zero flag) because there are no branches to use one.

## 5. Register-file design (deliverable 5)

Each `RegisterFile` object owns a private list of eight 8-bit values, all starting at 0 and all writable, including R0 (unlike MIPS `$zero`). Bad indices or out-of-range values raise `ValueError`. Every core builds its own object, so both cores can use "R1" while they are **different physical registers** (PDF example).

## 6. Control-unit design (deliverable 6)

The control unit uses the signal names from the lecture's single-cycle MIPS control table. `X` means "don't care" and is stored as `None`.

| Signal | R-type | LOAD | STORE | HALT | LOADI | NOT |
|---|---|---|---|---|---|---|
| RegDst | 1 | 1 | X | X | 1 | 1 |
| ALUSrc | 0 | X | X | X | X | X |
| MemtoReg | 0 | 1 | X | X | X | 0 |
| ImmToReg | 0 | 0 | 0 | 0 | 1 | 0 |
| RegWrite | 1 | 1 | 0 | 0 | 1 | 1 |
| MemRead | 0 | 1 | 0 | 0 | 0 | 0 |
| MemWrite | 0 | 0 | 1 | 0 | 0 | 0 |
| ALUOp | operation | X | X | X | X | NOT |

Three differences from MIPS follow from our ISA (design choices, explained in `docs/ARCHITECTURE.md`):

- RegDst is always 1, because the destination register is always in bits 11–9.
- ALUSrc and ALUOp are X for LOAD/STORE, because an absolute address needs no ALU addition.
- There is no Branch/PCSrc, because the course scope excludes branches.

## 7. Single-core implementation (deliverable 7)

`Core.step(memory)` runs exactly one instruction through the lecture's single-cycle path:

1. **Fetch** the word at `program[PC]`. A PC outside the program raises `RuntimeError` (missing HALT).
2. **Decode** the word, then generate control signals.
3. **Register read**: Rs and Rt (ALUSrc = 0).
4. **ALU** executes `ALUOp`.
5. **Memory** read or write if MemRead/MemWrite is set.
6. **Writeback** to Rd through the mux: immediate if ImmToReg, memory data if MemtoReg, otherwise the ALU result.
7. **Next PC** = PC + 1.

The PC is an index into the instruction list, so it advances by **1, not MIPS PC + 4** (design choice): instructions sit in a Python list, not byte-addressed memory. On **HALT** the core sets `halted`, the PC stays on the HALT instruction, and later steps do nothing (PDF: "stop when HALT is encountered").

## 8. Dual-core implementation (deliverable 8)

`DualCoreProcessor` creates two separate `Core` objects. Each has its own PC, registers, control unit and program; only the memory object is passed to both. Each `tick()` is one conceptual clock cycle in which every non-halted core executes one instruction. The cores are stepped one after the other in plain Python, with no threads. This models "same cycle" for teaching; it is not real parallel hardware. "Two PCs" means two separate state variables. In the demo both PCs equal 0–4 during ticks 1–5, yet core 0 freezes at 4 when it halts while core 1 continues to 9. `run(max_cycles)` raises `RuntimeError` if the cores never halt.

## 9. Shared-memory implementation (deliverable 9)

Both cores use the same 256-byte `SharedMemory` (PDF). To make simultaneous access deterministic we use a clock rule (design choice from `docs/ISA.md`):

1. At the start of a tick, take a snapshot of memory.
2. Both cores **LOAD** from that snapshot.
3. **STORE**s are buffered, then committed at the end of the tick: core 0 first, then core 1.

So a value stored in tick *n* becomes visible from tick *n + 1*, and if both cores store to the same address in one tick, core 1's value remains. This mirrors the lecture idea that state changes on the clock edge. It is a teaching simplification, not a model of a real bus, arbiter or cache. A single core stepped on its own reads and writes memory immediately.

## 10. Bonus instructions

The brief allows extra instructions; we added exactly two:

- **LOADI Rd, imm8** lets a program create its own constants. Without it, register values must come from Python test setup or from memory. It also introduces the immediate-operand idea. Because the constant comes from neither the ALU nor memory, the writeback mux gets a third input selected by the new **ImmToReg** signal (design choice, similar to the extra path MIPS extensions add for `lui`).
- **NOT Rd, Rs** adds one more bitwise ALU function at minimal cost. It is unary, so ALU input B is don't-care: `NOT 47 = 208` (`00101111 → 11010000`).

The 11 basic opcodes are unchanged.

## 11. Simulation results and test evidence (deliverable 10)

The automated **test** suite has 19 unit tests across six stages and runs via `python scripts/harness.py verify`. Before running, the harness also checks the hashes of 13 protected test and spec files. The observed results and full demo output are copied in `docs/RESULTS.md`. The tests cover:

- encoding, decoding and rejection of invalid words;
- register isolation;
- all ALU operations with masking;
- PC advance and HALT freeze;
- independent cores and the cycle count;
- memory bounds, next-tick visibility and the same-address conflict;
- both bonus instructions;
- the presence of these deliverables.

The scripted demo (`python -m dualcore.demo`) prints 9 PASS checks. Core 0 computes 25 + 17 = 42 and STOREs it in tick 4. Core 1's LOAD in tick 4 still reads 0, its LOAD in tick 5 reads 42, and it then writes 47 and NOT 47 = 208 to memory.

## 12. Live demonstration (deliverable 12)

`docs/DEMO_SCRIPT.md` gives a short presentation sequence: run the tests, run the scripted demo, point out the separate PCs and registers and the STORE→LOAD hand-off, then try expressions such as `"200 + 100" "3 - 5"` to show 8-bit wrap-around and two's complement live.

## 13. Limitations

- It is a simulator, not HDL hardware, with no timing or gate-level detail.
- There are no branches, jumps, flags, interrupts, pipelining, hazards or cache. These are excluded by the course scope, so programs run straight through to HALT.
- The cores run one after the other inside each tick, not truly in parallel. The snapshot/commit rule replaces real memory arbitration.
- LOAD/STORE use absolute addresses only. Programs are written in Python with the encoder functions; there is no assembler.
