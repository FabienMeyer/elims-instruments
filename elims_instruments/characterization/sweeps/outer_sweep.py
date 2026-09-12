"""Outer sweep orchestration for test operating conditions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from elims_instruments.characterization.voltages import AdjustableVoltage, Voltages

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from elims_instruments.characterization.temperatures import Temperature
    from elims_instruments.characterization.voltages import VoltageSetPoints


class OuterMatrix:
    """Create every temperature and voltage operating point for a test."""

    def __init__(
        self,
        test_id: str,
        temperature: Temperature | None,
        temperature_setpoints: Sequence[int | float | None],
        voltages: Voltages,
        voltage_setpoints: Sequence[VoltageSetPoints],
    ) -> None:
        """Store the DUT and validate the controlled operating conditions."""
        if not test_id.strip():
            raise ValueError("Outer matrix test_id must not be empty")
        self.test_id = test_id
        self.temperature = temperature
        self.temperature_setpoints = tuple(temperature_setpoints)
        self.voltages = voltages
        self.voltage_setpoints = tuple(voltage_setpoints)

    def __iter__(self) -> Iterator[OuterSweep]:
        """Yield the Cartesian product without changing hardware state."""
        for temperature_setpoint, voltage_setpoint in product(
            self.temperature_setpoints,
            self.voltage_setpoints,
        ):
            yield OuterSweep(
                test_id=self.test_id,
                temperature=self.temperature,
                temperature_setpoint=temperature_setpoint,
                voltages=self.voltages,
                voltage_setpoints=voltage_setpoint,
            )


@dataclass(frozen=True, slots=True)
class OuterSweep:
    """One operating point that controls test temperature and voltage."""

    test_id: str
    temperature: Temperature | None
    temperature_setpoint: int | float | None
    voltages: Voltages
    voltage_setpoints: VoltageSetPoints

    def report_header(self) -> list[str]:
        """Return temperature and voltage headers for this operating point."""
        temperature_headers = (
            ["t_target", "t_actual"]
            if self.temperature is None
            else self.temperature.report_header()
        )
        return [*temperature_headers, *self.voltages.report_header()]

    def report_value(self) -> list[str]:
        """Return measured operating-condition values in header order."""
        if self.temperature is None:
            values = ["", ""]
        else:
            values = [
                str(self.temperature_setpoint),
                str(self.temperature.get_temperature()),
            ]
        return [*values, *self.voltages.report_value()]

    def get_test_id(self) -> str:
        """Return the main test ID for this operating point."""
        return self.test_id

    def set_temperature(self) -> None:
        """Apply the temperature setpoint to the DUT."""
        if self.temperature is not None and self.temperature_setpoint is not None:
            self.temperature.set_temperature(self.temperature_setpoint)

    def enable_temperature(self) -> None:
        """Enable the configured temperature source."""
        if self.temperature is not None:
            self.temperature.enable()

    def disable_temperature(self) -> None:
        """Disable the configured temperature source."""
        if self.temperature is not None:
            self.temperature.disable()

    def set_voltages(self) -> None:
        """Apply the voltage setpoints to the DUT."""
        for name, setpoint in self.voltage_setpoints.as_dict().items():
            voltage = self.voltages[name]
            if not isinstance(voltage, AdjustableVoltage):  # pragma: no cover
                raise TypeError(f"Voltage {name!r} is not adjustable")
            voltage.set_voltage(float(setpoint))

    def power_up(self) -> None:
        """Enable all voltage sources for the DUT."""
        self.voltages.power_up()

    def power_down(self) -> None:
        """Disable all voltage sources for the DUT."""
        self.voltages.power_down()
