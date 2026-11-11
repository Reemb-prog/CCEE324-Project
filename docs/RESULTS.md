# Simulation results

Everything below was copied from real local runs on Windows 11 with Python 3.12 (`C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`). No output was edited except for trimming where marked. Re-run the commands to reproduce.

## 1. Test suite

Command: `python scripts/harness.py verify` (integrity check of the 14 protected test/spec files, then stages 01–07).

Exit code 0. Full output:

```text
Integrity OK: 14 protected files
Testing stages 01..07 with C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe
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
test_control_signals (tests.test_stage_07.TestAluAndControl.test_control_signals) ... ok
test_slt_is_unsigned (tests.test_stage_07.TestAluAndControl.test_slt_is_unsigned) ... ok
test_backward_bne_countdown (tests.test_stage_07.TestControlFlow.test_backward_bne_countdown) ... ok
test_branch_not_taken_falls_through (tests.test_stage_07.TestControlFlow.test_branch_not_taken_falls_through) ... ok
test_cross_core_spin_wait (tests.test_stage_07.TestControlFlow.test_cross_core_spin_wait)
Core 1 polls shared memory until core 0's STORE becomes visible. ... ok
test_if_skips_when_equal (tests.test_stage_07.TestControlFlow.test_if_skips_when_equal) ... ok
test_out_of_program_target_and_infinite_loop (tests.test_stage_07.TestControlFlow.test_out_of_program_target_and_infinite_loop) ... ok
test_r0_hard_wired_zero (tests.test_stage_07.TestControlFlow.test_r0_hard_wired_zero)
Instruction writes to R0 are discarded; R0 always reads 0 in programs. ... ok
test_slti_if_else (tests.test_stage_07.TestControlFlow.test_slti_if_else) ... ok
test_while_loop_sum (tests.test_stage_07.TestControlFlow.test_while_loop_sum)
sum = 0; i = 1; while (i < 6) { sum += i; i++ }  ->  sum = 15. ... ok
test_decode_round_trip (tests.test_stage_07.TestEncoding.test_decode_round_trip) ... ok
test_earlier_opcodes_unchanged (tests.test_stage_07.TestEncoding.test_earlier_opcodes_unchanged) ... ok
test_exact_bit_patterns (tests.test_stage_07.TestEncoding.test_exact_bit_patterns) ... ok
test_invalid_words_and_operands (tests.test_stage_07.TestEncoding.test_invalid_words_and_operands) ... ok

----------------------------------------------------------------------
Ran 33 tests in 0.031s

OK
```

**Summary: 33 run, 33 passed, 0 failed** (19 from the original six stages, 14 from the stage-07 extension).

Per-stage coverage:

| Stage | Tests | What they check |
|---|---|---|
| 01 | 6 | R/M/H encoding and decoding, all 8 ALU opcodes, invalid words rejected, 8 private writable 8-bit registers, RegWrite/MemRead/MemWrite signals |
| 02 | 4 | All 8 ALU operations with 8-bit masking, bad ALU inputs, single-core PC advance and HALT freeze, missing-HALT error |
| 03 | 2 | Separate cores/register files, independent PCs, per-core HALT, cycle count, `run()` budget error |
| 04 | 3 | 256-byte bounds, STORE visible to the other core only on the next tick, same-address conflict (core 1 wins) |
| 05 | 2 | LOADI/NOT encoding, immediate 255, NOT masking, a program using both, invalid bonus operands |
| 06 | 2 | Deliverable files exist and the report covers required concepts |
| 07 | 14 | Extension: SLT/SLTI/BEQ/BNE/J bit patterns and invalid words, unsigned SLT, control signals, if, while (sum 1..5), backward BNE loop, out-of-program target, infinite-loop budget, hard-wired R0, cross-core spin-wait (exactly 6 ticks) |

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

Command: `python -m dualcore.demo "200 + 100" "3 - 5"` (exit code 0). Excerpt (tick 1, tick 3 and the result section; ticks 2, 4, 5 trimmed). Tick 1 shows LOAD using the lecture's lw column: ALUSrc=1, ALUOp=ADD, address = R0 + imm8:

```text
   --- tick 1 ---
   core0  fetch    PC=0 -> 0x8200  LOAD  R1, [0]
          control  RegDst=1 ALUSrc=1 MemtoReg=1 RegWrite=1 MemRead=1 MemWrite=0 Branch=0 BranchNe=0 Jump=0 ALUOp=ADD
          ALU      address = R0 + 0 = 0  (ALUSrc=1: address field as input B)
          memory   read mem[0] = 200 (MemRead=1)
          write    R1 <- 200  (MemtoReg=1: memory data, not ALU)
          next PC  0 + 1 = 1
   core1  fetch    PC=0 -> 0x8220  LOAD  R1, [16]
          control  RegDst=1 ALUSrc=1 MemtoReg=1 RegWrite=1 MemRead=1 MemWrite=0 Branch=0 BranchNe=0 Jump=0 ALUOp=ADD
          ALU      address = R0 + 16 = 16  (ALUSrc=1: address field as input B)
          memory   read mem[16] = 3 (MemRead=1)
          write    R1 <- 3  (MemtoReg=1: memory data, not ALU)
          next PC  0 + 1 = 1
   ...
   --- tick 3 ---
   core0  fetch    PC=2 -> 0x0650  ADD   R3, R1, R2
          control  RegDst=1 ALUSrc=0 MemtoReg=0 RegWrite=1 MemRead=0 MemWrite=0 Branch=0 BranchNe=0 Jump=0 ALUOp=ADD
          read     R1 = 200 (11001000), R2 = 100 (01100100)
          ALU      ADD -> 44 (00101100)
          write    R3 <- 44  (MemtoReg=0: ALU result)
          next PC  2 + 1 = 3
   core1  fetch    PC=2 -> 0x1650  SUB   R3, R1, R2
          control  RegDst=1 ALUSrc=0 MemtoReg=0 RegWrite=1 MemRead=0 MemWrite=0 Branch=0 BranchNe=0 Jump=0 ALUOp=SUB
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

## 4. Branch demo (stage 07 extension)

Command: `python -m dualcore.demo -b` (exit code 0). Full output (trailing spaces trimmed):

```text
Branch demo: while loop on core 0, spin-wait + if/else on core 1

Program 0:
   0: 1010001000000010  LOADI R1, 1
   1: 1010010000001100  LOADI R2, 6
   2: 1010011000000000  LOADI R3, 0
   3: 1010101000000010  LOADI R5, 1
   4: 1101100001010000  SLT   R4, R1, R2
   5: 1100011000000011  BEQ   R4, R0, +3
   6: 0000011011001000  ADD   R3, R3, R1
   7: 0000001001101000  ADD   R1, R1, R5
   8: 1100110000000100  J     4
   9: 1001011001111000  STORE R3, [60]
  10: 1001101001111010  STORE R5, [61]
  11: 1111000000000000  HALT

Program 1:
   0: 1000001001111010  LOAD  R1, [61]
   1: 1100010010001110  BEQ   R1, R0, -2
   2: 1000010001111000  LOAD  R2, [60]
   3: 1110011010010100  SLTI  R3, R2, 20
   4: 1100010110000010  BEQ   R3, R0, +2
   5: 1010100000000010  LOADI R4, 1
   6: 1100110000001000  J     8
   7: 1010100000000000  LOADI R4, 0
   8: 1001100001111100  STORE R4, [62]
   9: 1111000000000000  HALT

Execution (one line per tick):
  tick  1 | core0 PC= 0 LOADI R1, 1       R1 <- 1          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick  2 | core0 PC= 1 LOADI R2, 6       R2 <- 6          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick  3 | core0 PC= 2 LOADI R3, 0       R3 <- 0          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick  4 | core0 PC= 3 LOADI R5, 1       R5 <- 1          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick  5 | core0 PC= 4 SLT   R4, R1, R2  R4 <- 1          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick  6 | core0 PC= 5 BEQ   R4, R0, +3  not taken        | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick  7 | core0 PC= 6 ADD   R3, R3, R1  R3 <- 1          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick  8 | core0 PC= 7 ADD   R1, R1, R5  R1 <- 2          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick  9 | core0 PC= 8 J     4           jump -> PC=4     | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 10 | core0 PC= 4 SLT   R4, R1, R2  R4 <- 1          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 11 | core0 PC= 5 BEQ   R4, R0, +3  not taken        | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 12 | core0 PC= 6 ADD   R3, R3, R1  R3 <- 3          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 13 | core0 PC= 7 ADD   R1, R1, R5  R1 <- 3          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 14 | core0 PC= 8 J     4           jump -> PC=4     | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 15 | core0 PC= 4 SLT   R4, R1, R2  R4 <- 1          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 16 | core0 PC= 5 BEQ   R4, R0, +3  not taken        | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 17 | core0 PC= 6 ADD   R3, R3, R1  R3 <- 6          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 18 | core0 PC= 7 ADD   R1, R1, R5  R1 <- 4          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 19 | core0 PC= 8 J     4           jump -> PC=4     | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 20 | core0 PC= 4 SLT   R4, R1, R2  R4 <- 1          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 21 | core0 PC= 5 BEQ   R4, R0, +3  not taken        | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 22 | core0 PC= 6 ADD   R3, R3, R1  R3 <- 10         | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 23 | core0 PC= 7 ADD   R1, R1, R5  R1 <- 5          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 24 | core0 PC= 8 J     4           jump -> PC=4     | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 25 | core0 PC= 4 SLT   R4, R1, R2  R4 <- 1          | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 26 | core0 PC= 5 BEQ   R4, R0, +3  not taken        | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 27 | core0 PC= 6 ADD   R3, R3, R1  R3 <- 15         | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 28 | core0 PC= 7 ADD   R1, R1, R5  R1 <- 6          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 29 | core0 PC= 8 J     4           jump -> PC=4     | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 30 | core0 PC= 4 SLT   R4, R1, R2  R4 <- 0          | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 31 | core0 PC= 5 BEQ   R4, R0, +3  taken -> PC=9    | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 32 | core0 PC= 9 STORE R3, [60]    mem[60] <- 15    | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 33 | core0 PC=10 STORE R5, [61]    mem[61] <- 1     | core1 PC= 0 LOAD  R1, [61]    R1 <- 0
  tick 34 | core0 PC=11 HALT                               | core1 PC= 1 BEQ   R1, R0, -2  taken -> PC=0
  tick 35 | core0 (halted)                                 | core1 PC= 0 LOAD  R1, [61]    R1 <- 1
  tick 36 | core0 (halted)                                 | core1 PC= 1 BEQ   R1, R0, -2  not taken
  tick 37 | core0 (halted)                                 | core1 PC= 2 LOAD  R2, [60]    R2 <- 15
  tick 38 | core0 (halted)                                 | core1 PC= 3 SLTI  R3, R2, 20  R3 <- 1
  tick 39 | core0 (halted)                                 | core1 PC= 4 BEQ   R3, R0, +2  not taken
  tick 40 | core0 (halted)                                 | core1 PC= 5 LOADI R4, 1       R4 <- 1
  tick 41 | core0 (halted)                                 | core1 PC= 6 J     8           jump -> PC=8
  tick 42 | core0 (halted)                                 | core1 PC= 8 STORE R4, [62]    mem[62] <- 1
  tick 43 | core0 (halted)                                 | core1 PC= 9 HALT

Final: mem[60]=15 mem[61]=1 mem[62]=1  after 43 ticks

Verification:
  [PASS] while loop: core 0 summed 1..5 = 15
  [PASS] spin-wait: core 1 read flag = 0 17 times before seeing 1
  [PASS] core 1 read core 0's sum only after the flag
  [PASS] if/else: 15 < 20 so the 'then' branch set verdict = 1
  [PASS] both cores halted
```

What it shows: core 0's `while` loop (SLT, BEQ exit, J back) sums 1..5 = 15. Core 1 spin-waits with LOAD + BEQ and reads flag = 0 seventeen times. Core 0's flag STORE in tick 33 becomes visible in tick 35: in tick 33 itself core 1 still reads 0 (same-tick rule) and in tick 34 it is branching. Core 1 then reads the sum and its SLTI `if/else` takes the *then* path. `BEQ Rx, R0` works as "branch if Rx is zero" because R0 is hard-wired to 0.
