"""Control unit: turns a decoded instruction into datapath control signals."""
from dataclasses import dataclass
from typing import Optional

from .isa import ALU_OPS, DecodedInstruction


@dataclass(frozen=True)
class ControlSignals:
    reg_write: bool = False   # write a result into register Rd
    mem_read: bool = False    # read shared data memory (LOAD)
    mem_write: bool = False   # write shared data memory (STORE)
    alu_op: Optional[str] = None  # which ALU operation to select, if any


class ControlUnit:
    def signals(self, decoded: DecodedInstruction) -> ControlSignals:
        name = decoded.mnemonic
        if name in ALU_OPS:
            return ControlSignals(reg_write=True, alu_op=name)
        if name == "LOAD":
            return ControlSignals(reg_write=True, mem_read=True)
        if name == "STORE":
            return ControlSignals(mem_write=True)
        if name == "HALT":
            return ControlSignals()
        raise ValueError(f"no control signals defined for {name!r}")
