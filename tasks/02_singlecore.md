# 02 — ALU and working single core

Goal: implement `alu.py`, `memory.py` base class, and `core.py`. Use the fixed decoding and control. Show one instruction per `Core.step`: fetch from this core's program, decode, read operands, execute, writeback, increment PC, or HALT. Add no extra opcodes yet. Values wrap to 8 bits. LOAD/STORE can stay unsupported inside the core until stage 04, but control signals and memory class must exist. Make the eight ALU instructions pass direct unit tests plus the single-core arithmetic trace.

Acceptance: stage 01+02 tests pass with `harness.py verify`. Briefly explain 8-bit subtraction via two's complement, bitwise behavior, PC increment, and halted state. Stop.
