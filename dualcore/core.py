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

        event = {"pc": pc, "word": word, "mnemonic": decoded.mnemonic, "halted": False}

        # Register read + execute: ALUSrc=0, so ALU input B is register Rt
        # (unary NOT has ALUSrc=X and ignores B). LOAD/STORE/LOADI leave
        # alu_op unset: they need no ALU.
        alu_result = None
        if signals.alu_op is not None:
            a = self.registers.read(decoded.rs)
            b = self.registers.read(decoded.rt) if signals.alu_src is False else 0
            alu_result = alu_execute(signals.alu_op, a, b)

        # Memory access: the address comes straight from instruction bits [8:1]
        mem_data = None
        if signals.mem_read:
            mem_data = memory.read(decoded.address)
            event["address"] = decoded.address
        if signals.mem_write:
            stored = self.registers.read(decoded.rs)
            memory.write(decoded.address, stored)
            event.update(address=decoded.address, stored=stored)

        # Writeback mux: ImmToReg picks the immediate (LOADI); otherwise MemtoReg
        # picks memory data (1) or the ALU result (0). RegDst=1 selects Rd.
        if signals.reg_write:
            if signals.imm_to_reg:
                write_data = decoded.immediate
            else:
                write_data = mem_data if signals.mem_to_reg else alu_result
            self.registers.write(decoded.rd, write_data)
            event.update(rd=decoded.rd, result=write_data)

        # Next PC: no branches, so always PC + 1
        self.pc = pc + 1
        return event
