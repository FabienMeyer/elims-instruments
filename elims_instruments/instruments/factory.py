"""Create and collect instrument drivers independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from elims_instruments.database import InstrumentCrud, InstrumentModel, InstrumentType
from elims_instruments.instruments.counter import create_counter
from elims_instruments.instruments.counter.abstract import Counter
from elims_instruments.instruments.multimeter import create_multimeter
from elims_instruments.instruments.multimeter.abstract import Multimeter
from elims_instruments.utils.logger import get_logger

from .error import InstrumentAssetNotFoundError, UnsupportedInstrumentTypeError

InstrumentDriver = Multimeter | Counter
InstrumentBuilder = Callable[[InstrumentModel], InstrumentDriver]
logger = get_logger(__name__)


class InstrumentFactory:
    """Create instrument drivers using factories registered by instrument type."""

    _registry: ClassVar[dict[InstrumentType, InstrumentBuilder]] = {}

    @classmethod
    def register(
        cls,
        instrument_type: InstrumentType,
        builder: InstrumentBuilder,
    ) -> None:
        """Register the builder responsible for an instrument category."""
        if not isinstance(instrument_type, InstrumentType):
            raise TypeError("Instrument type must be an InstrumentType")
        if not callable(builder):
            raise TypeError("Instrument builder must be callable")
        cls._registry[instrument_type] = builder
        logger.debug(
            "Registered driver builder {} for instrument type {}",
            getattr(builder, "__name__", type(builder).__name__),
            instrument_type.value,
        )

    @classmethod
    def create(cls, instrument: InstrumentModel) -> InstrumentDriver:
        """Create a driver using the factory registered for the model's type."""
        logger.debug(
            "Selecting driver for asset {} with type {}",
            instrument.asset_tag,
            instrument.type.value,
        )
        try:
            builder = cls._registry[instrument.type]
        except KeyError as error:
            raise UnsupportedInstrumentTypeError(
                instrument.type,
                cls._registry,
            ) from error
        driver = builder(instrument)
        if not isinstance(driver, (Multimeter, Counter)):
            raise TypeError("Instrument builders must return an instrument driver")
        logger.debug(
            "Created {} driver for asset {}",
            type(driver).__name__,
            instrument.asset_tag,
        )
        return driver


InstrumentFactory.register(InstrumentType.MULTIMETER, create_multimeter)
InstrumentFactory.register(InstrumentType.COUNTER, create_counter)


class InstrumentCollection(Mapping[str, InstrumentDriver]):
    """Read-only collection supporting mapping and attribute access."""

    def __init__(self, instruments: Mapping[str, InstrumentDriver]) -> None:
        """Store the named drivers in an immutable mapping."""
        self._drivers = MappingProxyType(dict(instruments))

    def __getitem__(self, name: str) -> InstrumentDriver:
        """Return the driver assigned to *name*."""
        return self._drivers[name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over configured script names."""
        return iter(self._drivers)

    def __len__(self) -> int:
        """Return the number of configured instruments."""
        return len(self._drivers)

    def __getattr__(self, name: str) -> InstrumentDriver:
        """Allow attribute access such as ``instruments.primary_dmm``."""
        try:
            return self._drivers[name]
        except KeyError as error:
            raise AttributeError(name) from error


def create_instruments(
    assignments: Mapping[str, str],
    configuration: Path = Path("bench.toml"),
) -> InstrumentCollection:
    """Resolve asset tags and create a named collection of instrument drivers."""
    logger.info(
        "Creating {} instrument drivers using bench configuration {}",
        len(assignments),
        configuration,
    )
    if not assignments:
        logger.info("Created 0 instrument drivers")
        return InstrumentCollection({})

    repository = InstrumentCrud(logger, configuration)
    instruments: dict[str, InstrumentDriver] = {}
    try:
        for name, asset_tag in assignments.items():
            logger.debug("Resolving bench instrument {} from asset {}", name, asset_tag)
            instrument = repository.fetch("asset_tag", asset_tag)
            if instrument is None:
                raise InstrumentAssetNotFoundError(asset_tag)
            instruments[name] = InstrumentFactory.create(instrument)
    finally:
        repository.engine.dispose()
    collection = InstrumentCollection(instruments)
    logger.info("Created {} instrument drivers", len(collection))
    return collection
