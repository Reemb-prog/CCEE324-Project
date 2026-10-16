"""Stage 03: separate instruction streams, PCs, registers and HALT."""
import unittest

class TestTwoCores(unittest.TestCase):
    def test_independent_execution(self):
        from dualcore.isa import encode_r,encode_halt
        from dualcore.processor import DualCoreProcessor
        c=DualCoreProcessor(
            [encode_r("ADD",3,1,2),encode_halt()],
            [encode_r("XOR",3,1,2),encode_r("ADD",4,3,1),encode_halt()]
        )
        self.assertIsNot(c.cores[0].registers,c.cores[1].registers)
        self.assertIsNot(c.cores[0],c.cores[1])
        c.cores[0].registers.write(1,8)
        c.cores[0].registers.write(2,4)
        c.cores[1].registers.write(1,10)
        c.cores[1].registers.write(2,3)
        c.tick()
        self.assertEqual((c.cores[0].pc,c.cores[1].pc),(1,1))
        self.assertEqual((c.cores[0].registers.read(3),c.cores[1].registers.read(3)),(12,9))
        c.tick()
        self.assertTrue(c.cores[0].halted)
        self.assertFalse(c.cores[1].halted)
        self.assertEqual((c.cores[0].pc,c.cores[1].pc),(1,2))
        c.tick()
        self.assertTrue(c.cores[1].halted)
        self.assertEqual(c.cores[1].registers.read(4),19)
        self.assertEqual(c.cycles,3)

    def test_exhaustion_raises(self):
        from dualcore.isa import encode_r,encode_halt
        from dualcore.processor import DualCoreProcessor
        c=DualCoreProcessor([encode_r("ADD",0,0,0),encode_halt()], [encode_halt()])
        with self.assertRaises(RuntimeError): c.run(max_cycles=1)
