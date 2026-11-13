"""Bundle a traced run into the self-contained HTML player (diagram + toolbar + text)."""
import json
from pathlib import Path

from . import datapath_svg, explain

_TEMPLATE = Path(__file__).with_name("player.html")


def watched_addresses(trace: dict, initial_memory: dict) -> list[int]:
    """Memory cells worth showing: initial values plus every address accessed."""
    addrs = set(initial_memory)
    for tick in trace["ticks"]:
        for w in tick["wires"]:
            if w.get("mem_addr") is not None:
                addrs.add(w["mem_addr"])
    return sorted(addrs)


def player_data(trace: dict, sources: list[list[str]], initial_memory: dict) -> dict:
    ticks = []
    for record in trace["ticks"]:
        cores = []
        for core_id, w in enumerate(record["wires"]):
            cores.append({
                "asm": w.get("asm", ""),
                "line": explain.tick_line(core_id, w),
                "stages": explain.stage_texts(w),
                "wires": datapath_svg.wire_labels(w),
                "info": datapath_svg.block_info(w),
            })
        ticks.append({
            "cycle": record["cycle"], "cores": cores,
            "summary": explain.tick_summary(record),
            "regs_before": record["before"]["regs"], "regs_after": record["after"]["regs"],
            "mem_before": record["before"]["memory"], "mem_after": record["after"]["memory"],
            "mem_changes": [a for a, _, _ in record["mem_changes"]],
        })
    return {
        "stages": explain.STAGES, "ticks": ticks, "programs": sources,
        "watch": watched_addresses(trace, initial_memory), "error": trace["error"],
    }


def build_html(trace: dict, sources: list[list[str]], initial_memory: dict) -> str:
    data = json.dumps(player_data(trace, sources, initial_memory), separators=(",", ":"))
    data = data.replace("</", "<\\/")   # keep "</script>" out of the inline JSON
    html = _TEMPLATE.read_text(encoding="utf-8")
    return html.replace("__SVG__", datapath_svg.build_svg()).replace("__DATA__", data)
