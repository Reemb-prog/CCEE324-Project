# Plan: Streamlit Datapath Visualizer (post-harness extension)

Status: **planned, not implemented.** Human-requested extension after all harness
stages (01–07) were approved. It is *not* a harness stage: `.harness/`, `tests/`,
`docs/ISA.md`, `docs/INTERFACES.md`, `contracts.sha256` stay untouched, and
`python scripts/harness.py verify` must keep passing unchanged.

## 1. Goal

A Streamlit web page for the live presentation that:

1. Runs the existing demos (scripted producer/consumer demo, branch demo,
   expression mode) **or** user-typed assembly for each core.
2. Shows, for every clock tick, a **terminal-style text trace** (same wording
   as `python -m dualcore.demo`) **next to an animated datapath diagram** for
   both cores, modeled on the lecture's single-cycle MIPS datapath sheet
   (PC, PC+1 adder, instruction memory, register file, immediate box, ALUSrc
   mux, ALU + Zero, data memory, MemtoReg mux, branch adder, PCSrc / Jump mux,
   control unit and its signal lines).
3. Animates the data: small value "tokens" (e.g. `0xA032`, `R1=25`, `addr 100`,
   `42`) travel along the active wires stage by stage; inactive wires are grey.
4. Has a small **play toolbar**: ⏮ reset · ◀ step back · ▶/⏸ play · ▶ step ·
   ⏭ end · speed · stage/tick scrubber.

## 2. Ground rules

* **`dualcore/` is the only source of truth and is not modified.** The
  visualizer only calls the public API (`DualCoreProcessor`, `Core`, `decode`,
  `ControlUnit`, encoders) and re-uses `dualcore.demo` builders/`describe`.
* Streamlit is the one new dependency, kept **optional**: listed in
  `requirements-visualizer.txt`; `dualcore/` and `tests/` stay stdlib-only.
* New code lives in a separate `visualizer/` package plus a root `app.py`.
* Run: `py -m pip install -r requirements-visualizer.txt` then
  `py -m streamlit run app.py`.
* Note: `CLAUDE.md` forbids GUIs/pip packages *for the harness stages*; this
  extension is an explicit human request made after stage completion.

## 3. Review of the teammate's `datapath_visualizer.py`

**Keep (ideas worth reusing)**

* Sidebar editor: one text area per core + `address=value` initial memory,
  with line-numbered assembly errors.
* Record `before` / `after` snapshots per tick so any tick can be replayed
  without re-executing the processor.
* Per-stage plain-English explanation of what each core is doing.
* Shared-memory panel: accesses this tick, committed changes, and the
  same-address write-conflict warning (core 1 wins).
* Decoder panel: machine word in binary, field split, control-signal table.
* Execution-history table, register tables (dec/bin/hex), memory inspector.
* Overall look: light dashboard, blue = core 0, purple = core 1.

**Must fix / improve**

| Issue | Why it matters | Plan |
|---|---|---|
| Written against the pre-stage-07 API (`ImmToReg`, LOADI bypassing the ALU, LOAD/STORE skipping the ALU) | Diagram contradicts the current simulator (LOADI/LOAD/STORE = R0 + imm8 through the ALU, ALUSrc=1) | Derive every path from the live `ControlSignals` instead of hard-coded per-mnemonic routes |
| No SLT, SLTI, BEQ, BNE, J | Branch demo cannot be shown | Assembler + diagram support all 18 instructions; draw branch adder, Zero, PCSrc and Jump muxes |
| Diagram is a chain of 9 boxes, not the lecture datapath | Doesn't match the course figure; no muxes, no PC adder, no immediate path | New SVG laid out like the lecture sheet |
| No values on wires; only box highlighting | The point is to *see data move* | Each active wire carries a labeled token with its actual value |
| Stage slider causes a full Streamlit rerun; no autoplay | Choppy, can't "let it play" | Animation and toolbar run client-side in JS inside one component |
| Own assembler duplicates demo logic, no labels, no branches | Divergence risk | One `visualizer/assembler.py`, round-trip tested against `demo.describe` |
| Ad-hoc `phase_map` hacks (e.g. `mem` phase depends on mnemonic) | Wrong for STORE/branch timing | Fixed stage model (§5) with per-wire stage numbers |
| Executing a tick mutates the only CPU; no step back | Can't rewind during presentation | Pre-compute the whole run (≤ 256 ticks) once per program load; scrub freely |
| `width="stretch"`, unused imports, hard-coded address list | Version fragility / clutter | Pin Streamlit version; show addresses actually touched |

## 4. Architecture

```
app.py                       Streamlit shell: sidebar inputs, layout, tables
visualizer/
  __init__.py
  assembler.py               text  -> machine words (+ labels for BEQ/BNE/J)
  scenarios.py               built-in demos wrapping dualcore.demo builders
  trace.py                   per-tick wire values, cross-checked with core.step
  explain.py                 text trace lines + per-stage explanations
  datapath_svg.py            SVG geometry: blocks, wires (ids + stage numbers)
  component.html / .js/.css  player: toolbar, animation, synced text log
  tests/test_assembler.py    stdlib unittest
  tests/test_trace.py        stdlib unittest
requirements-visualizer.txt  streamlit==<pinned>
```

### 4.1 `assembler.py`
* Syntax identical to `demo.describe` output: `ADD R3, R1, R2`, `NOT R7, R6`,
  `LOAD R4, [100]` (brackets optional), `STORE R3, [100]`, `LOADI R1, 25`,
  `SLT`, `SLTI R3, R2, 20`, `BEQ R4, R0, +3` **or** `BEQ R4, R0, done`,
  `J 4` **or** `J top`, `HALT`, `label:` lines, `#` comments, dec/hex/bin.
* Uses only the `dualcore.isa` encoders (so range checks are the simulator's).
* Errors: `ValueError("line N: …")`. Missing trailing HALT → auto-append
  (flagged in the listing), as the teammate did.

### 4.2 `trace.py` — the data on the wires
`dualcore` events don't contain intermediate values (ALU inputs, Zero,
PC+1, branch target, mem read data). Instead of changing `core.py`,
`trace_tick(cpu)`:

1. Reads the **pre-tick** state (PCs, registers, memory snapshot).
2. For each core derives a `WireValues` record using `decode` + `ControlUnit`:
   `pc, word, fields (op/rd/rs/rt/imm/offset/target), read_reg1/2,
   read_data1/2, imm, alu_a, alu_b, alu_op, alu_result, zero, mem_addr,
   mem_read_data, mem_write_data, write_reg, write_data, pc_plus_1,
   branch_target, taken, next_pc, signals`.
3. Calls the real `cpu.tick()`, then **asserts** the derived values agree with
   the event and the post-state (`result`, `address`, `stored`, `taken`,
   new PC, register/memory diffs). A mismatch raises — the simulator wins.
4. Returns `{cycle, before, after, events, wires[2], log_lines}`.

`run_trace(programs, memory, max_ticks=256)` loops this until both cores halt
(or the budget, reported as a warning — e.g. an endless spin-wait).

### 4.3 `scenarios.py`
* "Scripted demo" → `demo.build_processor()` + its verification checks.
* "Branch demo" → `demo.build_branch_processor()` + its checks.
* "Expression" → `demo.compile_expression` for one or two expressions.
* "Custom" → assembler output from the sidebar editors.
Each scenario exposes the programs as **editable text** (via `describe`), so
"load demo, then tweak it" works.

### 4.4 Diagram (`datapath_svg.py` + player)
* **Layout:** two core datapaths stacked (core 0 top, blue; core 1 bottom,
  purple), each a compact version of the lecture sheet. A **single shared
  data-memory block on the right spans both cores**, with each core's
  address/write-data/read-data wires entering it — visually showing the
  shared memory and the end-of-tick commit (pending write shown dashed until
  stage WB/commit, then solid).
* Blocks: PC, `+1` adder (our PC is an instruction index — label it, not +4),
  instruction memory, control unit (signal lines dotted to each mux/unit, each
  labeled with its 0/1/X value), register file (Read reg 1/2, Write reg,
  Write data), immediate box ("imm8 / imm6 / offset4", replacing sign-extend),
  ALUSrc mux, ALU with op label and Zero output, MemtoReg mux, branch adder
  (`PC+1+offset`, no shift-left-2), PCSrc mux, Jump mux, HALT indicator.
* Every wire has an id, the stage it belongs to, and a `WireValues` key for
  its label. A wire is *active* for an instruction iff its control signals
  route data there (e.g. ALUSrc=1 lights the imm→mux input, MemRead lights
  memory read data, Branch lights the branch adder → PCSrc path).
* Colors: core color = active & reached; light core tint = active, not yet
  reached; grey = unused this instruction. Current block gets a thick border.
* A legend box like the sheet: instruction text, machine word, control-signal
  values for the current instruction of each core.

### 4.5 Player (client-side, inside one `components.html`)
* Receives the whole trace as JSON; no Streamlit reruns while playing.
* Toolbar: ⏮ ◀ ▶/⏸ ▶ ⏭, speed (0.5×/1×/2×), mode toggle
  **Stage** (play through 6 stages of a tick, then next tick) / **Tick**
  (jump whole ticks), scrubber `tick k / N · stage s / 6`, keyboard ←/→/space.
* Tokens: small rounded labels moved along the SVG path with
  `getPointAtLength`, ~600 ms per stage at 1×.
* **Synced text panel** (monospace, terminal look) under/beside the diagram:
  the `demo.py`-style line for each core this tick, the explanation for the
  current stage, and a scrolling log of all previous ticks (click a line to
  jump there).
* Small live panels: both register files (changed register flashes) and the
  touched memory addresses (before → after).

### 4.6 Stage model (both cores advance in lockstep)

| # | Stage | Lit for |
|---|---|---|
| 1 | Fetch | PC → instr. memory → word; PC → +1 adder |
| 2 | Decode / Register read | fields → control unit (signals appear); rs/rt → register file → read data 1/2; imm box |
| 3 | Execute | ALUSrc mux → ALU → result, Zero; branch adder |
| 4 | Memory | LOAD read (pre-tick snapshot) / STORE buffered write; skipped instructions show "no memory access" |
| 5 | Writeback | MemtoReg mux → write data → Rd (R0 write shown discarded); STORE commits to shared memory at tick end (core 0 then core 1) |
| 6 | Next PC | PCSrc / Jump mux → PC (+1, branch target, jump target, or frozen on HALT) |

Halted cores show a dimmed datapath with "HALTED · PC frozen at n".

### 4.7 `app.py` (Streamlit shell)
* Sidebar: scenario picker → editable program text areas (core 0 / core 1)
  → initial memory → **Load / Reset**; assembly errors shown inline.
* Main: header; the player component (full width); below it, expanders:
  program listings (PC, assembly, machine word, binary), decoder & control
  signals for the selected tick (from the teammate's design), execution
  history table, memory inspector, and the demo's PASS/FAIL verification list
  for built-in scenarios.
* State: `st.session_state.trace` rebuilt only on Load/Reset.

## 5. Implementation steps (each verifiable on its own)

1. `visualizer/assembler.py` + tests (all 18 instructions, labels, errors,
   round-trip with `demo.describe` for both demo programs).
2. `visualizer/trace.py` + tests: run both demos and randomized programs,
   assert trace ↔ simulator agreement every tick; scripted demo still ends
   with mem[100]=42, mem[101]=47, mem[102]=208 in 10 ticks; branch demo
   mem[60]=15, mem[62]=1.
3. `visualizer/scenarios.py`, `visualizer/explain.py` (text lines match the
   terminal demo wording).
4. Static SVG datapath for one core; render in the browser pane and compare
   against the lecture figure; then two cores + shared memory.
5. Player JS: wire activation per stage, moving tokens, toolbar, text panel,
   register/memory panels.
6. `app.py` shell, sidebar, expanders, verification list.
7. Manual check in the browser: scripted demo, branch demo (spin-wait +
   taken/not-taken branches), expression mode, a custom program with an
   error, a same-address STORE conflict.
8. Docs: README "Visualizer" section, a short `docs/EXPLANATIONS.md` and
   `PROGRESS.md` note (marked as post-harness extension).

Verification at the end: `python scripts/harness.py verify` (unchanged
suite still passes), `python -m unittest discover visualizer/tests`,
`python -m dualcore.demo` and `-b` output unchanged.

## 6. Out of scope
Pipelining/hazard visuals, editing machine code bit-by-bit, saving programs
server-side, deployment/hosting, any change to the ISA or simulator behavior.
