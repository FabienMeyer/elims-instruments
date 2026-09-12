"""Voltage conditions used during characterization."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from elims_instruments.utils.logger import LoggerHelper, get_logger

if TYPE_CHECKING:
    from elims_instruments.utils import Limits

logger = get_logger(__name__, LoggerHelper.Color.BLUE)

VoltageSetter = Callable[[float], None]
VoltageGetter = Callable[[], float]
CurrentGetter = Callable[[], float]
CurrentLimitSetter = Callable[[float], None]
Enable = Callable[[], None]
Disable = Callable[[], None]

_VOLTAGE_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
_VOLTAGE_NAME_SEPARATOR_PATTERN = re.compile(r"[\s-]+")


@dataclass(frozen=True, slots=True)
class VoltageSpecification:
    """Static definition of a named DUT voltage."""

    name: str
    voltage_limits: Limits
    current_limits: Limits | None = None

    def __post_init__(self) -> None:
        """Normalize the rail name for attribute and mapping access."""
        if not isinstance(self.name, str):
            raise TypeError("Voltage name must be a string")
        name = _VOLTAGE_NAME_SEPARATOR_PATTERN.sub("_", self.name.strip().lower())
        name = re.sub(r"_+", "_", name).strip("_")
        if _VOLTAGE_NAME_PATTERN.fullmatch(name) is None:
            raise ValueError(
                "Voltage name must contain ASCII letters and numbers separated "
                "only by whitespace, hyphens, or underscores"
            )
        object.__setattr__(self, "name", name)


class Voltage(ABC):
    """Common description of a voltage applied to a DUT.

    Concrete types expose only the operations supported by their voltage
    source.
    """

    def __init__(
        self,
        specification: VoltageSpecification,
        *,
        voltage_getter: VoltageGetter | None = None,
        current_getter: CurrentGetter | None = None,
        enable: Enable | None = None,
        disable: Disable | None = None,
    ) -> None:
        """Initialize the common, validated voltage state."""
        self.name = specification.name
        self.current_limits = specification.current_limits
        self.voltage_limits = specification.voltage_limits
        self._voltage_getter = voltage_getter
        self._current_getter = current_getter
        self._enable = enable
        self._disable = disable
        self._voltage_setpoint = specification.voltage_limits.typical
        self._current_limit_setpoint = (
            None
            if specification.current_limits is None
            else specification.current_limits.typical
        )
        logger.debug(
            "Initialized {} voltage {!r} with nominal setpoint {} V",
            type(self).__name__,
            self.name,
            self._voltage_setpoint,
        )

    @abstractmethod
    def report_header(self) -> list[str]:
        """Return the CSV headers for the voltage information."""
        pass

    @abstractmethod
    def report_value(self) -> list[str]:
        """Return the voltage information as CSV values."""
        pass

    @property
    def setpoint(self) -> int | float:
        """Return the configured voltage, which is not a measured value."""
        return self._voltage_setpoint

    @property
    def current_limit_setpoint(self) -> int | float | None:
        """Return the configured current limit, or ``None`` when unspecified."""
        return self._current_limit_setpoint

    def get_voltage(self) -> float:
        """Return the measured voltage."""
        if self._voltage_getter is None:
            raise NotImplementedError(
                f"Cannot measure voltage for {self.name!r} because the getter is "
                "not provided."
            )
        voltage = self._voltage_getter()
        logger.debug("Measured voltage {!r}: {} V", self.name, voltage)
        return voltage

    def get_current(self) -> float:
        """Return the measured current."""
        if self._current_getter is None:
            raise NotImplementedError(
                f"Cannot measure current for {self.name!r} because the getter is "
                "not provided."
            )
        current = self._current_getter()
        logger.debug("Measured current for voltage {!r}: {} A", self.name, current)
        return current

    def enable(self) -> None:
        """Enable the voltage source."""
        if self._enable is None:
            raise NotImplementedError(
                f"Cannot enable voltage {self.name!r} because the callback is "
                "not provided."
            )
        self._enable()
        logger.info("Enabled voltage {!r}", self.name)

    def disable(self) -> None:
        """Disable the voltage source."""
        if self._disable is None:
            raise NotImplementedError(
                f"Cannot disable voltage {self.name!r} because the callback is "
                "not provided."
            )
        self._disable()
        logger.info("Disabled voltage {!r}", self.name)

    @property
    @abstractmethod
    def is_adjustable(self) -> bool:
        """Return whether software can adjust this voltage."""


class FixedVoltage(Voltage):
    """A voltage whose value is fixed by the board or fixture."""

    def __init__(
        self,
        specification: VoltageSpecification,
        voltage_getter: VoltageGetter | None = None,
        current_getter: CurrentGetter | None = None,
        *,
        enable: Enable | None = None,
        disable: Disable | None = None,
    ) -> None:
        """Initialize an immutable fixed-voltage description."""
        super().__init__(
            specification=specification,
            voltage_getter=voltage_getter,
            current_getter=current_getter,
            enable=enable,
            disable=disable,
        )

    def report_header(self) -> list[str]:
        """Return the CSV headers for the voltage information."""
        return [f"{self.name}_actual"]

    def report_value(self) -> list[str]:
        """Return the voltage information as CSV values."""
        return [str(self.get_voltage())]

    @property
    def is_adjustable(self) -> bool:
        """Return ``False`` because a fixed voltage cannot be controlled."""
        return False


class AdjustableVoltage(Voltage):
    """A voltage controlled by an instrument.

    Construction has no hardware side effects. The setpoint is written only
    when :meth:`apply` or :meth:`set_voltage` is called.
    """

    def __init__(
        self,
        specification: VoltageSpecification,
        *,
        voltage_getter: VoltageGetter | None = None,
        current_getter: CurrentGetter | None = None,
        voltage_setter: VoltageSetter,
        current_limit_setter: CurrentLimitSetter | None = None,
        enable: Enable | None = None,
        disable: Disable | None = None,
    ) -> None:
        """Initialize an adjustable voltage."""
        super().__init__(
            specification=specification,
            voltage_getter=voltage_getter,
            current_getter=current_getter,
            enable=enable,
            disable=disable,
        )
        self._voltage_setter = voltage_setter
        self._current_limit_setter = current_limit_setter

    def report_header(self) -> list[str]:
        """Return the CSV headers for the voltage information."""
        return [f"{self.name}_target", f"{self.name}_actual"]

    def report_value(self) -> list[str]:
        """Return the voltage information as CSV values."""
        return [str(self.setpoint), str(self.get_voltage())]

    @property
    def setpoint(self) -> int | float:
        """Return the configured voltage setpoint."""
        return self._voltage_setpoint

    @setpoint.setter
    def setpoint(self, value: int | float) -> None:
        """Validate and store a new voltage setpoint."""
        self._voltage_setpoint = self.voltage_limits.validate(
            value,
            label=f"voltage for {self.name!r}",
        )

    @property
    def is_adjustable(self) -> bool:
        """Return ``True`` because an instrument controls this voltage."""
        return True

    def set_voltage(self, voltage: float) -> None:
        """Validate and apply a new voltage setpoint."""
        value = self.voltage_limits.validate(
            voltage,
            label=f"voltage for {self.name!r}",
        )
        self._voltage_setter(value)
        self._voltage_setpoint = value
        logger.info("Set voltage {!r} to {} V", self.name, value)

    def apply(self) -> None:
        """Apply the currently configured voltage setpoint."""
        self._voltage_setter(self._voltage_setpoint)
        logger.info("Set voltage {!r} to {} V", self.name, self._voltage_setpoint)

    def set_current_limit(self, current_limit: float) -> None:
        """Validate and apply new current limit."""
        if self._current_limit_setter is None:
            logger.warning("Current-limit control is unavailable for {!r}", self.name)
            raise NotImplementedError(
                f"Cannot set current limit for {self.name!r} because the setter is "
                "not provided."
            )
        if self.current_limits is None:
            raise ValueError(
                f"Cannot set current limit for {self.name!r} because current-limit "
                "limits are not configured."
            )
        value = self.current_limits.validate(
            current_limit,
            label=f"current limit for {self.name!r}",
        )
        self._current_limit_setter(value)
        self._current_limit_setpoint = value
        logger.info("Set current limit for voltage {!r} to {} A", self.name, value)
