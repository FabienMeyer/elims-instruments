"""Outer sweep orchestration for test operating conditions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING, Generic, TypeVar

from elims_instruments.characterization.voltages import AdjustableVoltage, Voltages

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from elims_instruments.bench.duts import Dut
    from elims_instruments.characterization.temperatures import Temperature
    from elims_instruments.characterization.voltages import VoltageSetPoints

DutT = TypeVar("DutT", bound="Dut")


def _call_control_method(target: object, method_name: str, label: str) -> None:
    """Call an optional controller operation with a clear error when absent."""
    operation = getattr(target, method_name, None)
    if not callable(operation):
        raise NotImplementedError(f"{label} does not provide {method_name}()")
    operation()


class OuterMatrix(Generic[DutT]):
    """Create every temperature and voltage operating point for a test."""

    def __init__(
        self,
        dut: DutT,
        temperature: Temperature | None,
        temperature_setpoints: Sequence[int | float | None],
        voltages: Voltages,
        voltage_setpoints: Sequence[VoltageSetPoints],
    ) -> None:
        """Store the DUT and validate the controlled operating conditions."""
        self.dut = dut
        self.temperature = temperature
        self.temperature_setpoints = tuple(temperature_setpoints)
        self.voltages = voltages
        self.voltage_setpoints = tuple(voltage_setpoints)

    def __iter__(self) -> Iterator[OuterSweep[DutT]]:
        """Yield the Cartesian product without changing hardware state."""
        for temperature_setpoint, voltage_setpoint in product(
            self.temperature_setpoints,
            self.voltage_setpoints,
        ):
            yield OuterSweep(
                dut=self.dut,
                temperature=self.temperature,
                temperature_setpoint=temperature_setpoint,
                voltages=self.voltages,
                voltage_setpoints=voltage_setpoint,
            )


@dataclass(frozen=True, slots=True)
class OuterSweep(Generic[DutT]):
    """One operating point that controls test temperature and voltage."""

    dut: DutT
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

    def reset(self) -> None:
        """Reset the DUT to a known state."""
        self.dut.reset()
