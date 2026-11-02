"""Create and collect instrument drivers independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import ClassVar

from elims_instruments.bench.factory import NamedCollection, resolve_assignments
from elims_instruments.bench.instruments.abstract import Instrument
from elims_instruments.bench.instruments.counter import create_counter
from elims_instruments.bench.instruments.multimeter import create_multimeter
from elims_instruments.bench.instruments.power_supply import create_power_supply
from elims_instruments.bench.instruments.thermal_test_system import (
    create_thermal_test_system,
)
from elims_instruments.database import InstrumentCrud, InstrumentModel, InstrumentType
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .error import InstrumentAssetNotFoundError, UnsupportedInstrumentTypeError

InstrumentBuilder = Callable[[InstrumentModel], Instrument]
logger = get_logger(__name__, LoggerHelper.Color.CYAN)


class InstrumentFactory:
    """Create instrument drivers using factories registered by instrument type."""

    _registry: ClassVar[dict[InstrumentType, InstrumentBuilder]] = {}

    @classmethod
    def register(
        cls,
        instrument_type: InstrumentType,
        builder: InstrumentBuilder,
        *,
        replace: bool = False,
    ) -> None:
        """Register the builder responsible for an instrument category."""
        if not isinstance(instrument_type, InstrumentType):
            raise TypeError("Instrument type must be an InstrumentType")
        if not callable(builder):
            raise TypeError("Instrument builder must be callable")
        registered = cls._registry.get(instrument_type)
        if registered is builder:
            return
        if registered is not None and not replace:
            raise ValueError(
                "Instrument type already has a registered builder: "
                f"{instrument_type.value!r}"
            )
        cls._registry[instrument_type] = builder
        logger.debug(
            "Registered driver builder {} for instrument type {}",
            getattr(builder, "__name__", type(builder).__name__),
            instrument_type.value,
        )

    @classmethod
    def create(cls, instrument: InstrumentModel) -> Instrument:
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
        if not isinstance(driver, Instrument):
            raise TypeError("Instrument builders must return an instrument driver")
        logger.debug(
            "Created {} driver for asset {}",
            type(driver).__name__,
            instrument.asset_tag,
        )
        return driver


InstrumentFactory.register(InstrumentType.MULTIMETER, create_multimeter)
InstrumentFactory.register(InstrumentType.COUNTER, create_counter)
InstrumentFactory.register(InstrumentType.POWER_SUPPLY, create_power_supply)
InstrumentFactory.register(
    InstrumentType.THERMAL_TEST_SYSTEM,
    create_thermal_test_system,
)


class InstrumentCollection(NamedCollection[Instrument]):
    """Read-only collection supporting mapping and attribute access."""


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

    with InstrumentCrud(logger, configuration, create_tables=False) as repository:
        instruments = resolve_assignments(
            assignments,
            repository,
            lookup_field="asset_tag",
            builder=InstrumentFactory.create,
            not_found=InstrumentAssetNotFoundError,
        )
    collection = InstrumentCollection(instruments)
    logger.info("Created {} instrument drivers", len(collection))
    return collection
