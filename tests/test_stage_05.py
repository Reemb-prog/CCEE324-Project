"""Stage 05: optional immediate and unary logic operations."""
import unittest

class TestBonus(unittest.TestCase):
    def test_encode_and_execute(self):
        from dualcore.isa import encode_imm,encode_r,decode,encode_halt
        from dualcore.alu import alu_execute
        from dualcore.core import Core
        from dualcore.memory import SharedMemory
        loadi=encode_imm("LOADI",1,255)
        notr=encode_r("NOT",2,1)
        self.assertEqual(loadi,(10<<12)|(1<<9)|(255<<1))
        self.assertEqual(notr,(11<<12)|(2<<9)|(1<<6))
        self.assertEqual((decode(loadi).mnemonic,decode(loadi).immediate),("LOADI",255))
        self.assertEqual(decode(notr).mnemonic,"NOT")
        self.assertEqual(alu_execute("NOT",0x0F),0xF0)
        c=Core([loadi,notr,encode_halt()]); m=SharedMemory()
        c.step(m);c.step(m);c.step(m)
        self.assertEqual((c.registers.read(1),c.registers.read(2)),(255,0))

    def test_bonus_invalid(self):
        from dualcore.isa import encode_imm,encode_r,decode
        with self.assertRaises(ValueError): encode_imm("LOADI",1,256)
        with self.assertRaises(ValueError): encode_r("NOT",2,1,1)
        with self.assertRaises(ValueError): decode((11<<12)|(2<<9)|(1<<6)|1)
