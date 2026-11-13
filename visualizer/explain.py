"""Text side of the visualizer: terminal-demo style lines and per-stage narration.

All text is computed here in Python from the traced wire values and shipped to
the browser player, so the diagram and the text always describe the same data.
"""

STAGES = ["Fetch", "Decode / Register read", "Execute (ALU)", "Memory",
          "Writeback", "Next PC"]


def b8(value: int) -> str:
    return f"{value:08b}"


def tick_line(core_id: int, w: dict) -> str:
    """One-line summary per core per tick, worded like `python -m dualcore.demo`."""
    if w["halted_before"]:
        return f"core{core_id}: (halted, PC stays {w['pc']})"
    text = f"core{core_id}: PC={w['pc']:<2} {w['asm']:<20}"
    m = w["mnemonic"]
    if m == "HALT":
        return text + " halt (PC frozen)"
    if w["taken"] is not None:
        return text + (f" taken -> PC={w['next_pc']}" if w["taken"] else " not taken")
    if m == "J":
        return text + f" jump -> PC={w['next_pc']}"
    if w["mem_write_data"] is not None:
        return text + f" buffer mem[{w['mem_addr']}] <- {w['mem_write_data']}"
    if w["write_reg"] is not None:
        if w["r0_discard"]:
            return text + f" R0 <- {w['write_data']} discarded (R0 is always 0)"
        return text + f" R{w['write_reg']} <- {w['write_data']}"
    return text


def stage_texts(w: dict) -> list[str]:
    """Six explanations (one per stage) for one core's instruction this tick."""
    if w["halted_before"]:
        msg = f"Core is halted: nothing is fetched, PC stays {w['pc']}."
        return [msg] * len(STAGES)

    m, s = w["mnemonic"], w["signals"]
    fetch = (f"PC = {w['pc']} selects instruction memory word {w['hex']} "
             f"({w['binary']}) = {w['asm']}. The +1 adder already computes PC+1 = {w['pc_plus_1']}.")
    sig = ", ".join(f"{k}={v}" for k, v in s.items())
    decode = f"Opcode {w['opcode']:04b} = {m}. Control: {sig}."
    if w["read_reg1"] is not None:
        decode += f" Read reg 1 = R{w['read_reg1']} -> {w['read_data1']}"
        if w["read_reg1"] == 0 and m in ("LOAD", "STORE", "LOADI"):
            decode += " (R0 base, always 0)"
        decode += "."
    if w["read_reg2"] is not None:
        decode += f" Read reg 2 = R{w['read_reg2']} -> {w['read_data2']}."
    if w["imm"] is not None:
        decode += f" Immediate box: {w['imm_kind']} = {w['imm']}."

    if m == "HALT":
        return [fetch, decode + " HALT: the core will stop.",
                "No ALU operation.", "No memory access.", "No register is written.",
                f"Core halts; PC stays frozen at {w['pc']}."]

    # Execute
    if m == "J":
        execute = f"No ALU operation. Jump target = {w['jump_target']} (from the instruction)."
    elif w["alu_op"] == "NOT":
        execute = f"ALU NOT {w['alu_a']} ({b8(w['alu_a'])}) = {w['alu_result']} ({b8(w['alu_result'])})."
    else:
        src = "immediate" if s["ALUSrc"] == "1" else "Read data 2"
        execute = (f"ALUSrc={s['ALUSrc']} picks the {src} for input B. ALU {w['alu_op']}"
                   f"({w['alu_a']}, {w['alu_b']}) = {w['alu_result']}  Zero={int(w['zero'])}.")
        if m in ("LOAD", "STORE"):
            execute += f" This is the memory address R0 + {w['imm']}."
        if m in ("BEQ", "BNE"):
            execute += (f" Branch adder: PC+1 + offset = {w['pc_plus_1']} + ({w['imm']}) "
                        f"= {w['branch_target']}.")

    # Memory
    if w["mem_read_data"] is not None:
        memory = (f"MemRead=1: shared memory mem[{w['mem_addr']}] = {w['mem_read_data']} "
                  "(value at the start of the tick).")
    elif w["mem_write_data"] is not None:
        memory = (f"MemWrite=1: buffer mem[{w['mem_addr']}] <- {w['mem_write_data']}. "
                  "It is committed at the end of the tick (visible next tick).")
    else:
        memory = "No shared-memory access (MemRead=0, MemWrite=0)."

    # Writeback
    if w["write_reg"] is not None:
        src = "memory data" if s["MemtoReg"] == "1" else "ALU result"
        writeback = f"MemtoReg={s['MemtoReg']} picks the {src}: R{w['write_reg']} <- {w['write_data']}."
        if w["r0_discard"]:
            writeback += " The write is discarded: R0 is hard-wired to 0."
    elif w["mem_write_data"] is not None:
        writeback = (f"RegWrite=0. End of tick: the buffered STORE commits "
                     f"mem[{w['mem_addr']}] = {w['mem_write_data']}.")
    else:
        writeback = "RegWrite=0: no register is written."

    # Next PC
    if m == "J":
        next_pc = f"Jump=1: PC <- target {w['next_pc']}."
    elif w["taken"] is not None:
        rule = "branches when Zero=1" if m == "BEQ" else "branches when Zero=0 (BranchNe=1)"
        head = f"Branch=1, Zero={int(w['zero'])}; {m} {rule}"
        if w["taken"]:
            next_pc = f"{head}: taken, PCSrc picks the branch target, PC <- {w['next_pc']}."
        else:
            next_pc = f"{head}: not taken, PC <- PC+1 = {w['next_pc']}."
    else:
        next_pc = f"PC <- PC+1 = {w['next_pc']}."
    return [fetch, decode, execute, memory, writeback, next_pc]


def tick_summary(record: dict) -> list[str]:
    """Extra end-of-tick lines: committed memory and write conflicts."""
    lines = []
    if record["mem_changes"]:
        lines.append("end of tick: " + ", ".join(f"mem[{a}] {old} -> {new}"
                                                for a, old, new in record["mem_changes"]))
    if record["conflict"]:
        lines.append(f"conflict: both cores stored to mem[{record['stores'][0][1]}]; "
                     "core 1's write is committed last and wins")
    return lines
