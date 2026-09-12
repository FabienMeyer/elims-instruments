"""Tests for ordered collections of voltage rails."""

import pytest
from tests.characterization.voltage_helpers import rail_spec

from elims_instruments.characterization import AdjustableVoltage, FixedVoltage, Voltages


def test_voltages_builds_lookup_and_ordered_views() -> None:
    """The collection supports named access and power-ordered reports."""
    vdda = AdjustableVoltage(
        rail_spec("VDDA"),
        voltage_getter=lambda: 1.19,
        voltage_setter=lambda _value: None,
    )
    vddd = FixedVoltage(rail_spec("VDDD"), voltage_getter=lambda: 1.79)

    voltages = Voltages([(20, vdda), (10, vddd)])

    assert voltages.vdda is vdda
    assert voltages["vdda"] is vdda
    assert voltages.report_header() == [
        "vddd_actual",
        "vdda_target",
        "vdda_actual",
    ]
    assert voltages.report_value() == ["1.79", "1.2", "1.19"]


def test_voltages_rejects_duplicate_names_and_orders() -> None:
    """Names and sequence positions uniquely identify collection entries."""
    vdda = FixedVoltage(rail_spec("VDDA"))
    duplicate_vdda = FixedVoltage(rail_spec("vdda"))
    vddd = FixedVoltage(rail_spec("VDDD"))

    with pytest.raises(ValueError, match="Duplicate voltage name"):
        Voltages([(10, vdda), (20, duplicate_vdda)])
    with pytest.raises(ValueError, match="Duplicate voltage order"):
        Voltages([(10, vdda), (10, vddd)])


def test_voltages_power_up_and_down_in_sequence() -> None:
    """Collection power control follows the configured rail order."""
    events: list[str] = []
    vddd = FixedVoltage(
        rail_spec("VDDD"),
        enable=lambda: events.append("enable vddd"),
        disable=lambda: events.append("disable vddd"),
    )
    vdda = AdjustableVoltage(
        rail_spec("VDDA"),
        voltage_setter=lambda _value: None,
        enable=lambda: events.append("enable vdda"),
        disable=lambda: events.append("disable vdda"),
    )
    voltages = Voltages([(20, vdda), (10, vddd)])

    voltages.power_up()
    voltages.power_down()

    assert events == [
        "enable vddd",
        "enable vdda",
        "disable vdda",
        "disable vddd",
    ]
