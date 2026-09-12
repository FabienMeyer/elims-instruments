"""Demonstrate a test-specific inner sweep within each outer condition."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from elims_instruments.characterization import InnerMatrix, InnerSweep
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.bench_setup.dut import ExampleDut
from examples.characterization.outer_sweep import create_outer_matrix

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

logger = get_logger(__name__, LoggerHelper.Color.MAGENTA)


@dataclass(frozen=True, slots=True)
class FrequencySweep(InnerSweep[ExampleDut]):
    """One test iteration at one input frequency."""

    frequency_hz: int

    def report_header(self) -> list[str]:
        """Return the columns describing this inner point."""
        return ["iteration", "frequency_hz"]

    def report_value(self) -> list[str]:
        """Return this inner point in report-column order."""
        return [str(self.iteration), str(self.frequency_hz)]


class FrequencyMatrix(InnerMatrix[ExampleDut]):
    """Generate every iteration and input-frequency combination."""

    def __init__(
        self,
        dut: ExampleDut,
        iterations: int,
        frequencies_hz: Sequence[int],
    ) -> None:
        """Store the test-specific frequency axis."""
        super().__init__(dut, iterations)
        self.frequencies_hz = tuple(frequencies_hz)

    def __iter__(self) -> Iterator[FrequencySweep]:
        """Yield all frequency points for every requested iteration."""
        for iteration, frequency_hz in product(
            self.iterations,
            self.frequencies_hz,
        ):
            yield FrequencySweep(
                dut=self.dut,
                iteration=iteration,
                frequency_hz=frequency_hz,
            )


def create_inner_matrix(dut: ExampleDut) -> FrequencyMatrix:
    """Create the inner test matrix reused by the report example."""
    return FrequencyMatrix(
        dut=dut,
        iterations=2,
        frequencies_hz=[1_000_000, 2_000_000],
    )


def measure_current(sweep: FrequencySweep) -> float:
    """Return a deterministic stand-in for one instrument measurement."""
    return sweep.frequency_hz / 1_000_000_000 + sweep.iteration / 10_000


def main() -> None:
    """Run every inner test point at every outer operating condition."""
    LOGGER_HELPER.configure()

    for outer_sweep in create_outer_matrix():
        outer_sweep.reset()
        outer_sweep.set_temperature()
        outer_sweep.enable_temperature()
        outer_sweep.set_voltages()
        outer_sweep.power_up()
        try:
            for inner_sweep in create_inner_matrix(outer_sweep.dut):
                inner_sweep.reset()
                headers = [
                    *outer_sweep.report_header(),
                    *inner_sweep.report_header(),
                    "measured_current_a",
                ]
                values = [
                    *outer_sweep.report_value(),
                    *inner_sweep.report_value(),
                    f"{measure_current(inner_sweep):.4f}",
                ]
                logger.info(
                    "Inner sweep: {}",
                    dict(zip(headers, values, strict=True)),
                )
        finally:
            outer_sweep.power_down()
            outer_sweep.disable_temperature()


if __name__ == "__main__":
    main()
