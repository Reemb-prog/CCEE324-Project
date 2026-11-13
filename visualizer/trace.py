"""Per-tick datapath values ("what is on each wire") for both cores.

`dualcore` events report results (Rd value, memory address, stored byte, branch
taken), but not the intermediate wire values a diagram needs: ALU inputs, the
Zero output, PC + 1, the branch target, memory read data, ... This module
derives them from the *pre-tick* state with the simulator's own `decode` and
`ControlUnit`, then runs the real `cpu.tick()` and checks that every derived
value agrees with what the simulator actually did. The simulator stays the
source of truth: any disagreement raises `TraceMismatch`.
"""
from typing import Optional

from dualcore.alu import alu_execute
from dualcore.control import ControlUnit
from dualcore.demo import describe
from dualcore.isa import decode
from dualcore.processor import DualCoreProcessor

_BASE_R0 = ("LOAD", "STORE", "LOADI")   # no Rs field: ALU input A is R0 (= 0)
_CONTROL = ControlUnit()


class TraceMismatch(RuntimeError):
    """The derived wire values disagree with the simulator (a visualizer bug)."""


def _bit(value: Optional[bool]) -> str:
    return "X" if value is None else str(int(value))


def signal_table(signals) -> dict[str, str]:
    return {
        "RegDst": _bit(signals.reg_dst), "ALUSrc": _bit(signals.alu_src),
        "MemtoReg": _bit(signals.mem_to_reg), "RegWrite": _bit(signals.reg_write),
        "MemRead": _bit(signals.mem_read), "MemWrite": _bit(signals.mem_write),
        "Branch": _bit(signals.branch), "BranchNe": _bit(signals.branch_ne),
        "Jump": _bit(signals.jump), "ALUOp": signals.alu_op or "X",
    }


def derive_wires(pc: int, halted: bool, program: tuple, regs: tuple, memory: tuple) -> dict:
    """Wire values for one core executing the instruction at `pc` (pre-tick state)."""
    if halted:
        return {"halted_before": True, "pc": pc, "next_pc": pc}
    if not 0 <= pc < len(program):
        raise RuntimeError(f"PC {pc} is outside the program (missing HALT?)")

    word = program[pc]
    d = decode(word)
    s = _CONTROL.signals(d)
    read = lambda index: 0 if index == 0 else regs[index]   # R0 hard-wired to zero

    w = {
        "halted_before": False, "pc": pc, "word": word, "mnemonic": d.mnemonic,
        "asm": describe(word), "binary": f"{word:016b}", "hex": f"0x{word:04X}",
        "opcode": d.opcode, "rd": d.rd, "rs": d.rs, "rt": d.rt,
        "signals": signal_table(s), "pc_plus_1": pc + 1,
        "read_reg1": None, "read_reg2": None, "read_data1": None, "read_data2": None,
        "imm": None, "imm_kind": None, "alu_a": None, "alu_b": None, "alu_op": s.alu_op,
        "alu_result": None, "zero": None, "mem_addr": None, "mem_read_data": None,
        "mem_write_data": None, "write_reg": None, "write_data": None, "r0_discard": False,
        "branch_target": None, "taken": None, "jump_target": None, "halt": d.mnemonic == "HALT",
    }

    # Immediate box: the constant field this instruction carries.
    if d.mnemonic in ("LOAD", "STORE"):
        w["imm"], w["imm_kind"] = d.address, "imm8 address"
    elif d.mnemonic == "LOADI":
        w["imm"], w["imm_kind"] = d.immediate, "imm8"
    elif d.mnemonic == "SLTI":
        w["imm"], w["imm_kind"] = d.immediate, "imm6"
    elif d.mnemonic in ("BEQ", "BNE"):
        w["imm"], w["imm_kind"] = d.offset, "offset4"
    elif d.mnemonic == "J":
        w["imm"], w["imm_kind"] = d.address, "target8"

    if d.mnemonic == "HALT":
        w["next_pc"] = pc
        return w

    # Register file read ports. STORE's data register goes out on port 2,
    # like MIPS sw's rt -> "Read data 2" -> memory "Write data".
    if s.alu_op is not None:
        w["read_reg1"] = 0 if d.mnemonic in _BASE_R0 else d.rs
        w["read_data1"] = read(w["read_reg1"])
        if s.alu_src is False:
            w["read_reg2"] = d.rt
            w["read_data2"] = read(d.rt)
    if d.mnemonic == "STORE":
        w["read_reg2"] = d.rs
        w["read_data2"] = read(d.rs)

    # ALU (input B chosen by the ALUSrc mux).
    if s.alu_op is not None:
        w["alu_a"] = w["read_data1"]
        if s.alu_src is True:
            w["alu_b"] = w["imm"]
        elif s.alu_src is False:
            w["alu_b"] = w["read_data2"]
        else:
            w["alu_b"] = 0                      # unary NOT ignores input B
        w["alu_result"] = alu_execute(s.alu_op, w["alu_a"], w["alu_b"])
        w["zero"] = w["alu_result"] == 0

    # Shared data memory (reads see the pre-tick snapshot).
    if s.mem_read or s.mem_write:
        w["mem_addr"] = w["alu_result"]
    if s.mem_read:
        w["mem_read_data"] = memory[w["mem_addr"]]
    if s.mem_write:
        w["mem_write_data"] = w["read_data2"]

    # Writeback (MemtoReg mux); a write to R0 is discarded.
    if s.reg_write:
        w["write_reg"] = d.rd
        w["write_data"] = w["mem_read_data"] if s.mem_to_reg else w["alu_result"]
        w["r0_discard"] = d.rd == 0

    # Next PC (PCSrc / Jump muxes).
    if s.jump:
        w["jump_target"] = d.address
        w["next_pc"] = d.address
    elif s.branch:
        w["branch_target"] = pc + 1 + d.offset
        w["taken"] = w["zero"] != s.branch_ne
        w["next_pc"] = w["branch_target"] if w["taken"] else pc + 1
    else:
        w["next_pc"] = pc + 1
    return w


def _state(cpu: DualCoreProcessor) -> dict:
    return {
        "pcs": [core.pc for core in cpu.cores],
        "halted": [core.halted for core in cpu.cores],
        "regs": [list(core.registers.snapshot()) for core in cpu.cores],
        "memory": list(cpu.memory.snapshot()),
    }


def _check(core_id: int, w: dict, event: dict, after: dict) -> None:
    def fail(what, derived, actual):
        raise TraceMismatch(f"core {core_id} PC {w['pc']}: {what} derived {derived!r}, "
                            f"simulator {actual!r}")

    if after["pcs"][core_id] != w["next_pc"]:
        fail("next PC", w["next_pc"], after["pcs"][core_id])
    if w["halted_before"] or w.get("halt"):
        return
    if event.get("address") != w["mem_addr"]:
        fail("memory address", w["mem_addr"], event.get("address"))
    if event.get("stored") != w["mem_write_data"]:
        fail("stored value", w["mem_write_data"], event.get("stored"))
    if event.get("taken") != w["taken"]:
        fail("branch taken", w["taken"], event.get("taken"))
    if w["write_reg"] is not None:
        expected = 0 if w["r0_discard"] else w["write_data"]
        if event.get("result") != expected:
            fail("writeback value", expected, event.get("result"))
        if after["regs"][core_id][w["write_reg"]] != expected:
            fail("register file", expected, after["regs"][core_id][w["write_reg"]])


def trace_tick(cpu: DualCoreProcessor) -> dict:
    """Derive both cores' wires, run one real tick, verify, return the record."""
    before = _state(cpu)
    wires = [derive_wires(before["pcs"][i], before["halted"][i], core.program,
                          tuple(before["regs"][i]), tuple(before["memory"]))
             for i, core in enumerate(cpu.cores)]
    events = cpu.tick()
    after = _state(cpu)
    for i in range(2):
        _check(i, wires[i], events[i], after)

    stores = [(i, w["mem_addr"], w["mem_write_data"]) for i, w in enumerate(wires)
              if w.get("mem_write_data") is not None]
    conflict = len(stores) == 2 and stores[0][1] == stores[1][1]
    changes = [(a, before["memory"][a], after["memory"][a]) for a in range(256)
               if before["memory"][a] != after["memory"][a]]
    return {
        "cycle": cpu.cycles, "before": before, "after": after, "wires": wires,
        "events": [dict(e) for e in events], "stores": stores,
        "conflict": conflict, "mem_changes": changes,
    }


def run_trace(program0, program1, memory: Optional[dict] = None,
              max_ticks: int = 256) -> dict:
    """Run until both cores halt (or `max_ticks`), tracing every tick."""
    cpu = DualCoreProcessor(list(program0), list(program1))
    for address, value in (memory or {}).items():
        cpu.memory.write(address, value)
    initial = _state(cpu)
    ticks, error = [], None
    while not all(core.halted for core in cpu.cores):
        if len(ticks) >= max_ticks:
            error = (f"Stopped after {max_ticks} ticks without both cores halting "
                     "(endless loop or spin-wait?).")
            break
        try:
            ticks.append(trace_tick(cpu))
        except RuntimeError as exc:           # e.g. PC ran past the program
            if isinstance(exc, TraceMismatch):
                raise
            error = f"Tick {cpu.cycles + 1}: {exc}"
            break
    return {"initial": initial, "ticks": ticks, "final": _state(cpu), "error": error,
            "programs": [list(program0), list(program1)], "cpu": cpu}
