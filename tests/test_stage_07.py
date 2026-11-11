"""Stage 07 (extension): SLT, SLTI, BEQ, BNE, J -- control flow for if/while."""
import unittest


def run_single(program, max_cycles=200):
    """Run one program on core 0 (core 1 just halts) and return the processor."""
    from dualcore.isa import encode_halt
    from dualcore.processor import DualCoreProcessor
    cpu = DualCoreProcessor(program, [encode_halt()])
    cpu.run(max_cycles=max_cycles)
    return cpu


class TestEncoding(unittest.TestCase):
    def test_exact_bit_patterns(self):
        from dualcore.isa import encode_r, encode_slti, encode_branch, encode_jump
        self.assertEqual(encode_r("SLT", 1, 2, 3), (13 << 12) | (1 << 9) | (2 << 6) | (3 << 3))
        self.assertEqual(encode_slti(4, 5, 63), (14 << 12) | (4 << 9) | (5 << 6) | 63)
        self.assertEqual(encode_branch("BEQ", 1, 2, 3), (12 << 12) | (0b01 << 10) | (1 << 7) | (2 << 4) | 3)
        self.assertEqual(encode_branch("BNE", 7, 6, -1), (12 << 12) | (0b10 << 10) | (7 << 7) | (6 << 4) | 0xF)
        self.assertEqual(encode_branch("BEQ", 0, 0, -8), (12 << 12) | (0b01 << 10) | 0x8)
        self.assertEqual(encode_jump(255), (12 << 12) | (0b11 << 10) | 255)

    def test_decode_round_trip(self):
        from dualcore.isa import decode, encode_r, encode_slti, encode_branch, encode_jump
        d = decode(encode_r("SLT", 1, 2, 3))
        self.assertEqual((d.opcode, d.mnemonic, d.rd, d.rs, d.rt), (13, "SLT", 1, 2, 3))
        d = decode(encode_slti(4, 5, 40))
        self.assertEqual((d.opcode, d.mnemonic, d.rd, d.rs, d.immediate), (14, "SLTI", 4, 5, 40))
        d = decode(encode_branch("BEQ", 3, 4, 7))
        self.assertEqual((d.opcode, d.mnemonic, d.rs, d.rt, d.offset), (12, "BEQ", 3, 4, 7))
        d = decode(encode_branch("BNE", 3, 4, -8))
        self.assertEqual((d.mnemonic, d.rs, d.rt, d.offset), ("BNE", 3, 4, -8))
        d = decode(encode_jump(9))
        self.assertEqual((d.opcode, d.mnemonic, d.address), (12, "J", 9))

    def test_invalid_words_and_operands(self):
        from dualcore.isa import decode, encode_r, encode_slti, encode_branch, encode_jump
        for word in (0xC000,                              # kind 00 stays illegal
                     0xC000 | (0b11 << 10) | (1 << 8),    # J with nonzero bits [9:8]
                     (13 << 12) | 0b001):                 # SLT with nonzero bits [2:0]
            with self.subTest(word=hex(word)), self.assertRaises(ValueError):
                decode(word)
        for bad in (lambda: encode_branch("BEQ", 0, 0, 8),
                    lambda: encode_branch("BNE", 0, 0, -9),
                    lambda: encode_branch("J", 0, 0, 0),
                    lambda: encode_branch("BEQ", 8, 0, 0),
                    lambda: encode_slti(1, 2, 64),
                    lambda: encode_jump(256),
                    lambda: encode_jump(-1)):
            with self.assertRaises(ValueError):
                bad()

    def test_earlier_opcodes_unchanged(self):
        from dualcore.isa import decode, encode_r, encode_mem, encode_imm, encode_halt
        self.assertEqual(decode(encode_r("SRL", 7, 6, 5)).mnemonic, "SRL")
        self.assertEqual(decode(encode_mem("STORE", 3, 240)).address, 240)
        self.assertEqual(decode(encode_imm("LOADI", 1, 255)).immediate, 255)
        self.assertEqual(decode(encode_halt()).mnemonic, "HALT")


class TestAluAndControl(unittest.TestCase):
    def test_slt_is_unsigned(self):
        from dualcore.alu import alu_execute
        self.assertEqual(alu_execute("SLT", 3, 200), 1)
        self.assertEqual(alu_execute("SLT", 200, 3), 0)   # 200 is not "negative"
        self.assertEqual(alu_execute("SLT", 5, 5), 0)

    def test_control_signals(self):
        from dualcore.control import ControlUnit
        from dualcore.isa import decode, encode_r, encode_slti, encode_branch, encode_jump
        c = ControlUnit()
        beq = c.signals(decode(encode_branch("BEQ", 1, 2, 1)))
        self.assertTrue(beq.branch)
        self.assertFalse(beq.branch_ne or beq.jump or beq.reg_write or beq.mem_write or beq.mem_read)
        self.assertEqual((beq.alu_op, beq.alu_src), ("SUB", False))
        bne = c.signals(decode(encode_branch("BNE", 1, 2, 1)))
        self.assertTrue(bne.branch and bne.branch_ne)
        self.assertEqual(bne.alu_op, "SUB")
        j = c.signals(decode(encode_jump(3)))
        self.assertTrue(j.jump)
        self.assertFalse(j.branch or j.reg_write or j.mem_write or j.mem_read)
        slt = c.signals(decode(encode_r("SLT", 1, 2, 3)))
        self.assertEqual((slt.alu_op, slt.alu_src, slt.reg_write), ("SLT", False, True))
        slti = c.signals(decode(encode_slti(1, 2, 3)))
        self.assertEqual((slti.alu_op, slti.alu_src, slti.reg_write), ("SLT", True, True))
        self.assertFalse(slt.branch or slt.jump or slti.branch or slti.jump)
        add = c.signals(decode(encode_r("ADD", 1, 2, 3)))
        self.assertFalse(add.branch or add.branch_ne or add.jump)


class TestControlFlow(unittest.TestCase):
    def test_if_skips_when_equal(self):
        from dualcore.isa import encode_imm, encode_branch, encode_halt
        from dualcore.core import Core
        from dualcore.memory import SharedMemory
        c = Core([encode_imm("LOADI", 1, 5),
                  encode_imm("LOADI", 2, 5),
                  encode_branch("BEQ", 1, 2, 1),   # taken: skip the next instruction
                  encode_imm("LOADI", 3, 99),
                  encode_imm("LOADI", 4, 7),
                  encode_halt()])
        m = SharedMemory()
        for _ in range(3):
            c.step(m)
        self.assertEqual(c.pc, 4)                  # PC + 1 + offset = 2 + 1 + 1
        c.step(m); c.step(m)
        self.assertTrue(c.halted)
        self.assertEqual((c.registers.read(3), c.registers.read(4)), (0, 7))

    def test_branch_not_taken_falls_through(self):
        from dualcore.isa import encode_imm, encode_branch, encode_halt
        cpu = run_single([encode_imm("LOADI", 1, 5),
                          encode_imm("LOADI", 2, 6),
                          encode_branch("BEQ", 1, 2, 1),   # not taken
                          encode_imm("LOADI", 3, 99),
                          encode_halt()])
        self.assertEqual(cpu.cores[0].registers.read(3), 99)

    def test_slti_if_else(self):
        from dualcore.isa import encode_imm, encode_slti, encode_halt
        cpu = run_single([encode_imm("LOADI", 1, 20),
                          encode_slti(2, 1, 30),   # 20 < 30 -> 1
                          encode_slti(3, 1, 10),   # 20 < 10 -> 0
                          encode_imm("LOADI", 4, 200),
                          encode_slti(5, 4, 5),    # unsigned: 200 < 5 -> 0
                          encode_halt()])
        r = cpu.cores[0].registers
        self.assertEqual((r.read(2), r.read(3), r.read(5)), (1, 0, 0))

    def test_while_loop_sum(self):
        """sum = 0; i = 1; while (i < 6) { sum += i; i++ }  ->  sum = 15."""
        from dualcore.isa import encode_imm, encode_r, encode_branch, encode_jump, encode_halt
        program = [
            encode_imm("LOADI", 0, 0),        # 0: R0 = 0 (comparison zero)
            encode_imm("LOADI", 1, 1),        # 1: i = 1
            encode_imm("LOADI", 2, 6),        # 2: limit
            encode_imm("LOADI", 3, 0),        # 3: sum = 0
            encode_imm("LOADI", 5, 1),        # 4: constant 1
            encode_r("SLT", 4, 1, 2),         # 5: top: R4 = i < limit
            encode_branch("BEQ", 4, 0, 3),    # 6: if not, exit to 10
            encode_r("ADD", 3, 3, 1),         # 7: sum += i
            encode_r("ADD", 1, 1, 5),         # 8: i += 1
            encode_jump(5),                   # 9: back to top
            encode_halt(),                    # 10
        ]
        cpu = run_single(program)
        r = cpu.cores[0].registers
        self.assertEqual((r.read(3), r.read(1)), (15, 6))
        self.assertEqual(cpu.cores[0].pc, 10)

    def test_backward_bne_countdown(self):
        from dualcore.isa import encode_imm, encode_r, encode_branch, encode_halt
        cpu = run_single([encode_imm("LOADI", 1, 3),
                          encode_imm("LOADI", 2, 1),
                          encode_imm("LOADI", 0, 0),
                          encode_r("SUB", 1, 1, 2),          # 3: R1 -= 1
                          encode_branch("BNE", 1, 0, -2),    # 4: loop to 3 while R1 != 0
                          encode_halt()])
        self.assertEqual(cpu.cores[0].registers.read(1), 0)
        self.assertEqual(cpu.cycles, 3 + 3 * 2 + 1)          # 3 setup + 3 loop passes + HALT

    def test_out_of_program_target_and_infinite_loop(self):
        from dualcore.isa import encode_branch, encode_jump, encode_halt
        from dualcore.core import Core
        from dualcore.memory import SharedMemory
        from dualcore.processor import DualCoreProcessor
        c = Core([encode_branch("BEQ", 0, 0, 7), encode_halt()])
        m = SharedMemory()
        c.step(m)
        self.assertEqual(c.pc, 8)
        with self.assertRaises(RuntimeError):
            c.step(m)
        cpu = DualCoreProcessor([encode_jump(0)], [encode_halt()])
        with self.assertRaises(RuntimeError):
            cpu.run(max_cycles=10)

    def test_r0_hard_wired_zero(self):
        """Instruction writes to R0 are discarded; R0 always reads 0 in programs."""
        from dualcore.isa import encode_imm, encode_r, encode_mem, encode_branch, encode_halt
        from dualcore.processor import DualCoreProcessor
        cpu = DualCoreProcessor([encode_imm("LOADI", 0, 77),     # discarded
                                 encode_imm("LOADI", 1, 5),
                                 encode_r("ADD", 0, 1, 1),       # discarded
                                 encode_mem("LOAD", 0, 9),       # discarded (mem[9] = 99)
                                 encode_r("ADD", 2, 0, 1),       # R2 = 0 + 5
                                 encode_branch("BEQ", 0, 0, 1),  # R0 == R0: always taken
                                 encode_imm("LOADI", 3, 1),      # skipped
                                 encode_halt()],
                                [encode_halt()])
        cpu.memory.write(9, 99)
        cpu.run(max_cycles=20)
        r = cpu.cores[0].registers
        self.assertEqual((r.read(0), r.read(2), r.read(3)), (0, 5, 0))

    def test_cross_core_spin_wait(self):
        """Core 1 polls shared memory until core 0's STORE becomes visible."""
        from dualcore.isa import encode_imm, encode_mem, encode_branch, encode_halt
        from dualcore.processor import DualCoreProcessor
        cpu = DualCoreProcessor(
            [encode_imm("LOADI", 1, 7),          # tick 1
             encode_mem("STORE", 1, 50),         # tick 2 (visible from tick 3)
             encode_halt()],
            [encode_imm("LOADI", 0, 0),          # tick 1
             encode_mem("LOAD", 1, 50),          # tick 2 -> 0, tick 4 -> 7
             encode_branch("BEQ", 1, 0, -2),     # tick 3 taken, tick 5 not taken
             encode_halt()])                     # tick 6
        cpu.run(max_cycles=50)
        self.assertEqual(cpu.cores[1].registers.read(1), 7)
        self.assertEqual(cpu.cycles, 6)
        self.assertTrue(all(core.halted for core in cpu.cores))
