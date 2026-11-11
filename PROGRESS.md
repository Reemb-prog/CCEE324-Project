# Milestone progress

The harness state in `.harness/state.json` is authoritative. Claude adds entries headed `[STAGE 01]`, `[STAGE 02]`, etc. to **both** `PROGRESS.md` and `docs/EXPLANATIONS.md`, after running tests for each stage, recording actual pass/fail counts, the main CO concept, and a limitation. The human changes the stage via `harness.py advance` after reviewing.

| Stage | Expected state at delivery |
|---|---|
| 01 ISA/datapath | Approved |
| 02 ALU/single core | Approved |
| 03 two independent cores | Approved |
| 04 shared memory | Approved |
| 05 bonus instructions | Approved |
| 06 report/demo | Approved |
| 07 branching extension (branch `branching`) | Done, awaiting human approval |

## Checkpoints

<!-- Claude appends date-free, compact entries below. Do not claim successful tests without running them. -->

### [STAGE 01] ISA, decoder, register file, control

- **Files built:** `dualcore/isa.py` (encode/decode of 16-bit words, `DecodedInstruction`), `dualcore/registers.py` (`RegisterFile`, 8 x 8-bit), `dualcore/control.py` (`ControlUnit`, `ControlSignals`); explanation paragraph added to `docs/ARCHITECTURE.md`.
- **CO concept:** an instruction is just a binary word whose bit fields (opcode, Rd, Rs, Rt, address) are decoded into control signals that steer the datapath.
- **Revision (human request):** `ControlSignals` now mirrors the lecture's single-cycle MIPS control table: `reg_dst`, `alu_src`, `mem_to_reg`, `reg_write`, `mem_read`, `mem_write`, `alu_op` (`None` = X/don't care). Values adapted to our ISA: RegDst=1 for both R-type and LOAD (Rd is always bits [11:9]); ALUSrc/ALUOp are X for LOAD/STORE (absolute address, no base+offset ALU add); no Branch signal (branches excluded). Comparison table in `docs/ARCHITECTURE.md`.
- **Decisions:** field map and opcodes follow `docs/ISA.md` (project design decision; the PDF fixes widths/opcode count only). Bonus opcodes 1010/1011 are reserved: `decode` and `encode_imm` raise `ValueError` until stage 05 (implementation choice, per task 01).
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stage 01: **6 run, 6 passed, 0 failed** (re-run after the control-signal revision: still 6/6).
- **Limitations:** nothing executes yet — no ALU, memory, core, or PC logic (stages 02–04).

### [STAGE 02] ALU and working single core

- **Files built:** `dualcore/alu.py` (`alu_execute`, 8 operations, 8-bit masking), `dualcore/memory.py` (`SharedMemory`, 256 x 8-bit, strict bounds), `dualcore/core.py` (`Core` with `pc`, `halted`, `registers`, `step(memory)`).
- **CO concept:** the single-cycle instruction cycle — fetch at PC, decode, control signals, register read, ALU execute, writeback, next PC — with each step in `Core.step` driven by the stage-01 signals (ALUSrc=0 → B is Rt; MemtoReg=0 → write ALU result; RegDst=1 → write Rd).
- **Decisions:** PC is a program-list index that advances by 1 (CLAUDE.md / ISA.md, replacing MIPS PC+4). HALT sets `halted` and freezes PC on the HALT index; later steps are no-op events (ISA.md). LOAD/STORE raise `NotImplementedError` inside the core until stage 04, as task 02 allows; `SharedMemory` and their control signals already exist.
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stages 01–02: **10 run, 10 passed, 0 failed**.
- **Limitations:** one core only; no memory access from programs yet; no processor/tick (stage 03).

### [STAGE 03] Two independent cores on one conceptual clock

- **Files built:** `dualcore/processor.py` (`DualCoreProcessor` with `cores`, `memory`, `cycles`, `tick()`, `run(max_cycles)`).
- **CO concept:** a multicore processor replicates the whole core (PC, register file, decoder/control, ALU, instruction program) while sharing one data memory; a common clock gives each active core one instruction per cycle.
- **Decisions:** `tick()` steps core 0 then core 1 in plain Python — no threads (CLAUDE.md / COURSE_BOUNDARY.md). A halted core's step is a no-op, so the other keeps running (ISA.md). `cycles` counts every tick; `run()` raises `RuntimeError` if both cores have not halted within `max_cycles` ticks of that call (INTERFACES.md). The shared memory object is created and passed to both cores, but snapshot/buffered STORE commits are left to stage 04.
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stages 01–03: **12 run, 12 passed, 0 failed**.
- **Limitations:** programs still cannot use LOAD/STORE (stage 04), so the cores do not yet communicate through memory.

### [STAGE 04] Shared memory, LOAD/STORE, terminal demo

- **Files built/changed:** `dualcore/core.py` (LOAD/STORE executed via the control signals: MemRead/MemWrite, MemtoReg mux), `dualcore/memory.py` (private `_TickMemoryPort`: snapshot reads, buffered writes), `dualcore/processor.py` (`tick()` snapshot → step both → commit core 0 then core 1), new `dualcore/demo.py` (`python -m dualcore.demo`).
- **CO concept:** a shared data memory as the only communication path between cores with private registers; a clocked state update where all reads in a cycle see the old state and writes take effect at the clock edge.
- **Decisions:** snapshot/commit order and "core 1 wins same-address conflicts" come from ISA.md's clock rule (a simulation choice, not a physical arbitration model). A standalone `Core.step(SharedMemory)` still reads/writes immediately (ISA.md). Demo registers are preset directly because LOADI is a stage-05 bonus.
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stages 01–04: **15 run, 15 passed, 0 failed**. `python -m dualcore.demo` → 7/7 built-in checks PASS, exit code 0.
- **Limitations:** no LOADI/NOT yet (stage 05); the demo is a first version that stage 06 may polish.

### [STAGE 05] Bonus instructions LOADI and NOT

- **Files changed:** `dualcore/isa.py` (I-form LOADI opcode 1010, U-form NOT opcode 1011; reserved-opcode rejection removed; unused-bit checks), `dualcore/alu.py` (`NOT`), `dualcore/control.py` (LOADI/NOT signals + new `imm_to_reg`), `dualcore/core.py` (writeback mux: immediate / memory / ALU; NOT ignores ALU input B), `dualcore/demo.py` (scripted demo now initializes registers with LOADI and uses NOT; display helpers for the two new formats), `docs/ARCHITECTURE.md` (control table extended).
- **CO concept:** immediate operands (a constant encoded inside the instruction word) and a unary bitwise ALU operation; adding an instruction means adding a decoder case, a control-table column and, if needed, a datapath path.
- **Decisions:** field layouts and opcodes from ISA.md; only these two bonuses (PDF / CLAUDE.md). The 11 required opcodes are unchanged.
- **Revision (later, human request, on branch `branching`):** LOADI originally used a third writeback-mux input `ImmToReg`. It now goes through the ALU instead (ALUSrc=1, ALUOp=PASS, MemtoReg=0, where PASS is an internal ALU function: result = input B), and `ImmToReg` is removed. This matches the lecture datapath and shares SLTI's immediate path. Re-verified: 32/32 tests pass, and the scripted and branch demo outputs are identical.
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stages 01–05: **17 run, 17 passed, 0 failed**. `python -m dualcore.demo` → 9/9 checks PASS, exit 0; expression mode `python -m dualcore.demo "200 + 100" "3 - 5"` exit 0.
- **Limitations:** the expression mode still loads operands from memory rather than LOADI, and does not accept NOT expressions (kept as written by the team).

### [STAGE 06] Final deliverables, results and demo script

- **Files built/changed:** `docs/FINAL_REPORT.md` (1,299 prose words plus tables; sections map to the PDF's 12 deliverables), `docs/RESULTS.md` (verbatim test and demo output from local runs), `docs/DEMO_SCRIPT.md` (about 5-minute presentation sequence plus likely questions), `dualcore/demo.py` tidied (accurate docstring, `-h/--help`).
- **CO concept:** connecting the whole design: block diagram → ISA/format → ALU → register file → control table → single-core cycle → dual-core independence → shared-memory clock rule → bonus instructions, with test evidence.
- **Decisions:** the report labels each rule as PDF requirement or design choice. The deliverables list was read from `reference/CCEE324_Project_Instructions.pdf` (text extracted with the Python standard library; no tools installed).
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stages 01–06: **19 run, 19 passed, 0 failed**; `python -m unittest discover -s tests` → 19 OK. `python -m dualcore.demo` → 9/9 PASS, exit 0; `python -m dualcore.demo "200 + 100" "3 - 5"` → exit 0; `"1 + 999"` → rejected, exit 2.
- **Limitations:** simulator only (no HDL or timing); no branches, flags, pipeline or cache; the cores are stepped one after the other within a tick; no assembler. Final submission readiness is the team's decision.

### [STAGE 07] Extension: SLT, SLTI, BEQ, BNE, J (if / while)

- **Contract (written first, reviewed by the team before implementation):** `tasks/07_branching.md`, ISA addendum in `docs/ISA.md`, API additions in `docs/INTERFACES.md`, scope note in `docs/COURSE_BOUNDARY.md`, 13 tests in `tests/test_stage_07.py`; stage registered in `scripts/harness.py`, hashes refreshed in `contracts.sha256` (tests 01–06 byte-identical), CLAUDE.md rules updated. Work is on git branch `branching`; `master` keeps the six-stage submission.
- **Files changed:** `dualcore/isa.py` (opcode 1101 SLT, 1110 SLTI, 1100 group BEQ/BNE/J; `offset` field; `encode_slti`, `encode_branch`, `encode_jump`), `dualcore/alu.py` (`SLT`), `dualcore/control.py` (`branch`, `branch_ne`, `jump`; SLTI uses ALUSrc=1), `dualcore/core.py` (ALUSrc mux for the immediate; next-PC mux), `dualcore/demo.py` (`-b` branch demo, display helpers), report/results/demo script/architecture table.
- **CO concept:** control flow in a single-cycle datapath: the ALU subtracts, its zero result plus the Branch signal drive the PCSrc mux, branch target = PC + 1 + offset (index analogue of PC + 4 + offset<<2), Jump selects an absolute target.
- **Decisions (team-chosen):** proposed encoding (offset −8..+7, J target 0..255, SLTI imm 0..63, kind 00 invalid so `0xC000` stays illegal); unsigned comparisons; separate git branch; tests reviewed before implementation.
- **Tests:** `python scripts/harness.py verify` → integrity OK (14 protected files), stages 01–07: **32 run, 32 passed, 0 failed**. `python -m dualcore.demo -b` → 5/5 PASS, exit 0 (44 ticks); `python -m dualcore.demo` 9/9 PASS; expression mode exit 0.
- **Limitations:** short branch range (J needed for long jumps); no procedure calls/stack, flags or interrupts; FINAL_REPORT prose grew to ~1,630 words (slightly over the ~1,600 guideline).
- **Revisions (human requests, on branch `branching`):** (1) LOADI now goes through the ALU (ALUSrc=1, ALUOp=PASS, MemtoReg=0) and `ImmToReg` is removed. (2) R0 is hard-wired to zero for programs: the core discards instruction writes to R0, and `RegisterFile.write(0, …)` stays a direct test-setup path so the protected stage-01 test still holds. The ISA rule was amended, one test was added to `tests/test_stage_07.py`, and `contracts.sha256` was refreshed. Re-verified: **33 run, 33 passed, 0 failed**; all three demo outputs are byte-identical to before.
