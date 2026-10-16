# Milestone progress

The harness state in `.harness/state.json` is authoritative. Claude adds entries headed `[STAGE 01]`, `[STAGE 02]`, etc. to **both** `PROGRESS.md` and `docs/EXPLANATIONS.md`, after running tests for each stage, recording actual pass/fail counts, the main CO concept, and a limitation. The human changes the stage via `harness.py advance` after reviewing.

| Stage | Expected state at delivery |
|---|---|
| 01 ISA/datapath | Done, awaiting human approval |
| 02 ALU/single core | TODO |
| 03 two independent cores | TODO |
| 04 shared memory | TODO |
| 05 bonus instructions | TODO |
| 06 report/demo | TODO |

## Checkpoints

<!-- Claude appends date-free, compact entries below. Do not claim successful tests without running them. -->

### [STAGE 01] ISA, decoder, register file, control

- **Files built:** `dualcore/isa.py` (encode/decode of 16-bit words, `DecodedInstruction`), `dualcore/registers.py` (`RegisterFile`, 8 x 8-bit), `dualcore/control.py` (`ControlUnit`, `ControlSignals`); explanation paragraph added to `docs/ARCHITECTURE.md`.
- **CO concept:** an instruction is just a binary word whose bit fields (opcode, Rd, Rs, Rt, address) are decoded into control signals (`reg_write`, `mem_read`, `mem_write`, `alu_op`) that steer the datapath.
- **Decisions:** field map and opcodes follow `docs/ISA.md` (project design decision; the PDF fixes widths/opcode count only). Bonus opcodes 1010/1011 are reserved: `decode` and `encode_imm` raise `ValueError` until stage 05 (implementation choice, per task 01).
- **Tests:** `python scripts/harness.py verify` → integrity OK (13 protected files), stage 01: **6 run, 6 passed, 0 failed**.
- **Limitations:** nothing executes yet — no ALU, memory, core, or PC logic (stages 02–04).
