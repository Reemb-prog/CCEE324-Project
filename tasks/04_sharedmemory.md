# 04 — shared memory and verified communication

Goal: implement `LOAD` and `STORE` through the **same** SharedMemory object for both cores. CPU.tick() must present the **pre-tick memory snapshot** to both cores, buffer stores until the end, then commit core0 writes followed by core1 writes. Use a very small private `TickMemoryPort` adapter with read/write methods if needed; avoid complex bus emulation. Single-core Core.step(memory) may still use immediate memory operations. Build/update `dualcore/demo.py` to demonstrate a store by core 0 followed by a later read by core 1, plus separate register values.

Acceptance: stage 01..04 tests demonstrate next-tick visibility, 256-byte bounds, deterministic same-address conflict order, and halted-core handling. Explain snapshot/commit as a teaching simplification. Stop.
