"""Control unit: turns a decoded instruction into datapath control signals.

The signal names follow the single-cycle MIPS control table from the lectures
(RegDst, ALUSrc, MemtoReg, RegWrite, MemRead, MemWrite, Branch, ALUOp), plus
ImmToReg for the bonus LOADI and BranchNe/Jump for the stage-07 extension.
A value of None means "X" (don't care): the datapath ignores that signal for
the instruction. Values are adapted to this project's 16-bit ISA:

    signal      R-type  LOAD  STORE  HALT  LOADI  NOT   SLT  SLTI  BEQ  BNE   J
    reg_dst       1      1     X      X     1      1     1    1     X    X    X
    alu_src       0      X     X      X     X      X     0    1     0    0    X
    mem_to_reg    0      1     X      X     X      0     0    0     X    X    X
    imm_to_reg    0      0     0      0     1      0     0    0     0    0    0
    reg_write     1      1     0      0     1      1     1    1     0    0    0
    mem_read      0      1     0      0     0      0     0    0     0    0    0
    mem_write     0      0     1      0     0      0     0    0     0    0    0
    branch        0      0     0      0     0      0     0    0     1    1    0
    branch_ne     0      0     0      0     0      0     0    0     0    1    0
    jump          0      0     0      0     0      0     0    0     0    0    1
    alu_op       name    X     X      X     X     NOT   SLT  SLT   SUB  SUB   X

Next PC (the PCSrc mux): Jump -> target; Branch and the ALU's Zero test
passes (Zero for BEQ, not Zero for BNE) -> PC + 1 + offset; else PC + 1.
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
    # ALUSrc: 0 = ALU input B is register Rt, 1 = the instruction's immediate
    # (only SLTI). LOAD/STORE use an absolute 8-bit address taken straight from
    # the instruction (no base + offset), so the ALU is unused and ALUSrc is X.
    alu_src: Optional[bool] = None
    # MemtoReg: 0 = write back the ALU result, 1 = write back the memory byte.
    mem_to_reg: Optional[bool] = None
    # ImmToReg (bonus LOADI only): 1 = write back the 8-bit immediate from
    # instruction bits [8:1]; it overrides MemtoReg. This is a third input on
    # the writeback mux, like the extra path MIPS-style CPUs add for `lui`.
    imm_to_reg: bool = False
    reg_write: bool = False   # write a result into register Rd
    mem_read: bool = False    # read shared data memory (LOAD)
    mem_write: bool = False   # write shared data memory (STORE)
    # Branch: conditional branch (BEQ/BNE), as in the lecture table.
    branch: bool = False
    # BranchNe: branch when the ALU result is NOT zero (BNE) instead of zero.
    branch_ne: bool = False
    # Jump: unconditional jump to the absolute target (J).
    jump: bool = False
    # ALUOp: the opcode itself names the ALU operation (no MIPS funct field or
    # separate ALU-control unit). None when the ALU is not used.
    alu_op: Optional[str] = None


class ControlUnit:
    def signals(self, decoded: DecodedInstruction) -> ControlSignals:
        name = decoded.mnemonic
        if name in ALU_OPS or name == "SLT":
            return ControlSignals(reg_dst=True, alu_src=False, mem_to_reg=False,
                                  reg_write=True, alu_op=name)
        if name == "LOAD":
            return ControlSignals(reg_dst=True, mem_to_reg=True,
                                  reg_write=True, mem_read=True)
        if name == "STORE":
            return ControlSignals(mem_write=True)
        if name == "HALT":
            return ControlSignals()
        if name == "LOADI":
            return ControlSignals(reg_dst=True, imm_to_reg=True, reg_write=True)
        if name == "NOT":
            # Unary: ALU input B is unused, so ALUSrc is X.
            return ControlSignals(reg_dst=True, mem_to_reg=False,
                                  reg_write=True, alu_op="NOT")
        if name == "SLTI":
            return ControlSignals(reg_dst=True, alu_src=True, mem_to_reg=False,
                                  reg_write=True, alu_op="SLT")
        if name in ("BEQ", "BNE"):
            # Same column as the lecture's beq: ALU subtracts, Zero decides.
            return ControlSignals(alu_src=False, branch=True,
                                  branch_ne=(name == "BNE"), alu_op="SUB")
        if name == "J":
            return ControlSignals(jump=True)
        raise ValueError(f"no control signals defined for {name!r}")
