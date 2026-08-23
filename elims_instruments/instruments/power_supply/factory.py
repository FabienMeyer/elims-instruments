"""Factory for creating power-supply instrument instances."""

from typing import ClassVar

from elims_instruments.database.instrument import InstrumentModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .abstract import PowerSupply

logger = get_logger(__name__, LoggerHelper.Color.CYAN)


class PowerSupplyFactory:
    """Create power-supply drivers registered by model name."""

    _registry: ClassVar[dict[str, type[PowerSupply]]] = {}

    @classmethod
    def register(cls, model: str, power_supply_class: type[PowerSupply]) -> None:
        """Register a power-supply model or alias."""
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Power-supply model must be a non-empty string")
        if not isinstance(power_supply_class, type) or not issubclass(
            power_supply_class,
            PowerSupply,
        ):
            raise TypeError("Power-supply driver must be a PowerSupply subclass")
        cls._registry[model.strip().casefold()] = power_supply_class
        logger.debug(
            "Registered power-supply model {} with driver {}",
            model,
            power_supply_class.__name__,
        )

    @classmethod
    def create(cls, instrument: InstrumentModel) -> PowerSupply:
        """Create a power-supply driver for an instrument model."""
        model_key = instrument.model.strip().casefold()
        if model_key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown power-supply model: '{instrument.model}'. "
                f"Available models: {available or 'None registered yet'}"
            )

        power_supply_class = cls._registry[model_key]
        logger.debug(
            "Creating {} driver for power-supply asset {}",
            power_supply_class.__name__,
            instrument.asset_tag,
        )
        try:
            return power_supply_class(instrument)
        except Exception as error:
            raise TypeError(
                f"Failed to instantiate {instrument.model}: {error}"
            ) from error


def create_power_supply(instrument: InstrumentModel) -> PowerSupply:
    """Create a power-supply driver for an instrument model."""
    return PowerSupplyFactory.create(instrument)
