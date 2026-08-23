"""Tests for instrument driver factories and collection creation."""

from pathlib import Path

import pytest

from elims_instruments.database import (
    InstrumentModel,
    InstrumentType,
    VisaConnection,
)
from elims_instruments.instruments import InstrumentFactory, create_instruments
from elims_instruments.instruments.counter.factory import CounterFactory
from elims_instruments.instruments.counter.ks53220a import Keysight53220A
from elims_instruments.instruments.multimeter.factory import MultimeterFactory
from elims_instruments.instruments.multimeter.ks34401a import Keysight34401A
from elims_instruments.instruments.power_supply.factory import PowerSupplyFactory
from elims_instruments.instruments.power_supply.ks36313a import KeysightE36313A
from elims_instruments.instruments.thermal_test_system import (
    ThermalTestSystem,
    ThermalTestSystemFactory,
)


class ExampleThermalTestSystem(ThermalTestSystem):
    """Concrete test driver for the category factory contract."""

    def connect(self) -> None:
        """Open the test connection."""

    def disconnect(self) -> None:
        """Close the test connection."""

    def get_id(self) -> str:
        """Return the stored instrument ID."""
        return self.instrument.id


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
    counter = CounterFactory.create(_instrument(InstrumentType.COUNTER, " 53220a "))
    multimeter = MultimeterFactory.create(
        _instrument(InstrumentType.MULTIMETER, " 34401a ")
    )
    power_supply = PowerSupplyFactory.create(
        _instrument(InstrumentType.POWER_SUPPLY, " e36313a ")
    )

    assert isinstance(counter, Keysight53220A)
    assert isinstance(multimeter, Keysight34401A)
    assert isinstance(power_supply, KeysightE36313A)


def test_instrument_factory_creates_power_supply() -> None:
    """The top-level factory delegates power supplies to their model factory."""
    power_supply = InstrumentFactory.create(
        _instrument(InstrumentType.POWER_SUPPLY, "Keysight E36313A")
    )

    assert isinstance(power_supply, KeysightE36313A)


def test_instrument_factory_creates_thermal_test_system() -> None:
    """The top-level factory delegates thermal test systems."""
    ThermalTestSystemFactory.register(
        " Example Thermal System ",
        ExampleThermalTestSystem,
    )

    driver = InstrumentFactory.create(
        _instrument(
            InstrumentType.THERMAL_TEST_SYSTEM,
            "example thermal system",
        )
    )

    assert isinstance(driver, ExampleThermalTestSystem)
    assert driver.get_id() == "instrument-1"


def test_thermal_test_system_factory_rejects_unknown_model() -> None:
    """An unregistered thermal-system model raises ValueError."""
    with pytest.raises(
        ValueError,
        match="Unknown thermal test system model",
    ):
        ThermalTestSystemFactory.create(
            _instrument(
                InstrumentType.THERMAL_TEST_SYSTEM,
                "unregistered thermal system",
            )
        )


def test_factories_reject_invalid_registrations() -> None:
    """Invalid registry keys and builders fail with clear errors."""
    with pytest.raises(ValueError, match="non-empty"):
        CounterFactory.register(" ", Keysight53220A)
    with pytest.raises(TypeError, match="Counter subclass"):
        CounterFactory.register("counter", object)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        MultimeterFactory.register(" ", Keysight34401A)
    with pytest.raises(ValueError, match="non-empty"):
        PowerSupplyFactory.register(" ", KeysightE36313A)
    with pytest.raises(TypeError, match="PowerSupply subclass"):
        PowerSupplyFactory.register("power supply", object)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        ThermalTestSystemFactory.register(
            " ",
            ExampleThermalTestSystem,
        )
    with pytest.raises(TypeError, match="ThermalTestSystem subclass"):
        ThermalTestSystemFactory.register(  # type: ignore[arg-type]
            "thermal system",
            object,
        )
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
