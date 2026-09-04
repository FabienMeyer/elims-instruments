"""Temperature conditions used during characterization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import nan

from elims_instruments.utils import Limits
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.RED)

TemperatureSetter = Callable[[float], None]
TemperatureGetter = Callable[[], float]


@dataclass(frozen=True, slots=True)
class TemperatureSpecification:
    """Static definition of a named DUT temperature."""

    name: str
    temperature_limits: Limits

    def __post_init__(self) -> None:
        """Expose temperature limits consistently as degrees Celsius floats."""
        limits = self.temperature_limits
        object.__setattr__(
            self,
            "temperature_limits",
            Limits(
                absolute_minimum=(
                    None
                    if limits.absolute_minimum is None
                    else float(limits.absolute_minimum)
                ),
                minimum=None if limits.minimum is None else float(limits.minimum),
                typical=float(limits.typical),
                maximum=None if limits.maximum is None else float(limits.maximum),
                absolute_maximum=(
                    None
                    if limits.absolute_maximum is None
                    else float(limits.absolute_maximum)
                ),
            ),
        )


class Temperature:
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
            "Initialized {} temperature {!r} with nominal setpoint {:g} °C",
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
        """Return whether software can adjust this temperature."""
        return self._temperature_setter is not None

    def set_temperature(self, temperature: float) -> None:
        """Validate and apply a new temperature setpoint."""
        if self._temperature_setter is None:
            logger.warning("Temperature control is unavailable for {!r}", self.name)
            raise NotImplementedError(
                f"Cannot set temperature for {self.name!r} because the setter is "
                "not provided."
            )
        self.setpoint = temperature
        self._temperature_setter(self._temperature_setpoint)
        logger.info(
            "Set temperature {!r} to {} °C",
            self.name,
            self._temperature_setpoint,
        )

    def apply(self) -> None:
        """Apply the currently configured temperature setpoint."""
        if self._temperature_setter is None:
            logger.warning("Temperature control is unavailable for {!r}", self.name)
            raise NotImplementedError(
                f"Cannot set temperature for {self.name!r} because the setter is "
                "not provided."
            )
        self._temperature_setter(self._temperature_setpoint)
        logger.info(
            "Set temperature {!r} to {} °C",
            self.name,
            self._temperature_setpoint,
        )
