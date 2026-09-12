"""Demonstrate a test-specific inner sweep within each outer condition."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from elims_instruments.characterization import InnerMatrix, InnerSweep
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.bench_setup.dut import ExampleDut, create_example_dut
from examples.characterization.outer_sweep import MAIN_BLOCK, create_outer_matrix

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

logger = get_logger(__name__, LoggerHelper.Color.MAGENTA)
SUB_BLOCK = "bandgap"


@dataclass(frozen=True, slots=True)
class BandgapMeasurement:
    """One normalized bandgap result produced at a sweep frequency."""

    name: str
    frequency_hz: int
    unit: str
    result: float


BANDGAP_MEASUREMENTS = (
    BandgapMeasurement("iref", 1_000_000, "uA", 0.311),
    BandgapMeasurement("vref", 2_000_000, "mV", 1.1),
)


class BandgapMatrix(InnerMatrix[ExampleDut]):
    """Generate every iteration and normalized bandgap measurement."""

    def __init__(
        self,
        dut: ExampleDut,
        iterations: int,
        measurements: Sequence[BandgapMeasurement] = BANDGAP_MEASUREMENTS,
        *,
        main_block: str = MAIN_BLOCK,
        sub_block: str = SUB_BLOCK,
    ) -> None:
        """Store the bandgap measurements and their sweep frequencies."""
        super().__init__(f"{main_block}-{sub_block}", dut, iterations)
        self.measurements = tuple(measurements)

    def __iter__(self) -> Iterator[BandgapSweep]:
        """Yield every bandgap result for every requested iteration."""
        for iteration, measurement in product(
            self.iterations,
            self.measurements,
        ):
            yield BandgapSweep(
                test_id=self.test_id,
                dut=self.dut,
                iteration=iteration,
                measurement=measurement,
            )


@dataclass(frozen=True, slots=True)
class BandgapSweep(InnerSweep[ExampleDut]):
    """One bandgap result at one input frequency."""

    measurement: BandgapMeasurement

    def get_test_id(self) -> str:
        """Return the complete ID for this bandgap result."""
        return f"{self.test_id}-{self.measurement.name}"

    def report_header(self) -> list[str]:
        """Return the columns describing this inner point."""
        return ["iteration", "frequency_hz"]

    def report_value(self) -> list[str]:
        """Return this inner point in report-column order."""
        return [str(self.iteration), str(self.measurement.frequency_hz)]

    def run(self) -> tuple[str, Sequence[str]]:
        """Return the result using the shared unit and result columns."""
        return self.get_test_id(), [
            self.measurement.unit,
            str(self.measurement.result),
        ]


def main() -> None:
    """Run every inner test point at every outer operating condition."""
    LOGGER_HELPER.configure()
    dut = create_example_dut()
    for outer_sweep in create_outer_matrix():
        outer_sweep.set_temperature()
        outer_sweep.enable_temperature()
        outer_sweep.set_voltages()
        outer_sweep.power_up()

        try:
            inner_matrix = BandgapMatrix(
                dut=dut,
                iterations=2,
                main_block=outer_sweep.get_test_id(),
                sub_block=SUB_BLOCK,
            )
            for inner_sweep in inner_matrix:
                inner_sweep.reset()
                test_id, measurements = inner_sweep.run()
                headers = [
                    "test_id",
                    *outer_sweep.report_header(),
                    *inner_sweep.report_header(),
                    "result_unit",
                    "result",
                ]
                values = [
                    test_id,
                    *outer_sweep.report_value(),
                    *inner_sweep.report_value(),
                    *measurements,
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
