"""Control unit: turns a decoded instruction into datapath control signals.

The signal names and values follow the single-cycle MIPS control table from
the lectures (RegDst, ALUSrc, MemtoReg, RegWrite, MemRead, MemWrite, Branch,
ALUOp). Jump is the textbook's extension for `j`; BranchNe (for BNE) is the
only signal added by this project. None means "X" (don't care).

    signal      R-type  LOAD  STORE  HALT  LOADI  NOT   SLT  SLTI  BEQ  BNE   J
    reg_dst       1      1     X      X     1      1     1    1     X    X    X
    alu_src       0      1     1      X     1      X     0    1     0    0    X
    mem_to_reg    0      1     X      X     0      0     0    0     X    X    X
    reg_write     1      1     0      0     1      1     1    1     0    0    0
    mem_read      0      1     0      0     0      0     0    0     0    0    0
    mem_write     0      0     1      0     0      0     0    0     0    0    0
    branch        0      0     0      0     0      0     0    0     1    1    0
    branch_ne     0      0     0      0     0      0     0    0     0    1    0
    jump          0      0     0      0     0      0     0    0     0    0    1
    alu_op       name   ADD   ADD     X    ADD    NOT   SLT  SLT   SUB  SUB   X

LOAD, STORE and LOADI have no Rs field, so their base register is R0 (always
0): the ALU computes R0 + imm8, like MIPS `lw $t0, 100($zero)` and
`addi $t0, $zero, 5`.

Next PC (PCSrc mux): Jump -> target; Branch and the Zero test passes (Zero for
BEQ, not Zero for BNE) -> PC + 1 + offset; otherwise PC + 1.
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
    # (address for LOAD/STORE, imm8 for LOADI, imm6 for SLTI).
    alu_src: Optional[bool] = None
    # MemtoReg: 0 = write back the ALU result, 1 = write back the memory byte.
    mem_to_reg: Optional[bool] = None
    reg_write: bool = False   # write a result into register Rd
    mem_read: bool = False    # read shared data memory (LOAD)
    mem_write: bool = False   # write shared data memory (STORE)
    branch: bool = False      # conditional branch (BEQ/BNE), as in the lecture table
    branch_ne: bool = False   # added for BNE: branch when the ALU result is NOT zero
    jump: bool = False        # textbook extension: PC = absolute target (J)
    # ALUOp: the 4-bit opcode names the ALU operation directly (no MIPS funct
    # field or separate ALU-control unit). None when the ALU is not used.
    alu_op: Optional[str] = None


class ControlUnit:
    def signals(self, decoded: DecodedInstruction) -> ControlSignals:
        name = decoded.mnemonic
        if name in ALU_OPS or name == "SLT":
            return ControlSignals(reg_dst=True, alu_src=False, mem_to_reg=False,
                                  reg_write=True, alu_op=name)
        if name == "LOAD":       # lecture lw column: address = R0 + imm8
            return ControlSignals(reg_dst=True, alu_src=True, mem_to_reg=True,
                                  reg_write=True, mem_read=True, alu_op="ADD")
        if name == "STORE":      # lecture sw column: address = R0 + imm8
            return ControlSignals(alu_src=True, mem_write=True, alu_op="ADD")
        if name == "HALT":
            return ControlSignals()
        if name == "LOADI":      # Rd = R0 + imm8, like addi $t0, $zero, imm
            return ControlSignals(reg_dst=True, alu_src=True, mem_to_reg=False,
                                  reg_write=True, alu_op="ADD")
        if name == "NOT":        # unary: ALU input B is unused, so ALUSrc is X
            return ControlSignals(reg_dst=True, mem_to_reg=False,
                                  reg_write=True, alu_op="NOT")
        if name == "SLTI":
            return ControlSignals(reg_dst=True, alu_src=True, mem_to_reg=False,
                                  reg_write=True, alu_op="SLT")
        if name in ("BEQ", "BNE"):   # lecture beq column: ALU subtracts, Zero decides
            return ControlSignals(alu_src=False, branch=True,
                                  branch_ne=(name == "BNE"), alu_op="SUB")
        if name == "J":
            return ControlSignals(jump=True)
        raise ValueError(f"no control signals defined for {name!r}")
