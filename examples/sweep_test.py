"""Runnable nested-sweep example using simulated DUT and hardware callbacks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from elims_instruments.database import DutModel
from elims_instruments.duts import Dut
from elims_instruments.sweeps import (
    InnerMatrix,
    InnerSweep,
    OuterMatrix,
    OuterSweep,
)
from elims_instruments.temperatures import Temperature, TemperatureSpecification
from elims_instruments.utils import Limits
from elims_instruments.voltages import (
    AdjustableVoltage,
    FixedVoltage,
    VoltageSpecification,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


class ClockDut(Dut):
    """Small DUT driver illustrating register access from both sweep layers."""

    def __init__(self) -> None:
        """Create a simulated DUT with an in-memory register map."""
        super().__init__(
            DutModel(
                id="example-dut",
                asset_tag="DUT-001",
                project="demo-project",
                corner="TT",
                die_revision="A",
            )
        )
        self.registers: dict[str, int] = {}

    def get_id(self) -> str:
        """Return the persistent DUT ID."""
        return self.dut.id

    def reset(self) -> None:
        """Reset all simulated DUT registers."""
        super().reset()
        self.registers.clear()

    def write_register(self, name: str, value: int) -> None:
        """Write one simulated DUT register."""
        self.registers[name] = value


@dataclass(frozen=True, slots=True)
class ClockSweep(InnerSweep[ClockDut]):
    """Arguments for one clock measurement."""

    frequency_hz: int
    divider: int


class ClockMatrix(InnerMatrix[ClockDut]):
    """Cartesian matrix of clock frequencies, dividers, and iterations."""

    def __init__(
        self,
        dut: ClockDut,
        iterations: int,
        frequencies_hz: Sequence[int],
        dividers: Sequence[int],
    ) -> None:
        """Store the DUT and test-specific parameter sequences."""
        super().__init__(dut, iterations)
        self.frequencies_hz = tuple(frequencies_hz)
        self.dividers = tuple(dividers)

    def __iter__(self) -> Iterator[ClockSweep]:
        """Yield every test-specific parameter combination."""
        for iteration, frequency_hz, divider in product(
            self.iterations,
            self.frequencies_hz,
            self.dividers,
        ):
            yield ClockSweep(
                dut=self.dut,
                iteration=iteration,
                frequency_hz=frequency_hz,
                divider=divider,
            )


def run_clock_test(
    outer: OuterSweep[ClockDut],
    inner: ClockSweep,
) -> str:
    """Configure DUT registers and return one simulated measurement record."""
    inner.dut.write_register("CLOCK_FREQUENCY_HZ", inner.frequency_hz)
    inner.dut.write_register("CLOCK_DIVIDER", inner.divider)
    temperature = None if outer.temperature is None else outer.temperature[1]
    voltages = {voltage.name: value for voltage, value in outer.voltages.items()}
    return (
        f"T={temperature} deg C, rails={voltages}, iteration={inner.iteration}, "
        f"registers={inner.dut.registers}"
    )


def main() -> None:
    """Run the nested matrix without connecting to physical hardware."""
    dut = ClockDut()
    applied_conditions: list[str] = []
    temperature = Temperature(
        TemperatureSpecification(
            "DUT",
            Limits(minimum=-40, typical=25, maximum=125),
        ),
        temperature_setter=lambda value: applied_conditions.append(f"T={value}"),
    )
    vdd_io = AdjustableVoltage(
        VoltageSpecification(
            "VDD_IO",
            Limits(minimum=1.7, typical=1.8, maximum=1.9),
        ),
        voltage_setter=lambda value: applied_conditions.append(f"VDD_IO={value}"),
    )
    vdd_core = AdjustableVoltage(
        VoltageSpecification(
            "VDD_CORE",
            Limits(minimum=1.1, typical=1.2, maximum=1.3),
        ),
        voltage_setter=lambda value: applied_conditions.append(f"VDD_CORE={value}"),
    )
    ground = FixedVoltage(
        VoltageSpecification("GND", Limits.exact(0.0)),
    )

    outer_matrix = OuterMatrix(
        dut,
        temperatures=[(temperature, [-40, 25])],
        voltages=[
            {
                vdd_io: [1.8],  # DUT-specific application order: IO before core.
                vdd_core: [1.1, 1.2],
                ground: [0.0],
            }
        ],
    )
    inner_matrix = ClockMatrix(
        dut,
        iterations=2,
        frequencies_hz=[1_000_000, 2_000_000],
        dividers=[1, 2],
    )

    results: list[str] = []
    for outer in outer_matrix:
        outer.reset()
        outer.set_temperature()
        outer.set_voltages()
        outer.dut.write_register("OPERATING_POINT_READY", 1)
        for inner in inner_matrix:
            results.append(run_clock_test(outer, inner))

    print(f"Applied operating conditions: {applied_conditions}")
    print(f"Completed {len(results)} measurements")
    for result in results:
        print(result)


if __name__ == "__main__":
    main()
