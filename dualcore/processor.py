"""Dual-core processor: two independent cores driven by one conceptual clock."""
from typing import Optional, Sequence

from .core import Core
from .memory import SharedMemory


class DualCoreProcessor:
    def __init__(self, program0: Sequence[int], program1: Sequence[int],
                 memory: Optional[SharedMemory] = None) -> None:
        # Two separate Core objects: each has its own PC, registers, decoder/control and program.
        self.cores = (Core(program0), Core(program1))
        self.memory = memory if memory is not None else SharedMemory()
        self.cycles = 0

    def tick(self) -> tuple:
        """One clock tick: every non-halted core executes exactly one instruction.

        The cores are stepped one after the other in plain Python; this models
        "both cores act in the same cycle" without real threads.
        """
        events = tuple(core.step(self.memory) for core in self.cores)
        self.cycles += 1
        return events

    def run(self, max_cycles: int = 100) -> None:
        """Tick until both cores have halted; fail if the cycle budget runs out."""
        used = 0
        while not all(core.halted for core in self.cores):
            if used >= max_cycles:
                raise RuntimeError(f"cores did not halt within {max_cycles} cycles")
            self.tick()
            used += 1
