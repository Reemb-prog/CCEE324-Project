"""Stage 02: all ALU functions and single core state changes."""
import unittest

class TestSingleCore(unittest.TestCase):
    def test_eight_operations_and_masking(self):
        from dualcore.alu import alu_execute as f
        self.assertEqual(f("ADD",250,10),4)
        self.assertEqual(f("SUB",3,5),254)
        self.assertEqual(f("AND",0xAA,0x0F),0x0A)
        self.assertEqual(f("OR",0xA0,0x0F),0xAF)
        self.assertEqual(f("XOR",0xF0,0x0F),0xFF)
        self.assertEqual(f("NOR",0xF0,0x0F),0x00)
        self.assertEqual(f("SLL",0x40,2),0x00)
        self.assertEqual(f("SRL",0x80,2),0x20)
        self.assertEqual(f("SLL",255,8),0)
        self.assertEqual(f("SRL",255,8),0)

    def test_bad_alu_inputs(self):
        from dualcore.alu import alu_execute as f
        for operation, a,b in (("MUL",1,2),("ADD",-1,1),("SUB",1,256)):
            with self.assertRaises(ValueError): f(operation,a,b)

    def test_single_core_pc_and_halt(self):
        from dualcore.isa import encode_r, encode_halt
        from dualcore.core import Core
        from dualcore.memory import SharedMemory
        c=Core([encode_r("ADD",3,1,2),encode_r("SUB",4,3,1),encode_halt()])
        m=SharedMemory()
        c.registers.write(1,200)
        c.registers.write(2,100)
        c.step(m)
        self.assertEqual((c.pc,c.registers.read(3)),(1,44))
        c.step(m)
        self.assertEqual((c.pc,c.registers.read(4)),(2,100))
        c.step(m)
        self.assertTrue(c.halted)
        self.assertEqual(c.pc,2)
        c.step(m)
        self.assertEqual(c.pc,2)

    def test_unterminated_program_fails(self):
        from dualcore.core import Core
        from dualcore.memory import SharedMemory
        c=Core([])
        with self.assertRaises(RuntimeError): c.step(SharedMemory())
