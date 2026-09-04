"""Temperature conditions used during characterization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from math import nan
from typing import TYPE_CHECKING

from elims_instruments.utils.logger import LoggerHelper, get_logger

if TYPE_CHECKING:
    from elims_instruments.utils import Limits

logger = get_logger(__name__, LoggerHelper.Color.RED)

TemperatureSetter = Callable[[float], None]
TemperatureGetter = Callable[[], float]


@dataclass(frozen=True, slots=True)
class TemperatureSpecification:
    """Static definition of a named DUT temperature."""

    name: str
    temperature_limits: Limits


class Temperature(ABC):
    """Common description of a temperature applied to a DUT.

    Concrete types expose only the operations supported by their temperature
    source.
    """

    def __init__(
        self,
        specification: TemperatureSpecification,
        *,
        temperature_getter: TemperatureGetter | None = None,
        temperature_setter: TemperatureSetter | None = None,
    ) -> None:
        """Initialize the common, validated temperature state."""
        self.name = specification.name
        self.temperature_limits = specification.temperature_limits
        self._temperature_getter = temperature_getter
        self._temperature_setter = temperature_setter
        self._temperature_setpoint = specification.temperature_limits.typical
        logger.debug(
            "Initialized {} temperature {!r} with nominal setpoint {} °C",
            type(self).__name__,
            self.name,
            self._temperature_setpoint,
        )

    @property
    def setpoint(self) -> int | float:
        """Return the configured temperature, which is not a measured value."""
        return self._temperature_setpoint

    @setpoint.setter
    def setpoint(self, value: int | float) -> None:
        """Validate and store a new temperature setpoint."""
        self._temperature_setpoint = self.temperature_limits.validate(
            value,
            label=f"temperature for {self.name!r}",
        )

    def get_temperature(self) -> float:
        """Return the measured temperature, or NaN if not supported."""
        if self._temperature_getter is None:
            logger.debug("Temperature measurement is unavailable for {!r}", self.name)
            return nan
        temperature = self._temperature_getter()
        logger.debug("Measured temperature {!r}: {} °C", self.name, temperature)
        return temperature

    @property
    def is_adjustable(self) -> bool:
        """Return ``True`` because an instrument controls this temperature."""
        return True

    def set_temperature(self, temperature: float) -> None:
        """Validate and apply a new temperature setpoint."""
        self.setpoint = temperature
        self._temperature_setter(self._temperature_setpoint)
        logger.info(
            "Set temperature {!r} to {} °C",
            self.name,
            self._temperature_setpoint,
        )

    def apply(self) -> None:
        """Apply the currently configured temperature setpoint."""
        self._temperature_setter(self._temperature_setpoint)
        logger.info(
            "Set temperature {!r} to {} °C",
            self.name,
            self._temperature_setpoint,
        )
