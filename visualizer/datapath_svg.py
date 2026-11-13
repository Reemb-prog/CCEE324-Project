"""SVG geometry of the single-cycle datapath, modeled on the lecture sheet.

Two copies are drawn (core 0 on top, core 1 below), and ONE shared data-memory
block on the right spans both cores. Every wire has an id, the stage in which
data flows over it, and (per instruction) a value label. The browser player
(player.js) only toggles classes and moves value tokens; all geometry and all
"which wire is used by this instruction" decisions are made here in Python.

Differences from the MIPS figure, all from this project's ISA (docs/ISA.md):
  * PC is an instruction index, so the adder is "+1" (not +4) and the branch
    adder computes PC+1+offset (no shift-left-2).
  * Every register write goes to bits [11:9], so RegDst is always 1 when
    writing: no RegDst mux is drawn, only its value.
  * Constants are zero-extended imm8/imm6 or a 4-bit two's-complement offset,
    so the "sign extend" oval is an "Imm" oval.
  * A Jump mux after the PCSrc mux handles J (textbook extension).
"""
CORE_COLORS = ["#2563EB", "#9333EA"]
CORE_HEIGHT = 372
CORE1_Y = 392
WIDTH = 930
HEIGHT = CORE1_Y + CORE_HEIGHT + 4
MEM_X, MEM_W = 772, 150

# Stage numbers (0-based): 0 fetch, 1 decode/reg read, 2 execute, 3 memory, 4 writeback, 5 next PC
WIRES = {
    #  id           stage  points (core-local coordinates)
    "pc_im":      (0, [(80, 185), (120, 185)]),
    "pc_add":     (0, [(60, 150), (60, 62), (140, 62)]),
    "add_pcp1":   (0, [(180, 66), (640, 66)]),
    "im_bus":     (0, [(232, 195), (270, 195)]),
    "bus_cu":     (1, [(270, 195), (270, 100), (285, 100)]),
    "bus_rr1":    (1, [(270, 195), (270, 160), (330, 160)]),
    "bus_rr2":    (1, [(270, 195), (330, 195)]),
    "bus_wr":     (1, [(270, 195), (270, 230), (330, 230)]),
    "bus_imm":    (1, [(270, 195), (270, 305), (360, 305)]),
    "rd1_alu":    (2, [(460, 170), (560, 170)]),
    "rd2_mux":    (2, [(460, 225), (500, 225)]),
    "imm_mux":    (2, [(430, 305), (490, 305), (490, 252), (500, 252)]),
    "mux_alu":    (2, [(522, 237), (560, 237)]),
    "pcp1_badd":  (2, [(520, 66), (520, 85), (560, 85)]),
    "imm_badd":   (2, [(430, 305), (540, 305), (540, 115), (560, 115)]),
    "imm_jump":   (2, [(430, 305), (540, 305), (540, 140), (682, 140), (682, 106), (700, 106)]),
    "badd_mux":   (2, [(600, 100), (640, 100)]),
    "alu_mem":    (3, [(620, 215), (772, 215)]),
    "rd2_wd":     (3, [(460, 225), (480, 225), (480, 272), (750, 272), (750, 245), (772, 245)]),
    "mem_rd":     (3, [(772, 295), (712, 295)]),
    "alu_wb":     (4, [(620, 215), (736, 215), (736, 323), (712, 323)]),
    "mux_wb":     (4, [(690, 309), (676, 309), (676, 352), (312, 352), (312, 258), (330, 258)]),
    "zero_pcsrc": (5, [(620, 185), (651, 185), (651, 116)]),
    "pcsrc_jmux": (5, [(662, 83), (700, 83)]),
    "jmux_pc":    (5, [(722, 90), (746, 90), (746, 16), (22, 16), (22, 185), (40, 185)]),
}

# Where along each wire (0..1 of its length) the parked value label sits;
# chosen so labels do not cover blocks or other labels. Default 0.5.
LABEL_AT = {
    "pc_add": 0.3, "add_pcp1": 0.35, "bus_cu": 0.75, "bus_rr1": 0.7, "bus_wr": 0.75,
    "bus_imm": 0.8, "imm_mux": 0.35, "imm_badd": 0.78, "imm_jump": 0.62, "pcp1_badd": 0.75,
    "rd2_wd": 0.62, "alu_mem": 0.6, "alu_wb": 0.62, "mux_wb": 0.5, "jmux_pc": 0.42,
    "zero_pcsrc": 0.75, "rd1_alu": 0.45,
}

# Signal tags: (signal name, x, y) drawn near the unit the signal controls.
TAGS = [
    ("RegWrite", 395, 133), ("RegDst", 296, 242), ("ALUSrc", 511, 194),
    ("ALUOp", 590, 274), ("MemtoReg", 636, 334), ("PCSrc", 651, 42), ("Jump", 711, 46),
]


def _path(points) -> str:
    return "M " + " L ".join(f"{x} {y}" for x, y in points)


def _mux(x, y, h, labels=("0", "1"), flip=False) -> str:
    out = [f'<rect class="blk mux" x="{x}" y="{y}" width="22" height="{h}" rx="11"/>']
    top, bot = labels if not flip else labels[::-1]
    out.append(f'<text class="mt" x="{x + 11}" y="{y + 18}">{top}</text>')
    out.append(f'<text class="mt" x="{x + 11}" y="{y + h - 8}">{bot}</text>')
    return "".join(out)


def _core(core_id: int) -> str:
    c = f"c{core_id}"
    oy = 0 if core_id == 0 else CORE1_Y
    color = CORE_COLORS[core_id]
    g = [f'<g id="{c}" class="core" transform="translate(0 {oy})" style="--core:{color}">',
         f'<rect class="corebg" x="4" y="4" width="{MEM_X - 14}" height="{CORE_HEIGHT - 8}" rx="16"/>',
         f'<text class="coretitle" x="770" y="{CORE_HEIGHT - 12}" text-anchor="end">CORE {core_id}</text>',
         f'<text id="{c}-asm" class="asm" x="96" y="{CORE_HEIGHT - 14}"></text>']

    # Wires first (behind blocks).
    for wid, (stage, pts) in WIRES.items():
        g.append(f'<path id="{c}-{wid}" class="wire" data-stage="{stage}" '
                 f'data-lf="{LABEL_AT.get(wid, 0.5)}" d="{_path(pts)}" marker-end="url(#arr-{c})"/>')
    g.append(f'<path class="wire const" d="M 128 82 L 140 82"/>'
             f'<text class="small" x="122" y="86" text-anchor="end">1</text>')

    # PC
    g.append(f'<rect id="{c}-b-pc" class="blk" x="40" y="150" width="40" height="70" rx="6"/>'
             f'<text class="bt" x="60" y="178">PC</text>'
             f'<text id="{c}-v-pc" class="bv" x="60" y="200"></text>')
    # +1 adder
    g.append(f'<path id="{c}-b-add" class="blk" d="M 140 36 L 180 52 L 180 80 L 140 96 L 140 72 '
             f'L 148 66 L 140 60 Z"/><text class="bt s" x="164" y="70">+1</text>')
    # Instruction memory
    g.append(f'<rect id="{c}-b-im" class="blk" x="120" y="140" width="112" height="112" rx="6"/>'
             f'<text class="bt" x="176" y="168">Instruction</text><text class="bt" x="176" y="183">memory</text>'
             f'<text id="{c}-v-im" class="bv mono" x="176" y="208"></text>'
             f'<text class="small" x="124" y="181" text-anchor="start">addr</text>'
             f'<text class="small" x="228" y="208" text-anchor="end">instr</text>')
    # Control unit
    g.append(f'<ellipse id="{c}-b-cu" class="blk" cx="333" cy="100" rx="48" ry="26"/>'
             f'<text class="bt" x="333" y="96">Control</text>'
             f'<text id="{c}-v-cu" class="bv s" x="333" y="112"></text>')
    # Register file
    g.append(f'<rect id="{c}-b-rf" class="blk" x="330" y="140" width="130" height="132" rx="6"/>'
             f'<text class="bt" x="395" y="268">Registers</text>')
    for label, y in (("Read reg 1", 163), ("Read reg 2", 198), ("Write reg", 233), ("Write data", 261)):
        g.append(f'<text class="port" x="334" y="{y}">{label}</text>')
    for label, y in (("Read data 1", 173), ("Read data 2", 228)):
        g.append(f'<text class="port" x="456" y="{y}" text-anchor="end">{label}</text>')
    # Immediate
    g.append(f'<ellipse id="{c}-b-imm" class="blk" cx="395" cy="305" rx="35" ry="20"/>'
             f'<text class="bt s" x="395" y="301">Imm</text>'
             f'<text id="{c}-v-imm" class="bv s" x="395" y="316"></text>')
    # ALUSrc mux
    g.append(f'<g id="{c}-b-alusrc">{_mux(500, 202, 70)}</g>')
    # ALU
    g.append(f'<path id="{c}-b-alu" class="blk" d="M 560 150 L 620 175 L 620 235 L 560 260 L 560 215 '
             f'L 572 205 L 560 195 Z"/><text class="bt" x="594" y="200">ALU</text>'
             f'<text id="{c}-v-alu" class="bv s" x="594" y="226"></text>'
             f'<text class="small" x="624" y="181" text-anchor="start">Zero</text>')
    # Branch adder
    g.append(f'<path id="{c}-b-badd" class="blk" d="M 560 70 L 600 86 L 600 114 L 560 130 L 560 106 '
             f'L 568 100 L 560 94 Z"/><text class="bt s" x="583" y="104">Add</text>')
    # PCSrc and Jump muxes
    g.append(f'<g id="{c}-b-pcsrc">{_mux(640, 50, 66)}</g>')
    g.append(f'<g id="{c}-b-jmux">{_mux(700, 56, 66)}</g>')
    # MemtoReg mux (faces left: inputs on the right)
    g.append(f'<g id="{c}-b-memtoreg">{_mux(690, 280, 58, labels=("1", "0"))}</g>')
    # Signal tags
    for name, x, y in TAGS:
        g.append(f'<text id="{c}-t-{name}" class="tag" x="{x}" y="{y}"></text>')
    # Token layer (filled by the player)
    g.append(f'<g id="{c}-tokens"></g>')
    g.append(f'<g id="{c}-halt" class="haltmask"><rect x="4" y="4" width="{MEM_X - 14}" '
             f'height="{CORE_HEIGHT - 8}" rx="16"/><text x="380" y="190">HALTED</text>'
             f'<text id="{c}-haltpc" class="sub" x="380" y="216"></text></g>')
    g.append("</g>")
    return "".join(g)


def build_svg() -> str:
    defs = "".join(
        f'<marker id="arr-c{i}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" '
        f'markerUnits="userSpaceOnUse"><path d="M0 0 L8 4 L0 8 Z" fill="{CORE_COLORS[i]}"/></marker>'
        for i in range(2))
    memory = (
        f'<g id="mem"><rect class="blk memblk" x="{MEM_X}" y="150" width="{MEM_W}" '
        f'height="{CORE1_Y + 340 - 150}" rx="8"/>'
        f'<text class="bt" x="{MEM_X + MEM_W / 2}" y="174">Shared data</text>'
        f'<text class="bt" x="{MEM_X + MEM_W / 2}" y="190">memory 256×8</text>'
        f'<text class="small" x="{MEM_X + 4}" y="212" text-anchor="start">addr</text>'
        f'<text class="small" x="{MEM_X + 4}" y="242" text-anchor="start">write data</text>'
        f'<text class="small" x="{MEM_X + 4}" y="292" text-anchor="start">read data</text>'
        f'<text class="small" x="{MEM_X + 4}" y="{CORE1_Y + 212}" text-anchor="start">addr</text>'
        f'<text class="small" x="{MEM_X + 4}" y="{CORE1_Y + 242}" text-anchor="start">write data</text>'
        f'<text class="small" x="{MEM_X + 4}" y="{CORE1_Y + 292}" text-anchor="start">read data</text>'
        f'<text id="mem-sig0" class="tag" x="{MEM_X + MEM_W / 2}" y="142"></text>'
        f'<text id="mem-sig1" class="tag" x="{MEM_X + MEM_W / 2}" y="{CORE1_Y + 356}"></text>'
        f'<g id="mem-cells"></g></g>')
    return (f'<svg id="dp" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">'
            f'<defs>{defs}</defs>{_core(0)}{_core(1)}{memory}</svg>')


# ---------------------------------------------------------------------------
# Per-instruction data: which wires carry what
# ---------------------------------------------------------------------------

def _fmt(value) -> str:
    return "" if value is None else str(value)


def wire_labels(w: dict) -> dict[str, str]:
    """{wire id: value label} for every wire this instruction actually uses."""
    if w["halted_before"]:
        return {}
    s = w["signals"]
    on = {
        "pc_im": f"PC {w['pc']}",
        "pc_add": str(w["pc"]),
        "im_bus": w["hex"],
        "bus_cu": f"op {w['opcode']:04b}",
    }
    if w["halt"]:
        return on
    on["add_pcp1"] = str(w["pc_plus_1"])
    if w["read_reg1"] is not None:
        on["bus_rr1"] = f"R{w['read_reg1']}"
        on["rd1_alu"] = str(w["read_data1"])
    if w["read_reg2"] is not None:
        on["bus_rr2"] = f"R{w['read_reg2']}"
        if s["ALUSrc"] == "0":
            on["rd2_mux"] = str(w["read_data2"])
    if w["write_reg"] is not None:
        on["bus_wr"] = f"R{w['write_reg']}"
    if w["imm"] is not None:
        on["bus_imm"] = f"{w['imm_kind'].split()[0]}"
        if s["ALUSrc"] == "1":
            on["imm_mux"] = str(w["imm"])
    if w["alu_b"] is not None and s["ALUSrc"] != "X":
        on["mux_alu"] = str(w["alu_b"])
    if w["branch_target"] is not None:
        on["imm_badd"] = f"{w['imm']:+d}"
        on["pcp1_badd"] = str(w["pc_plus_1"])
        on["badd_mux"] = str(w["branch_target"])
        on["zero_pcsrc"] = f"Zero {int(w['zero'])}"
    if w["jump_target"] is not None:
        on["imm_jump"] = str(w["jump_target"])
    if w["mem_addr"] is not None:
        on["alu_mem"] = f"addr {w['mem_addr']}"
    if w["mem_write_data"] is not None:
        on["rd2_wd"] = str(w["mem_write_data"])
    if w["mem_read_data"] is not None:
        on["mem_rd"] = str(w["mem_read_data"])
    if w["write_reg"] is not None:
        if s["MemtoReg"] == "0":
            on["alu_wb"] = str(w["alu_result"])
        on["mux_wb"] = str(w["write_data"]) + (" ✗R0" if w["r0_discard"] else "")
    on["pcsrc_jmux"] = str(w["branch_target"] if w["taken"] else w["pc_plus_1"])
    on["jmux_pc"] = f"PC {w['next_pc']}"
    return on


def block_info(w: dict) -> dict:
    """Values written inside blocks and the signal-tag texts, plus active blocks per stage."""
    if w["halted_before"]:
        return {"halted": True, "pc": w["pc"]}
    s = w["signals"]
    tags = {name: f"{name}={s[name]}" for name, _, _ in TAGS if name in s}
    tags["ALUOp"] = f"ALUOp={s['ALUOp']}"
    branch = s["Branch"] == "1"
    tags["PCSrc"] = f"PCSrc={int(bool(w['taken']))}" if branch else "PCSrc=0"
    blocks = {0: ["pc", "add", "im"], 1: ["cu"], 2: [], 3: [], 4: [], 5: []}
    if w["read_reg1"] is not None or w["read_reg2"] is not None:
        blocks[1].append("rf")
    if w["imm"] is not None:
        blocks[1].append("imm")
    if w["alu_op"] is not None:
        blocks[2].append("alu")
        if s["ALUSrc"] != "X":
            blocks[2].append("alusrc")
    if branch:
        blocks[2].append("badd")
    if w["write_reg"] is not None:
        blocks[4] += ["memtoreg", "rf"]
    if not w["halt"]:
        blocks[5] += ["pcsrc", "jmux", "pc"]
    mem = ""
    if s["MemRead"] == "1":
        mem = f"MemRead=1 [{w['mem_addr']}]"
    elif s["MemWrite"] == "1":
        mem = f"MemWrite=1 [{w['mem_addr']}]"
    alu = ""
    if w["alu_op"] is not None:
        alu = f"{w['alu_op']} = {w['alu_result']}"
    return {
        "halted": False, "halt": w["halt"], "pc": w["pc"], "next_pc": w["next_pc"],
        "asm": f"PC {w['pc']}: {w['asm']}   ({w['hex']} = {w['binary']})",
        "im": w["hex"], "cu": w["mnemonic"], "alu": alu,
        "imm": "" if w["imm"] is None else str(w["imm"]),
        "tags": tags, "blocks": blocks, "mem": mem,
        "mem_addr": w["mem_addr"], "mem_read": s["MemRead"] == "1",
        "mem_write": s["MemWrite"] == "1",
    }
