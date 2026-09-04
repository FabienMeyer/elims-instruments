"""Factory for creating thermal test system drivers."""

from typing import ClassVar

from elims_instruments.database.instrument import InstrumentModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .abstract import ThermalTestSystem

logger = get_logger(__name__, LoggerHelper.Color.CYAN)


class ThermalTestSystemFactory:
    """Create thermal test system drivers registered by model name."""

    _registry: ClassVar[dict[str, type[ThermalTestSystem]]] = {}

    @classmethod
    def register(
        cls,
        model: str,
        driver_class: type[ThermalTestSystem],
    ) -> None:
        """Register a thermal test system model or alias."""
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Thermal test system model must be a non-empty string")
        if not isinstance(driver_class, type) or not issubclass(
            driver_class,
            ThermalTestSystem,
        ):
            raise TypeError(
                "Thermal test system driver must be a ThermalTestSystem subclass"
            )
        cls._registry[model.strip().casefold()] = driver_class
        logger.debug(
            "Registered thermal test system model {} with driver {}",
            model,
            driver_class.__name__,
        )

    @classmethod
    def create(cls, instrument: InstrumentModel) -> ThermalTestSystem:
        """Create the driver registered for an instrument model."""
        model_key = instrument.model.strip().casefold()
        if model_key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown thermal test system model: '{instrument.model}'. "
                f"Available models: {available or 'None registered yet'}"
            )

        driver_class = cls._registry[model_key]
        logger.debug(
            "Creating {} driver for thermal test system asset {}",
            driver_class.__name__,
            instrument.asset_tag,
        )
        try:
            return driver_class(instrument)
        except Exception as error:
            raise TypeError(
                f"Failed to instantiate {instrument.model}: {error}"
            ) from error


def create_thermal_test_system(
    instrument: InstrumentModel,
) -> ThermalTestSystem:
    """Create a thermal test system driver for an instrument model."""
    return ThermalTestSystemFactory.create(instrument)
