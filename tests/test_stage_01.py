"""Stage 01: machine encoding, independent register-file semantics, control."""
import unittest

class TestDatapath(unittest.TestCase):
    def test_r_format(self):
        from dualcore.isa import encode_r, decode
        word = encode_r("ADD", 1, 2, 3)
        self.assertEqual(word, (1 << 9) | (2 << 6) | (3 << 3))
        d=decode(word)
        self.assertEqual((d.opcode, d.mnemonic, d.rd, d.rs, d.rt),(0,"ADD",1,2,3))
        self.assertEqual(decode(encode_r("SRL",7,6,5)).mnemonic,"SRL")

    def test_all_required_opcodes(self):
        from dualcore.isa import encode_r, decode
        ops=["ADD","SUB","AND","OR","XOR","NOR","SLL","SRL"]
        for opcode,name in enumerate(ops):
            with self.subTest(name=name):
                d=decode(encode_r(name,2,3,4))
                self.assertEqual((d.opcode,d.mnemonic),(opcode,name))

    def test_m_and_halt(self):
        from dualcore.isa import encode_mem, encode_halt, decode
        w=encode_mem("STORE",3,240)
        self.assertEqual(w,(9<<12)|(3<<9)|(240<<1))
        d=decode(w)
        self.assertEqual((d.mnemonic,d.rs,d.address),("STORE",3,240))
        d=decode(encode_mem("LOAD",4,255))
        self.assertEqual((d.mnemonic,d.rd,d.address),("LOAD",4,255))
        self.assertEqual((encode_halt(),decode(encode_halt()).mnemonic),(0xF000,"HALT"))

    def test_invalid_encoding(self):
        from dualcore.isa import decode, encode_r, encode_mem
        for word in (-1,65536, 0xC000,0xF001, 0x0001,0x8001):
            with self.subTest(word=word), self.assertRaises(ValueError): decode(word)
        with self.assertRaises(ValueError): encode_r("ADD",8,0,0)
        with self.assertRaises(ValueError): encode_mem("LOAD",0,256)

    def test_register_file(self):
        from dualcore.registers import RegisterFile
        a,b=RegisterFile(),RegisterFile()
        self.assertEqual(a.snapshot(),(0,)*8)
        a.write(0,255)
        a.write(7,21)
        self.assertEqual((a.read(0),a.read(7),b.read(7)),(255,21,0))
        for fn in (lambda:a.read(8),lambda:a.write(-1,0),lambda:a.write(1,256)):
            with self.assertRaises(ValueError): fn()

    def test_control_signals(self):
        from dualcore.control import ControlUnit
        from dualcore.isa import decode, encode_r, encode_mem, encode_halt
        c=ControlUnit()
        a=c.signals(decode(encode_r("XOR",3,1,2)))
        self.assertTrue(a.reg_write)
        self.assertFalse(a.mem_read)
        self.assertFalse(a.mem_write)
        self.assertEqual(a.alu_op,"XOR")
        l=c.signals(decode(encode_mem("LOAD",2,1)))
        self.assertTrue(l.mem_read and l.reg_write)
        s=c.signals(decode(encode_mem("STORE",2,1)))
        self.assertTrue(s.mem_write)
        self.assertFalse(s.reg_write)
        h=c.signals(decode(encode_halt()))
        self.assertFalse(h.reg_write or h.mem_read or h.mem_write)
