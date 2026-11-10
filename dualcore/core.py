"""One single-cycle core: PC, private register file, decoder, control unit, ALU."""
from typing import Sequence

from .alu import alu_execute
from .control import ControlUnit
from .isa import decode
from .memory import SharedMemory
from .registers import RegisterFile


class Core:
    def __init__(self, program: Sequence[int]) -> None:
        self.program = tuple(program)   # read-only instruction program
        self.pc = 0                     # index into self.program, not a byte address
        self.halted = False
        self.registers = RegisterFile()
        self.control = ControlUnit()

    def step(self, memory: SharedMemory) -> dict:
        """Execute exactly one instruction (fetch, decode, execute, writeback, next PC)."""
        if self.halted:
            return {"pc": self.pc, "mnemonic": None, "halted": True}

        # Fetch
        if not 0 <= self.pc < len(self.program):
            raise RuntimeError(f"PC {self.pc} is outside the program (missing HALT?)")
        pc = self.pc
        word = self.program[pc]

        # Decode and generate control signals
        decoded = decode(word)
        signals = self.control.signals(decoded)

        if decoded.mnemonic == "HALT":
            self.halted = True          # PC stays frozen on the HALT instruction
            return {"pc": pc, "word": word, "mnemonic": "HALT", "halted": True}

        if signals.mem_read or signals.mem_write:
            raise NotImplementedError("LOAD/STORE execution is added in stage 04")

        # Register read: ALUSrc=0, so ALU input B is register Rt
        a = self.registers.read(decoded.rs)
        b = self.registers.read(decoded.rt)

        # Execute
        result = alu_execute(signals.alu_op, a, b)

        # Writeback: MemtoReg=0 selects the ALU result; RegDst=1 selects Rd
        if signals.reg_write:
            self.registers.write(decoded.rd, result)

        # Next PC: no branches, so always PC + 1
        self.pc = pc + 1
        return {"pc": pc, "word": word, "mnemonic": decoded.mnemonic,
                "rd": decoded.rd, "result": result, "halted": False}
