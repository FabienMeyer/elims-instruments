# Sweeps

Outer operating-condition matrices and test-specific inner matrices.

Both `OuterMatrix` and `InnerMatrix` receive the DUT. Every generated outer or
inner sweep retains its concrete DUT type, allowing either layer to configure
DUT state such as registers before a measurement.

Voltage configurations are dictionaries whose insertion order defines the
DUT-specific rail order:

```python
outer = OuterMatrix(
    dut,
    temperatures=[(thermal_controller, [-40, 25])],
    voltages=[
        {vdd_io: [1.8], vdd_core: [1.2], ground: [0.0]},
        {vdd_core: [1.1], vdd_io: [1.8], ground: [0.0]},
    ],
)

for sweep in outer:
    sweep.set_temperature()
    sweep.set_voltages()  # applies adjustable rails in dictionary order
```

An `AdjustableVoltage` is written; a `FixedVoltage` remains in the mapping as
part of the operating condition but requires no set operation.

Define a typed `InnerSweep` subclass for the arguments required by one test,
then make its matrix generic over that subtype:

```python
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product

from elims_instruments.sweeps import InnerMatrix, InnerSweep


@dataclass(frozen=True, slots=True)
class FrequencySweep(InnerSweep[ClockDut]):
    frequency: int
    duty_cycle: float


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

::: elims_instruments.sweeps
