"""ALU: the eight required 8-bit operations. All inputs and results are 0..255."""

MASK = 0xFF  # keep only the low 8 bits, like an 8-bit hardware result bus

_OPERATIONS = {
    "ADD": lambda a, b: (a + b) & MASK,      # carry out of bit 7 is dropped
    "SUB": lambda a, b: (a - b) & MASK,      # same as a + (~b + 1): two's complement
    "AND": lambda a, b: a & b,
    "OR":  lambda a, b: a | b,
    "XOR": lambda a, b: a ^ b,
    "NOR": lambda a, b: ~(a | b) & MASK,
    "SLL": lambda a, b: (a << b) & MASK,     # bits shifted past bit 7 are lost
    "SRL": lambda a, b: a >> b,              # logical: zeros shift in from the left
}


def alu_execute(mnemonic: str, a: int, b: int = 0) -> int:
    if mnemonic not in _OPERATIONS:
        raise ValueError(f"unknown ALU operation {mnemonic!r}")
    for name, value in (("a", a), ("b", b)):
        if type(value) is not int or not 0 <= value <= MASK:
            raise ValueError(f"ALU input {name} must be 0..255, got {value!r}")
    return _OPERATIONS[mnemonic](a, b)
