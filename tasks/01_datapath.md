# 01 — ISA, decoder, register file, control, architecture

Goal: build `dualcore/isa.py`, `registers.py`, `control.py` using `docs/ISA.md` and `docs/INTERFACES.md`. Build only the 11 **required** opcodes for now; reserve bonus opcodes without implementing. Add 3–6 student-level sentences to `docs/ARCHITECTURE.md` explaining fetch, control, register read, ALU selection, writeback, and PC. Keep all integer validation and reserved-bit checks simple.

Acceptance: stage-01 tests validate 16-bit encoding/decoding, eight distinct writable 8-bit registers, illegal operand rejection, and representative RegWrite/MemRead/MemWrite signals. Do not implement core execution yet. Update PROGRESS and EXPLANATIONS once after testing. Stop.
