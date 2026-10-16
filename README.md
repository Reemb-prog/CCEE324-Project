# CCEE 324: Claude Code milestone harness

This is **a guided implementation environment, not a finished processor**. Claude Code implements the project one approved stage at a time, while the local harness checks milestone tests and preserves progress. Python 3.10+ and the standard library are enough. No Anthropic API key, cloud automation, pip install, or MCP server is required.

## Start (Windows PowerShell)

1. Extract the ZIP into a **new, dedicated folder**. Install Python 3.10+ and Claude Code from its official documentation if not already installed.
2. In PowerShell: `cd CCEE324_Claude_Harness` (or the actual extracted folder).
3. Run `python scripts/harness.py status` to check the milestone. Then run `python scripts/harness.py task` to view its assignment.
4. Run `claude` in **this folder**, sign in with your Claude Pro account, and submit the single prompt below. Do not provide an API key. If `ANTHROPIC_API_KEY` is present in your PowerShell environment, run `Remove-Item Env:ANTHROPIC_API_KEY` before launching Claude, so your Pro login is used rather than API billing.

```text
Read CLAUDE.md and the current stage in tasks/. Implement ONLY that stage. Run python scripts/harness.py verify. Update PROGRESS.md and docs/EXPLANATIONS.md with a short plain-English explanation and the observed test result. Stop for my approval. Do not advance the stage or edit tests, harness scripts, state, or requirement files.
```

5. Inspect Claude's changes and explanations. In your own terminal, run `python scripts/harness.py verify`.
6. If the tests pass and you approve, run `python scripts/harness.py advance`; **type the confirmation**. Then give Claude this shorter request in the same session:

```text
Implement the newly current stage according to CLAUDE.md. Verify it, log progress and explanation, and stop for approval.
```

One session can handle several stages; keeping the same session avoids repeated startup context. When a session grows, restart Claude; `CLAUDE.md`, `state.json`, and `PROGRESS.md` retain the important context. **Do not paste the whole PDF or all test files into chat.** Claude can read them locally if necessary. Use the standard model for ordinary changes rather than spawning subagents, parallel agents, or changing models repeatedly.

## Essential commands

| Command | Purpose |
|---|---|
| `python scripts/harness.py status` | Show current milestone and completion |
| `python scripts/harness.py task` | Print current stage's compact instructions |
| `python scripts/harness.py verify` | Integrity check plus current and earlier milestone tests |
| `python scripts/harness.py advance` | Human approval gate, then move to next stage |
| `python scripts/harness.py audit` | Check protected test/spec file hashes |
| `python -m unittest discover -s tests -v` | Full suite; expected to fail until stage 6 is built |
| `python -m dualcore.demo` | Final demonstrator; available once implemented |

## How the six stages map to the instructor's four milestones

| Stage | Work | Instructor milestone |
|---|---|---|
| 01 | ISA, diagram, register file, decoder, control signals | Single-core datapath design |
| 02 | ALU and single-core fetch/decode/execute | ALU implementation and single core |
| 03 | Independent PC/program/registers, clock tick | Dual-core independence |
| 04 | Common 256-byte memory, LOAD/STORE, reproducible demo | Shared memory and dual-core operation |
| 05 | **Bonus:** LOADI and NOT | Bonus additional instructions |
| 06 | Report, complete testing, demo walkthrough | All submitted deliverables |

`reference/CCEE324_Project_Instructions.pdf` is the authoritative assignment. `docs/ISA.md` and `docs/INTERFACES.md` fix ambiguities left by its schematic hints; changes require **human review**. Instructions are 16 bits but data registers are 8 bits, matching the final specification on page 5.

## Safety and token budget

The shared Claude settings run in manual mode, deny web fetch/search and common network/destructive commands, and allow just the exact local test command. They are **not a security sandbox**. On native Windows, Claude's sandboxed Bash is not supported; use a separate folder, inspect permissions, and avoid unrestricted or automatic execution. For higher isolation use WSL2 and optionally the included `config/strict-wsl-settings.json` as CLI settings. No harness script connects to Claude or makes network requests. Your Claude Pro subscription can be used through interactive sign-in; no paid API setup is needed. Do not run `claude -p` in an unattended loop.

Source: instructor PDF and CCEE 324 Modules 01–04 / solving-session concepts, summarized in `docs/COURSE_BOUNDARY.md`.
