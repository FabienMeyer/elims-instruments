"""Tests for the board SQLModel and CRUD repository."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    ComConnection,
    USBConnection,
    SocketConnection,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository(tmp_path: Path) -> BoardCrud:
    configuration = tmp_path / "database.toml"
    database = (tmp_path / "boards.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return BoardCrud(logging.getLogger(__name__), configuration)


def test_com_board_round_trip(repository: BoardCrud) -> None:
    board = BoardModel(
        id="board-1",
        type="controller",
        maker="Acme",
        model="CTRL-1",
        connection=ComConnection(port="COM3", baud_rate=115200),
    )
    repository.add(board)
    stored = repository.fetch("id", "board-1")

    assert stored is not None
    assert isinstance(stored.connection, ComConnection)
    assert stored.connection.baud_rate == 115200


def test_usb_board_can_be_updated_and_removed(repository: BoardCrud) -> None:
    board = BoardModel(
        id="dev-1",
        type="sensor",
        maker="Acme",
        model="SEN-1",
        connection=USBConnection(vendor_id=1, product_id=2),
    )
    repository.add(board)

    updated = repository.update("id", "dev-1", "dev-main")

    assert updated is not None
    assert updated.id == "dev-main"
    assert repository.remove("id", "dev-main") is True
    assert repository.remove("id", "dev-main") is False


def test_invalid_connection_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SocketConnection(ip_address="not-an-ip", port=0)
