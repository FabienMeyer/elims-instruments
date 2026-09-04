"""Demonstrate fixed and adjustable voltage rails without real hardware."""

from __future__ import annotations

from dataclasses import dataclass

from elims_instruments.utils import Limits
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from elims_instruments.voltages import (
    AdjustableVoltage,
    FixedVoltage,
    VoltageSpecification,
)

logger = get_logger(__name__, LoggerHelper.Color.BLUE)


@dataclass
class SimulatedPowerSupply:
    """Small stand-in for a programmable laboratory power supply."""

    voltage: float = 0.0
    current_limit: float = 0.0

    def set_voltage(self, value: float) -> None:
        """Apply a simulated output-voltage setting."""
        self.voltage = value

    def set_current_limit(self, value: float) -> None:
        """Apply a simulated current-limit setting."""
        self.current_limit = value

    def measure_voltage(self) -> float:
        """Return the simulated measured output voltage."""
        return self.voltage

    def measure_current(self) -> float:
        """Return a deterministic simulated load current."""
        return min(self.voltage / 100.0, self.current_limit)


def main() -> None:
    """Create voltage rails and exercise their public operations."""
    LOGGER_HELPER.configure()
    supply = SimulatedPowerSupply()

    vdda = AdjustableVoltage(
        VoltageSpecification(
            name="VDDA",
            voltage_limits=Limits(minimum=1.0, typical=1.20, maximum=1.4),
            current_limits=Limits(minimum=0.0, typical=0.05, maximum=0.10),
        ),
        voltage_setter=supply.set_voltage,
        current_limit_setter=supply.set_current_limit,
        voltage_getter=supply.measure_voltage,
        current_getter=supply.measure_current,
    )
    vddd = FixedVoltage(
        VoltageSpecification(
            name="VDDD", voltage_limits=Limits(minimum=0.8, typical=1.0, maximum=1.2)
        ),
        voltage_getter=supply.measure_voltage,
    )

    vdda.set_current_limit(0.08)
    vdda.set_voltage(1.22)

    logger.info(
        "{}: setpoint={:.2f} V, measured={:.2f} V, current={:.3f} A",
        vdda.name,
        vdda.setpoint,
        vdda.get_voltage(),
        vdda.get_current(),
    )
    logger.info(
        "{}: fixed={}, measured={:.2f} V",
        vddd.name,
        not vddd.is_adjustable,
        vddd.get_voltage(),
    )


if __name__ == "__main__":
    main()
