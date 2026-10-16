"""Register file: eight 8-bit registers R0..R7, private to one core."""

NUM_REGISTERS = 8


class RegisterFile:
    def __init__(self) -> None:
        # Each RegisterFile object owns its own list, so two cores never share registers.
        self._values = [0] * NUM_REGISTERS

    @staticmethod
    def _check_index(index: int) -> None:
        if type(index) is not int or not 0 <= index < NUM_REGISTERS:
            raise ValueError(f"register index must be 0..7, got {index!r}")

    def read(self, index: int) -> int:
        self._check_index(index)
        return self._values[index]

    def write(self, index: int, value: int) -> None:
        """Write an unsigned 8-bit value. Every register, including R0, is writable."""
        self._check_index(index)
        if type(value) is not int or not 0 <= value <= 0xFF:
            raise ValueError(f"register value must be 0..255, got {value!r}")
        self._values[index] = value

    def snapshot(self) -> tuple[int, ...]:
        return tuple(self._values)
