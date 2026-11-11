# Final design review: lecture first, extras only where needed

This is the last review before approval. We checked every module in `dualcore/` and every file in `docs/` against two sources:

- the instructor brief (PDF), which sets the scope;
- the lecture's single-cycle MIPS datapath and control table, which is the model the design should follow.

**Rule we applied:** use the lecture's blocks, formats and signal values unchanged wherever they fit our 8-bit, 16-bit-instruction machine. Add something new only when the lecture has no block for it.

## 1. Findings

| # | Finding | Where | Decision |
|---|---|---|---|
| 1 | LOAD/STORE sent the address straight to memory, leaving the ALU idle with ALUSrc = X and ALUOp = X. The lecture's `lw`/`sw` compute `base + offset` in the ALU with ALUSrc = 1 and ALUOp = Add. | `core.py`, `control.py` | **Changed.** R0 is now hard-wired to zero, so every imm8 instruction reads R0 as its base. The ALU computes `R0 + address` (ALUSrc = 1, ALUOp = ADD), exactly like `lw $t0, 100($zero)`. The control columns for LOAD and STORE now match the lecture's lw/sw columns everywhere except RegDst. |
| 2 | LOADI used an internal ALU function **PASS** (result = input B). We only needed PASS because R0 was not hard-wired. | `alu.py`, `control.py` | **Removed PASS.** LOADI is now `Rd = R0 + imm8` (ALUOp = ADD), the same idea as MIPS `addi $t0, $zero, imm`. The ALU now holds only real instructions: the 8 required operations, NOT and SLT. |
| 3 | R0 was hard-wired on writes only. A value placed in R0 by Python test setup could still be read by an instruction. | `core.py` | **Fixed.** The core also reads R0 as 0, like MIPS `$zero`. `RegisterFile` is unchanged, so the protected stage-01 register-file test still passes. |
| 4 | The docs used six format names (R, M, I, U, H, S, B, J). The lecture uses three: R, I, J. | `ISA.md`, report, architecture | **Renamed only. No bit layout changed.** R = register operations (NOT is R with Rt = 000). I = a register plus an immediate: imm8 for LOAD/STORE/LOADI, imm6 for SLTI, offset4 for BEQ/BNE. J = J. HALT is a special all-zero word. |
| 5 | The demos began with `LOADI R0, 0`, which does nothing now that R0 is hard-wired. | `demo.py` | **Removed.** The branch demo is one tick shorter, and all of its outputs were regenerated. |
| 6 | The report was built up in layers ("original design… stage-07 revision… section 10b"), so it read as a change log rather than a single design. | `FINAL_REPORT.md` | **Rewritten** to present the final design once, in the deliverable order. The history now lives only in `PROGRESS.md` and this file. |
| 7 | Stale statements remained: `dualcore/README.md` said the components were not implemented; `ISA.md` said "every register is writable including R0"; `COURSE_BOUNDARY.md` listed branch/jump as excluded; `ARCHITECTURE.md` had no next-PC hardware in its diagram. | several | **Fixed.** The architecture diagram now shows the lecture datapath: PC + 1 adder, ALUSrc mux, MemtoReg mux, sign-extend, branch adder and the PCSrc/Jump muxes. |

## 2. What is still outside the lecture, and why

| Addition | Why it is needed | Source |
|---|---|---|
| PC + 1 instead of PC + 4 | Instructions sit in a list of 16-bit words, not in byte-addressed memory. | Implementation choice (required by CLAUDE.md) |
| RegDst is always 1 | Every instruction that writes a register names it in bits [11:9], so the RegDst mux has only one real input. | Forced by the 16-bit format |
| ALUOp names the operation | The 4-bit opcode selects the ALU function directly, so there is no `funct` field and no separate ALU-control unit. | Forced by the 16-bit format |
| **BranchNe** signal | The lecture table has `beq` only. BNE needs the Zero test inverted. This is the **only signal not found in the lecture or textbook**. | Extension |
| **Jump** signal | This is the textbook's own extension of the single-cycle datapath for `j`. It is not in the lecture's 8-signal table. | Textbook (Patterson & Hennessy) |
| 2-bit "kind" field in opcode 1100 | Only three opcodes were free for five new instructions, and the word `0xC000` must stay illegal. | Encoding choice |
| Unsigned SLT/SLTI | All data in this machine is unsigned 8-bit, so SLT behaves like MIPS `sltu`. | Design choice |
| Snapshot/commit memory rule | Makes two cores using one memory in the same tick deterministic. | Design choice (in ISA.md) |

## 3. Scope check

- **Required (PDF):** 2 cores; 8-bit data; 8 registers per core; 16-bit instructions; 256 × 8 shared memory; ADD, SUB, AND, OR, XOR, NOR, SLL, SRL, LOAD, STORE, HALT. All present.
- **Bonus (the PDF allows extra instructions):** LOADI and NOT (stage 05); SLT, SLTI, BEQ, BNE and J (stage 07, human-approved).
- **Still excluded:** pipelining, hazards, cache, interrupts, flags, procedure calls/stack, multiply/divide, threads, GUI, an assembler.

## 4. Effect on tests and demos

- The 33 tests are unchanged, and all 33 pass.
- The scripted demo and the expression mode give the same results. Their control lines now print `ALUSrc=1 ALUOp=ADD` for LOAD and STORE.
- The branch demo gives the same results one tick earlier, because its no-op `LOADI R0, 0` lines were removed.
- The new outputs are in `docs/RESULTS.md`.
