from collections.abc import Iterator, Sequence
from dataclasses import dataclass, fields
from typing import TypeAlias

from elims_instruments.characterization._lifecycle import raise_lifecycle_errors

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

    def unreadable_names(self) -> tuple[str, ...]:
        """Return rails that cannot provide the report values they declare."""
        return tuple(
            voltage.name for _, voltage in self._ordered if not voltage.is_readable
        )

    def power_up(self) -> None:
        """Enable switchable rails in order and roll back every attempted rail."""
        attempted: list[VoltageSource] = []
        try:
            for _, voltage in self._ordered:
                if not voltage.is_switchable:
                    continue
                attempted.append(voltage)
                voltage.enable()
        except BaseException as operation_error:
            cleanup_errors: list[BaseException] = []
            for voltage in reversed(attempted):
                try:
                    voltage.disable()
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            raise_lifecycle_errors(
                "Voltage power-up failed and rollback was incomplete",
                operation_error,
                cleanup_errors,
            )

    def power_down(self) -> None:
        """Disable every switchable rail in reverse power-up order."""
        errors: list[BaseException] = []
        for _, voltage in reversed(self._ordered):
            if not voltage.is_switchable:
                continue
            try:
                voltage.disable()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise_lifecycle_errors(
                "One or more voltage rails failed to disable",
                None,
                errors,
            )
