from collections.abc import Iterator, Sequence
from dataclasses import dataclass, fields
from typing import TypeAlias

from .abstract import AdjustableVoltage, FixedVoltage

VoltageSource: TypeAlias = FixedVoltage | AdjustableVoltage
VoltageEntry: TypeAlias = tuple[int, VoltageSource]


@dataclass(frozen=True, slots=True)
class VoltageSetPoints:
    """Base for project-specific voltage operating-point values."""

    def as_dict(self) -> dict[str, int | float]:
        """Return the dataclass fields as named voltage setpoints."""
        setpoints: dict[str, int | float] = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"Voltage setpoint {field.name!r} must be an int or float"
                )
            setpoints[field.name] = value
        return setpoints


class Voltages:
    def __init__(self, voltages: Sequence[VoltageEntry]) -> None:
        """Create named and ordered views of the voltage rails."""
        self._voltages, self._ordered = self._validate_voltages(voltages)

    @staticmethod
    def _validate_voltages(
        voltages: Sequence[VoltageEntry],
    ) -> tuple[dict[str, VoltageSource], tuple[VoltageEntry, ...]]:
        """Validate unique names and orders, then return both voltage views."""
        by_name: dict[str, VoltageSource] = {}
        orders: set[int] = set()

        for order, voltage in voltages:
            name = voltage.name

            if name in by_name:
                raise ValueError(f"Duplicate voltage name: {name!r}")
            if order in orders:
                raise ValueError(f"Duplicate voltage order: {order}")

            by_name[name] = voltage
            orders.add(order)

        ordered = tuple(sorted(voltages, key=lambda entry: entry[0]))
        return by_name, ordered

    def __getitem__(self, name: str) -> VoltageSource:
        try:
            return self._voltages[name]
        except KeyError:
            raise KeyError(f"Unknown voltage: {name!r}") from None

    def __getattr__(self, name: str) -> VoltageSource:
        try:
            return self._voltages[name]
        except KeyError:
            raise AttributeError(f"Unknown voltage: {name!r}") from None

    def __iter__(self) -> Iterator[str]:
        """Iterate over voltage names in power-up order."""
        return (voltage.name for _, voltage in self._ordered)

    def __len__(self) -> int:
        """Return the number of voltage rails."""
        return len(self._ordered)

    def values(self) -> tuple[VoltageSource, ...]:
        """Return voltage sources in power-up order."""
        return tuple(voltage for _, voltage in self._ordered)

    def report_header(self) -> list[str]:
        """Return report headers in power-up order."""
        headers: list[str] = []
        for _, voltage in self._ordered:
            headers.extend(voltage.report_header())
        return headers

    def report_value(self) -> list[str]:
        """Return report values in the same order as their headers."""
        values: list[str] = []
        for _, voltage in self._ordered:
            values.extend(voltage.report_value())
        return values

    def power_up(self) -> None:
        """Enable rails in ascending order."""
        enabled: list[VoltageSource] = []
        try:
            for _, voltage in self._ordered:
                voltage.enable()
                enabled.append(voltage)
        except Exception:
            for voltage in reversed(enabled):
                voltage.disable()
            raise

    def power_down(self) -> None:
        """Disable rails in reverse power-up order."""
        errors: list[Exception] = []
        for _, voltage in reversed(self._ordered):
            try:
                voltage.disable()
            except Exception as error:
                errors.append(error)
        if errors:
            raise ExceptionGroup("One or more voltage rails failed to disable", errors)
