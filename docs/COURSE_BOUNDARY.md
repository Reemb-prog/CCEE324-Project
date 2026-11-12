# Scope boundary: what has been covered

Sources consulted: CCEE 324 Modules 01–04 and the Modules 01–03 solving session (RHU), plus the five-page instructor project brief included under `reference/`.

**Aligned concepts:**

- architecture vs organization, and the ISA;
- binary instruction encodings and the R/I/J instruction formats (our six formats R, I, S, B, J, H map onto them);
- binary, hexadecimal and two's complement;
- register operands, writeback, and `$zero` as a hard-wired zero register;
- MIPS `add`, `sub`, the logical operators, `slt`, `lw`, `sw`, `beq` and `j`;
- the single-cycle datapath: PC, PC adder, instruction memory, register file, ALU and its Zero output, sign-extend, multiplexers (ALUSrc, MemtoReg, PCSrc), control signals, data memory;
- combinational logic vs state updated on clock edges;
- step-by-step fetch/decode/execute traces;
- separate cores sharing memory.

**Simplifications, not MIPS:**

- The instructor specifies an 8-bit datapath, 8 registers per core, 16-bit instruction words and 256 bytes of shared data memory.
- MIPS uses 32-bit byte-addressed instructions and PC+4. This teaching model indexes a list of 16-bit instructions, so the next PC is PC+1 and the branch target is PC+1+offset.
- LOAD, STORE and LOADI have no room for a base register, so they use R0 (always 0) as the base. Addresses are therefore effectively absolute.
- The control unit adds one signal, BranchNe for BNE, plus the textbook's Jump signal.
- It is a simulator, not electronic HDL hardware.

**Bonus instructions** (the PDF allows extras):

- LOADI and NOT;
- SLT, SLTI, BEQ, BNE and J. These were added later at the team's request as stage 07, building on the lecture's `beq` datapath.

**Deliberate exclusions:**

- pipelining, hazards and forwarding;
- cache and coherence, virtual memory;
- true parallel execution;
- flags and interrupts;
- procedure calls and stack (`jal`/`jr`);
- multiplication and division;
- an assembler, GUI, network or external dependencies.

These are not needed for this assignment and would distract from the tested topics.
