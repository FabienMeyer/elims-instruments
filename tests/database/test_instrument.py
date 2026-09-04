"""Tests for the instrument SQLModel and CRUD repository."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from elims_instruments.database import (
    CalibrationStatus,
    DuplicateAssetTagError,
    InstrumentCrud,
    InstrumentModel,
    InstrumentRevisionAction,
    InstrumentType,
    SocketConnection,
    VisaConnection,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository(tmp_path: Path) -> InstrumentCrud:
    """Create an isolated SQLite instrument repository."""
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "instruments.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return InstrumentCrud(logging.getLogger(__name__), configuration)


def test_socket_instrument_round_trip(repository: InstrumentCrud) -> None:
    """A socket instrument retains its nested connection after persistence."""
    instrument = InstrumentModel(
        id="scope-1",
        asset_tag="SCOPE-001",
        type=InstrumentType.OSCILLOSCOPE,
        maker="Keysight",
        model="DSOX1204G",
        calibration_date=date(2026, 1, 15),
        calibration_due_date=date(2027, 1, 15),
        calibration_certificate_number="CAL-2026-001",
        calibration_status=CalibrationStatus.VALID,
        connection=SocketConnection(ip_address="192.168.1.10", port=5025),
    )

    repository.add(instrument)
    stored = repository.fetch("id", "scope-1")

    assert stored is not None
    assert stored.type is InstrumentType.OSCILLOSCOPE
    assert isinstance(stored.connection, SocketConnection)
    assert stored.connection.port == 5025
    assert stored.calibration_date == date(2026, 1, 15)
    assert stored.calibration_due_date == date(2027, 1, 15)
    assert stored.calibration_certificate_number == "CAL-2026-001"
    assert stored.calibration_status is CalibrationStatus.VALID
    assert repository.fetchall() == [stored]


def test_calibration_due_date_cannot_precede_calibration_date() -> None:
    """Calibration date ranges are validated before persistence."""
    with pytest.raises(ValidationError, match="calibration_due_date"):
        InstrumentModel.model_validate(
            {
                "id": "dmm-1",
                "asset_tag": "DMM-001",
                "type": "multimeter",
                "maker": "Keysight",
                "model": "34465A",
                "calibration_date": "2026-09-06",
                "calibration_due_date": "2026-09-05",
                "connection": VisaConnection(resource_name="GPIB0::1::INSTR"),
            }
        )


def test_calibration_status_is_validated_and_defaults_to_unknown() -> None:
    """Calibration status uses the declared lifecycle states."""
    instrument_data = {
        "id": "dmm-1",
        "asset_tag": "DMM-001",
        "type": "multimeter",
        "maker": "Keysight",
        "model": "34465A",
        "connection": VisaConnection(resource_name="GPIB0::1::INSTR"),
    }

    instrument = InstrumentModel.model_validate(instrument_data)

    assert instrument.calibration_status is CalibrationStatus.UNKNOWN
    with pytest.raises(ValidationError, match="calibration_status"):
        InstrumentModel.model_validate(
            {**instrument_data, "calibration_status": "unrecognized"}
        )


def test_visa_instrument_can_be_updated_by_asset_tag_and_removed(
    repository: InstrumentCrud,
) -> None:
    """CRUD update and removal report their resulting records."""
    instrument = InstrumentModel(
        id="dmm-1",
        asset_tag="DMM-001",
        type=InstrumentType.MULTIMETER,
        maker="Keysight",
        model="34461A",
        connection=VisaConnection(resource_name="TCPIP0::dmm::INSTR"),
    )
    repository.add(instrument)

    updated = repository.update_by_asset_tag("DMM-001", {"model": "34465A"})

    assert updated is not None
    assert updated.id == "dmm-1"
    assert updated.model == "34465A"
    assert repository.remove("id", "dmm-1") is True
    assert repository.remove("id", "dmm-1") is False


def test_instrument_changes_are_audited_and_historically_queryable(
    repository: InstrumentCrud,
) -> None:
    """Every state change is retained while normal reads return the latest state."""
    instrument = InstrumentModel(
        id="dmm-1",
        asset_tag="DMM-001",
        type=InstrumentType.MULTIMETER,
        maker="Keysight",
        model="34461A",
        connection=VisaConnection(resource_name="GPIB0::1::INSTR"),
    )
    repository.add(instrument)
    created_revision = repository.history("DMM-001")[0]

    updated = repository.update_by_asset_tag("DMM-001", {"model": "34465A"})

    assert updated is not None
    assert repository.fetch("asset_tag", "DMM-001").model == "34465A"
    revisions = repository.history("DMM-001")
    assert [revision.action for revision in revisions] == [
        InstrumentRevisionAction.CREATED,
        InstrumentRevisionAction.UPDATED,
    ]
    assert revisions[0].snapshot["model"] == "34461A"
    assert revisions[1].snapshot["model"] == "34465A"
    historical = repository.fetch_at("DMM-001", created_revision.recorded_at)
    assert historical is not None
    assert historical.model == "34461A"

    repository.upsert_many([updated])
    assert len(repository.history_for_instrument("dmm-1")) == 2

    renamed = repository.update_by_asset_tag(
        "DMM-001",
        {"asset_tag": "DMM-NEW"},
    )
    assert renamed is not None
    renamed_revision = repository.history("DMM-NEW")[-1]
    assert repository.fetch_at("DMM-001", renamed_revision.recorded_at) is None
    historical = repository.fetch_at("DMM-NEW", renamed_revision.recorded_at)
    assert historical is not None
    assert historical.asset_tag == "DMM-NEW"
    assert len(repository.history_for_instrument("dmm-1")) == 3

    assert repository.remove("asset_tag", "DMM-NEW") is True
    revisions = repository.history("DMM-NEW")
    assert revisions[-1].action is InstrumentRevisionAction.DELETED
    assert repository.fetch_at("DMM-NEW", revisions[-1].recorded_at) is None


def test_unknown_field_is_rejected(repository: InstrumentCrud) -> None:
    """Queries cannot address arbitrary model attributes."""
    with pytest.raises(ValueError, match="Unknown InstrumentModel field"):
        repository.fetch("missing", "value")


def test_invalid_connection_is_rejected() -> None:
    """Connection constraints are enforced before database access."""
    with pytest.raises(ValidationError):
        SocketConnection(ip_address="not-an-ip", port=0)


def test_unknown_instrument_type_is_rejected() -> None:
    """Only declared instrument categories are accepted."""
    with pytest.raises(ValidationError, match="type"):
        InstrumentModel.model_validate(
            {
                "id": "analyzer-1",
                "asset_tag": "ANALYZER-001",
                "type": "unknown",
                "maker": "Acme",
                "model": "A-1",
                "connection": VisaConnection(resource_name="GPIB0::3::INSTR"),
            }
        )


def test_upsert_many_creates_and_fully_updates(repository: InstrumentCrud) -> None:
    """Bulk upsert creates missing IDs and replaces all fields on existing IDs."""
    repository.add(
        InstrumentModel(
            id="scope-1",
            asset_tag="SCOPE-001",
            type=InstrumentType.OSCILLOSCOPE,
            maker="Keysight",
            model="old",
            serial_number="old-serial",
            connection=SocketConnection(ip_address="192.168.1.10", port=5025),
        )
    )

    created, updated = repository.upsert_many(
        [
            InstrumentModel(
                id="scope-1",
                asset_tag="SCOPE-001",
                type=InstrumentType.OSCILLOSCOPE,
                maker="Keysight",
                model="new",
                serial_number=None,
                connection=VisaConnection(resource_name="TCPIP0::scope::INSTR"),
            ),
            InstrumentModel(
                id="dmm-1",
                asset_tag="DMM-001",
                type=InstrumentType.MULTIMETER,
                maker="Keysight",
                model="34461A",
                connection=VisaConnection(resource_name="TCPIP0::dmm::INSTR"),
            ),
        ]
    )

    assert (created, updated) == (1, 1)
    scope = repository.fetch("id", "scope-1")
    assert scope is not None
    assert scope.model == "new"
    assert scope.serial_number is None
    assert isinstance(scope.connection, VisaConnection)


def test_upsert_many_rejects_duplicate_ids(repository: InstrumentCrud) -> None:
    """Bulk upsert rejects ambiguous duplicate IDs before changing the database."""
    instrument = InstrumentModel(
        id="scope-1",
        asset_tag="SCOPE-001",
        type=InstrumentType.OSCILLOSCOPE,
        maker="Keysight",
        model="DSOX1204G",
        connection=SocketConnection(ip_address="192.168.1.10", port=5025),
    )

    with pytest.raises(ValueError, match="duplicate IDs"):
        repository.upsert_many([instrument, instrument])

    assert repository.fetchall() == []


def test_asset_tag_must_have_at_least_five_characters() -> None:
    """Asset tags shorter than five characters are rejected."""
    with pytest.raises(ValidationError, match="asset_tag"):
        InstrumentModel.model_validate(
            {
                "id": "dmm-1",
                "asset_tag": "DMM1",
                "type": "multimeter",
                "maker": "Keysight",
                "model": "34461A",
                "connection": VisaConnection(resource_name="GPIB0::1::INSTR"),
            }
        )


def test_asset_tag_must_be_unique(repository: InstrumentCrud) -> None:
    """The database rejects duplicate instrument asset tags."""
    first = InstrumentModel.model_validate(
        {
            "id": "dmm-1",
            "asset_tag": "DMM-001",
            "type": "multimeter",
            "maker": "Keysight",
            "model": "34461A",
            "connection": VisaConnection(resource_name="GPIB0::1::INSTR"),
        }
    )
    duplicate = InstrumentModel.model_validate(
        {
            "id": "dmm-2",
            "asset_tag": "DMM-001",
            "type": "multimeter",
            "maker": "Keysight",
            "model": "34465A",
            "connection": VisaConnection(resource_name="GPIB0::2::INSTR"),
        }
    )

    repository.add(first)
    with pytest.raises(DuplicateAssetTagError, match="DMM-001"):
        repository.add(duplicate)


def test_update_rejects_duplicate_asset_tag(repository: InstrumentCrud) -> None:
    """An update cannot take another instrument's asset tag."""
    instruments = [
        InstrumentModel.model_validate(
            {
                "id": f"dmm-{number}",
                "asset_tag": f"DMM-00{number}",
                "type": "multimeter",
                "maker": "Keysight",
                "model": "34461A",
                "connection": VisaConnection(resource_name=f"GPIB0::{number}::INSTR"),
            }
        )
        for number in (1, 2)
    ]
    repository.upsert_many(instruments)

    with pytest.raises(DuplicateAssetTagError, match="DMM-002"):
        repository.update_by_asset_tag("DMM-001", {"asset_tag": "DMM-002"})

    assert repository.fetch("id", "dmm-1").asset_tag == "DMM-001"


def test_instrument_validation_normalizes_identity() -> None:
    """Instrument identity values are trimmed and reject whitespace-only input."""
    instrument = InstrumentModel.model_validate(
        {
            "id": " dmm-1 ",
            "asset_tag": " DMM-001 ",
            "type": "multimeter",
            "maker": " Keysight ",
            "model": " 34461A ",
            "connection": VisaConnection(resource_name="GPIB0::1::INSTR"),
        }
    )

    assert instrument.id == "dmm-1"
    assert instrument.asset_tag == "DMM-001"
    assert instrument.model == "34461A"

    with pytest.raises(ValidationError):
        InstrumentModel.model_validate(
            {
                "id": "dmm-2",
                "asset_tag": "DMM-002",
                "type": "multimeter",
                "maker": " ",
                "model": "34465A",
                "connection": VisaConnection(resource_name="GPIB0::2::INSTR"),
            }
        )


def test_repository_validates_constructed_table_models(
    repository: InstrumentCrud,
) -> None:
    """Persistence rejects invalid models created through SQLModel's constructor."""
    invalid = InstrumentModel(
        id="dmm-1",
        asset_tag="DMM-001",
        type=InstrumentType.MULTIMETER,
        maker=" ",
        model="34461A",
        connection=VisaConnection(resource_name="GPIB0::1::INSTR"),
    )

    with pytest.raises(ValidationError):
        repository.add(invalid)
