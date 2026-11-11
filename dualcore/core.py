"""One single-cycle core: PC, private register file, decoder, control unit, ALU."""
from typing import Sequence

from .alu import alu_execute
from .control import ControlUnit
from .isa import decode
from .memory import SharedMemory
from .registers import RegisterFile

# I-format instructions with an 8-bit immediate have no Rs field, so the Rs
# read address is 000 and ALU input A is R0 (always 0), as with MIPS $zero.
_BASE_R0 = ("LOAD", "STORE", "LOADI")


class Core:
    def __init__(self, program: Sequence[int]) -> None:
        self.program = tuple(program)   # read-only instruction program
        self.pc = 0                     # index into self.program, not a byte address
        self.halted = False
        self.registers = RegisterFile()
        self.control = ControlUnit()

    def _read(self, index: int) -> int:
        """Register-file read port. R0 is hard-wired to zero (like MIPS $zero)."""
        return 0 if index == 0 else self.registers.read(index)

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
        uses_memory = signals.mem_read or signals.mem_write

        # Register read + ALU. Input A = Rs (R0 for LOAD/STORE/LOADI).
        # ALUSrc picks input B: 0 = register Rt, 1 = the immediate (the address
        # for LOAD/STORE, imm8 for LOADI, imm6 for SLTI). Unary NOT ignores B.
        alu_result = None
        if signals.alu_op is not None:
            a = self._read(0 if decoded.mnemonic in _BASE_R0 else decoded.rs)
            if signals.alu_src is True:
                b = decoded.address if uses_memory else decoded.immediate
            elif signals.alu_src is False:
                b = self._read(decoded.rt)
            else:
                b = 0
            alu_result = alu_execute(signals.alu_op, a, b)

        # Memory access at the ALU result (R0 + address = address).
        mem_data = None
        if signals.mem_read:
            mem_data = memory.read(alu_result)
            event["address"] = alu_result
        if signals.mem_write:
            stored = self._read(decoded.rs)
            memory.write(alu_result, stored)
            event.update(address=alu_result, stored=stored)

        # Writeback mux: MemtoReg picks memory data (1) or the ALU result (0).
        # RegDst=1 selects Rd. A write to R0 is discarded (hard-wired zero).
        if signals.reg_write:
            write_data = mem_data if signals.mem_to_reg else alu_result
            if decoded.rd != 0:
                self.registers.write(decoded.rd, write_data)
            event.update(rd=decoded.rd, result=self._read(decoded.rd))

        # Next PC (PCSrc mux): jump target, taken-branch target, or PC + 1.
        # A branch is taken when the ALU's Rs - Rt result is zero (BEQ) or
        # nonzero (BNE) -- the "Zero" output in the lecture datapath.
        if signals.jump:
            self.pc = decoded.address
        elif signals.branch:
            zero = alu_result == 0
            taken = zero != signals.branch_ne
            self.pc = pc + 1 + decoded.offset if taken else pc + 1
            event["taken"] = taken
        else:
            self.pc = pc + 1
        return event
