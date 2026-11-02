"""Demonstrate fixed and adjustable voltage rails without real hardware."""

from __future__ import annotations

from dataclasses import dataclass

from elims_instruments.characterization import (
    AdjustableVoltage,
    FixedVoltage,
    VoltageSpecification,
)
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.characterization.specifications import (
    ADJUSTABLE_SUPPLY_NAME,
    FIXED_SUPPLY_NAME,
    create_revision_specifications,
    voltage_specification_for,
)

logger = get_logger(__name__, LoggerHelper.Color.BLUE)


@dataclass
class SimulatedPowerSupply:
    """Small stand-in for a programmable laboratory power supply."""

    voltage: float
    current_limit: float = 0.0
    enabled: bool = False

    def enable(self) -> None:
        """Enable the simulated output."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the simulated output."""
        self.enabled = False

    def set_voltage(self, value: float) -> None:
        """Apply a simulated output-voltage setting."""
        self.voltage = value

    def set_current_limit(self, value: float) -> None:
        """Apply a simulated current-limit setting."""
        self.current_limit = value

    def measure_voltage(self) -> float:
        """Return the simulated measured output voltage."""
        return self.voltage if self.enabled else 0.0

    def measure_current(self) -> float:
        """Return a deterministic simulated load current."""
        return min(self.voltage / 100.0, self.current_limit)


def create_adjustable_voltage(
    specification: VoltageSpecification | None = None,
    *,
    supply: SimulatedPowerSupply | None = None,
) -> AdjustableVoltage:
    """Create an adjustable rail backed by a simulated power supply."""
    rail = specification or voltage_specification_for(
        create_revision_specifications(),
        ADJUSTABLE_SUPPLY_NAME,
    )
    current_limit = (
        0.0
        if rail.current_limits is None
        else float(rail.current_limits.typical)
    )
    source = supply or SimulatedPowerSupply(
        voltage=float(rail.voltage_limits.typical),
        current_limit=current_limit,
    )
    return AdjustableVoltage(
        rail,
        voltage_setter=source.set_voltage,
        current_limit_setter=source.set_current_limit,
        voltage_getter=source.measure_voltage,
        current_getter=source.measure_current,
        enable=source.enable,
        disable=source.disable,
    )


def create_fixed_voltage(
    specification: VoltageSpecification | None = None,
    *,
    supply: SimulatedPowerSupply | None = None,
) -> FixedVoltage:
    """Create a fixed rail backed by a simulated power supply."""
    rail = specification or voltage_specification_for(
        create_revision_specifications(),
        FIXED_SUPPLY_NAME,
    )
    limits = rail.voltage_limits
    if any(
        value is not None and value != limits.typical
        for value in (
            limits.absolute_minimum,
            limits.minimum,
            limits.maximum,
            limits.absolute_maximum,
        )
    ):
        raise ValueError("A fixed voltage specification must use exact limits")
    source = supply or SimulatedPowerSupply(voltage=float(limits.typical))
    return FixedVoltage(
        rail,
        voltage_getter=source.measure_voltage,
        enable=source.enable,
        disable=source.disable,
    )


def main() -> None:
    """Create voltage rails and exercise their public operations."""
    LOGGER_HELPER.configure()
    vdda = create_adjustable_voltage()
    vddd = create_fixed_voltage()

    vdda.enable()
    vddd.enable()
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
    logger.info(
        "Adjustable report: {}",
        dict(
            zip(
                vdda.report_header(),
                vdda.report_value(),
                strict=True,
            )
        ),
    )
    logger.info(
        "Fixed report: {}",
        dict(
            zip(
                vddd.report_header(),
                vddd.report_value(),
                strict=True,
            )
        ),
    )
    vdda.disable()
    vddd.disable()


if __name__ == "__main__":
    main()
