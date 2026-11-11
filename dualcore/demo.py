"""Terminal demo: two cores with private registers communicating through shared memory.

Run with:
    python -m dualcore.demo                  scripted demo: LOADI setup, core 0 STORE ->
                                             core 1 LOAD (next-tick visibility), NOT
    python -m dualcore.demo "3 + 4"          compile and trace one expression on core 0
    python -m dualcore.demo "3 + 4" "9 - 2"  one expression per core, run side by side
    python -m dualcore.demo -i               type expressions at a prompt
    python -m dualcore.demo -b               stage-07 branch demo: while loop, cross-core
                                             spin-wait, if/else (SLT, SLTI, BEQ, J)
    python -m dualcore.demo -h               show this help

Expression operators: + - & | ^ nor << >>  (operands 0..255, decimal, 0x.. or 0b..)
"""
import re
import sys
from typing import Optional

from .control import ControlUnit
from .isa import (decode, encode_branch, encode_halt, encode_imm, encode_jump,
                  encode_mem, encode_r, encode_slti)
from .processor import DualCoreProcessor

MAILBOX = 100   # core 0 writes here, core 1 reads it
RESULT = 101    # core 1 writes its answer here
INVERTED = 102  # core 1 writes NOT of its answer here


def describe(word: int) -> str:
    """Turn a machine word back into readable assembly."""
    d = decode(word)
    if d.mnemonic == "HALT":
        return "HALT"
    if d.mnemonic == "LOAD":
        return f"LOAD  R{d.rd}, [{d.address}]"
    if d.mnemonic == "STORE":
        return f"STORE R{d.rs}, [{d.address}]"
    if d.mnemonic == "LOADI":
        return f"LOADI R{d.rd}, {d.immediate}"
    if d.mnemonic == "NOT":
        return f"NOT   R{d.rd}, R{d.rs}"
    if d.mnemonic == "SLTI":
        return f"SLTI  R{d.rd}, R{d.rs}, {d.immediate}"
    if d.mnemonic in ("BEQ", "BNE"):
        return f"{d.mnemonic:<5} R{d.rs}, R{d.rt}, {d.offset:+d}"
    if d.mnemonic == "J":
        return f"J     {d.address}"
    return f"{d.mnemonic:<5} R{d.rd}, R{d.rs}, R{d.rt}"


def build_processor() -> DualCoreProcessor:
    # Core 0 (producer): compute 25 + 17 and publish it to memory.
    program0 = [
        encode_imm("LOADI", 1, 25),        # R1 = 25   (bonus LOADI: no Python fixture needed)
        encode_imm("LOADI", 2, 17),        # R2 = 17
        encode_r("ADD", 3, 1, 2),          # R3 = R1 + R2 = 42
        encode_mem("STORE", 3, MAILBOX),   # mem[100] = R3 (committed at end of tick 4)
        encode_halt(),
    ]
    # Core 1 (consumer): does its own work, then reads core 0's value.
    program1 = [
        encode_imm("LOADI", 1, 5),         # R1 = 5    (its own R1, not core 0's)
        encode_imm("LOADI", 2, 3),         # R2 = 3
        encode_r("SUB", 3, 1, 2),          # R3 = R1 - R2 = 2
        encode_mem("LOAD", 4, MAILBOX),    # tick 4: same tick as the STORE -> still sees 0
        encode_mem("LOAD", 5, MAILBOX),    # tick 5: the store is now visible -> 42
        encode_r("ADD", 6, 5, 1),          # R6 = 42 + 5 = 47
        encode_mem("STORE", 6, RESULT),    # mem[101] = 47
        encode_r("NOT", 7, 6),             # R7 = ~47 = 208   (bonus NOT)
        encode_mem("STORE", 7, INVERTED),  # mem[102] = 208
        encode_halt(),
    ]
    return DualCoreProcessor(program0, program1)


def show_event(core_id: int, core, event: dict) -> str:
    if event["mnemonic"] is None:
        return f"core{core_id}: (halted, PC stays {core.pc})"
    text = f"core{core_id}: PC={event['pc']}  {describe(event['word']):<20}"
    if "stored" in event:
        text += f" buffer mem[{event['address']}] <- {event['stored']}"
    elif "result" in event:
        text += f" R{event['rd']} <- {event['result']}"
    return text


def show_memory(cpu) -> str:
    return ", ".join(f"mem[{a}]={cpu.memory.read(a)}" for a in (MAILBOX, RESULT, INVERTED))


def run_scripted_demo() -> int:
    cpu = build_processor()
    print("Dual-core 8-bit CPU demo")
    for core_id, core in enumerate(cpu.cores):
        print(f"\nProgram {core_id}:")
        for index, word in enumerate(core.program):
            print(f"  {index}: {word:016b}  {describe(word)}")

    print("\nExecution (one instruction per active core per tick):")
    while not all(core.halted for core in cpu.cores):
        events = cpu.tick()
        print(f"tick {cpu.cycles}:")
        for core_id, (core, event) in enumerate(zip(cpu.cores, events)):
            print("   " + show_event(core_id, core, event))
        print(f"   end of tick: {show_memory(cpu)}")

    print("\nFinal state:")
    for core_id, core in enumerate(cpu.cores):
        regs = " ".join(f"R{i}={v}" for i, v in enumerate(core.registers.snapshot()))
        print(f"  core{core_id}: PC={core.pc} halted={core.halted}  {regs}")
    print(f"  shared memory: {show_memory(cpu)}")

    c0, c1 = cpu.cores
    checks = [
        ("core 0 stored 25 + 17 = 42 in shared memory", cpu.memory.read(MAILBOX) == 42),
        ("core 1 LOAD in the same tick as the STORE saw the old value 0", c1.registers.read(4) == 0),
        ("core 1 LOAD one tick later saw core 0's value 42", c1.registers.read(5) == 42),
        ("core 1 wrote 42 + 5 = 47 back to memory", cpu.memory.read(RESULT) == 47),
        ("core 1 wrote NOT 47 = 208 (00101111 -> 11010000)", cpu.memory.read(INVERTED) == 208),
        ("LOADI set R1/R2 from the programs themselves", (c0.registers.read(1), c1.registers.read(1)) == (25, 5)),
        ("R3 differs per core (private register files)", (c0.registers.read(3), c1.registers.read(3)) == (42, 2)),
        ("core 0 halted early at PC 4 while core 1 ran on", c0.pc == 4 and c1.pc == 9),
        ("both cores halted after 10 ticks", cpu.cycles == 10),
    ]
    print("\nVerification:")
    for text, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {text}")
    return 0 if all(ok for _, ok in checks) else 1


# ---------------------------------------------------------------------------
# Expression mode: "3 + 4" -> machine code -> traced execution
# ---------------------------------------------------------------------------

OPERATORS = {"+": "ADD", "-": "SUB", "&": "AND", "|": "OR", "^": "XOR",
             "nor": "NOR", "<<": "SLL", ">>": "SRL"}
_EXPRESSION = re.compile(r"^\(?\s*(\w+)\s*(<<|>>|nor|[-+&|^])\s*(\w+)\s*\)?$", re.IGNORECASE)

# Each core gets its own 3-byte area of shared memory: operand a, operand b, result.
DATA_BASE = (0, 16)


def parse_expression(text: str) -> tuple[int, str, int]:
    """'3 + 4' -> (3, 'ADD', 4). Operands are 8-bit: 0..255 (decimal, 0x.., or 0b..)."""
    match = _EXPRESSION.match(text.strip())
    if not match:
        raise ValueError(f"expected 'a op b' with op one of {' '.join(OPERATORS)}, got {text!r}")
    left, op, right = match.groups()
    values = []
    for token in (left, right):
        try:
            value = int(token, 0)
        except ValueError:
            raise ValueError(f"{token!r} is not a number") from None
        if not 0 <= value <= 255:
            raise ValueError(f"{token} does not fit in 8 bits (0..255)")
        values.append(value)
    return values[0], OPERATORS[op.lower()], values[1]


def compile_expression(mnemonic: str, base: int) -> list[int]:
    """Machine code for: mem[base+2] = mem[base] <op> mem[base+1]."""
    return [
        encode_mem("LOAD", 1, base),        # R1 = first operand
        encode_mem("LOAD", 2, base + 1),    # R2 = second operand
        encode_r(mnemonic, 3, 1, 2),        # R3 = R1 op R2
        encode_mem("STORE", 3, base + 2),   # result back to shared memory
        encode_halt(),
    ]


def fields(word: int) -> str:
    """Show a machine word split into its instruction-format fields."""
    d = decode(word)
    op = f"{d.opcode:04b}"
    if d.mnemonic == "HALT":
        return f"{op} 000000000000          (opcode | unused)"
    if d.mnemonic in ("LOAD", "STORE"):
        reg = d.rd if d.mnemonic == "LOAD" else d.rs
        return f"{op} {reg:03b} {d.address:08b} 0      (opcode | reg | address | 0)"
    if d.mnemonic == "LOADI":
        return f"{op} {d.rd:03b} {d.immediate:08b} 0      (opcode | rd | immediate | 0)"
    if d.mnemonic == "NOT":
        return f"{op} {d.rd:03b} {d.rs:03b} 000000      (opcode | rd | rs | unused)"
    if d.mnemonic == "SLTI":
        return f"{op} {d.rd:03b} {d.rs:03b} {d.immediate:06b}      (opcode | rd | rs | imm6)"
    if d.mnemonic in ("BEQ", "BNE"):
        kind = "01" if d.mnemonic == "BEQ" else "10"
        return f"{op} {kind} {d.rs:03b} {d.rt:03b} {d.offset & 0xF:04b}   (opcode | kind | rs | rt | offset)"
    if d.mnemonic == "J":
        return f"{op} 11 00 {d.address:08b}     (opcode | kind | 00 | target)"
    return f"{op} {d.rd:03b} {d.rs:03b} {d.rt:03b} 000     (opcode | rd | rs | rt | unused)"


def _bit(value: Optional[bool]) -> str:
    return "X" if value is None else str(int(value))


def show_control(word: int) -> str:
    s = ControlUnit().signals(decode(word))
    return (f"RegDst={_bit(s.reg_dst)} ALUSrc={_bit(s.alu_src)} MemtoReg={_bit(s.mem_to_reg)} "
            f"ImmToReg={_bit(s.imm_to_reg)} RegWrite={_bit(s.reg_write)} MemRead={_bit(s.mem_read)} "
            f"MemWrite={_bit(s.mem_write)} Branch={_bit(s.branch)} BranchNe={_bit(s.branch_ne)} "
            f"Jump={_bit(s.jump)} ALUOp={s.alu_op or 'X'}")


def explain_step(event: dict, regs_before: tuple[int, ...], core) -> list[str]:
    """Plain-English lines for what one core did in one tick."""
    if event["mnemonic"] is None:
        return [f"(halted, PC stays {core.pc})"]
    word = event["word"]
    d = decode(word)
    lines = [f"fetch    PC={event['pc']} -> {word:#06x}  {describe(word)}",
             f"control  {show_control(word)}"]
    if d.mnemonic == "HALT":
        lines.append(f"halt     core stops; PC frozen at {core.pc}")
        return lines
    if d.mnemonic == "LOAD":
        lines.append(f"memory   read mem[{d.address}] = {event['result']} (MemRead=1)")
        lines.append(f"write    R{d.rd} <- {event['result']}  (MemtoReg=1: memory data, not ALU)")
    elif d.mnemonic == "STORE":
        lines.append(f"read     R{d.rs} = {event['stored']}")
        lines.append(f"memory   buffer mem[{d.address}] <- {event['stored']} "
                     f"(MemWrite=1, committed at end of tick)")
    elif d.mnemonic == "LOADI":
        lines.append(f"write    R{d.rd} <- {d.immediate}  (ImmToReg=1: immediate from the instruction)")
    elif d.mnemonic == "NOT":
        a = regs_before[d.rs]
        lines.append(f"read     R{d.rs} = {a} ({a:08b})")
        lines.append(f"ALU      NOT -> {event['result']} ({event['result']:08b})")
        lines.append(f"write    R{d.rd} <- {event['result']}  (MemtoReg=0: ALU result)")
    else:
        a, b = regs_before[d.rs], regs_before[d.rt]
        lines.append(f"read     R{d.rs} = {a} ({a:08b}), R{d.rt} = {b} ({b:08b})")
        lines.append(f"ALU      {d.mnemonic} -> {event['result']} ({event['result']:08b})")
        lines.append(f"write    R{d.rd} <- {event['result']}  (MemtoReg=0: ALU result)")
    lines.append(f"next PC  {event['pc']} + 1 = {core.pc}")
    return lines


def explain_wrap(a: int, mnemonic: str, b: int, result: int) -> str:
    """Say why the 8-bit answer differs from ordinary arithmetic, if it does."""
    exact = {"ADD": a + b, "SUB": a - b, "SLL": a << b}.get(mnemonic)
    if exact is None or exact == result:
        return ""
    if mnemonic == "SUB":
        return (f"  note: {a} - {b} = {exact} is negative; the 8-bit pattern {result:08b} is "
                f"{exact} in two's complement, read as unsigned it is {result}.")
    if mnemonic == "ADD":
        return f"  note: {exact} does not fit in 8 bits; the carry out of bit 7 is dropped ({exact} - 256 = {result})."
    return f"  note: bits shifted past bit 7 are lost ({exact} masked to 8 bits = {result})."


def run_expressions(expr0: str, expr1: Optional[str] = None) -> int:
    parsed = [parse_expression(expr0)] + ([parse_expression(expr1)] if expr1 else [])
    programs = [compile_expression(m, DATA_BASE[i]) for i, (_, m, _) in enumerate(parsed)]
    if len(programs) == 1:
        programs.append([encode_halt()])   # core 1 has no work: it halts on tick 1
    cpu = DualCoreProcessor(programs[0], programs[1])

    print("1) Parse")
    for i, (text, (a, m, b)) in enumerate(zip((expr0, expr1), parsed)):
        print(f"   core{i}: {text.strip()!r} -> ALU operation {m} with operands {a} and {b}")

    print("\n2) Put the operands in shared data memory (like a MIPS .data section;")
    print("   bonus LOADI could load them directly, but this mode shows LOAD/STORE)")
    for i, (a, _, b) in enumerate(parsed):
        base = DATA_BASE[i]
        cpu.memory.write(base, a)
        cpu.memory.write(base + 1, b)
        print(f"   mem[{base}] = {a} ({a:08b})   mem[{base + 1}] = {b} ({b:08b})")

    print("\n3) Assemble into 16-bit machine code")
    for i, core in enumerate(cpu.cores):
        print(f"   core{i} program:")
        for index, word in enumerate(core.program):
            print(f"     {index}: {describe(word):<17} {word:#06x} = {fields(word)}")

    print("\n4) Execute (each tick: one instruction per active core)")
    while not all(core.halted for core in cpu.cores):
        regs_before = [core.registers.snapshot() for core in cpu.cores]
        events = cpu.tick()
        print(f"   --- tick {cpu.cycles} ---")
        for i, (core, event) in enumerate(zip(cpu.cores, events)):
            for n, line in enumerate(explain_step(event, regs_before[i], core)):
                print(f"   {'core' + str(i) if n == 0 else '':<6} {line}")

    print("\n5) Result")
    ok = True
    for i, (a, m, b) in enumerate(parsed):
        base = DATA_BASE[i]
        result = cpu.memory.read(base + 2)
        expected = {"ADD": (a + b) & 0xFF, "SUB": (a - b) & 0xFF, "AND": a & b, "OR": a | b,
                    "XOR": a ^ b, "NOR": ~(a | b) & 0xFF, "SLL": (a << b) & 0xFF,
                    "SRL": a >> b}[m]
        ok = ok and result == expected
        print(f"   core{i}: mem[{base + 2}] = {result} ({result:08b})   "
              f"[{'PASS' if result == expected else 'FAIL'}] expected {expected}")
        wrap = explain_wrap(a, m, b, result)
        if wrap:
            print("   " + wrap)
    print(f"   {cpu.cycles} ticks.", end="")
    if len(parsed) == 2:
        r3 = [core.registers.read(3) for core in cpu.cores]
        print(f" Both cores used the names R1-R3, but each had its own copy "
              f"(core0 R3={r3[0]}, core1 R3={r3[1]}).", end="")
    print()
    return 0 if ok else 1


def interactive() -> int:
    print("Type an expression like 3 + 4  (ops: + - & | ^ nor << >>, operands 0..255).")
    print("Blank line or 'q' quits.")
    while True:
        try:
            expr0 = input("\ncore 0 expression> ").strip()
            if not expr0 or expr0.lower() in ("q", "quit", "exit"):
                return 0
            expr1 = input("core 1 expression (Enter = idle)> ").strip()
        except EOFError:
            return 0
        print()
        try:
            run_expressions(expr0, expr1 or None)
        except ValueError as error:
            print(f"error: {error}")


# ---------------------------------------------------------------------------
# Branch mode (stage 07): while loop, cross-core spin-wait, if/else
# ---------------------------------------------------------------------------

SUM_ADDR = 60    # core 0's loop result
FLAG_ADDR = 61   # core 0 sets this to 1 when the result is ready
VERDICT = 62     # core 1's if/else answer


def build_branch_processor() -> DualCoreProcessor:
    # Core 0: sum = 1 + 2 + 3 + 4 + 5 with a while loop, then publish it.
    program0 = [
        encode_imm("LOADI", 0, 0),            #  0: R0 = 0 (no hard-wired zero register)
        encode_imm("LOADI", 1, 1),            #  1: i = 1
        encode_imm("LOADI", 2, 6),            #  2: limit = 6
        encode_imm("LOADI", 3, 0),            #  3: sum = 0
        encode_imm("LOADI", 5, 1),            #  4: constant 1
        encode_r("SLT", 4, 1, 2),             #  5: top: R4 = (i < limit)
        encode_branch("BEQ", 4, 0, 3),        #  6: if R4 == 0 exit loop -> 10
        encode_r("ADD", 3, 3, 1),             #  7: sum += i
        encode_r("ADD", 1, 1, 5),             #  8: i += 1
        encode_jump(5),                       #  9: back to top
        encode_mem("STORE", 3, SUM_ADDR),     # 10: mem[60] = sum
        encode_mem("STORE", 5, FLAG_ADDR),    # 11: mem[61] = 1 (ready flag, after the data)
        encode_halt(),                        # 12
    ]
    # Core 1: wait for the flag, then: if sum < 20 then verdict = 1 else verdict = 0.
    program1 = [
        encode_imm("LOADI", 0, 0),            #  0: R0 = 0
        encode_mem("LOAD", 1, FLAG_ADDR),     #  1: wait: R1 = flag
        encode_branch("BEQ", 1, 0, -2),       #  2: while flag == 0 -> 1
        encode_mem("LOAD", 2, SUM_ADDR),      #  3: R2 = sum
        encode_slti(3, 2, 20),                #  4: R3 = (sum < 20)
        encode_branch("BEQ", 3, 0, 2),        #  5: if not -> else at 8
        encode_imm("LOADI", 4, 1),            #  6: then: verdict = 1
        encode_jump(9),                       #  7: skip else
        encode_imm("LOADI", 4, 0),            #  8: else: verdict = 0
        encode_mem("STORE", 4, VERDICT),      #  9: mem[62] = verdict
        encode_halt(),                        # 10
    ]
    return DualCoreProcessor(program0, program1)


def show_short(core, event: dict) -> str:
    if event["mnemonic"] is None:
        return "(halted)"
    text = f"PC={event['pc']:>2} {describe(event['word']):<17}"
    if "taken" in event:
        text += f" {'taken -> PC=' + str(core.pc) if event['taken'] else 'not taken'}"
    elif event["mnemonic"] == "J":
        text += f" jump -> PC={core.pc}"
    elif "stored" in event:
        text += f" mem[{event['address']}] <- {event['stored']}"
    elif "result" in event:
        text += f" R{event['rd']} <- {event['result']}"
    return text


def run_branch_demo() -> int:
    cpu = build_branch_processor()
    print("Branch demo: while loop on core 0, spin-wait + if/else on core 1")
    for core_id, core in enumerate(cpu.cores):
        print(f"\nProgram {core_id}:")
        for index, word in enumerate(core.program):
            print(f"  {index:>2}: {word:016b}  {describe(word)}")

    print("\nExecution (one line per tick):")
    flag_reads = 0
    while not all(core.halted for core in cpu.cores):
        events = cpu.tick()
        e1 = events[1]
        if e1["mnemonic"] == "LOAD" and e1["address"] == FLAG_ADDR and e1["result"] == 0:
            flag_reads += 1
        cols = [show_short(core, event) for core, event in zip(cpu.cores, events)]
        print(f"  tick {cpu.cycles:>2} | core0 {cols[0]:<40} | core1 {cols[1]}")
        if cpu.cycles > 200:
            raise RuntimeError("branch demo did not finish")

    c0, c1 = cpu.cores
    mem = cpu.memory
    print(f"\nFinal: mem[{SUM_ADDR}]={mem.read(SUM_ADDR)} mem[{FLAG_ADDR}]={mem.read(FLAG_ADDR)} "
          f"mem[{VERDICT}]={mem.read(VERDICT)}  after {cpu.cycles} ticks")
    checks = [
        ("while loop: core 0 summed 1..5 = 15", mem.read(SUM_ADDR) == 15 and c0.registers.read(1) == 6),
        (f"spin-wait: core 1 read flag = 0 {flag_reads} times before seeing 1", flag_reads > 1),
        ("core 1 read core 0's sum only after the flag", c1.registers.read(2) == 15),
        ("if/else: 15 < 20 so the 'then' branch set verdict = 1", mem.read(VERDICT) == 1),
        ("both cores halted", c0.halted and c1.halted),
    ]
    print("\nVerification:")
    for text, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {text}")
    return 0 if all(ok for _, ok in checks) else 1


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        return run_scripted_demo()
    if args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] in ("-b", "--branch"):
        return run_branch_demo()
    if args[0] in ("-i", "--interactive"):
        return interactive()
    if len(args) > 2:
        print('usage: python -m dualcore.demo ["expr for core 0" ["expr for core 1"]] | -i')
        return 2
    try:
        return run_expressions(*args)
    except ValueError as error:
        print(f"error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
