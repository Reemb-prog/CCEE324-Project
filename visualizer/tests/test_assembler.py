import unittest

from dualcore import demo
from dualcore.isa import (decode, encode_branch, encode_halt, encode_imm, encode_jump,
                          encode_mem, encode_r, encode_slti)
from visualizer.assembler import assemble, parse_memory


class AssemblerTests(unittest.TestCase):
    def test_every_instruction_form(self):
        text = """
            ADD R3, R1, R2
            sub r3, r1, r2
            AND R1,R2,R3
            OR R1, R2, R3
            XOR R1, R2, R3
            NOR R1, R2, R3
            SLL R1, R2, R3
            SRL R1, R2, R3
            SLT R4, R1, R2
            NOT R7, R6
            LOAD R4, [100]
            STORE R3, 0x64
            LOADI R1, 0b11001
            SLTI R3, R2, 20
            BEQ R4, R0, +3
            BNE R1, R0, -2
            J 4
            HALT
        """
        expected = [
            encode_r("ADD", 3, 1, 2), encode_r("SUB", 3, 1, 2), encode_r("AND", 1, 2, 3),
            encode_r("OR", 1, 2, 3), encode_r("XOR", 1, 2, 3), encode_r("NOR", 1, 2, 3),
            encode_r("SLL", 1, 2, 3), encode_r("SRL", 1, 2, 3), encode_r("SLT", 4, 1, 2),
            encode_r("NOT", 7, 6), encode_mem("LOAD", 4, 100), encode_mem("STORE", 3, 100),
            encode_imm("LOADI", 1, 25), encode_slti(3, 2, 20), encode_branch("BEQ", 4, 0, 3),
            encode_branch("BNE", 1, 0, -2), encode_jump(4), encode_halt(),
        ]
        program = assemble(text)
        self.assertEqual(program.words, expected)
        self.assertFalse(program.auto_halt)

    def test_round_trip_with_demo_describe(self):
        for cpu in (demo.build_processor(), demo.build_branch_processor()):
            for core in cpu.cores:
                text = "\n".join(demo.describe(word) for word in core.program)
                self.assertEqual(assemble(text).words, list(core.program))

    def test_labels_resolve_to_offsets_and_targets(self):
        program = assemble("""
            LOADI R1, 3
        loop: SUB R1, R1, R2   # label on the same line
            BNE R1, R0, loop
            J end
            NOP_NOT_USED_ABOVE: HALT
        end:
            HALT
        """)
        self.assertEqual(program.labels, {"loop": 1, "nop_not_used_above": 4, "end": 5})
        self.assertEqual(decode(program.words[2]).offset, -2)   # 1 - (2 + 1)
        self.assertEqual(decode(program.words[3]).address, 5)

    def test_auto_halt_and_line_numbers(self):
        program = assemble("# comment only\nLOADI R1, 5\n\nADD R2, R1, R1")
        self.assertTrue(program.auto_halt)
        self.assertEqual(program.lines, [2, 4, 0])
        self.assertEqual(decode(program.words[-1]).mnemonic, "HALT")

    def test_errors_name_the_line(self):
        cases = {
            "LOADI R1, 5\nADD R8, R1, R2": "line 2",
            "LOADI R1, 300": "line 1",
            "FOO R1": "unknown instruction",
            "BEQ R1, R0, nowhere": "expected a number",
            "BEQ R1, R0, 9": "offset",
            "ADD R1, R2": "3 operand",
            "x: HALT\nx: HALT": "defined twice",
            "": "empty",
        }
        for text, fragment in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as caught:
                    assemble(text)
                self.assertIn(fragment, str(caught.exception))

    def test_parse_memory(self):
        self.assertEqual(parse_memory("100=42\n# c\n0x10 = 0b11  ; note\n"), {100: 42, 16: 3})
        for bad in ("100", "300=1", "1=x"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_memory(bad)


if __name__ == "__main__":
    unittest.main()
