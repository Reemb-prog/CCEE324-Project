"""CCEE 324 Dual-Core Datapath Lab (Streamlit).

Run from the project root:
    py -m pip install -r requirements-visualizer.txt
    py -m streamlit run app.py

The simulator in `dualcore/` is used unchanged. Each Load/Reset assembles the
programs, runs the real DualCoreProcessor to completion while tracing every
tick (visualizer/trace.py), and hands the whole run to the browser player.
"""
import streamlit as st
import streamlit.components.v1 as components

from dualcore.demo import fields
from visualizer import scenarios
from visualizer.assembler import assemble, parse_memory
from visualizer.player import build_html, watched_addresses
from visualizer.trace import run_trace

st.set_page_config(page_title="Dual-Core Datapath Lab", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; max-width: 1600px; }
[data-testid="stSidebar"] textarea { font-family: Consolas, monospace; font-size: 12.5px; }
.hdr { background: linear-gradient(110deg, #E7F0FF, #F0EBFF); border: 1px solid #DAE3F8;
       border-radius: 14px; padding: 12px 20px; margin-bottom: 10px; color: #172B4D; }
.hdr h1 { font-size: 24px; margin: 0; padding: 0; color: #172B4D; }
.hdr p { margin: 2px 0 0; font-size: 13px; color: #52647F; }
</style>
""", unsafe_allow_html=True)

MODES = ["Scripted demo", "Branch demo", "Expression", "Custom program"]

SYNTAX = """ADD   R3, R1, R2     # also SUB AND OR XOR NOR SLL SRL SLT
NOT   R7, R6
LOAD  R4, [100]      # Rd = mem[100]
STORE R3, [100]      # mem[100] = R3
LOADI R1, 25         # Rd = 25 (0..255)
SLTI  R3, R2, 20     # Rd = 1 if R2 < 20 (imm 0..63)
BEQ   R4, R0, +3     # or a label: BEQ R4, R0, done
BNE   R1, R0, loop   # offset -8..+7 from PC+1
J     top            # or an absolute index
HALT
top:                 # labels end with ':'"""


def _set_editors(scenario: scenarios.Scenario) -> None:
    st.session_state.src0 = scenario.program_text(0)
    st.session_state.src1 = scenario.program_text(1)
    st.session_state.mem_src = scenario.memory_text()


def _scenario_for(mode: str):
    if mode == "Scripted demo":
        return scenarios.scripted()
    if mode == "Branch demo":
        return scenarios.branch()
    if mode == "Expression":
        return scenarios.expression(st.session_state.get("expr0", "3 + 4"),
                                    st.session_state.get("expr1", "200 + 100"))
    return None


def _on_mode_change() -> None:
    mode = st.session_state.mode
    if mode == "Custom program":
        st.session_state.src0 = scenarios.CUSTOM_CORE0
        st.session_state.src1 = scenarios.CUSTOM_CORE1
        st.session_state.mem_src = scenarios.CUSTOM_MEMORY
    else:
        try:
            _set_editors(_scenario_for(mode))
        except ValueError as error:
            st.session_state.load_error = str(error)
    st.session_state.pending_load = True


def _on_expr_change() -> None:
    try:
        _set_editors(_scenario_for("Expression"))
        st.session_state.load_error = ""
        st.session_state.pending_load = True
    except ValueError as error:
        st.session_state.load_error = f"Expression: {error}"


def load() -> None:
    """Assemble the editors, run + trace the whole program, store the result."""
    try:
        prog0 = assemble(st.session_state.src0)
    except ValueError as error:
        st.session_state.load_error = f"Core 0, {error}"
        return
    try:
        prog1 = assemble(st.session_state.src1)
    except ValueError as error:
        st.session_state.load_error = f"Core 1, {error}"
        return
    try:
        memory = parse_memory(st.session_state.mem_src)
    except ValueError as error:
        st.session_state.load_error = str(error)
        return
    trace = run_trace(prog0.words, prog1.words, memory, max_ticks=st.session_state.max_ticks)

    # The demo's PASS/FAIL checks only apply if the program is the demo's, unedited.
    checks = []
    scenario = _scenario_for(st.session_state.mode)
    if (scenario is not None and [prog0.words, prog1.words] == scenario.programs
            and memory == scenario.memory and trace["error"] is None):
        checks = scenario.checks(trace["final"], trace["ticks"])
    st.session_state.run = {"trace": trace, "programs": [prog0, prog1], "memory": memory,
                            "checks": checks}
    st.session_state.load_error = ""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
if "src0" not in st.session_state:
    st.session_state.mode = MODES[0]
    st.session_state.max_ticks = 256
    _set_editors(scenarios.scripted())
    st.session_state.pending_load = True
    st.session_state.load_error = ""

with st.sidebar:
    st.markdown("### 🧩 Programs")
    st.radio("What to run", MODES, key="mode", on_change=_on_mode_change)
    if st.session_state.mode == "Expression":
        st.text_input("Core 0 expression", value="3 + 4", key="expr0", on_change=_on_expr_change)
        st.text_input("Core 1 expression (empty = idle)", value="200 + 100", key="expr1",
                      on_change=_on_expr_change)
        st.caption("Operators: + - & | ^ nor << >>  ·  operands 0..255")
    current = _scenario_for(st.session_state.mode) if st.session_state.mode != "Expression" else None
    if current is not None:
        st.caption(current.blurb)

    st.markdown('<span style="color:#2563EB;font-weight:700">● Core 0 program</span>',
                unsafe_allow_html=True)
    st.text_area("Core 0", key="src0", height=210, label_visibility="collapsed")
    st.markdown('<span style="color:#9333EA;font-weight:700">● Core 1 program</span>',
                unsafe_allow_html=True)
    st.text_area("Core 1", key="src1", height=210, label_visibility="collapsed")
    st.text_area("Initial shared memory (address=value per line)", key="mem_src", height=80)
    st.number_input("Tick budget", min_value=10, max_value=1000, step=10, key="max_ticks",
                    help="Stop after this many ticks if the cores never halt (e.g. an endless loop).")
    if st.button("↻ Assemble & run", type="primary", width="stretch"):
        st.session_state.pending_load = True
    with st.expander("📖 Instruction syntax"):
        st.code(SYNTAX, language="text")
        st.caption("Registers R0..R7 (R0 is always 0). Values 0..255. `#` starts a comment.")

if st.session_state.pop("pending_load", False):
    load()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hdr"><h1>⚡ Dual-Core Datapath Lab</h1>
<p>Two single-cycle cores (private PC, registers, control, ALU) sharing one 256×8 data memory.
Each clock tick, every active core executes one instruction. Use ▶ to play the six stages of
each tick, or step with ← / →.</p></div>
""", unsafe_allow_html=True)

run = st.session_state.get("run")
if st.session_state.get("load_error"):
    st.error(st.session_state.load_error +
             ("  \nThe diagram below still shows the last program that assembled." if run else ""))

if run is None:
    st.info("Fix the error above, then press **Assemble & run**.")
    st.stop()

trace, programs, memory = run["trace"], run["programs"], run["memory"]
if trace["error"]:
    st.warning(trace["error"] + " The ticks that did run are shown below.")
for core_id, prog in enumerate(programs):
    if prog.auto_halt:
        st.caption(f"Core {core_id}: no HALT at the end, so one was added automatically.")

sources = [[text + ("   # auto" if prog.auto_halt and i == len(prog.words) - 1 else "")
            for i, text in enumerate(prog.source)] for prog in programs]
if trace["ticks"]:
    components.html(build_html(trace, sources, memory), height=1420, scrolling=True)
else:
    st.info("Nothing ran (both cores start halted?).")

final = trace["final"]
a, b, c, d = st.columns(4)
a.metric("Clock ticks", len(trace["ticks"]))
b.metric("Core 0", "HALTED" if final["halted"][0] else f"PC {final['pcs'][0]}")
c.metric("Core 1", "HALTED" if final["halted"][1] else f"PC {final['pcs'][1]}")
d.metric("Instructions executed",
         sum(1 for t in trace["ticks"] for w in t["wires"] if not w["halted_before"]))

if run["checks"]:
    with st.expander("✅ Demo verification (same checks as the terminal demo)", expanded=True):
        for text, ok in run["checks"]:
            st.markdown(f"{'🟢 **PASS**' if ok else '🔴 **FAIL**'} — {text}")

with st.expander("🧾 Programs as machine code"):
    cols = st.columns(2)
    for core_id, (col, prog) in enumerate(zip(cols, programs)):
        with col:
            st.markdown(f"**Core {core_id}**")
            st.dataframe([{"PC": i, "Assembly": prog.source[i], "Hex": f"0x{word:04X}",
                           "Fields": fields(word)} for i, word in enumerate(prog.words)],
                         hide_index=True, width="stretch")

with st.expander("🎛️ Decoder & control signals per tick"):
    if trace["ticks"]:
        tick_no = st.slider("Tick", 1, len(trace["ticks"]), 1)
        record = trace["ticks"][tick_no - 1]
        cols = st.columns(2)
        for core_id, (col, w) in enumerate(zip(cols, record["wires"])):
            with col:
                st.markdown(f"**Core {core_id}**")
                if w["halted_before"]:
                    st.caption("Already halted.")
                    continue
                st.code(f"{w['asm']}\n{w['hex']} = {fields(w['word'])}", language="text")
                st.dataframe([{"Signal": k, "Value": v} for k, v in w["signals"].items()],
                             hide_index=True, width="stretch")

with st.expander("📜 Execution history"):
    rows = []
    for record in trace["ticks"]:
        for core_id, w in enumerate(record["wires"]):
            rows.append({
                "Tick": record["cycle"], "Core": core_id, "PC": w["pc"],
                "Instruction": "(halted)" if w["halted_before"] else w["asm"],
                "ALU": "" if w.get("alu_result") is None else f"{w['alu_op']} = {w['alu_result']}",
                "Write": "" if w.get("write_reg") is None else f"R{w['write_reg']} <- {w['write_data']}",
                "Memory": ("" if w.get("mem_addr") is None else
                           f"read [{w['mem_addr']}] = {w['mem_read_data']}" if w["mem_read_data"] is not None
                           else f"write [{w['mem_addr']}] <- {w['mem_write_data']}"),
                "Next PC": w["next_pc"],
            })
    st.dataframe(rows, hide_index=True, width="stretch")

with st.expander("🧠 Shared memory (initial → final)"):
    addrs = watched_addresses(trace, memory)
    if addrs:
        st.dataframe([{"Address": addr, "Initial": trace["initial"]["memory"][addr],
                       "Final": final["memory"][addr],
                       "Binary": f"{final['memory'][addr]:08b}"} for addr in addrs],
                     hide_index=True, width="stretch")
    else:
        st.caption("These programs never touched shared memory.")

with st.expander("📚 How to read the diagram"):
    st.markdown("""
* **Six stages per tick** (single-cycle: all happen in one clock, shown one at a time):
  Fetch → Decode / register read → Execute → Memory → Writeback → Next PC.
* **Wires:** solid core colour = data already flowed, moving pill = data flowing now,
  dashed tint = will be used later in this instruction, grey = not used by this instruction.
* **Orange tags** are the control-unit outputs (RegWrite, ALUSrc, MemtoReg, ...), as in the lecture table.
* **Differences from the MIPS figure** (from this project's ISA): PC counts instructions, so the
  adder is **+1** and the branch target is **PC+1+offset** (no shift-left-2); every register write
  uses bits [11:9], so RegDst is always 1 (no mux drawn); LOAD/STORE/LOADI use **R0 (= 0)** as the
  base, so the ALU computes `0 + imm`; a **Jump mux** handles `J`.
* **Shared memory:** both cores read the value from the *start* of the tick; STOREs are buffered
  (dashed cell) and committed at the end of the tick, core 0 then core 1 (core 1 wins a conflict).
""")

st.caption("CCEE 324 · Dual-core simulator visualizer · simulator: dualcore/ (unchanged)")
