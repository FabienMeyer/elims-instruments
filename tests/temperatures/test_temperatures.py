"""Tests for characterization temperatures."""

from dataclasses import FrozenInstanceError
from math import isnan

import pytest
from loguru import logger

from elims_instruments.temperatures import Temperature, TemperatureSpecification
from elims_instruments.utils import Limits


def temperature_specification(
    name: str = "DUT",
    *,
    temperature_limits: Limits | None = None,
) -> TemperatureSpecification:
    """Build a representative temperature definition."""
    return TemperatureSpecification(
        name=name,
        temperature_limits=temperature_limits or Limits(typical=25),
    )


def test_temperature_specification_is_immutable() -> None:
    """A temperature definition is a safe reusable value object."""
    specification = temperature_specification()

    assert specification.name == "DUT"
    assert specification.temperature_limits == Limits(typical=25)
    with pytest.raises(FrozenInstanceError):
        specification.name = "AMBIENT"  # type: ignore[misc]


def test_temperature_initialization_has_no_hardware_side_effect() -> None:
    """Construction stores the nominal setpoint without applying it."""
    applied: list[float] = []
    temperature = Temperature(
        temperature_specification(),
        temperature_setter=applied.append,
    )

    assert applied == []
    assert temperature.name == "DUT"
    assert temperature.setpoint == 25
    assert temperature.is_adjustable
    assert temperature.temperature_limits == Limits(typical=25)


def test_temperature_measurement_is_optional() -> None:
    """Measurement returns NaN when no getter is configured."""
    temperature = Temperature(temperature_specification())

    assert isnan(temperature.get_temperature())


def test_temperature_control_is_optional() -> None:
    """Control operations fail clearly when no setter is configured."""
    temperature = Temperature(temperature_specification())

    assert not temperature.is_adjustable
    with pytest.raises(NotImplementedError, match="setter is not provided"):
        temperature.set_temperature(30)
    with pytest.raises(NotImplementedError, match="setter is not provided"):
        temperature.apply()
    assert temperature.setpoint == 25


def test_temperature_reads_configured_getter() -> None:
    """Measurement delegates to the configured instrument getter."""
    temperature = Temperature(
        temperature_specification(),
        temperature_getter=lambda: 24.8,
    )

    assert temperature.get_temperature() == 24.8


def test_temperature_applies_setpoints() -> None:
    """Explicit requests are validated and sent to the instrument."""
    applied: list[float] = []
    temperature = Temperature(
        temperature_specification(
            temperature_limits=Limits(
                typical=25,
                absolute_minimum=-55,
                minimum=-40,
                maximum=125,
                absolute_maximum=150,
            )
        ),
        temperature_setter=applied.append,
    )

    temperature.apply()
    temperature.set_temperature(85)

    assert applied == [25, 85]
    assert temperature.setpoint == 85


def test_temperature_rejects_unsafe_setpoint() -> None:
    """An out-of-range request never reaches the instrument."""
    applied: list[float] = []
    temperature = Temperature(
        temperature_specification(
            temperature_limits=Limits(typical=25, minimum=-40, maximum=125)
        ),
        temperature_setter=applied.append,
    )

    with pytest.raises(ValueError, match="outside the allowed range"):
        temperature.set_temperature(130)

    assert applied == []
    assert temperature.setpoint == 25


def test_temperature_logs_measurements_and_control_operations() -> None:
    """Temperature logging covers measurements and completed hardware writes."""
    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(message.record["message"]),
        level="DEBUG",
    )
    temperature = Temperature(
        temperature_specification(
            temperature_limits=Limits(typical=25, minimum=-40, maximum=125)
        ),
        temperature_getter=lambda: 24.8,
        temperature_setter=lambda _value: None,
    )

    try:
        temperature.get_temperature()
        temperature.set_temperature(85)
    finally:
        logger.remove(sink_id)

    assert len(messages) == 3
    assert messages[0].startswith(
        "Initialized Temperature temperature 'DUT' with nominal setpoint 25 "
    )
    assert messages[1].startswith("Measured temperature 'DUT': 24.8 ")
    assert messages[2].startswith("Set temperature 'DUT' to 85 ")


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_temperature_values_must_be_finite(value: float) -> None:
    """Non-finite temperatures are rejected before construction."""
    with pytest.raises(ValueError, match="finite"):
        temperature_specification(temperature_limits=Limits(typical=value))
