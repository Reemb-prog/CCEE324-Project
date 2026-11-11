# Milestone progress

The harness state in `.harness/state.json` is authoritative. Claude adds entries headed `[STAGE 01]`, `[STAGE 02]`, etc. to **both** `PROGRESS.md` and `docs/EXPLANATIONS.md`, after running tests for each stage, recording actual pass/fail counts, the main CO concept, and a limitation. The human changes the stage via `harness.py advance` after reviewing.

| Stage | Expected state at delivery |
|---|---|
| 01 ISA/datapath | Approved |
| 02 ALU/single core | Approved |
| 03 two independent cores | Approved |
| 04 shared memory | Done, awaiting human approval |
| 05 bonus instructions | TODO |
| 06 report/demo | TODO |

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
