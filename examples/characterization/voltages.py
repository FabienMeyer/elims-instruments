"""Demonstrate an ordered collection of named voltage rails."""

from __future__ import annotations

from dataclasses import dataclass

from elims_instruments.characterization import (
    AdjustableVoltage,
    Voltages,
    VoltageSetPoints,
)
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.characterization.voltage import (
    create_adjustable_voltage,
    create_fixed_voltage,
)

logger = get_logger(__name__, LoggerHelper.Color.BLUE)


@dataclass(frozen=True, slots=True)
class SupplySetPoints(VoltageSetPoints):
    """Setpoints for one complete adjustable-voltage operating point."""

    vdda: int | float


def create_voltages() -> Voltages:
    """Create the ordered rails reused by the outer-sweep example."""
    vddd = create_fixed_voltage(name="VDDD", voltage=1.8)
    vdda = create_adjustable_voltage(name="VDDA", voltage=1.2)

    # Lower order values power up first. Power down uses the reverse order.
    return Voltages([(10, vddd), (20, vdda)])


def main() -> None:
    """Create, access, sequence, and report a voltage collection."""
    LOGGER_HELPER.configure()
    voltages = create_voltages()

    # Specification names are normalized for both access styles.
    assert voltages.vdda is voltages["vdda"]
    adjustable = voltages.vdda
    if isinstance(adjustable, AdjustableVoltage):
        operating_point = SupplySetPoints(vdda=1.25)
        adjustable.set_voltage(float(operating_point.vdda))
        logger.info("Setpoints: {}", operating_point.as_dict())

    voltages.power_up()
    logger.info("Report headers: {}", voltages.report_header())
    logger.info("Report values: {}", voltages.report_value())
    voltages.power_down()


if __name__ == "__main__":
    main()
