"""Factory for creating multimeter instrument instances."""

from typing import ClassVar

from elims_instruments.database.instrument import InstrumentModel
from elims_instruments.utils.logger import get_logger

from .abstract import Multimeter

logger = get_logger(__name__)


class MultimeterFactory:
    """Factory for creating multimeter instances.

    Manages registration and instantiation of multimeter models using
    a registry pattern for flexibility and extensibility.
    """

    _registry: ClassVar[dict[str, type[Multimeter]]] = {}

    @classmethod
    def register(cls, model: str, multimeter_class: type[Multimeter]) -> None:
        """Register a multimeter model.

        Args:
            model: Model name or alias
            multimeter_class: Multimeter class to register

        Raises:
            TypeError: If multimeter_class is not a Multimeter subclass
        """
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Multimeter model must be a non-empty string")
        if not isinstance(multimeter_class, type) or not issubclass(
            multimeter_class,
            Multimeter,
        ):
            raise TypeError("Multimeter driver must be a Multimeter subclass")
        cls._registry[model.strip().casefold()] = multimeter_class
        logger.debug(
            "Registered multimeter model {} with driver {}",
            model,
            multimeter_class.__name__,
        )

    @classmethod
    def create(cls, instrument: InstrumentModel) -> Multimeter:
        """Create a multimeter instance.

        Args:
            instrument: InstrumentModel class

        Returns:
            Multimeter instance

        Raises:
            ValueError: If model is not registered
            TypeError: If instantiation fails
        """
        model_key = instrument.model.strip().casefold()
        if model_key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown multimeter model: '{instrument.model}'. "
                f"Available models: {available or 'None registered yet'}"
            )

        multimeter_class = cls._registry[model_key]
        logger.debug(
            "Creating {} driver for multimeter asset {}",
            multimeter_class.__name__,
            instrument.asset_tag,
        )
        try:
            return multimeter_class(instrument)
        except Exception as error:
            raise TypeError(
                f"Failed to instantiate {instrument.model}: {error}"
            ) from error


def create_multimeter(instrument: InstrumentModel) -> Multimeter:
    """
    Convenience function to create a multimeter.

    Args:
        instrument: InstrumentModel instance

    Returns:
        Multimeter instance
    """
    return MultimeterFactory.create(instrument)
