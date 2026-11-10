"""Control unit: turns a decoded instruction into datapath control signals.

The signal names follow the single-cycle MIPS control table from the lectures
(RegDst, ALUSrc, MemtoReg, RegWrite, MemRead, MemWrite, ALUOp). A value of
None means "X" (don't care): the datapath ignores that signal for the
instruction. Values are adapted to this project's 16-bit ISA:

    signal      R-type   LOAD   STORE   HALT
    reg_dst       1       1      X       X
    alu_src       0       X      X       X
    mem_to_reg    0       1      X       X
    reg_write     1       1      0       0
    mem_read      0       1      0       0
    mem_write     0       0      1       0
    alu_op       name     X      X       X

There is no Branch signal: this ISA has no branch instructions, so the next
PC is always PC+1 (or unchanged after HALT).
"""
from dataclasses import dataclass
from typing import Optional

from .isa import ALU_OPS, DecodedInstruction


@dataclass(frozen=True)
class ControlSignals:
    # RegDst: 1 = write register comes from bits [11:9]. Unlike MIPS (lw writes
    # rt, R-type writes rd), every instruction here that writes a register
    # names it in [11:9], so the value is 1 whenever RegWrite is 1.
    reg_dst: Optional[bool] = None
    # ALUSrc: 0 = ALU input B is register Rt. LOAD/STORE use an absolute
    # 8-bit address taken straight from the instruction (no base + offset),
    # so the ALU is unused for them and ALUSrc is X instead of MIPS's 1.
    alu_src: Optional[bool] = None
    # MemtoReg: 0 = write back the ALU result, 1 = write back the memory byte.
    mem_to_reg: Optional[bool] = None
    reg_write: bool = False   # write a result into register Rd
    mem_read: bool = False    # read shared data memory (LOAD)
    mem_write: bool = False   # write shared data memory (STORE)
    # ALUOp: the opcode itself names the ALU operation (no MIPS funct field or
    # separate ALU-control unit). None when the ALU is not used.
    alu_op: Optional[str] = None


class ControlUnit:
    def signals(self, decoded: DecodedInstruction) -> ControlSignals:
        name = decoded.mnemonic
        if name in ALU_OPS:
            return ControlSignals(reg_dst=True, alu_src=False, mem_to_reg=False,
                                  reg_write=True, alu_op=name)
        if name == "LOAD":
            return ControlSignals(reg_dst=True, mem_to_reg=True,
                                  reg_write=True, mem_read=True)
        if name == "STORE":
            return ControlSignals(mem_write=True)
        if name == "HALT":
            return ControlSignals()
        raise ValueError(f"no control signals defined for {name!r}")
