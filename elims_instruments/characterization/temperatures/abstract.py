"""Temperature conditions used during characterization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from elims_instruments.utils import Limits
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.RED)

TemperatureSetter = Callable[[float], None]
TemperatureGetter = Callable[[], float]
Enable = Callable[[], None]
Disable = Callable[[], None]


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

    Measurement and control capabilities are enabled by supplying the
    corresponding getter and setter callbacks.
    """

    def __init__(
        self,
        specification: TemperatureSpecification,
        *,
        temperature_getter: TemperatureGetter | None = None,
        temperature_setter: TemperatureSetter | None = None,
        enable: Enable | None = None,
        disable: Disable | None = None,
    ) -> None:
        """Initialize the common, validated temperature state."""
        self.name = specification.name
        self.temperature_limits = specification.temperature_limits
        self._temperature_getter = temperature_getter
        self._temperature_setter = temperature_setter
        self._enable = enable
        self._disable = disable
        self._temperature_setpoint = specification.temperature_limits.typical
        logger.debug(
            "Initialized {} temperature {!r} with nominal setpoint {:g} °C",
            type(self).__name__,
            self.name,
            self._temperature_setpoint,
        )

    def report_header(self) -> list[str]:
        """Return the CSV headers for the temperature information."""
        return ["t_target", "t_actual"]

    def report_value(self) -> list[str]:
        """Return the temperature information as CSV values."""
        return [str(self.setpoint), str(self.get_temperature())]

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
        """Return the measured temperature."""
        if self._temperature_getter is None:
            raise NotImplementedError(
                f"Cannot measure temperature for {self.name!r} because the getter is "
                "not provided."
            )
        temperature = self._temperature_getter()
        logger.debug("Measured temperature {!r}: {} °C", self.name, temperature)
        return temperature

    def enable(self) -> None:
        """Enable the temperature source."""
        if self._enable is None:
            raise NotImplementedError(
                f"Cannot enable temperature {self.name!r} because the callback is "
                "not provided."
            )
        self._enable()
        logger.info("Enabled temperature {!r}", self.name)

    def disable(self) -> None:
        """Disable the temperature source."""
        if self._disable is None:
            raise NotImplementedError(
                f"Cannot disable temperature {self.name!r} because the callback is "
                "not provided."
            )
        self._disable()
        logger.info("Disabled temperature {!r}", self.name)

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
        value = self.temperature_limits.validate(
            temperature,
            label=f"temperature for {self.name!r}",
        )
        self._temperature_setter(value)
        self._temperature_setpoint = value
        logger.info(
            "Set temperature {!r} to {} °C",
            self.name,
            value,
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
