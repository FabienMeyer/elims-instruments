"""Factory for creating counter instrument instances."""

from typing import ClassVar

from elims_instruments.database.instrument import InstrumentModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .abstract import Counter

logger = get_logger(__name__, LoggerHelper.Color.CYAN)


class CounterFactory:
    """Factory for creating counter instances.

    Manages registration and instantiation of counter models using
    a registry pattern for flexibility and extensibility.
    """

    _registry: ClassVar[dict[str, type[Counter]]] = {}

    @classmethod
    def register(cls, model: str, counter_class: type[Counter]) -> None:
        """Register a counter model.

        Args:
            model: Model name or alias
            counter_class: Counter class to register

        Raises:
            TypeError: If counter_class is not a Counter subclass
        """
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Counter model must be a non-empty string")
        if not isinstance(counter_class, type) or not issubclass(
            counter_class,
            Counter,
        ):
            raise TypeError("Counter driver must be a Counter subclass")
        cls._registry[model.strip().casefold()] = counter_class
        logger.debug(
            "Registered counter model {} with driver {}",
            model,
            counter_class.__name__,
        )

    @classmethod
    def create(cls, instrument: InstrumentModel) -> Counter:
        """Create a counter instance.

        Args:
            instrument: InstrumentModel class

        Returns:
            Counter instance

        Raises:
            ValueError: If model is not registered
            TypeError: If instantiation fails
        """
        model_key = instrument.model.strip().casefold()
        if model_key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown counter model: '{instrument.model}'. "
                f"Available models: {available or 'None registered yet'}"
            )

        counter_class = cls._registry[model_key]
        logger.debug(
            "Creating {} driver for counter asset {}",
            counter_class.__name__,
            instrument.asset_tag,
        )
        try:
            return counter_class(instrument)
        except Exception as error:
            raise TypeError(
                f"Failed to instantiate {instrument.model}: {error}"
            ) from error


def create_counter(instrument: InstrumentModel) -> Counter:
    """
    Convenience function to create a counter.

    Args:
        instrument: InstrumentModel instance

    Returns:
        Counter instance
    """
    return CounterFactory.create(instrument)
