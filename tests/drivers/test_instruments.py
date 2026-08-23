"""Tests for instrument driver factories and collection creation."""

from pathlib import Path

import pytest

from elims_instruments.database import (
    InstrumentModel,
    InstrumentType,
    VisaConnection,
)
from elims_instruments.intruments import InstrumentFactory, create_instruments
from elims_instruments.intruments.counter.factory import CounterFactory
from elims_instruments.intruments.counter.ks53220a import Keysight53220A
from elims_instruments.intruments.multimeter.factory import MultimeterFactory
from elims_instruments.intruments.multimeter.ks34401a import Keysight34401A


def _instrument(
    instrument_type: InstrumentType,
    model: str,
) -> InstrumentModel:
    """Build a valid instrument model for factory tests."""
    return InstrumentModel(
        id="instrument-1",
        asset_tag="INST-001",
        type=instrument_type,
        maker="Keysight",
        model=model,
        connection=VisaConnection(resource_name="GPIB0::1::INSTR"),
    )


def test_model_factories_normalize_model_keys() -> None:
    """Model lookup ignores surrounding whitespace and letter case."""
    counter = CounterFactory.create(
        _instrument(InstrumentType.COUNTER, " 53220a ")
    )
    multimeter = MultimeterFactory.create(
        _instrument(InstrumentType.MULTIMETER, " 34401a ")
    )

    assert isinstance(counter, Keysight53220A)
    assert isinstance(multimeter, Keysight34401A)


def test_factories_reject_invalid_registrations() -> None:
    """Invalid registry keys and builders fail with clear errors."""
    with pytest.raises(ValueError, match="non-empty"):
        CounterFactory.register(" ", Keysight53220A)
    with pytest.raises(TypeError, match="Counter subclass"):
        CounterFactory.register("counter", object)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        MultimeterFactory.register(" ", Keysight34401A)
    with pytest.raises(TypeError, match="InstrumentType"):
        InstrumentFactory.register(  # type: ignore[arg-type]
            "multimeter",
            MultimeterFactory.create,
        )
    with pytest.raises(TypeError, match="callable"):
        InstrumentFactory.register(
            InstrumentType.MULTIMETER,
            None,  # type: ignore[arg-type]
        )


def test_empty_assignments_need_no_database_configuration() -> None:
    """An empty instrument collection does not open a database."""
    instruments = create_instruments({}, Path("missing-bench.toml"))

    assert len(instruments) == 0
