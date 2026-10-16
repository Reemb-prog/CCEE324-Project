# Minimal public Python API for stage tests

Create these files in `dualcore/`; no extra dependencies:

* `isa.py`: `DecodedInstruction` object with fields `opcode` (int), `mnemonic` (uppercase str), `rd`, `rs`, `rt`, `address`, `immediate` (ints, default zero when unused). Functions: `decode(word:int) -> DecodedInstruction`, `encode_r(mnemonic, rd, rs, rt=0) -> int`, `encode_mem(mnemonic, reg, address) -> int`, `encode_imm(mnemonic, rd, value) -> int`, `encode_halt() -> int`.
  * `encode_r` accepts 8 ALU names and, beginning stage 05, unary NOT (Rt must be zero); `encode_imm` accepts LOADI only from stage 05.
  * `decode` must reject malformed/unknown machine words with `ValueError`.
* `registers.py`: `RegisterFile()` with eight initialized 8-bit values, `read(index:int)->int`, `write(index:int, value:int)->None`, `snapshot()->tuple[int,...]`. Invalid indices or values raise `ValueError`.
* `control.py`: `ControlUnit.signals(decoded)->ControlSignals` with attributes `reg_write`, `mem_read`, `mem_write` booleans, `alu_op` string or None. R instructions set write + opcode; LOAD sets read + write; STORE sets write-to-memory; HALT all false; bonus LOADI/NOT implemented in stage 05. Do not introduce hardware irrelevant to this single-cycle demo.
* `alu.py`: `alu_execute(mnemonic:str,a:int,b:int=0)->int` for 8 required operations; NOT added at stage 05. Bad mnemonic/values raise `ValueError`.
* `memory.py`: `SharedMemory()` with `read(address)->int`, `write(address,value)->None`, `snapshot()->tuple[int,...]`. Strict 0..255 bounds. Stage 04 may add tiny private internal clock-buffer helper.
* `core.py`: `Core(program: Sequence[int])`: public `pc` integer, `halted` bool, `registers: RegisterFile`. `step(memory)->dict` fetches 16-bit instruction at current PC, decodes, executes exactly once, writes back, increments PC unless HALT. Raises `RuntimeError` if PC is past program without HALT. For halted cores step is a no-op event. No need to invent elaborate trace classes.
* `processor.py`: `DualCoreProcessor(program0,program1,memory=None)` with `cores` indexable `(Core0,Core1)`, `memory:SharedMemory`, `cycles:int`; `tick()->tuple` steps both once, `run(max_cycles=100)->None` ticks until both halted. If budget exhausted, `RuntimeError`. The stage-04 tick should use the shared pre-tick memory snapshot and buffer writes before commit as specified in ISA.
* `demo.py`: executable via `python -m dualcore.demo`, runs two understandable, different programs and prints states/memory and verification; no UI.

Design is small enough for a student to explain each component in the live presentation. Typed dataclasses are optional. Use simple integer bit masks/shifts and explicit booleans. Do **not** rename the public API just to satisfy a style preference.
