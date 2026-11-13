"""Tiny two-pass assembler: assembly text -> 16-bit machine words.

The syntax is the one `dualcore.demo.describe` prints, so a demo program can be
shown as text, edited, and assembled again:

    ADD   R3, R1, R2        # also SUB AND OR XOR NOR SLL SRL SLT
    NOT   R7, R6
    LOAD  R4, [100]         # brackets optional
    STORE R3, [100]
    LOADI R1, 25
    SLTI  R3, R2, 20
    BEQ   R4, R0, +3        # numeric offset ...
    BNE   R1, R0, loop      # ... or a label (offset = label - (PC + 1))
    J     4                 # absolute target or a label
    HALT
  loop:                     # labels end with ':' (may share a line)

Numbers may be decimal, 0x.. or 0b... `#` and `;` start comments. All range
checks are done by the `dualcore.isa` encoders, so the rules are the simulator's.
"""
import re
from dataclasses import dataclass, field

from dualcore.isa import (ALU_OPS, decode, encode_branch, encode_halt, encode_imm,
                          encode_jump, encode_mem, encode_r, encode_slti)

MAX_PROGRAM = 256
_LABEL = re.compile(r"^([A-Za-z_]\w*)\s*:")
_REGISTER = re.compile(r"^R([0-7])$", re.IGNORECASE)


@dataclass
class Program:
    words: list[int] = field(default_factory=list)
    source: list[str] = field(default_factory=list)   # cleaned text per word
    lines: list[int] = field(default_factory=list)    # 1-based source line per word (0 = auto)
    labels: dict[str, int] = field(default_factory=dict)
    auto_halt: bool = False


def _strip_comment(raw: str) -> str:
    return re.split(r"[#;]", raw, maxsplit=1)[0].strip()


def _register(token: str) -> int:
    match = _REGISTER.match(token)
    if not match:
        raise ValueError(f"expected a register R0..R7, got {token!r}")
    return int(match.group(1))


def _number(token: str) -> int:
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        token = token[1:-1].strip()
    try:
        return int(token, 0)
    except ValueError:
        raise ValueError(f"expected a number, got {token!r}") from None


def _target(token: str, labels: dict[str, int]) -> int:
    key = token.lower()
    if key in labels:
        return labels[key]
    return _number(token)


def _split(text: str) -> tuple[str, list[str]]:
    parts = text.split(None, 1)
    op = parts[0].upper()
    args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
    if any(a == "" for a in args):
        raise ValueError("empty operand (check the commas)")
    return op, args


def _expect(op: str, args: list[str], count: int) -> None:
    if len(args) != count:
        raise ValueError(f"{op} takes {count} operand(s), got {len(args)}")


def _encode(op: str, args: list[str], pc: int, labels: dict[str, int]) -> int:
    if op in ALU_OPS or op == "SLT":
        _expect(op, args, 3)
        return encode_r(op, _register(args[0]), _register(args[1]), _register(args[2]))
    if op == "NOT":
        _expect(op, args, 2)
        return encode_r(op, _register(args[0]), _register(args[1]))
    if op in ("LOAD", "STORE"):
        _expect(op, args, 2)
        return encode_mem(op, _register(args[0]), _number(args[1]))
    if op == "LOADI":
        _expect(op, args, 2)
        return encode_imm(op, _register(args[0]), _number(args[1]))
    if op == "SLTI":
        _expect(op, args, 3)
        return encode_slti(_register(args[0]), _register(args[1]), _number(args[2]))
    if op in ("BEQ", "BNE"):
        _expect(op, args, 3)
        token = args[2]
        if token.lower() in labels:
            offset = labels[token.lower()] - (pc + 1)
        else:
            offset = _number(token)
        return encode_branch(op, _register(args[0]), _register(args[1]), offset)
    if op == "J":
        _expect(op, args, 1)
        return encode_jump(_target(args[0], labels))
    if op == "HALT":
        _expect(op, args, 0)
        return encode_halt()
    raise ValueError(f"unknown instruction {op!r}")


def assemble(text: str) -> Program:
    """Assemble one core's program. Raises ValueError('line N: ...')."""
    # Pass 1: find instructions and label positions.
    pending: list[tuple[int, str]] = []
    labels: dict[str, int] = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw)
        while (match := _LABEL.match(line)):
            name = match.group(1).lower()
            if name in labels:
                raise ValueError(f"line {number}: label {match.group(1)!r} defined twice")
            if _REGISTER.match(name) or name.upper() in ("HALT",):
                raise ValueError(f"line {number}: {match.group(1)!r} cannot be a label")
            labels[name] = len(pending)
            line = line[match.end():].strip()
        if line:
            pending.append((number, line))

    # Pass 2: encode with every label known.
    program = Program(labels=labels)
    for pc, (number, line) in enumerate(pending):
        try:
            op, args = _split(line)
            word = _encode(op, args, pc, labels)
        except ValueError as error:
            raise ValueError(f"line {number}: {error}") from None
        program.words.append(word)
        program.source.append(" ".join(line.split()))
        program.lines.append(number)

    if not program.words:
        raise ValueError("program is empty (add at least HALT)")
    if decode(program.words[-1]).mnemonic not in ("HALT", "J"):
        program.words.append(encode_halt())
        program.source.append("HALT")
        program.lines.append(0)
        program.auto_halt = True
    if len(program.words) > MAX_PROGRAM:
        raise ValueError(f"program has {len(program.words)} instructions; the limit is {MAX_PROGRAM}")
    return program


def parse_memory(text: str) -> dict[int, int]:
    """'address=value' lines (comments allowed) -> {address: value}, both 0..255."""
    values: dict[int, int] = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw)
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"memory line {number}: use address=value, e.g. 100=42")
        left, right = line.split("=", 1)
        try:
            address, value = _number(left), _number(right)
        except ValueError as error:
            raise ValueError(f"memory line {number}: {error}") from None
        if not 0 <= address <= 255 or not 0 <= value <= 255:
            raise ValueError(f"memory line {number}: address and value must be 0..255")
        values[address] = value
    return values
