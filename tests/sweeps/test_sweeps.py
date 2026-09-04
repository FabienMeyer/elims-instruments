"""Tests for outer operating-condition and inner test-parameter sweeps."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

import pytest

from elims_instruments.database import DutModel
from elims_instruments.duts import Dut
from elims_instruments.sweeps import InnerMatrix, InnerSweep, OuterMatrix
from elims_instruments.temperatures import Temperature, TemperatureSpecification
from elims_instruments.utils import Limits
from elims_instruments.voltages import (
    AdjustableVoltage,
    FixedVoltage,
    VoltageSpecification,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


class RegisterDut(Dut):
    """DUT exposing the register operation required by the example test."""

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


@dataclass(frozen=True, slots=True)
class FrequencySweep(InnerSweep[RegisterDut]):
    """Arguments required by one example frequency test point."""

    frequency: int
    duty_cycle: float


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
        super().__init__(dut, iterations)
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
                dut=self.dut,
                iteration=iteration,
                frequency=frequency,
                duty_cycle=duty_cycle,
            )


def controlled_temperature(applied: list[tuple[str, float]]) -> Temperature:
    """Create a controllable temperature for an outer sweep."""
    return Temperature(
        TemperatureSpecification(
            "DUT",
            Limits(minimum=-40, typical=25, maximum=125),
        ),
        temperature_setter=lambda value: applied.append(("temperature", value)),
    )


def controlled_voltage(
    applied: list[tuple[str, float]],
    name: str = "VDD",
) -> AdjustableVoltage:
    """Create a controllable voltage for an outer sweep."""
    return AdjustableVoltage(
        VoltageSpecification(
            name,
            Limits(minimum=1.1, typical=1.2, maximum=1.3),
        ),
        voltage_setter=lambda value: applied.append((name, value)),
    )


def fixed_voltage(name: str, value: float) -> FixedVoltage:
    """Create a fixed rail included in an outer operating point."""
    return FixedVoltage(VoltageSpecification(name, Limits.exact(value)))


def test_outer_matrix_applies_conditions_before_each_test() -> None:
    """Every matrix point configures temperature then voltage before testing."""
    applied: list[tuple[str, float]] = []
    tested: list[tuple[float, list[str]]] = []
    dut = RegisterDut()
    temperature = controlled_temperature(applied)
    vdd = controlled_voltage(applied, "VDD")
    vio = controlled_voltage(applied, "VIO")
    ground = fixed_voltage("GND", 0.0)
    matrix = OuterMatrix(
        dut,
        [(temperature, [-40, 25])],
        [
            {vdd: [1.1], vio: [1.3], ground: [0.0]},
            {vio: [1.1], vdd: [1.3], ground: [0.0]},
        ],
    )

    for sweep in matrix:
        assert sweep.dut is dut
        sweep.set_temperature()
        sweep.set_voltages()
        assert sweep.temperature is not None
        tested.append(
            (sweep.temperature[1], [voltage.name for voltage in sweep.voltages])
        )
    next(iter(matrix)).dut.write_register("OPERATING_MODE", 1)

    assert tested == [
        (-40.0, ["VDD", "VIO", "GND"]),
        (-40.0, ["VIO", "VDD", "GND"]),
        (25.0, ["VDD", "VIO", "GND"]),
        (25.0, ["VIO", "VDD", "GND"]),
    ]
    assert applied == [
        ("temperature", -40.0),
        ("VDD", 1.1),
        ("VIO", 1.3),
        ("temperature", -40.0),
        ("VIO", 1.1),
        ("VDD", 1.3),
        ("temperature", 25.0),
        ("VDD", 1.1),
        ("VIO", 1.3),
        ("temperature", 25.0),
        ("VIO", 1.1),
        ("VDD", 1.3),
    ]
    assert dut.register_writes == [("OPERATING_MODE", 1)]


def test_iterating_outer_matrix_does_not_touch_hardware() -> None:
    """A caller can inspect matrix points without applying them."""
    applied: list[tuple[str, float]] = []
    matrix = OuterMatrix(
        RegisterDut(),
        [(controlled_temperature(applied), [25])],
        [{controlled_voltage(applied): [1.2]}],
    )

    sweep = next(iter(matrix))

    assert sweep.temperature is not None
    assert sweep.temperature[1] == 25.0
    assert tuple(sweep.voltages.values()) == (1.2,)
    assert applied == []


def test_outer_matrix_validates_controller_and_setpoints() -> None:
    """Invalid matrices fail without sending partial hardware commands."""
    applied: list[tuple[str, float]] = []
    with pytest.raises(ValueError, match="outside the allowed range"):
        OuterMatrix(
            RegisterDut(),
            [(controlled_temperature(applied), [25])],
            [{controlled_voltage(applied): [1.0]}],
        )
    with pytest.raises(ValueError, match="at least one temperature"):
        OuterMatrix(
            RegisterDut(),
            [],
            [{controlled_voltage(applied): [1.2]}],
        )
    assert applied == []


def test_inner_matrix_supports_multiple_test_arguments() -> None:
    """A typed sweep subtype can carry every argument required by its test."""
    dut = RegisterDut()
    sweeps = list(FrequencyMatrix(dut, 2, [1_000_000, 2_000_000], [0.4, 0.6]))

    assert all(sweep.dut is dut for sweep in sweeps)
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


@pytest.mark.parametrize(
    "iterations",
    [0, -1],
)
def test_inner_matrix_rejects_invalid_iterations(iterations: int) -> None:
    """Inner matrices require a positive iteration count."""
    with pytest.raises(ValueError, match="iterations must be at least one"):
        FrequencyMatrix(RegisterDut(), iterations, [1_000_000], [0.5])
