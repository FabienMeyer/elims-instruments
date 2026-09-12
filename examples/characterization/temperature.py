"""Demonstrate measured and controlled temperatures without real hardware."""

from __future__ import annotations

from dataclasses import dataclass

from elims_instruments.characterization import Temperature, TemperatureSpecification
from elims_instruments.utils import Limits
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.RED)


@dataclass
class SimulatedThermalChamber:
    """Small stand-in for a programmable thermal chamber."""

    setpoint: float = 25.0
    measured_temperature: float = 24.8
    enabled: bool = False

    def enable(self) -> None:
        """Enable the simulated chamber."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the simulated chamber."""
        self.enabled = False

    def set_temperature(self, value: float) -> None:
        """Apply a simulated chamber setpoint."""
        self.setpoint = value
        # A real chamber would approach its setpoint over time.
        self.measured_temperature = value - 0.2

    def measure_temperature(self) -> float:
        """Return the simulated chamber measurement."""
        return self.measured_temperature


def create_ambient_temperature() -> Temperature:
    """Create the fixed ambient-temperature measurement."""
    return Temperature(
        TemperatureSpecification(
            name="AMBIENT",
            temperature_limits=Limits(minimum=15, typical=25, maximum=35),
        ),
        temperature_getter=lambda: 23.6,
    )


def create_dut_temperature(
    chamber: SimulatedThermalChamber | None = None,
) -> Temperature:
    """Create the adjustable DUT temperature around a simulated chamber."""
    source = chamber or SimulatedThermalChamber()
    return Temperature(
        TemperatureSpecification(
            name="DUT",
            temperature_limits=Limits(
                absolute_minimum=-55,
                minimum=-40,
                typical=25,
                maximum=125,
                absolute_maximum=150,
            ),
        ),
        temperature_getter=source.measure_temperature,
        temperature_setter=source.set_temperature,
        enable=source.enable,
        disable=source.disable,
    )


def main() -> None:
    """Create temperature conditions and exercise their public operations."""
    LOGGER_HELPER.configure()
    ambient = create_ambient_temperature()
    dut_temperature = create_dut_temperature()

    dut_temperature.enable()
    dut_temperature.set_temperature(85)

    logger.info(
        "{}: adjustable={}, measured={:.1f} °C",
        ambient.name,
        ambient.is_adjustable,
        ambient.get_temperature(),
    )
    logger.info(
        "{}: setpoint={:.1f} °C, measured={:.1f} °C",
        dut_temperature.name,
        dut_temperature.setpoint,
        dut_temperature.get_temperature(),
    )
    logger.info(
        "Report: {}",
        dict(
            zip(
                dut_temperature.report_header(),
                dut_temperature.report_value(),
                strict=True,
            )
        ),
    )
    dut_temperature.disable()


if __name__ == "__main__":
    main()
