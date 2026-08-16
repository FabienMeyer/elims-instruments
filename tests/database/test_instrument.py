"""Tests for the instrument SQLModel and CRUD repository."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from elims_instruments.database import (
    InstrumentCrud,
    InstrumentModel,
    SocketConnection,
    VisaConnection,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository(tmp_path: Path) -> InstrumentCrud:
    """Create an isolated SQLite instrument repository."""
    configuration = tmp_path / "database.toml"
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
        type="oscilloscope",
        maker="Keysight",
        model="DSOX1204G",
        connection=SocketConnection(ip_address="192.168.1.10", port=5025),
    )

    repository.add(instrument)
    stored = repository.fetch("id", "scope-1")

    assert stored is not None
    assert isinstance(stored.connection, SocketConnection)
    assert stored.connection.port == 5025
    assert repository.fetchall() == [stored]


def test_visa_instrument_can_be_updated_and_removed(
    repository: InstrumentCrud,
) -> None:
    """CRUD update and removal report their resulting records."""
    instrument = InstrumentModel(
        id="dmm-1",
        type="multimeter",
        maker="Keysight",
        model="34461A",
        connection=VisaConnection(resource_name="TCPIP0::dmm::INSTR"),
    )
    repository.add(instrument)

    updated = repository.update("id", "dmm-1", "dmm-main")

    assert updated is not None
    assert updated.id == "dmm-main"
    assert repository.remove("id", "dmm-main") is True
    assert repository.remove("id", "dmm-main") is False


def test_unknown_field_is_rejected(repository: InstrumentCrud) -> None:
    """Queries cannot address arbitrary model attributes."""
    with pytest.raises(ValueError, match="Unknown InstrumentModel field"):
        repository.fetch("missing", "value")


def test_invalid_connection_is_rejected() -> None:
    """Connection constraints are enforced before database access."""
    with pytest.raises(ValidationError):
        SocketConnection(ip_address="not-an-ip", port=0)


def test_upsert_many_creates_and_fully_updates(repository: InstrumentCrud) -> None:
    """Bulk upsert creates missing IDs and replaces all fields on existing IDs."""
    repository.add(
        InstrumentModel(
            id="scope-1",
            type="oscilloscope",
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
                type="oscilloscope",
                maker="Keysight",
                model="new",
                serial_number=None,
                connection=VisaConnection(resource_name="TCPIP0::scope::INSTR"),
            ),
            InstrumentModel(
                id="dmm-1",
                type="multimeter",
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
        type="oscilloscope",
        maker="Keysight",
        model="DSOX1204G",
        connection=SocketConnection(ip_address="192.168.1.10", port=5025),
    )

    with pytest.raises(ValueError, match="duplicate IDs"):
        repository.upsert_many([instrument, instrument])

    assert repository.fetchall() == []
