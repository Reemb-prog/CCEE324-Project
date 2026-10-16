# 03 — two independent CPU cores and clock steps

Goal: implement `processor.py` with two separate Core instances, instruction sequences and private register files. `tick` advances each non-halted core by one instruction on a common *conceptual* clock. The first core may halt earlier; the other must keep running. No actual Python threads or asynchronous tasks. For now, simple non-memory instructions are sufficient.

Acceptance: stage 01..03 tests verify register separation, independent PC advancement, per-core HALT, and tick count. Explain what "two PCs" means: they are separate state variables even if values happen to match. Stop.
