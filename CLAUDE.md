# CCEE 324 Claude Code working rules

You are implementing a **small educational Python simulator**, not a production CPU or an actual parallel execution engine.

## Mandatory discipline

1. Read `scripts/harness.py status` output or `.harness/state.json` to find the active stage. Read **only** `tasks/NN_*.md`, `docs/ISA.md`, `docs/INTERFACES.md`, and relevant source/tests. The supplied PDF is authoritative for scope; `docs/COURSE_BOUNDARY.md` is a short summary.
2. Implement **one stage only**. Do not prebuild later stages. Do not change design, add tools, pip packages, frameworks, GUI, browser, services, API clients, databases, threads, CI, containers, or extra instructions beyond the two named bonus operations.
3. Never change: `tests/`, `.harness/`, `scripts/harness.py`, `docs/ISA.md`, `docs/INTERFACES.md`, `docs/COURSE_BOUNDARY.md`, `.claude/settings.json`, `reference/`, or `contracts.sha256`. If a test or contract is inconsistent, **stop and explain**; do not modify it.
4. Work only in this project directory. No network, shell downloads, installations, secrets, user home traversal, other repositories, destructive commands, pushes, or file deletions. Ask before anything outside the scoped task. Never bypass permissions.
5. Use Python standard library, straightforward functions and classes, readable code, types when helpful. Treat all register and memory data as unsigned 8-bit; wrap arithmetic to 8 bits. No advanced ISA features not required.
6. Run `python scripts/harness.py verify` after implementing. If tests fail, fix code **within the stage** and rerun. If blocked, explain the smallest issue and stop. Do not claim passing results without actual execution.
7. Write one checkpoint headed `[STAGE NN]` per stage to `PROGRESS.md` and one headed `[STAGE NN]` to `docs/EXPLANATIONS.md`: files built, essential CO concept, test status and observed counts, limitations. Update `docs/EXPLANATIONS.md` in similarly accessible terms. Explain architectural decisions with their source (PDF vs implementation choice). Do not narrate every tool command.
8. Stop after the current stage. **Only the human runs `harness.py advance`.** Keep final chat summary <=120 words: changes, tests, next stage or blocker. Do not start extra Claude sessions, subagents, research, or repeated large file dumps.

## Course-level implementation

Two cores, each with its own program counter, 8 x 8-bit registers, decoder, control unit, ALU, and instruction program. 16-bit instructions, eight ALU operations, 256 x 8-bit common data memory, LOAD, STORE, HALT. The two bonus instructions are LOADI and NOT. One instruction per active core per conceptual clock tick; no branches, interrupts, cache, pipeline, flag register, hazards, real multithreading, or MIPS ISA compatibility. Include tests, a simple terminal demo, Mermaid/ASCII block diagram, technical report, and explanation of independent/shared execution.

**Important:** Course lectures show MIPS PC+4 for a 32-bit, byte-addressed instruction. This simplified simulator's PC is an **instruction-list index**: it advances by 1. Two distinct PCs need not hold different numeric values at all times.
