# Live demo script (about 5 minutes)

Run everything from the project folder in a terminal. Python 3.10+ only; nothing to install.

## 1. Prove it is tested (about 1 min)

```bash
python scripts/harness.py verify
```

Point out:
- **"Integrity OK: 14 protected files":** the tests were not edited.
- **"Ran 33 tests (19 original + 14 stage-07 extension) … OK":** all stages pass.
- The test names map to the milestones: datapath (01), ALU and single core (02), two cores (03), shared memory (04), bonus (05), deliverables (06), branching extension (07).

## 2. Run the dual-core program (about 2 min)

```bash
python -m dualcore.demo
```

Walk through the output top to bottom:

1. **Programs:** each instruction is shown as its 16-bit machine word, e.g. `1010 001 00011001 0` = `LOADI R1, 25`. Each core has its own program.
2. **Ticks 1–3, separate registers:** both cores write "R1", "R2", "R3", but core 0 ends with R3 = 42 and core 1 with R3 = 2. Same names, different physical registers.
3. **Tick 4, shared memory:** core 0 runs `STORE R3, [100]` (buffered) while core 1 runs `LOAD R4, [100]` and gets **0**, the old value. At the end of the tick memory shows `mem[100]=42`.
4. **Tick 5, next-tick visibility:** core 1's `LOAD R5, [100]` now gets **42**. That is the core 0 → core 1 hand-off. In the same tick core 0 executes HALT.
5. **Ticks 6–10, separate PCs:** core 0 shows "halted, PC stays 4" while core 1's PC keeps going 5, 6, 7, 8, 9. Before this both PCs held equal numbers, but they were always two separate PC registers.
6. **Bonus:** the LOADIs at the start set registers without Python help. `NOT R7, R6` turns 47 into 208.
7. **Verification:** 9 × PASS.

## 2b. Branches and loops (stage 07 extension, about 1-2 min)

```bash
python -m dualcore.demo -b
```

- **Core 0, ticks 5-31:** a `while` loop. `SLT` tests i < 6 and `BEQ ... +3` exits when it is false; `J 4` jumps back. Watch R3 grow 1, 3, 6, 10, 15.
- **Core 1, at the same time:** a spin-wait. `LOAD R1, [61]` then `BEQ R1, R0, -2` ("taken -> PC=0") repeat until core 0's flag store (tick 33) becomes visible (tick 35).
- **Then an `if/else`:** `SLTI R3, R2, 20` gives 1, so `BEQ` is "not taken", the *then* path runs, and `J 8` skips the *else*.
- Link to the lecture: BEQ uses ALUSrc=0, ALUOp=Subtract, Branch=1, and the ALU's Zero output picks the next PC. R0 is hard-wired to 0 (like `$zero`), so `BEQ R1, R0` means "branch if R1 is zero".

## 3. Show the ALU live (about 1–2 min, optional)

```bash
python -m dualcore.demo "200 + 100" "3 - 5"
```

- Each core LOADs its operands, runs one ALU instruction, and STOREs the result. The control signals are printed for every step; compare them with the lecture control table. LOAD/STORE show `ALUSrc=1 ALUOp=ADD`: the ALU computes the address R0 + imm8, exactly like `lw $t0, 100($zero)`.
- `200 + 100 = 44`: the carry out of bit 7 is dropped.
- `3 - 5 = 254`: `11111110` is −2 in two's complement.

Other quick examples:

```bash
python -m dualcore.demo "0xF0 nor 0x0F" "0x80 >> 2"
```

Interactive mode, for audience questions:

```bash
python -m dualcore.demo -i
```

## Likely questions

- **Why PC + 1, not PC + 4?** Our PC indexes a list of 16-bit instructions; it is not a byte address.
- **Do the cores really run in parallel?** No. Within one clock tick they are stepped one after the other. The snapshot/commit rule makes the result as if both acted in the same cycle.
- **Same-address STORE conflict?** Commits happen core 0 then core 1, so core 1's value remains (tested).
- **Why is the branch offset only -8 to +7?** The 16-bit word must also hold the opcode, a kind code and two registers; J covers long jumps.
- **Why LOADI and NOT?** LOADI lets programs set constants and shows immediate operands. NOT adds one more bitwise ALU operation.
- **Which control signals are not from the lecture?** Only BranchNe (for BNE). Jump is the textbook's extension for `j`; everything else is the lecture table, and LOAD/STORE/BEQ match the lw/sw/beq columns except RegDst.
