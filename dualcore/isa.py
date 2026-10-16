"""Instruction set: 16-bit machine-word encoding and decoding (see docs/ISA.md).

Field layout (bit 15 is the most significant bit):
    R form: [15:12]=opcode [11:9]=Rd  [8:6]=Rs [5:3]=Rt [2:0]=000
    M form: [15:12]=opcode [11:9]=Reg [8:1]=address    [0]=0
    H form: [15:12]=1111   [11:0]=0
"""
from dataclasses import dataclass

# The eight ALU operations use opcodes 0..7, in this order.
ALU_OPS = ("ADD", "SUB", "AND", "OR", "XOR", "NOR", "SLL", "SRL")

OPCODES = {name: code for code, name in enumerate(ALU_OPS)}
OPCODES.update({"LOAD": 0b1000, "STORE": 0b1001, "HALT": 0b1111})
MNEMONICS = {code: name for name, code in OPCODES.items()}

# Bonus opcodes are reserved here but not implemented until stage 05.
RESERVED_BONUS = {0b1010: "LOADI", 0b1011: "NOT"}


@dataclass
class DecodedInstruction:
    opcode: int
    mnemonic: str
    rd: int = 0
    rs: int = 0
    rt: int = 0
    address: int = 0
    immediate: int = 0


def _check_range(name: str, value: int, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer {low}..{high}, got {value!r}")


def encode_r(mnemonic: str, rd: int, rs: int, rt: int = 0) -> int:
    """Encode one of the eight ALU operations: Rd = Rs op Rt."""
    if mnemonic not in ALU_OPS:
        raise ValueError(f"not an R-form instruction: {mnemonic!r}")
    for name, reg in (("rd", rd), ("rs", rs), ("rt", rt)):
        _check_range(name, reg, 0, 7)
    return (OPCODES[mnemonic] << 12) | (rd << 9) | (rs << 6) | (rt << 3)


def encode_mem(mnemonic: str, reg: int, address: int) -> int:
    """Encode LOAD (reg is Rd) or STORE (reg is Rs) with an 8-bit absolute address."""
    if mnemonic not in ("LOAD", "STORE"):
        raise ValueError(f"not a memory instruction: {mnemonic!r}")
    _check_range("reg", reg, 0, 7)
    _check_range("address", address, 0, 255)
    return (OPCODES[mnemonic] << 12) | (reg << 9) | (address << 1)


def encode_imm(mnemonic: str, rd: int, value: int) -> int:
    """LOADI is a bonus instruction, implemented only at stage 05."""
    raise ValueError(f"immediate instruction {mnemonic!r} is not implemented yet (bonus, stage 05)")


def encode_halt() -> int:
    return OPCODES["HALT"] << 12


def decode(word: int) -> DecodedInstruction:
    """Split a 16-bit machine word into its fields; reject malformed words."""
    _check_range("instruction word", word, 0, 0xFFFF)
    opcode = (word >> 12) & 0xF
    if opcode in RESERVED_BONUS:
        raise ValueError(f"opcode {opcode:04b} ({RESERVED_BONUS[opcode]}) is reserved, not implemented yet")
    if opcode not in MNEMONICS:
        raise ValueError(f"unknown opcode {opcode:04b}")
    mnemonic = MNEMONICS[opcode]

    if mnemonic in ALU_OPS:
        if word & 0b111:
            raise ValueError(f"R-form unused bits [2:0] must be zero: {word:#06x}")
        return DecodedInstruction(opcode, mnemonic,
                                  rd=(word >> 9) & 0b111,
                                  rs=(word >> 6) & 0b111,
                                  rt=(word >> 3) & 0b111)

    if mnemonic in ("LOAD", "STORE"):
        if word & 0b1:
            raise ValueError(f"M-form unused bit [0] must be zero: {word:#06x}")
        reg = (word >> 9) & 0b111
        address = (word >> 1) & 0xFF
        if mnemonic == "LOAD":
            return DecodedInstruction(opcode, mnemonic, rd=reg, address=address)
        return DecodedInstruction(opcode, mnemonic, rs=reg, address=address)

    # HALT
    if word & 0x0FFF:
        raise ValueError(f"HALT unused bits [11:0] must be zero: {word:#06x}")
    return DecodedInstruction(opcode, mnemonic)
