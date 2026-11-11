"""Instruction set: 16-bit machine-word encoding and decoding (see docs/ISA.md).

Field layout (bit 15 is the most significant bit):
    R form: [15:12]=opcode [11:9]=Rd  [8:6]=Rs [5:3]=Rt [2:0]=000
    M form: [15:12]=opcode [11:9]=Reg [8:1]=address    [0]=0
    I form: [15:12]=opcode [11:9]=Rd  [8:1]=immediate  [0]=0       (bonus LOADI)
    U form: [15:12]=opcode [11:9]=Rd  [8:6]=Rs [5:0]=000000        (bonus NOT)
    H form: [15:12]=1111   [11:0]=0
Stage 07 extension:
    S form: [15:12]=1110   [11:9]=Rd  [8:6]=Rs [5:0]=imm6          (SLTI)
    B form: [15:12]=1100   [11:10]=kind [9:7]=Rs [6:4]=Rt [3:0]=offset  (BEQ 01, BNE 10)
    J form: [15:12]=1100   [11:10]=11   [9:8]=00 [7:0]=target            (J)
    SLT uses the R form with opcode 1101.
"""
from dataclasses import dataclass

# The eight ALU operations use opcodes 0..7, in this order.
ALU_OPS = ("ADD", "SUB", "AND", "OR", "XOR", "NOR", "SLL", "SRL")

OPCODES = {name: code for code, name in enumerate(ALU_OPS)}
OPCODES.update({"LOAD": 0b1000, "STORE": 0b1001, "HALT": 0b1111})
# The two bonus instructions (stage 05).
OPCODES.update({"LOADI": 0b1010, "NOT": 0b1011})
# Stage 07 extension. Opcode 1100 is shared by BEQ/BNE/J, told apart by bits [11:10].
OPCODES.update({"SLT": 0b1101, "SLTI": 0b1110})
BRANCH_OPCODE = 0b1100
BRANCH_KINDS = {0b01: "BEQ", 0b10: "BNE", 0b11: "J"}   # kind 00 is invalid
MNEMONICS = {code: name for name, code in OPCODES.items()}

# Instructions whose operands are laid out exactly like ADD (Rd, Rs, Rt).
R_FORM = ALU_OPS + ("SLT",)


@dataclass
class DecodedInstruction:
    opcode: int
    mnemonic: str
    rd: int = 0
    rs: int = 0
    rt: int = 0
    address: int = 0      # LOAD/STORE address, or J target
    immediate: int = 0    # LOADI / SLTI constant
    offset: int = 0       # BEQ/BNE signed offset (-8..7)


def _check_range(name: str, value: int, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer {low}..{high}, got {value!r}")


def encode_r(mnemonic: str, rd: int, rs: int, rt: int = 0) -> int:
    """Encode Rd = Rs op Rt (ALU ops and SLT), or bonus NOT: Rd = ~Rs (Rt must be 0)."""
    if mnemonic not in R_FORM and mnemonic != "NOT":
        raise ValueError(f"not an R-form instruction: {mnemonic!r}")
    for name, reg in (("rd", rd), ("rs", rs), ("rt", rt)):
        _check_range(name, reg, 0, 7)
    if mnemonic == "NOT" and rt != 0:
        raise ValueError("NOT takes one source register; Rt must be 0")
    return (OPCODES[mnemonic] << 12) | (rd << 9) | (rs << 6) | (rt << 3)


def encode_mem(mnemonic: str, reg: int, address: int) -> int:
    """Encode LOAD (reg is Rd) or STORE (reg is Rs) with an 8-bit address (base R0 = 0)."""
    if mnemonic not in ("LOAD", "STORE"):
        raise ValueError(f"not a memory instruction: {mnemonic!r}")
    _check_range("reg", reg, 0, 7)
    _check_range("address", address, 0, 255)
    return (OPCODES[mnemonic] << 12) | (reg << 9) | (address << 1)


def encode_imm(mnemonic: str, rd: int, value: int) -> int:
    """Encode bonus LOADI: Rd = 8-bit immediate value."""
    if mnemonic != "LOADI":
        raise ValueError(f"not an immediate instruction: {mnemonic!r}")
    _check_range("rd", rd, 0, 7)
    _check_range("immediate", value, 0, 255)
    return (OPCODES[mnemonic] << 12) | (rd << 9) | (value << 1)


def encode_slti(rd: int, rs: int, value: int) -> int:
    """Encode SLTI: Rd = 1 if Rs < value else 0 (unsigned, value 0..63)."""
    _check_range("rd", rd, 0, 7)
    _check_range("rs", rs, 0, 7)
    _check_range("immediate", value, 0, 63)
    return (OPCODES["SLTI"] << 12) | (rd << 9) | (rs << 6) | value


def encode_branch(mnemonic: str, rs: int, rt: int, offset: int) -> int:
    """Encode BEQ/BNE: if the test holds, PC = PC + 1 + offset (offset -8..7)."""
    kinds = {name: kind for kind, name in BRANCH_KINDS.items() if name != "J"}
    if mnemonic not in kinds:
        raise ValueError(f"not a branch instruction: {mnemonic!r}")
    _check_range("rs", rs, 0, 7)
    _check_range("rt", rt, 0, 7)
    _check_range("offset", offset, -8, 7)
    # offset & 0xF keeps the 4-bit two's-complement pattern (-1 -> 1111)
    return (BRANCH_OPCODE << 12) | (kinds[mnemonic] << 10) | (rs << 7) | (rt << 4) | (offset & 0xF)


def encode_jump(target: int) -> int:
    """Encode J: PC = target (absolute instruction index 0..255)."""
    _check_range("target", target, 0, 255)
    return (BRANCH_OPCODE << 12) | (0b11 << 10) | target


def encode_halt() -> int:
    return OPCODES["HALT"] << 12


def _decode_branch_group(word: int) -> DecodedInstruction:
    kind = (word >> 10) & 0b11
    if kind not in BRANCH_KINDS:
        raise ValueError(f"opcode 1100 needs kind 01 (BEQ), 10 (BNE) or 11 (J): {word:#06x}")
    mnemonic = BRANCH_KINDS[kind]
    if mnemonic == "J":
        if word & 0b11_0000_0000:
            raise ValueError(f"J unused bits [9:8] must be zero: {word:#06x}")
        return DecodedInstruction(BRANCH_OPCODE, mnemonic, address=word & 0xFF)
    raw = word & 0xF
    offset = raw - 16 if raw & 0b1000 else raw   # 4-bit two's complement -> -8..7
    return DecodedInstruction(BRANCH_OPCODE, mnemonic,
                              rs=(word >> 7) & 0b111,
                              rt=(word >> 4) & 0b111,
                              offset=offset)


def decode(word: int) -> DecodedInstruction:
    """Split a 16-bit machine word into its fields; reject malformed words."""
    _check_range("instruction word", word, 0, 0xFFFF)
    opcode = (word >> 12) & 0xF
    if opcode == BRANCH_OPCODE:
        return _decode_branch_group(word)
    if opcode not in MNEMONICS:
        raise ValueError(f"unknown opcode {opcode:04b}")
    mnemonic = MNEMONICS[opcode]

    if mnemonic in R_FORM:
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

    if mnemonic == "LOADI":
        if word & 0b1:
            raise ValueError(f"I-form unused bit [0] must be zero: {word:#06x}")
        return DecodedInstruction(opcode, mnemonic,
                                  rd=(word >> 9) & 0b111,
                                  immediate=(word >> 1) & 0xFF)

    if mnemonic == "NOT":
        if word & 0b111111:
            raise ValueError(f"U-form unused bits [5:0] must be zero: {word:#06x}")
        return DecodedInstruction(opcode, mnemonic,
                                  rd=(word >> 9) & 0b111,
                                  rs=(word >> 6) & 0b111)

    if mnemonic == "SLTI":   # all 16 bits are used, nothing to check
        return DecodedInstruction(opcode, mnemonic,
                                  rd=(word >> 9) & 0b111,
                                  rs=(word >> 6) & 0b111,
                                  immediate=word & 0b111111)

    # HALT
    if word & 0x0FFF:
        raise ValueError(f"HALT unused bits [11:0] must be zero: {word:#06x}")
    return DecodedInstruction(opcode, mnemonic)
