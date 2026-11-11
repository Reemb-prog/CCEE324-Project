"""Terminal demo: two cores with private registers communicating through shared memory.

Run with:  python -m dualcore.demo
"""
from .isa import decode, encode_halt, encode_mem, encode_r
from .processor import DualCoreProcessor

MAILBOX = 100   # core 0 writes here, core 1 reads it
RESULT = 101    # core 1 writes its answer here


def describe(word: int) -> str:
    """Turn a machine word back into readable assembly."""
    d = decode(word)
    if d.mnemonic == "HALT":
        return "HALT"
    if d.mnemonic == "LOAD":
        return f"LOAD  R{d.rd}, [{d.address}]"
    if d.mnemonic == "STORE":
        return f"STORE R{d.rs}, [{d.address}]"
    return f"{d.mnemonic:<5} R{d.rd}, R{d.rs}, R{d.rt}"


def build_processor() -> DualCoreProcessor:
    # Core 0 (producer): compute 25 + 17 and publish it to memory.
    program0 = [
        encode_r("ADD", 3, 1, 2),          # R3 = R1 + R2 = 42
        encode_mem("STORE", 3, MAILBOX),   # mem[100] = R3 (committed at end of tick 2)
        encode_halt(),
    ]
    # Core 1 (consumer): does its own work, then reads core 0's value.
    program1 = [
        encode_r("SUB", 3, 1, 2),          # R3 = R1 - R2 = 2 (its own R3, not core 0's)
        encode_mem("LOAD", 4, MAILBOX),    # tick 2: same tick as the STORE -> still sees 0
        encode_mem("LOAD", 5, MAILBOX),    # tick 3: the store is now visible -> 42
        encode_r("ADD", 6, 5, 1),          # R6 = 42 + 5 = 47
        encode_mem("STORE", 6, RESULT),    # mem[101] = 47
        encode_halt(),
    ]
    cpu = DualCoreProcessor(program0, program1)
    # Starting register values are set directly (LOADI is only added at stage 05).
    cpu.cores[0].registers.write(1, 25)
    cpu.cores[0].registers.write(2, 17)
    cpu.cores[1].registers.write(1, 5)
    cpu.cores[1].registers.write(2, 3)
    return cpu


def show_event(core_id: int, core, event: dict) -> str:
    if event["mnemonic"] is None:
        return f"core{core_id}: (halted, PC stays {core.pc})"
    text = f"core{core_id}: PC={event['pc']}  {describe(event['word']):<20}"
    if "stored" in event:
        text += f" buffer mem[{event['address']}] <- {event['stored']}"
    elif "result" in event:
        text += f" R{event['rd']} <- {event['result']}"
    return text


def main() -> int:
    cpu = build_processor()
    print("Dual-core 8-bit CPU demo")
    for core_id, core in enumerate(cpu.cores):
        print(f"\nProgram {core_id}:")
        for index, word in enumerate(core.program):
            print(f"  {index}: {word:016b}  {describe(word)}")

    print("\nExecution (one instruction per active core per tick):")
    while not all(core.halted for core in cpu.cores):
        events = cpu.tick()
        print(f"tick {cpu.cycles}:")
        for core_id, (core, event) in enumerate(zip(cpu.cores, events)):
            print("   " + show_event(core_id, core, event))
        print(f"   end of tick: mem[{MAILBOX}]={cpu.memory.read(MAILBOX)}, "
              f"mem[{RESULT}]={cpu.memory.read(RESULT)}")

    print("\nFinal state:")
    for core_id, core in enumerate(cpu.cores):
        regs = " ".join(f"R{i}={v}" for i, v in enumerate(core.registers.snapshot()))
        print(f"  core{core_id}: PC={core.pc} halted={core.halted}  {regs}")
    print(f"  shared memory: mem[{MAILBOX}]={cpu.memory.read(MAILBOX)}, "
          f"mem[{RESULT}]={cpu.memory.read(RESULT)}")

    c0, c1 = cpu.cores
    checks = [
        ("core 0 stored 25 + 17 = 42 in shared memory", cpu.memory.read(MAILBOX) == 42),
        ("core 1 LOAD in the same tick as the STORE saw the old value 0", c1.registers.read(4) == 0),
        ("core 1 LOAD one tick later saw core 0's value 42", c1.registers.read(5) == 42),
        ("core 1 wrote 42 + 5 = 47 back to memory", cpu.memory.read(RESULT) == 47),
        ("R3 differs per core (private register files)", (c0.registers.read(3), c1.registers.read(3)) == (42, 2)),
        ("core 0 halted early at PC 2 while core 1 ran on", c0.pc == 2 and c1.pc == 5),
        ("both cores halted after 6 ticks", cpu.cycles == 6),
    ]
    print("\nVerification:")
    for text, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {text}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
