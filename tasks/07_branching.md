# 07 — extension: SLT, SLTI, BEQ, BNE, J (human-requested, beyond the original six stages)

Goal: add conditional and unconditional control flow so programs can express `if` and `while`. Follow the encoding in the "Stage 07 extension" section of `docs/ISA.md` and the API additions in `docs/INTERFACES.md`. Keep every earlier opcode, test, and behavior unchanged (in particular `0xC000` stays invalid).

Build:
- `isa.py`: `SLT` (R-form, opcode 1101), `SLTI` (opcode 1110), and the 1100 branch/jump group (`BEQ`, `BNE`, `J`). Encoders `encode_r("SLT",…)`, `encode_slti`, `encode_branch`, `encode_jump`; decode with strict unused-bit and range checks.
- `alu.py`: `SLT` (unsigned 8-bit compare, result 1 or 0).
- `control.py`: new signals `branch`, `branch_ne`, `jump`. BEQ/BNE use ALUSrc=0 and ALUOp=SUB (the ALU's zero result decides the branch, as in the lecture's single-cycle datapath). SLTI uses ALUSrc=1 (immediate as ALU input B).
- `core.py`: next-PC mux — PC+1, branch target PC+1+offset when taken, or the jump target. Fetching outside the program still raises `RuntimeError`.
- `demo.py`: add a short demonstration of a `while` loop and an `if`, plus a cross-core spin-wait on shared memory.

Acceptance: stage 01..07 tests pass with `harness.py verify`. Explain branch target computation, the Zero/PCSrc idea, why SLT is unsigned, and the offset range limit. Update the report/results/demo script for the extension. Stop.
