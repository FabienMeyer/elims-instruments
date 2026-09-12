"""Tests for board voltage rails."""

from dataclasses import FrozenInstanceError

import pytest
from loguru import logger
from tests.characterization.voltage_helpers import rail_spec

from elims_instruments.characterization import (
    AdjustableVoltage,
    FixedVoltage,
)
from elims_instruments.utils import Limits


def test_voltage_specification_is_immutable() -> None:
    """A rail definition is a safe reusable value object."""
    spec = rail_spec("VDD_CORE", current_limits=Limits(typical=0.5))

    assert spec.name == "vdd_core"
    assert spec.voltage_limits == Limits(typical=1.2)
    assert spec.current_limits == Limits(typical=0.5)
    with pytest.raises(FrozenInstanceError):
        spec.name = "VDD_IO"  # type: ignore[misc]


@pytest.mark.parametrize(
    "name",
    ["", "_", "-", "VDD@CORE", "VDD.CORE"],
)
def test_voltage_specification_rejects_invalid_names(name: str) -> None:
    """Empty names and unsupported symbols are rejected."""
    with pytest.raises(ValueError, match="ASCII letters and numbers"):
        rail_spec(name)


@pytest.mark.parametrize(
    ("name", "normalized"),
    [
        ("VDD", "vdd"),
        (" VDD CORE ", "vdd_core"),
        ("VDD-CORE", "vdd_core"),
        ("VDD__CORE", "vdd_core"),
    ],
)
def test_voltage_specification_normalizes_names(name: str, normalized: str) -> None:
    """Rail names become lowercase identifiers suitable for lookup."""
    assert rail_spec(name).name == normalized


def test_voltage_specification_name_must_be_a_string() -> None:
    """Runtime validation rejects non-string rail names clearly."""
    with pytest.raises(TypeError, match="Voltage name must be a string"):
        rail_spec(1)  # type: ignore[arg-type]


def test_voltage_logs_initialization() -> None:
    """A voltage reports its concrete type and validated rail details."""
    records: list[dict[str, object]] = []
    sink_id = logger.add(lambda message: records.append(message.record), level="DEBUG")

    try:
        FixedVoltage(rail_spec("VDD_IO", voltage_limits=Limits(typical=3.3)))
    finally:
        logger.remove(sink_id)

    record = records[-1]
    assert record["message"] == (
        "Initialized FixedVoltage voltage 'vdd_io' with nominal setpoint 3.3 V"
    )
    assert record["extra"] == {
        "source": "elims_instruments.characterization.voltages.abstract",
        "source_color": "blue",
    }


def test_voltage_logs_measurements_and_control_operations() -> None:
    """Voltage logging focuses on measurements and completed hardware writes."""
    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(message.record["message"]),
        level="DEBUG",
    )
    voltage = AdjustableVoltage(
        rail_spec(
            voltage_limits=Limits(typical=1.2, minimum=0.8, maximum=1.4),
            current_limits=Limits(
                typical=0.5,
                minimum=0.1,
                maximum=1.0,
            ),
        ),
        voltage_getter=lambda: 1.19,
        current_getter=lambda: 0.025,
        voltage_setter=lambda _value: None,
        current_limit_setter=lambda _value: None,
    )

    try:
        assert voltage.setpoint == 1.2
        voltage.setpoint = 1.1
        assert voltage.get_voltage() == 1.19
        assert voltage.get_current() == 0.025
        assert voltage.is_adjustable
        voltage.set_voltage(1.0)
        voltage.set_current_limit(0.8)
    finally:
        logger.remove(sink_id)

    assert messages == [
        "Initialized AdjustableVoltage voltage 'vdd_core' with nominal setpoint 1.2 V",
        "Measured voltage 'vdd_core': 1.19 V",
        "Measured current for voltage 'vdd_core': 0.025 A",
        "Set voltage 'vdd_core' to 1.0 V",
        "Set current limit for voltage 'vdd_core' to 0.8 A",
    ]


def test_fixed_voltage_describes_board_rail() -> None:
    """A fixed rail exposes its configured voltage without hardware I/O."""
    voltage = FixedVoltage(rail_spec("VDD_IO", voltage_limits=Limits(typical=3.3)))

    assert voltage.name == "vdd_io"
    assert voltage.setpoint == 3.3
    assert isinstance(voltage, FixedVoltage)
    assert not voltage.is_adjustable
    assert voltage.voltage_limits == Limits(typical=3.3)
    assert not hasattr(voltage, "limits")
    assert not hasattr(voltage, "minimum_voltage")
    assert not hasattr(voltage, "maximum_voltage")
    assert not hasattr(voltage, "absolute_minimum_voltage")
    assert not hasattr(voltage, "absolute_maximum_voltage")
    assert not hasattr(voltage, "set_voltage")
    assert not hasattr(voltage, "apply")
    with pytest.raises(AttributeError):
        voltage.setpoint = 3.2  # type: ignore[misc]


def test_fixed_voltage_reports_only_its_actual_value() -> None:
    """A fixed rail has no configurable target report column."""
    voltage = FixedVoltage(rail_spec("VDD IO"), voltage_getter=lambda: 3.29)

    assert voltage.report_header() == ["vdd_io_actual"]
    assert voltage.report_value() == ["3.29"]


def test_adjustable_voltage_reports_target_and_actual_values() -> None:
    """An adjustable rail reports its setpoint before its measurement."""
    voltage = AdjustableVoltage(
        rail_spec("VDD CORE"),
        voltage_getter=lambda: 1.19,
        voltage_setter=lambda _value: None,
    )

    assert voltage.report_header() == ["vdd_core_target", "vdd_core_actual"]
    assert voltage.report_value() == ["1.2", "1.19"]


def test_voltage_power_control_requires_callbacks() -> None:
    """Unsupported source controls fail with rail-specific messages."""
    voltage = FixedVoltage(rail_spec("VDDD"))

    with pytest.raises(NotImplementedError, match="Cannot enable voltage 'vddd'"):
        voltage.enable()
    with pytest.raises(NotImplementedError, match="Cannot disable voltage 'vddd'"):
        voltage.disable()


def test_adjustable_voltage_applies_setpoints() -> None:
    """An adjustable rail sends only explicit requests to its instrument."""
    applied: list[float] = []
    voltage = AdjustableVoltage(
        rail_spec(
            voltage_limits=Limits(
                typical=1.2,
                absolute_minimum=0.7,
                minimum=0.8,
                maximum=1.4,
                absolute_maximum=1.5,
            )
        ),
        voltage_setter=applied.append,
    )

    assert applied == []
    assert isinstance(voltage, AdjustableVoltage)
    assert voltage.is_adjustable
    voltage.set_voltage(1.1)

    assert applied == [1.1]
    assert voltage.setpoint == 1.1


def test_adjustable_voltage_rejects_unsafe_setpoint() -> None:
    """An out-of-range request never reaches the instrument."""
    applied: list[float] = []
    voltage = AdjustableVoltage(
        rail_spec(
            voltage_limits=Limits(
                typical=1.2,
                absolute_minimum=0.7,
                minimum=0.8,
                maximum=1.4,
                absolute_maximum=1.5,
            )
        ),
        voltage_setter=applied.append,
    )

    with pytest.raises(ValueError, match="outside the allowed range"):
        voltage.set_voltage(1.5)

    assert applied == []
    assert voltage.setpoint == 1.2


def test_failed_voltage_write_preserves_previous_setpoint() -> None:
    """A hardware failure does not make the cached state report success."""
    voltage = AdjustableVoltage(
        rail_spec(voltage_limits=Limits(minimum=0.8, typical=1.2, maximum=1.4)),
        voltage_setter=lambda _value: (_ for _ in ()).throw(OSError("write failed")),
    )

    with pytest.raises(OSError, match="write failed"):
        voltage.set_voltage(1.1)

    assert voltage.setpoint == 1.2


def test_measurements_require_getters() -> None:
    """Unavailable measurements fail explicitly instead of returning NaN."""
    voltage = FixedVoltage(rail_spec())

    with pytest.raises(NotImplementedError, match="Cannot measure voltage"):
        voltage.get_voltage()
    with pytest.raises(NotImplementedError, match="Cannot measure current"):
        voltage.get_current()


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_voltage_values_must_be_finite(value: float) -> None:
    """Non-finite values are rejected before defining or driving a rail."""
    with pytest.raises(ValueError, match="finite"):
        FixedVoltage(rail_spec("VDD", voltage_limits=Limits(typical=value)))


def test_adjustable_voltage_validates_current_limit() -> None:
    """An invalid current limit never reaches the instrument."""
    applied: list[float] = []
    voltage = AdjustableVoltage(
        rail_spec(current_limits=Limits(typical=0.5, minimum=0.1, maximum=1.0)),
        voltage_setter=lambda _value: None,
        current_limit_setter=applied.append,
    )

    voltage.set_current_limit(0.8)
    assert voltage.current_limit_setpoint == 0.8
    with pytest.raises(ValueError, match="outside the allowed range"):
        voltage.set_current_limit(1.1)

    assert applied == [0.8]


def test_current_limit_requires_configured_limits() -> None:
    """Current-limit control requires an explicit safe operating range."""
    voltage = AdjustableVoltage(
        rail_spec(),
        voltage_setter=lambda _value: None,
        current_limit_setter=lambda _value: None,
    )

    with pytest.raises(ValueError, match="limits are not configured"):
        voltage.set_current_limit(0.5)
