"""Voltage conditions used during characterization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from math import nan
from typing import TYPE_CHECKING

from elims_instruments.utils.logger import LoggerHelper, get_logger

if TYPE_CHECKING:
    from elims_instruments.utils import Limits

logger = get_logger(__name__, LoggerHelper.Color.BLUE)

VoltageSetter = Callable[[float], None]
VoltageGetter = Callable[[], float]
CurrentGetter = Callable[[], float]
CurrentLimitSetter = Callable[[float], None]


@dataclass(frozen=True, slots=True)
class VoltageSpecification:
    """Static definition of a named DUT voltage."""

    name: str
    voltage_limits: Limits
    current_limits: Limits | None = None


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
    ) -> None:
        """Initialize the common, validated voltage state."""
        self.name = specification.name
        self.current_limits = specification.current_limits
        self.voltage_limits = specification.voltage_limits
        self._voltage_getter = voltage_getter
        self._current_getter = current_getter
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

    @property
    def setpoint(self) -> int | float:
        """Return the configured voltage, which is not a measured value."""
        return self._voltage_setpoint

    @setpoint.setter
    def setpoint(self, value: int | float) -> None:
        """Validate and store a new voltage setpoint."""
        self._voltage_setpoint = self.voltage_limits.validate(
            value,
            label=f"voltage for {self.name!r}",
        )

    @property
    def current_limit_setpoint(self) -> int | float | None:
        """Return the configured current limit, or ``None`` when unspecified."""
        return self._current_limit_setpoint

    def get_voltage(self) -> float:
        """Return the measured voltage, or NaN if not supported."""
        if self._voltage_getter is None:
            logger.debug("Voltage measurement is unavailable for {!r}", self.name)
            return nan
        voltage = self._voltage_getter()
        logger.debug("Measured voltage {!r}: {} V", self.name, voltage)
        return voltage

    def get_current(self) -> float:
        """Return the measured current, or NaN if not supported."""
        if self._current_getter is None:
            logger.debug("Current measurement is unavailable for {!r}", self.name)
            return nan
        current = self._current_getter()
        logger.debug("Measured current for voltage {!r}: {} A", self.name, current)
        return current

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
    ) -> None:
        """Initialize an immutable fixed-voltage description."""
        super().__init__(
            specification=specification,
            voltage_getter=voltage_getter,
            current_getter=current_getter,
        )

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
    ) -> None:
        """Initialize an adjustable voltage."""
        super().__init__(
            specification=specification,
            voltage_getter=voltage_getter,
            current_getter=current_getter,
        )
        self._voltage_setter = voltage_setter
        self._current_limit_setter = current_limit_setter

    @property
    def is_adjustable(self) -> bool:
        """Return ``True`` because an instrument controls this voltage."""
        return True

    def set_voltage(self, voltage: float) -> None:
        """Validate and apply a new voltage setpoint."""
        self.setpoint = voltage
        self._voltage_setter(self._voltage_setpoint)
        logger.info("Set voltage {!r} to {} V", self.name, self._voltage_setpoint)

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
