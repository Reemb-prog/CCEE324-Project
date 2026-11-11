"""Shared data memory: 256 bytes, addresses 0..255, each holding 0..255."""

MEMORY_SIZE = 256


class SharedMemory:
    def __init__(self) -> None:
        self._cells = [0] * MEMORY_SIZE

    @staticmethod
    def _check_address(address: int) -> None:
        if type(address) is not int or not 0 <= address < MEMORY_SIZE:
            raise ValueError(f"memory address must be 0..255, got {address!r}")

    def read(self, address: int) -> int:
        self._check_address(address)
        return self._cells[address]

    def write(self, address: int, value: int) -> None:
        self._check_address(address)
        if type(value) is not int or not 0 <= value <= 0xFF:
            raise ValueError(f"memory value must be 0..255, got {value!r}")
        self._cells[address] = value

    def snapshot(self) -> tuple[int, ...]:
        return tuple(self._cells)


class _TickMemoryPort:
    """One core's view of memory during a single processor tick.

    Reads see the pre-tick snapshot; writes are only recorded, so the
    processor can commit them at the end of the tick (see docs/ISA.md).
    """

    def __init__(self, snapshot: tuple[int, ...]) -> None:
        self._snapshot = snapshot
        self.pending: list[tuple[int, int]] = []

    def read(self, address: int) -> int:
        SharedMemory._check_address(address)
        return self._snapshot[address]

    def write(self, address: int, value: int) -> None:
        SharedMemory._check_address(address)
        if type(value) is not int or not 0 <= value <= 0xFF:
            raise ValueError(f"memory value must be 0..255, got {value!r}")
        self.pending.append((address, value))
