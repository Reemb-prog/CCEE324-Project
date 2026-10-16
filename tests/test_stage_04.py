"""Stage 04: shared memory and pre-tick visibility."""
import unittest

class TestSharedMemory(unittest.TestCase):
    def test_memory_bounds(self):
        from dualcore.memory import SharedMemory
        m=SharedMemory()
        self.assertEqual(len(m.snapshot()),256)
        m.write(255,255)
        self.assertEqual(m.read(255),255)
        for fn in (lambda:m.read(256),lambda:m.write(-1,0),lambda:m.write(1,256)):
            with self.assertRaises(ValueError):fn()

    def test_store_visible_next_tick(self):
        from dualcore.isa import encode_mem,encode_halt
        from dualcore.processor import DualCoreProcessor
        cpu=DualCoreProcessor(
            [encode_mem("STORE",1,10),encode_halt()],
            [encode_mem("LOAD",2,10),encode_mem("LOAD",3,10),encode_halt()]
        )
        cpu.memory.write(10,2)
        cpu.cores[0].registers.write(1,9)
        cpu.tick()
        self.assertEqual(cpu.cores[1].registers.read(2),2)
        self.assertEqual(cpu.memory.read(10),9)
        cpu.tick()
        self.assertEqual(cpu.cores[1].registers.read(3),9)
        cpu.run()
        self.assertTrue(all(core.halted for core in cpu.cores))

    def test_same_tick_conflict_last_core_wins(self):
        from dualcore.isa import encode_mem,encode_halt
        from dualcore.processor import DualCoreProcessor
        cpu=DualCoreProcessor(
            [encode_mem("STORE",1,7),encode_halt()],
            [encode_mem("STORE",1,7),encode_halt()]
        )
        cpu.cores[0].registers.write(1,17)
        cpu.cores[1].registers.write(1,33)
        cpu.tick()
        self.assertEqual(cpu.memory.read(7),33)
