"""Define characterization parameters for one exact DUT revision."""

from __future__ import annotations

from elims_instruments.characterization import (
    ProjectRevisionSpecifications,
    TemperatureSpecification,
    VoltageSpecification,
)
from elims_instruments.utils import Limits
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.MAGENTA)

ADJUSTABLE_SUPPLY_NAME = "vdda"
FIXED_SUPPLY_NAME = "vddd"
DUT_TEMPERATURE_NAME = "DUT"


def create_revision_specifications() -> ProjectRevisionSpecifications:
    """Create the electrical and thermal limits for revision A0R1."""
    return ProjectRevisionSpecifications(
        die_revision="A",
        metal_revision=0,
        package_revision="R1",
        voltage_specifications=(
            VoltageSpecification(
                name=ADJUSTABLE_SUPPLY_NAME,
                voltage_limits=Limits(
                    minimum=1.10,
                    typical=1.20,
                    maximum=1.30,
                ),
                current_limits=Limits(
                    minimum=0.0,
                    typical=0.05,
                    maximum=0.10,
                ),
            ),
            VoltageSpecification(
                name=FIXED_SUPPLY_NAME,
                voltage_limits=Limits.exact(1.8),
            ),
        ),
        temperature_specifications=(
            TemperatureSpecification(
                name=DUT_TEMPERATURE_NAME,
                temperature_limits=Limits(
                    absolute_minimum=-55,
                    minimum=-40,
                    typical=25,
                    maximum=125,
                    absolute_maximum=150,
                ),
            ),
        ),
    )


def voltage_specification_for(
    specifications: ProjectRevisionSpecifications,
    name: str,
) -> VoltageSpecification:
    """Return one named voltage specification from a revision profile."""
    normalized_name = name.strip().casefold()
    for specification in specifications.voltage_specifications:
        if specification.name == normalized_name:
            return specification
    raise LookupError(f"Voltage specification not found: {name}")


def temperature_specification_for(
    specifications: ProjectRevisionSpecifications,
    name: str,
) -> TemperatureSpecification:
    """Return one named temperature specification from a revision profile."""
    normalized_name = name.strip().casefold()
    for specification in specifications.temperature_specifications:
        if specification.name.strip().casefold() == normalized_name:
            return specification
    raise LookupError(f"Temperature specification not found: {name}")


def main() -> None:
    """Build a revision profile and display its normalized parameters."""
    LOGGER_HELPER.configure()
    specifications = create_revision_specifications()

    logger.info(
        "Revision: {}{}{}",
        specifications.die_revision,
        specifications.metal_revision,
        specifications.package_revision,
    )
    for voltage in specifications.voltage_specifications:
        logger.info("Voltage {}: {}", voltage.name, voltage.voltage_limits)
    for temperature in specifications.temperature_specifications:
        logger.info(
            "Temperature {}: {}",
            temperature.name,
            temperature.temperature_limits,
        )


if __name__ == "__main__":
    main()

