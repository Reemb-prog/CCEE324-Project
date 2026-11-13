import random
import unittest

from dualcore import demo
from dualcore.isa import (ALU_OPS, encode_branch, encode_halt, encode_imm, encode_jump,
                          encode_mem, encode_r, encode_slti)
from visualizer.trace import derive_wires, run_trace


def _programs(cpu):
    return [list(core.program) for core in cpu.cores]


class TraceTests(unittest.TestCase):
    def test_scripted_demo_matches_terminal_demo(self):
        trace = run_trace(*_programs(demo.build_processor()))
        self.assertIsNone(trace["error"])
        self.assertEqual(len(trace["ticks"]), 10)
        mem = trace["final"]["memory"]
        self.assertEqual((mem[100], mem[101], mem[102]), (42, 47, 208))
        # Tick 4: core 0 STOREs 42 while core 1 LOADs the same address and sees 0.
        tick4 = trace["ticks"][3]["wires"]
        self.assertEqual((tick4[0]["mnemonic"], tick4[0]["mem_write_data"]), ("STORE", 42))
        self.assertEqual((tick4[1]["mnemonic"], tick4[1]["mem_read_data"]), ("LOAD", 0))

    def test_branch_demo_matches_terminal_demo(self):
        trace = run_trace(*_programs(demo.build_branch_processor()))
        self.assertIsNone(trace["error"])
        mem = trace["final"]["memory"]
        self.assertEqual((mem[60], mem[61], mem[62]), (15, 1, 1))
        taken = [w["taken"] for t in trace["ticks"] for w in t["wires"] if w.get("taken") is not None]
        self.assertIn(True, taken)
        self.assertIn(False, taken)

    def test_store_wires(self):
        w = derive_wires(0, False, (encode_mem("STORE", 3, 100),), (0, 0, 0, 9, 0, 0, 0, 0),
                         tuple([0] * 256))
        self.assertEqual((w["read_reg1"], w["alu_a"], w["alu_b"], w["alu_result"]), (0, 0, 100, 100))
        self.assertEqual((w["read_reg2"], w["read_data2"], w["mem_write_data"]), (3, 9, 9))
        self.assertIsNone(w["write_reg"])
        self.assertEqual(w["signals"]["ALUSrc"], "1")

    def test_r0_write_is_discarded(self):
        trace = run_trace([encode_imm("LOADI", 0, 7), encode_halt()], [encode_halt()])
        w = trace["ticks"][0]["wires"][0]
        self.assertTrue(w["r0_discard"])
        self.assertEqual(trace["final"]["regs"][0][0], 0)

    def test_same_address_conflict_detected(self):
        p0 = [encode_imm("LOADI", 1, 5), encode_mem("STORE", 1, 9), encode_halt()]
        p1 = [encode_imm("LOADI", 1, 6), encode_mem("STORE", 1, 9), encode_halt()]
        trace = run_trace(p0, p1)
        self.assertTrue(trace["ticks"][1]["conflict"])
        self.assertEqual(trace["final"]["memory"][9], 6)   # core 1 wins

    def test_endless_loop_and_missing_halt_are_reported(self):
        self.assertIn("Stopped after 20 ticks",
                      run_trace([encode_jump(0)], [encode_halt()], max_ticks=20)["error"])
        error = run_trace([encode_jump(5)], [encode_halt()])["error"]
        self.assertIn("outside the program", error)

    def test_random_programs_agree_with_simulator(self):
        rng = random.Random(324)
        reg = lambda: rng.randrange(8)
        for _ in range(150):
            programs = []
            for _core in range(2):
                n = rng.randrange(3, 14)
                words = []
                for pc in range(n):
                    kind = rng.randrange(8)
                    if kind == 0:
                        words.append(encode_r(rng.choice(ALU_OPS + ("SLT",)), reg(), reg(), reg()))
                    elif kind == 1:
                        words.append(encode_r("NOT", reg(), reg()))
                    elif kind == 2:
                        words.append(encode_mem("LOAD", reg(), rng.randrange(4)))
                    elif kind == 3:
                        words.append(encode_mem("STORE", reg(), rng.randrange(4)))
                    elif kind == 4:
                        words.append(encode_imm("LOADI", reg(), rng.randrange(256)))
                    elif kind == 5:
                        words.append(encode_slti(reg(), reg(), rng.randrange(64)))
                    elif kind == 6:   # forward-only branches keep programs terminating
                        words.append(encode_branch(rng.choice(("BEQ", "BNE")), reg(), reg(),
                                                   rng.randrange(0, min(7, n - pc - 1) + 1)))
                    else:
                        words.append(encode_jump(rng.randrange(pc + 1, n + 1)))
                words.append(encode_halt())
                programs.append(words)
            memory = {a: rng.randrange(256) for a in range(4)}
            trace = run_trace(*programs, memory=memory)   # raises TraceMismatch on disagreement
            self.assertIsNone(trace["error"])


if __name__ == "__main__":
    unittest.main()
