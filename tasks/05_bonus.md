# 05 — the optional bonus, bounded to two instructions

Goal: add only `LOADI Rd, imm8` (opcode 1010, I-format) and `NOT Rd, Rs` (opcode 1011, U-format), following the fixed bit layout. Update codec, control, ALU/Core and demo. LOADI is useful because core programs can set register values without a Python test fixture. NOT demonstrates another bitwise ALU function. Preserve all 11 basic opcodes unchanged.

Acceptance: stage 01..05 tests pass, including 255 immediate, NOT masking and a program that uses both bonus instructions. Briefly explain why these two were selected. No more bonuses. Stop.
