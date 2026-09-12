# Sweeps

Outer operating-condition matrices and test-specific inner matrices.

`InnerMatrix` receives the DUT because inner tests may configure DUT state.
`OuterMatrix` contains only temperature and voltage operating conditions.

`Voltages` defines the DUT-specific rail order once. A project-specific
`VoltageSetPoints` dataclass defines each complete operating point; fixed rails do
not need setpoint fields:

```python
from dataclasses import dataclass

from elims_instruments.characterization import Voltages, VoltageSetPoints


@dataclass(frozen=True, slots=True)
class SupplySetPoints(VoltageSetPoints):
    vdd_io: int | float
    vdd_core: int | float

supplies = Voltages([
    (10, vdd_io),
    (20, vdd_core),
    (30, ground),
])

outer = OuterMatrix(
    temperature=thermal_controller,
    temperature_setpoints=[-40, 25],
    voltages=supplies,
    voltage_setpoints=[
        SupplySetPoints(vdd_io=1.8, vdd_core=1.2),
        SupplySetPoints(vdd_io=1.8, vdd_core=1.1),
    ],
)

for sweep in outer:
    sweep.set_temperature()
    sweep.set_voltages()  # applies adjustable rails in power-up order
```

An `AdjustableVoltage` is written; a `FixedVoltage` remains in `Voltages` for
power sequencing and reporting but requires no setpoint axis.

Define a typed `InnerSweep` subclass for the arguments required by one test,
then make its matrix generic over that subtype. Each sweep provides report
columns and returns measurement values from `run()`:

```python
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product

from elims_instruments.characterization import InnerMatrix, InnerSweep


@dataclass(frozen=True, slots=True)
class FrequencySweep(InnerSweep[ClockDut]):
    frequency: int
    duty_cycle: float

    def report_header(self) -> list[str]:
        return ["iteration", "frequency", "duty_cycle"]

    def report_value(self) -> list[str]:
        return [str(self.iteration), str(self.frequency), str(self.duty_cycle)]

    def run(self) -> list[str]:
        return ["0.0012"]


class FrequencyMatrix(InnerMatrix[ClockDut]):
    def __init__(self, dut: ClockDut, iterations: int) -> None:
        super().__init__(dut, iterations)

    def __iter__(self) -> Iterator[FrequencySweep]:
        for iteration, frequency, duty_cycle in product(
            self.iterations,
            (1_000_000, 2_000_000),
            (0.4, 0.6),
        ):
            yield FrequencySweep(self.dut, iteration, frequency, duty_cycle)
```

Every point retains the concrete DUT type, so test code can configure it
directly, for example `sweep.dut.write_register("CLOCK_DIVIDER", 4)`.

::: elims_instruments.characterization.sweeps
