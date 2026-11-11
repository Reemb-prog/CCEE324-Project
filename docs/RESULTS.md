# Simulation results

Everything below was copied from real local runs on Windows 11 with Python 3.12 (`C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`). No output was edited except for trimming where marked. Re-run the commands to reproduce.

## 1. Test suite

Command: `python scripts/harness.py verify` (integrity check of the 13 protected test/spec files, then stages 01–06).

Exit code 0. Full output:

```text
Integrity OK: 13 protected files
Testing stages 01..06 with C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe
test_all_required_opcodes (tests.test_stage_01.TestDatapath.test_all_required_opcodes) ... ok
test_control_signals (tests.test_stage_01.TestDatapath.test_control_signals) ... ok
test_invalid_encoding (tests.test_stage_01.TestDatapath.test_invalid_encoding) ... ok
test_m_and_halt (tests.test_stage_01.TestDatapath.test_m_and_halt) ... ok
test_r_format (tests.test_stage_01.TestDatapath.test_r_format) ... ok
test_register_file (tests.test_stage_01.TestDatapath.test_register_file) ... ok
test_bad_alu_inputs (tests.test_stage_02.TestSingleCore.test_bad_alu_inputs) ... ok
test_eight_operations_and_masking (tests.test_stage_02.TestSingleCore.test_eight_operations_and_masking) ... ok
test_single_core_pc_and_halt (tests.test_stage_02.TestSingleCore.test_single_core_pc_and_halt) ... ok
test_unterminated_program_fails (tests.test_stage_02.TestSingleCore.test_unterminated_program_fails) ... ok
test_exhaustion_raises (tests.test_stage_03.TestTwoCores.test_exhaustion_raises) ... ok
test_independent_execution (tests.test_stage_03.TestTwoCores.test_independent_execution) ... ok
test_memory_bounds (tests.test_stage_04.TestSharedMemory.test_memory_bounds) ... ok
test_same_tick_conflict_last_core_wins (tests.test_stage_04.TestSharedMemory.test_same_tick_conflict_last_core_wins) ... ok
test_store_visible_next_tick (tests.test_stage_04.TestSharedMemory.test_store_visible_next_tick) ... ok
test_bonus_invalid (tests.test_stage_05.TestBonus.test_bonus_invalid) ... ok
test_encode_and_execute (tests.test_stage_05.TestBonus.test_encode_and_execute) ... ok
test_report_mentions_required_concepts (tests.test_stage_06.TestDeliverables.test_report_mentions_required_concepts) ... ok
test_reports_are_nonempty (tests.test_stage_06.TestDeliverables.test_reports_are_nonempty) ... ok

----------------------------------------------------------------------
Ran 19 tests in 0.065s

OK
```

**Summary: 19 run, 19 passed, 0 failed.** `python -m unittest discover -s tests` gives the same 19 tests.

Per-stage coverage:

| Stage | Tests | What they check |
|---|---|---|
| 01 | 6 | R/M/H encoding and decoding, all 8 ALU opcodes, invalid words rejected, 8 private writable 8-bit registers, RegWrite/MemRead/MemWrite signals |
| 02 | 4 | All 8 ALU operations with 8-bit masking, bad ALU inputs, single-core PC advance and HALT freeze, missing-HALT error |
| 03 | 2 | Separate cores/register files, independent PCs, per-core HALT, cycle count, `run()` budget error |
| 04 | 3 | 256-byte bounds, STORE visible to the other core only on the next tick, same-address conflict (core 1 wins) |
| 05 | 2 | LOADI/NOT encoding, immediate 255, NOT masking, a program using both, invalid bonus operands |
| 06 | 2 | Deliverable files exist and the report covers required concepts |

## 2. Scripted dual-core demo

Command: `python -m dualcore.demo` (exit code 0). Full output:

```text
Dual-core 8-bit CPU demo

Program 0:
  0: 1010001000110010  LOADI R1, 25
  1: 1010010000100010  LOADI R2, 17
  2: 0000011001010000  ADD   R3, R1, R2
  3: 1001011011001000  STORE R3, [100]
  4: 1111000000000000  HALT

Program 1:
  0: 1010001000001010  LOADI R1, 5
  1: 1010010000000110  LOADI R2, 3
  2: 0001011001010000  SUB   R3, R1, R2
  3: 1000100011001000  LOAD  R4, [100]
  4: 1000101011001000  LOAD  R5, [100]
  5: 0000110101001000  ADD   R6, R5, R1
  6: 1001110011001010  STORE R6, [101]
  7: 1011111110000000  NOT   R7, R6
  8: 1001111011001100  STORE R7, [102]
  9: 1111000000000000  HALT

Execution (one instruction per active core per tick):
tick 1:
   core0: PC=0  LOADI R1, 25         R1 <- 25
   core1: PC=0  LOADI R1, 5          R1 <- 5
   end of tick: mem[100]=0, mem[101]=0, mem[102]=0
tick 2:
   core0: PC=1  LOADI R2, 17         R2 <- 17
   core1: PC=1  LOADI R2, 3          R2 <- 3
   end of tick: mem[100]=0, mem[101]=0, mem[102]=0
tick 3:
   core0: PC=2  ADD   R3, R1, R2     R3 <- 42
   core1: PC=2  SUB   R3, R1, R2     R3 <- 2
   end of tick: mem[100]=0, mem[101]=0, mem[102]=0
tick 4:
   core0: PC=3  STORE R3, [100]      buffer mem[100] <- 42
   core1: PC=3  LOAD  R4, [100]      R4 <- 0
   end of tick: mem[100]=42, mem[101]=0, mem[102]=0
tick 5:
   core0: PC=4  HALT
   core1: PC=4  LOAD  R5, [100]      R5 <- 42
   end of tick: mem[100]=42, mem[101]=0, mem[102]=0
tick 6:
   core0: (halted, PC stays 4)
   core1: PC=5  ADD   R6, R5, R1     R6 <- 47
   end of tick: mem[100]=42, mem[101]=0, mem[102]=0
tick 7:
   core0: (halted, PC stays 4)
   core1: PC=6  STORE R6, [101]      buffer mem[101] <- 47
   end of tick: mem[100]=42, mem[101]=47, mem[102]=0
tick 8:
   core0: (halted, PC stays 4)
   core1: PC=7  NOT   R7, R6         R7 <- 208
   end of tick: mem[100]=42, mem[101]=47, mem[102]=0
tick 9:
   core0: (halted, PC stays 4)
   core1: PC=8  STORE R7, [102]      buffer mem[102] <- 208
   end of tick: mem[100]=42, mem[101]=47, mem[102]=208
tick 10:
   core0: (halted, PC stays 4)
   core1: PC=9  HALT
   end of tick: mem[100]=42, mem[101]=47, mem[102]=208

Final state:
  core0: PC=4 halted=True  R0=0 R1=25 R2=17 R3=42 R4=0 R5=0 R6=0 R7=0
  core1: PC=9 halted=True  R0=0 R1=5 R2=3 R3=2 R4=0 R5=42 R6=47 R7=208
  shared memory: mem[100]=42, mem[101]=47, mem[102]=208

Verification:
  [PASS] core 0 stored 25 + 17 = 42 in shared memory
  [PASS] core 1 LOAD in the same tick as the STORE saw the old value 0
  [PASS] core 1 LOAD one tick later saw core 0's value 42
  [PASS] core 1 wrote 42 + 5 = 47 back to memory
  [PASS] core 1 wrote NOT 47 = 208 (00101111 -> 11010000)
  [PASS] LOADI set R1/R2 from the programs themselves
  [PASS] R3 differs per core (private register files)
  [PASS] core 0 halted early at PC 4 while core 1 ran on
  [PASS] both cores halted after 10 ticks
```

What it shows: both PCs hold the same number for ticks 1–5 yet are separate (core 0 freezes at 4 while core 1 continues to 9); R3 is 42 in core 0 and 2 in core 1; core 1's LOAD in tick 4 (same tick as core 0's STORE) reads the old 0, and its LOAD in tick 5 reads 42.

## 3. Expression mode (8-bit wrap-around)

Command: `python -m dualcore.demo "200 + 100" "3 - 5"` (exit code 0). Excerpt (tick 3 and the result section; ticks 1, 2, 4, 5 trimmed):

```text
   --- tick 3 ---
   core0  fetch    PC=2 -> 0x0650  ADD   R3, R1, R2
          control  RegDst=1 ALUSrc=0 MemtoReg=0 ImmToReg=0 RegWrite=1 MemRead=0 MemWrite=0 ALUOp=ADD
          read     R1 = 200 (11001000), R2 = 100 (01100100)
          ALU      ADD -> 44 (00101100)
          write    R3 <- 44  (MemtoReg=0: ALU result)
          next PC  2 + 1 = 3
   core1  fetch    PC=2 -> 0x1650  SUB   R3, R1, R2
          control  RegDst=1 ALUSrc=0 MemtoReg=0 ImmToReg=0 RegWrite=1 MemRead=0 MemWrite=0 ALUOp=SUB
          read     R1 = 3 (00000011), R2 = 5 (00000101)
          ALU      SUB -> 254 (11111110)
          write    R3 <- 254  (MemtoReg=0: ALU result)
          next PC  2 + 1 = 3

5) Result
   core0: mem[2] = 44 (00101100)   [PASS] expected 44
     note: 300 does not fit in 8 bits; the carry out of bit 7 is dropped (300 - 256 = 44).
   core1: mem[18] = 254 (11111110)   [PASS] expected 254
     note: 3 - 5 = -2 is negative; the 8-bit pattern 11111110 is -2 in two's complement, read as unsigned it is 254.
   5 ticks. Both cores used the names R1-R3, but each had its own copy (core0 R3=44, core1 R3=254).
```

Invalid input is rejected: `python -m dualcore.demo "1 + 999"` printed `error: 999 does not fit in 8 bits (0..255)` and exited with code 2.
