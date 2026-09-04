"""Outer sweep orchestration for test operating conditions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING, Generic, TypeVar

from elims_instruments.voltages import AdjustableVoltage, FixedVoltage

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from elims_instruments.duts import Dut
    from elims_instruments.temperatures import Temperature

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
        temperatures: Sequence[tuple[Temperature, list[int | float]] | None],
        voltages: Sequence[dict[AdjustableVoltage | FixedVoltage, list[int | float]]],
    ) -> None:
        """Store the DUT and validate the controlled operating conditions."""
        self.dut = dut
        self.temperatures = self._validate_temperatures(temperatures)
        self.voltages = self._validate_voltages(voltages)

    def _validate_temperatures(
        self,
        values: Sequence[tuple[Temperature, list[int | float]] | None],
    ) -> tuple[tuple[Temperature, float] | None, ...]:
        """Expand and validate all temperature setpoint sequences."""
        if not values:
            raise ValueError("Outer matrix requires at least one temperature")
        temperatures: list[tuple[Temperature, float] | None] = []
        for condition in values:
            if condition is None:
                temperatures.append(None)
                continue
            temperature, setpoints = condition
            if not setpoints:
                raise ValueError("Temperature sweep sequences cannot be empty")
            for setpoint in setpoints:
                temperatures.append(
                    (
                        temperature,
                        float(
                            temperature.temperature_limits.validate(
                                setpoint,
                                label="outer sweep temperature",
                            )
                        ),
                    )
                )
        return tuple(temperatures)

    def _validate_voltages(
        self,
        values: Sequence[dict[AdjustableVoltage | FixedVoltage, list[int | float]]],
    ) -> tuple[dict[AdjustableVoltage | FixedVoltage, float], ...]:
        """Expand voltage products while preserving DUT-specific rail order."""
        if not values:
            raise ValueError("Outer matrix requires at least one voltage configuration")
        configurations: list[dict[AdjustableVoltage | FixedVoltage, float]] = []
        for configuration in values:
            if not configuration:
                raise ValueError("Outer voltage configurations cannot be empty")
            rails = tuple(configuration)
            setpoint_axes: list[tuple[float, ...]] = []
            for voltage, setpoints in configuration.items():
                if not setpoints:
                    raise ValueError(
                        f"Voltage sweep sequence {voltage.name!r} cannot be empty"
                    )
                setpoint_axes.append(
                    tuple(
                        float(
                            voltage.voltage_limits.validate(
                                setpoint,
                                label=f"outer sweep voltage {voltage.name!r}",
                            )
                        )
                        for setpoint in setpoints
                    )
                )
            for combination in product(*setpoint_axes):
                configurations.append(dict(zip(rails, combination, strict=True)))
        return tuple(configurations)

    def __iter__(self) -> Iterator[OuterSweep[DutT]]:
        """Yield the Cartesian product without changing hardware state."""
        for temperature, voltages in product(self.temperatures, self.voltages):
            yield OuterSweep(
                dut=self.dut,
                temperature=temperature,
                voltages=dict(voltages),
            )


@dataclass(frozen=True, slots=True)
class OuterSweep(Generic[DutT]):
    """One operating point that controls test temperature and voltage."""

    dut: DutT
    temperature: tuple[Temperature, float] | None
    voltages: dict[AdjustableVoltage | FixedVoltage, float]

    def set_temperature(self) -> None:
        """Apply the temperature setpoint to the DUT."""
        if self.temperature is not None:
            self.temperature[0].set_temperature(self.temperature[1])

    def enable_temperature(self) -> None:
        """Enable the temperature source for the DUT."""
        if self.temperature is not None:
            _call_control_method(
                self.temperature[0],
                "enable",
                f"Temperature {self.temperature[0].name!r}",
            )

    def disable_temperature(self) -> None:
        """Disable the temperature source for the DUT."""
        if self.temperature is not None:
            _call_control_method(
                self.temperature[0],
                "disable",
                f"Temperature {self.temperature[0].name!r}",
            )

    def set_voltages(self) -> None:
        """Apply the voltage setpoints to the DUT."""
        for voltage, setpoint in self.voltages.items():
            if isinstance(voltage, AdjustableVoltage):
                voltage.set_voltage(setpoint)

    def enable_voltages(self) -> None:
        """Enable all voltage sources for the DUT."""
        for voltage in self.voltages:
            _call_control_method(voltage, "enable", f"Voltage {voltage.name!r}")

    def disable_voltages(self) -> None:
        """Disable all voltage sources for the DUT."""
        for voltage in self.voltages:
            _call_control_method(voltage, "disable", f"Voltage {voltage.name!r}")

    def reset(self) -> None:
        """Reset the DUT to a known state."""
        _call_control_method(self.dut, "reset", "The DUT")
