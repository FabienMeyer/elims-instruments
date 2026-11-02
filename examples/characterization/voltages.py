"""Demonstrate an ordered collection of named voltage rails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from elims_instruments.characterization import (
    AdjustableVoltage,
    Voltages,
    VoltageSetPoints,
)
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.characterization.specifications import (
    ADJUSTABLE_SUPPLY_NAME,
    FIXED_SUPPLY_NAME,
    create_revision_specifications,
    voltage_specification_for,
)
from examples.characterization.voltage import (
    create_adjustable_voltage,
    create_fixed_voltage,
)

if TYPE_CHECKING:
    from elims_instruments.characterization import ProjectRevisionSpecifications

logger = get_logger(__name__, LoggerHelper.Color.BLUE)


@dataclass(frozen=True, slots=True)
class SupplySetPoints(VoltageSetPoints):
    """Setpoints for one complete adjustable-voltage operating point."""

    vdda: int | float


def create_supply_setpoints(
    specifications: ProjectRevisionSpecifications,
) -> tuple[SupplySetPoints, ...]:
    """Create boundary operating points from the revision's VDDA limits."""
    limits = voltage_specification_for(
        specifications,
        ADJUSTABLE_SUPPLY_NAME,
    ).voltage_limits
    if limits.minimum is None or limits.maximum is None:
        raise ValueError("VDDA requires minimum and maximum sweep limits")
    values = dict.fromkeys((limits.minimum, limits.maximum))
    return tuple(SupplySetPoints(vdda=value) for value in values)


def create_voltages(
    specifications: ProjectRevisionSpecifications | None = None,
) -> Voltages:
    """Create the ordered rails reused by the outer-sweep example."""
    profile = specifications or create_revision_specifications()
    vddd = create_fixed_voltage(
        voltage_specification_for(profile, FIXED_SUPPLY_NAME)
    )
    vdda = create_adjustable_voltage(
        voltage_specification_for(profile, ADJUSTABLE_SUPPLY_NAME)
    )

    # Lower order values power up first. Power down uses the reverse order.
    return Voltages([(10, vddd), (20, vdda)])


def main() -> None:
    """Create, access, sequence, and report a voltage collection."""
    LOGGER_HELPER.configure()
    specifications = create_revision_specifications()
    voltages = create_voltages(specifications)

    # Specification names are normalized for both access styles.
    assert voltages.vdda is voltages["vdda"]
    adjustable = voltages.vdda
    if isinstance(adjustable, AdjustableVoltage):
        operating_point = SupplySetPoints(
            vdda=voltage_specification_for(
                specifications,
                ADJUSTABLE_SUPPLY_NAME,
            ).voltage_limits.typical
        )
        adjustable.set_voltage(float(operating_point.vdda))
        logger.info("Setpoints: {}", operating_point.as_dict())

    voltages.power_up()
    logger.info("Report headers: {}", voltages.report_header())
    logger.info("Report values: {}", voltages.report_value())
    voltages.power_down()


if __name__ == "__main__":
    main()
