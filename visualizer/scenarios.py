"""Built-in programs for the visualizer, taken from the terminal demo.

The machine code comes straight from `dualcore.demo` (same builders), shown as
editable assembly text via `demo.describe`. Each scenario carries the demo's
own PASS/FAIL checks, evaluated on the final traced state.
"""
from dataclasses import dataclass, field
from typing import Callable

from dualcore import demo
from dualcore.alu import alu_execute
from dualcore.isa import encode_halt

Check = Callable[[dict, list], list[tuple[str, bool]]]


@dataclass
class Scenario:
    name: str
    blurb: str
    programs: list[list[int]]
    memory: dict[int, int] = field(default_factory=dict)
    checks: Check = lambda final, ticks: []

    def program_text(self, core_id: int) -> str:
        return "\n".join(demo.describe(word) for word in self.programs[core_id])

    def memory_text(self) -> str:
        return "\n".join(f"{a}={v}" for a, v in sorted(self.memory.items()))


def _scripted_checks(final: dict, ticks: list) -> list[tuple[str, bool]]:
    mem, r0, r1 = final["memory"], final["regs"][0], final["regs"][1]
    return [
        ("core 0 stored 25 + 17 = 42 in shared memory", mem[demo.MAILBOX] == 42),
        ("core 1 LOAD in the same tick as the STORE saw the old value 0", r1[4] == 0),
        ("core 1 LOAD one tick later saw core 0's value 42", r1[5] == 42),
        ("core 1 wrote 42 + 5 = 47 back to memory", mem[demo.RESULT] == 47),
        ("core 1 wrote NOT 47 = 208 (00101111 -> 11010000)", mem[demo.INVERTED] == 208),
        ("LOADI set R1/R2 from the programs themselves", (r0[1], r1[1]) == (25, 5)),
        ("R3 differs per core (private register files)", (r0[3], r1[3]) == (42, 2)),
        ("core 0 halted early at PC 4 while core 1 ran on", final["pcs"] == [4, 9]),
        ("both cores halted after 10 ticks", len(ticks) == 10),
    ]


def _branch_checks(final: dict, ticks: list) -> list[tuple[str, bool]]:
    mem, r0, r1 = final["memory"], final["regs"][0], final["regs"][1]
    flag_reads = sum(1 for t in ticks
                     if t["wires"][1].get("mnemonic") == "LOAD"
                     and t["wires"][1]["mem_addr"] == demo.FLAG_ADDR
                     and t["wires"][1]["mem_read_data"] == 0)
    return [
        ("while loop: core 0 summed 1..5 = 15", mem[demo.SUM_ADDR] == 15 and r0[1] == 6),
        (f"spin-wait: core 1 read flag = 0 {flag_reads} times before seeing 1", flag_reads > 1),
        ("core 1 read core 0's sum only after the flag", r1[2] == 15),
        ("if/else: 15 < 20 so the 'then' branch set verdict = 1", mem[demo.VERDICT] == 1),
        ("both cores halted", all(final["halted"])),
    ]


def scripted() -> Scenario:
    cpu = demo.build_processor()
    return Scenario(
        "Scripted demo (producer / consumer)",
        "Core 0 computes 25 + 17 and STOREs it to mem[100]. Core 1 LOADs mem[100] in "
        "the same tick (sees the old 0) and one tick later (sees 42), then uses NOT.",
        [list(c.program) for c in cpu.cores], {}, _scripted_checks)


def branch() -> Scenario:
    cpu = demo.build_branch_processor()
    return Scenario(
        "Branch demo (while / spin-wait / if-else)",
        "Core 0 sums 1..5 in a while loop (SLT, BEQ, J) and raises a flag. Core 1 "
        "spin-waits on the flag, then decides if sum < 20 (SLTI, BEQ, J).",
        [list(c.program) for c in cpu.cores], {}, _branch_checks)


def expression(expr0: str, expr1: str = "") -> Scenario:
    """Expression mode: mem[base+2] = mem[base] op mem[base+1] on each core."""
    parsed = [demo.parse_expression(expr0)] + ([demo.parse_expression(expr1)] if expr1.strip() else [])
    programs = [demo.compile_expression(m, demo.DATA_BASE[i]) for i, (_, m, _) in enumerate(parsed)]
    if len(programs) == 1:
        programs.append([encode_halt()])
    memory = {}
    for i, (a, _, b) in enumerate(parsed):
        memory[demo.DATA_BASE[i]] = a
        memory[demo.DATA_BASE[i] + 1] = b

    def checks(final, ticks):
        out = []
        for i, (a, m, b) in enumerate(parsed):
            base = demo.DATA_BASE[i]
            expected = alu_execute(m, a, b)
            out.append((f"core {i}: {a} {m} {b} -> mem[{base + 2}] = {expected}",
                        final["memory"][base + 2] == expected))
        return out

    label = expr0.strip() + (f"  |  {expr1.strip()}" if expr1.strip() else "")
    return Scenario(f"Expression: {label}",
                    "Operands are placed in shared memory; each core LOADs them, "
                    "runs one ALU operation and STOREs the result.",
                    programs, memory, checks)


CUSTOM_CORE0 = """# Core 0: count down from 3, then publish 99
        LOADI R1, 3
        LOADI R2, 1
loop:   SUB   R1, R1, R2
        BNE   R1, R0, loop
        LOADI R3, 99
        STORE R3, [50]
        HALT"""

CUSTOM_CORE1 = """# Core 1: read mem[40], add 5, write mem[41]
        LOAD  R4, [40]
        LOADI R1, 5
        ADD   R6, R4, R1
        STORE R6, [41]
        HALT"""

CUSTOM_MEMORY = "40=10"


BUILT_IN = {"Scripted demo": scripted, "Branch demo": branch}
