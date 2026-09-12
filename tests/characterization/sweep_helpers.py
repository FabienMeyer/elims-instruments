"""Shared DUT fixture for characterization sweep tests."""

from elims_instruments.bench import Dut
from elims_instruments.database import DutModel


class RegisterDut(Dut):
    """DUT exposing the register operation required by sweep tests."""

    def __init__(self) -> None:
        """Create a representative DUT and register-write history."""
        super().__init__(
            DutModel(
                id="dut-1",
                asset_tag="DUT-001",
                project="demo-project",
                corner="TT",
                die_revision="A",
            )
        )
        self.register_writes: list[tuple[str, int]] = []

    def get_id(self) -> str:
        """Return the database DUT ID."""
        return self.dut.id

    def write_register(self, register: str, value: int) -> None:
        """Record one representative register write."""
        self.register_writes.append((register, value))

    def reset(self) -> None:
        """Reset this representative DUT."""
        super().reset()
