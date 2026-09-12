"""Tests for test-specific inner sweeps."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

import pytest
from tests.characterization.sweep_helpers import RegisterDut

from elims_instruments.characterization import InnerMatrix, InnerSweep

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@dataclass(frozen=True, slots=True)
class FrequencySweep(InnerSweep[RegisterDut]):
    """Arguments required by one example frequency test point."""

    frequency: int
    duty_cycle: float

    def get_test_id(self) -> str:
        return f"{self.test_id}-{self.iteration}"


class FrequencyMatrix(InnerMatrix[RegisterDut]):
    """Example test matrix with two test-specific arguments."""

    def __init__(
        self,
        dut: RegisterDut,
        iterations: int,
        frequencies: Sequence[int],
        duty_cycles: Sequence[float],
    ) -> None:
        """Store the frequency test axes."""
        super().__init__("frequency", dut, iterations)
        self.frequencies = frequencies
        self.duty_cycles = duty_cycles

    def __iter__(self) -> Iterator[FrequencySweep]:
        """Yield every iteration, frequency, and duty-cycle combination."""
        for iteration, frequency, duty_cycle in product(
            self.iterations,
            self.frequencies,
            self.duty_cycles,
        ):
            yield FrequencySweep(
                test_id=self.test_id,
                dut=self.dut,
                iteration=iteration,
                frequency=frequency,
                duty_cycle=duty_cycle,
            )


def test_inner_matrix_supports_multiple_test_arguments() -> None:
    """A typed sweep subtype can carry every argument required by its test."""
    dut = RegisterDut()
    sweeps = list(FrequencyMatrix(dut, 2, [1_000_000, 2_000_000], [0.4, 0.6]))

    assert all(sweep.dut is dut for sweep in sweeps)
    assert [sweep.get_test_id() for sweep in sweeps] == [
        "frequency-1",
        "frequency-1",
        "frequency-1",
        "frequency-1",
        "frequency-2",
        "frequency-2",
        "frequency-2",
        "frequency-2",
    ]
    assert [
        (sweep.iteration, sweep.frequency, sweep.duty_cycle) for sweep in sweeps
    ] == [
        (1, 1_000_000, 0.4),
        (1, 1_000_000, 0.6),
        (1, 2_000_000, 0.4),
        (1, 2_000_000, 0.6),
        (2, 1_000_000, 0.4),
        (2, 1_000_000, 0.6),
        (2, 2_000_000, 0.4),
        (2, 2_000_000, 0.6),
    ]
    sweeps[0].dut.write_register("CLOCK_DIVIDER", 4)
    assert dut.register_writes == [("CLOCK_DIVIDER", 4)]


@pytest.mark.parametrize("iterations", [0, -1])
def test_inner_matrix_rejects_invalid_iterations(iterations: int) -> None:
    """Inner matrices require a positive iteration count."""
    with pytest.raises(ValueError, match="iterations must be at least one"):
        FrequencyMatrix(RegisterDut(), iterations, [1_000_000], [0.5])
