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

st.set_page_config(page_title="Dual-Core Datapath Lab", layout="wide")

st.markdown("""
<style>
:root {
  --page: #F4F6F9; --surface: #FFFFFF; --surface-soft: #F8FAFC;
  --line: #DCE3EC; --ink: #17263A; --muted: #65758A;
  --blue: #285A9F; --blue-soft: #EAF1FA; --purple: #76519B; --purple-soft: #F1EBF7;
}
.stApp { background: var(--page); color: var(--ink); }
.block-container { max-width: 1800px; padding: 1.15rem 1.6rem 2.2rem; }
[data-testid="stSidebar"] { background: #EDF1F5; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div { padding: 1.2rem 1rem 2rem; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--ink); letter-spacing: -.02em; }
[data-testid="stSidebar"] [data-testid="stExpander"] { background: #F8FAFC; border: 1px solid var(--line); border-radius: 9px; }
[data-testid="stSidebar"] textarea, [data-testid="stSidebar"] input {
  font-family: "Cascadia Code", Consolas, monospace; font-size: 13px;
  border-radius: 7px;
}
[data-testid="stSidebar"] textarea { background: #FFFFFF; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: 2px 0; }
.hdr { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--blue);
  border-radius: 9px; padding: 17px 21px; margin: 0 0 15px; }
.hdr h1 { color: var(--ink); font-size: 25px; line-height: 1.2; font-weight: 720;
  letter-spacing: -.035em; margin: 0; }
.hdr p { color: var(--muted); margin: 6px 0 0; font-size: 13px; line-height: 1.55; }
.section-head { display:flex; align-items:center; justify-content:space-between; gap:12px;
  border-bottom:1px solid var(--line); padding:0 0 8px; margin: 2px 0 12px; }
.section-head strong { color:var(--ink); font-size:15px; }
.section-head span { color:var(--muted); font-size:12px; }
[data-testid="stTabs"] [role="tablist"] { gap: 5px; border-bottom: 1px solid var(--line); }
[data-testid="stTabs"] button[role="tab"] { background: transparent; border: 1px solid transparent;
  border-radius: 7px 7px 0 0; padding: 9px 13px; color: #52647A; font-weight: 600; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--blue);
  background: #FFFFFF; border-color: var(--line); border-bottom-color: #FFFFFF; }
[data-testid="stButton"] button { border-radius: 7px; font-weight: 650; min-height: 2.45rem; }
[data-testid="stButton"] button[kind="primary"] { background: var(--blue); border-color: var(--blue); }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 8px; background: #FFFFFF; }
[data-testid="stExpander"] summary { font-weight: 650; color: var(--ink); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid var(--line); padding: 12px 14px; border-radius: 8px; }
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stMetricValue"] { color: var(--ink); }
[data-testid="stAlert"] { border-radius: 8px; }
code, pre, textarea { font-family: "Cascadia Code", Consolas, monospace !important; }
@media (max-width: 850px) {
  .block-container { padding: .8rem .8rem 1.5rem; }
  .hdr h1 { font-size: 21px; }
  [data-testid="stTabs"] [role="tablist"] { overflow-x: auto; flex-wrap: nowrap; }
}
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
    st.markdown("### Simulator setup")
    st.radio("Program preset", MODES, key="mode", on_change=_on_mode_change)
    if st.session_state.mode == "Expression":
        with st.expander("Expression inputs", expanded=True):
            st.text_input("Core 0 expression", value="3 + 4", key="expr0", on_change=_on_expr_change)
            st.text_input("Core 1 expression (empty = idle)", value="200 + 100", key="expr1",
                          on_change=_on_expr_change)
            st.caption("Operators: +  -  &  |  ^  nor  <<  >>. Operands: 0–255.")
    current = _scenario_for(st.session_state.mode) if st.session_state.mode != "Expression" else None
    if current is not None:
        st.caption(current.blurb)

    with st.expander("Core programs", expanded=True):
        st.markdown('<div style="font-weight:700;color:#285A9F;margin:2px 0 5px">CORE 0</div>',
                    unsafe_allow_html=True)
        st.text_area("Core 0 program", key="src0", height=165, label_visibility="collapsed")
        st.markdown('<div style="font-weight:700;color:#76519B;margin:10px 0 5px">CORE 1</div>',
                    unsafe_allow_html=True)
        st.text_area("Core 1 program", key="src1", height=165, label_visibility="collapsed")

    with st.expander("Shared memory", expanded=False):
        st.text_area("Initial memory (address=value per line)", key="mem_src", height=105)

    with st.expander("Execution settings", expanded=False):
        st.number_input("Tick budget", min_value=10, max_value=1000, step=10, key="max_ticks",
                        help="Stops a program if it does not halt within this number of ticks.")

    if st.button("Assemble and run", type="primary", width="stretch"):
        st.session_state.pending_load = True

    with st.expander("Instruction reference", expanded=False):
        st.code(SYNTAX, language="text")
        st.caption("Registers R0–R7. R0 is always zero. Values are 0–255. Use # for comments.")

if st.session_state.pop("pending_load", False):
    load()

# ---------------------------------------------------------------------------
# Main area — organized into focused tabs
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hdr"><h1>Dual-Core Datapath Lab</h1>
<p>Two single-cycle cores with private program counters and registers, sharing one 256×8 data memory.
Explore the live execution, machine code, control signals, execution history, and memory in separate tabs.</p></div>
""", unsafe_allow_html=True)

run = st.session_state.get("run")
if st.session_state.get("load_error"):
    st.error(st.session_state.load_error +
             ("  \nThe views below still show the last program that assembled." if run else ""))

if run is None:
    st.info("Fix the error above, then press **Assemble and run** in the sidebar.")
    st.stop()

trace, programs, memory = run["trace"], run["programs"], run["memory"]
if trace["error"]:
    st.warning(trace["error"] + " The ticks that did run are shown below.")
for core_id, prog in enumerate(programs):
    if prog.auto_halt:
        st.caption(f"Core {core_id}: no HALT at the end, so one was added automatically.")

sources = [[text + ("   # auto" if prog.auto_halt and i == len(prog.words) - 1 else "")
            for i, text in enumerate(prog.source)] for prog in programs]
final = trace["final"]

# Keep each type of information in its own workspace so the page stays readable.
tab_sim, tab_programs, tab_signals, tab_history, tab_memory, tab_reference = st.tabs([
    "Live simulator", "Programs and machine code", "Control signals",
    "Execution history", "Shared memory", "Verification and guide"
])

with tab_sim:
    st.markdown('<div class="section-head"><strong>Processor execution</strong><span>Playback controls, datapath and live state</span></div>',
                unsafe_allow_html=True)
    if trace["ticks"]:
        components.html(build_html(trace, sources, memory), height=1800, scrolling=False)
    else:
        st.info("Nothing ran (both cores start halted?).")

    st.markdown('<div class="section-head"><strong>Run summary</strong><span>Final state of this simulation</span></div>',
                unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("Clock ticks", len(trace["ticks"]))
    b.metric("Core 0", "HALTED" if final["halted"][0] else f"PC {final['pcs'][0]}")
    c.metric("Core 1", "HALTED" if final["halted"][1] else f"PC {final['pcs'][1]}")
    d.metric("Instructions executed",
             sum(1 for t in trace["ticks"] for w in t["wires"] if not w["halted_before"]))

with tab_programs:
    st.markdown('<div class="section-head"><strong>Program source</strong><span>Assembly submitted to each core</span></div>', unsafe_allow_html=True)
    source_cols = st.columns(2)
    for core_id, col in enumerate(source_cols):
        with col:
            st.markdown(f"**Core {core_id}**")
            st.code("\n".join(sources[core_id]), language="text")

    st.markdown('<div class="section-head"><strong>Encoded machine instructions</strong><span>PC, assembly, hexadecimal and decoded fields</span></div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for core_id, (col, prog) in enumerate(zip(cols, programs)):
        with col:
            st.markdown(f"**Core {core_id}**")
            st.dataframe([{"PC": i, "Assembly": prog.source[i], "Hex": f"0x{word:04X}",
                           "Fields": fields(word)} for i, word in enumerate(prog.words)],
                         hide_index=True, width="stretch")

with tab_signals:
    st.markdown('<div class="section-head"><strong>Decoder and control signals</strong><span>Inspect the signal values for one clock tick</span></div>', unsafe_allow_html=True)
    if trace["ticks"]:
        tick_no = st.slider("Select clock tick", 1, len(trace["ticks"]), 1, key="signals_tick")
        record = trace["ticks"][tick_no - 1]
        cols = st.columns(2)
        for core_id, (col, w) in enumerate(zip(cols, record["wires"])):
            with col:
                st.markdown(f"**Core {core_id}**")
                if w["halted_before"]:
                    st.info("This core was already halted at the start of this tick.")
                    continue
                st.code(f"{w['asm']}\n{w['hex']} = {fields(w['word'])}", language="text")
                st.dataframe([{"Signal": k, "Value": v} for k, v in w["signals"].items()],
                             hide_index=True, width="stretch")
    else:
        st.info("No control-signal records are available because no instructions ran.")

with tab_history:
    st.markdown('<div class="section-head"><strong>Execution history</strong><span>One row per core per clock tick</span></div>', unsafe_allow_html=True)
    rows = []
    for record in trace["ticks"]:
        for core_id, w in enumerate(record["wires"]):
            rows.append({
                "Tick": record["cycle"], "Core": core_id, "PC": w["pc"],
                "Instruction": "(halted)" if w["halted_before"] else w["asm"],
                "ALU": "" if w.get("alu_result") is None else f"{w['alu_op']} = {w['alu_result']}",
                "Register write": "" if w.get("write_reg") is None else f"R{w['write_reg']} <- {w['write_data']}",
                "Memory": ("" if w.get("mem_addr") is None else
                           f"read [{w['mem_addr']}] = {w['mem_read_data']}" if w["mem_read_data"] is not None
                           else f"write [{w['mem_addr']}] <- {w['mem_write_data']}"),
                "Next PC": w["next_pc"],
            })
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("No execution history is available.")

with tab_memory:
    st.markdown('<div class="section-head"><strong>Shared data memory</strong><span>Addresses initialized or accessed during this run</span></div>', unsafe_allow_html=True)
    addrs = watched_addresses(trace, memory)
    if addrs:
        st.caption("Addresses initialized or accessed by either core during this run.")
        st.dataframe([{"Address": addr, "Initial value": trace["initial"]["memory"][addr],
                       "Final value": final["memory"][addr],
                       "Final value (8-bit binary)": f"{final['memory'][addr]:08b}"}
                      for addr in addrs], hide_index=True, width="stretch")
    else:
        st.info("These programs never accessed shared memory.")

with tab_reference:
    st.markdown('<div class="section-head"><strong>Verification</strong><span>Built-in scenario checks</span></div>', unsafe_allow_html=True)
    if run["checks"]:
        for text, ok in run["checks"]:
            st.markdown(f"{'**PASS**' if ok else '**FAIL**'} — {text}")
    else:
        st.caption("Verification checks are shown for the unedited built-in demo scenarios.")

    st.divider()
    st.markdown("#### How to read the datapath")
    st.markdown("""
* **Six stages per tick:** Fetch → Decode / register read → Execute → Memory → Writeback → Next PC.
* **Wires:** solid core colour = data already flowed, moving pill = data flowing now,
  dashed tint = will be used later in this instruction, grey = not used by this instruction.
* **Control tags** show the control-unit outputs (RegWrite, ALUSrc, MemToReg, and others).
* **Program counter:** PC counts instructions, so the adder is +1 and the branch target is PC+1+offset.
* **Register writes:** destination register is selected by bits [11:9].
* **LOAD / STORE / LOADI:** use R0 (= 0) as the base, so the ALU computes 0 + immediate.
* **Shared memory:** both cores read the value from the start of the tick; STOREs are buffered
  and committed at the end of the tick, core 0 then core 1 (core 1 wins a conflict).
""")

st.caption("CCEE 324 - Dual-core simulator visualizer")