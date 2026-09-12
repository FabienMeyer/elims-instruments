"""Tests for outer operating-condition sweeps."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from tests.characterization.sweep_helpers import RegisterDut

from elims_instruments.characterization import (
    AdjustableVoltage,
    FixedVoltage,
    OuterMatrix,
    Temperature,
    TemperatureSpecification,
    Voltages,
    VoltageSetPoints,
    VoltageSpecification,
)
from elims_instruments.utils import Limits


@dataclass(frozen=True, slots=True)
class VddSetPoints(VoltageSetPoints):
    """One-rail voltage operating point."""

    vdd: int | float


@dataclass(frozen=True, slots=True)
class VddVioSetPoints(VoltageSetPoints):
    """Two-rail voltage operating point."""

    vdd: int | float
    vio: int | float


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
        "operating-point",
        temperature,
        [-40, 25],
        Voltages([(10, vdd), (20, vio), (30, ground)]),
        [
            VddVioSetPoints(vdd=1.1, vio=1.3),
            VddVioSetPoints(vdd=1.3, vio=1.1),
        ],
    )

    for sweep in matrix:
        sweep.set_temperature()
        sweep.set_voltages()
        assert sweep.temperature is not None
        tested.append(
            (
                sweep.temperature_setpoint,
                [voltage.name for voltage in sweep.voltages.values()],
            )
        )
    dut.write_register("OPERATING_MODE", 1)

    assert tested == [
        (-40.0, ["vdd", "vio", "gnd"]),
        (-40.0, ["vdd", "vio", "gnd"]),
        (25.0, ["vdd", "vio", "gnd"]),
        (25.0, ["vdd", "vio", "gnd"]),
    ]
    assert applied == [
        ("temperature", -40.0),
        ("VDD", 1.1),
        ("VIO", 1.3),
        ("temperature", -40.0),
        ("VDD", 1.3),
        ("VIO", 1.1),
        ("temperature", 25.0),
        ("VDD", 1.1),
        ("VIO", 1.3),
        ("temperature", 25.0),
        ("VDD", 1.3),
        ("VIO", 1.1),
    ]
    assert dut.register_writes == [("OPERATING_MODE", 1)]


def test_iterating_outer_matrix_does_not_touch_hardware() -> None:
    """A caller can inspect matrix points without applying them."""
    applied: list[tuple[str, float]] = []
    matrix = OuterMatrix(
        "operating-point",
        controlled_temperature(applied),
        [25],
        Voltages([(10, controlled_voltage(applied))]),
        [VddSetPoints(vdd=1.2)],
    )

    sweep = next(iter(matrix))

    assert sweep.get_test_id() == "operating-point"
    assert sweep.temperature is not None
    assert sweep.temperature_setpoint == 25.0
    assert tuple(sweep.voltage_setpoints.as_dict().values()) == (1.2,)
    assert applied == []


def test_outer_sweep_validates_setpoints_before_hardware_writes() -> None:
    """Invalid operating points fail without sending hardware commands."""
    applied: list[tuple[str, float]] = []
    voltage_matrix = OuterMatrix(
        "operating-point",
        None,
        [None],
        Voltages([(10, controlled_voltage(applied))]),
        [VddSetPoints(vdd=1.0)],
    )
    with pytest.raises(ValueError, match="outside the allowed range"):
        next(iter(voltage_matrix)).set_voltages()

    temperature_matrix = OuterMatrix(
        "operating-point",
        controlled_temperature(applied),
        [130],
        Voltages([(10, controlled_voltage(applied))]),
        [VddSetPoints(vdd=1.2)],
    )
    with pytest.raises(ValueError, match="outside the allowed range"):
        next(iter(temperature_matrix)).set_temperature()
    assert applied == []


def test_outer_sweep_reports_through_voltage_collection() -> None:
    """Operating-point reports follow the collection's power order."""
    temperature = Temperature(
        TemperatureSpecification("DUT", Limits(typical=25)),
        temperature_getter=lambda: 24.8,
    )
    vdd = AdjustableVoltage(
        VoltageSpecification("VDD", Limits(typical=1.2)),
        voltage_getter=lambda: 1.19,
        voltage_setter=lambda _value: None,
    )
    ground = FixedVoltage(
        VoltageSpecification("GND", Limits.exact(0.0)),
        voltage_getter=lambda: 0.0,
    )
    sweep = next(
        iter(
            OuterMatrix(
                "operating-point",
                temperature,
                [25],
                Voltages([(10, ground), (20, vdd)]),
                [VddSetPoints(vdd=1.2)],
            )
        )
    )

    assert sweep.report_header() == [
        "t_target",
        "t_actual",
        "gnd_actual",
        "vdd_target",
        "vdd_actual",
    ]
    assert sweep.report_value() == ["25", "24.8", "0.0", "1.2", "1.19"]
