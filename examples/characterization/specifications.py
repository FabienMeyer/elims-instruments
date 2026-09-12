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


def create_revision_specifications() -> ProjectRevisionSpecifications:
    """Create the electrical and thermal limits for revision A0R1."""
    return ProjectRevisionSpecifications(
        die_revision="A",
        metal_revision=0,
        package_revision="R1",
        voltage_specifications=(
            VoltageSpecification(
                name="VDD",
                voltage_limits=Limits(
                    minimum=1.14,
                    typical=1.20,
                    maximum=1.26,
                ),
            ),
        ),
        temperature_specifications=(
            TemperatureSpecification(
                name="DUT",
                temperature_limits=Limits(
                    minimum=-40,
                    typical=25,
                    maximum=125,
                ),
            ),
        ),
    )


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

