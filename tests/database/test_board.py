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
    SocketConnection,
    USBConnection,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository(tmp_path: Path) -> BoardCrud:
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "boards.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return BoardCrud(logging.getLogger(__name__), configuration)


def test_com_board_round_trip(repository: BoardCrud) -> None:
    board = BoardModel(
        id="board-1",
        asset_tag="BOARD-001",
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


def test_usb_board_can_be_updated_by_asset_tag_and_removed(
    repository: BoardCrud,
) -> None:
    board = BoardModel(
        id="dev-1",
        asset_tag="BOARD-002",
        type="sensor",
        maker="Acme",
        model="SEN-1",
        connection=USBConnection(vendor_id=1, product_id=2),
    )
    repository.add(board)

    updated = repository.update_by_asset_tag("BOARD-002", {"model": "SEN-2"})

    assert updated is not None
    assert updated.id == "dev-1"
    assert updated.model == "SEN-2"
    assert repository.remove("id", "dev-1") is True
    assert repository.remove("id", "dev-1") is False


def test_invalid_connection_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SocketConnection(ip_address="not-an-ip", port=0)


def test_board_validation_normalizes_identity() -> None:
    """Board identity values are trimmed and cannot contain only whitespace."""
    board = BoardModel.model_validate(
        {
            "id": " board-1 ",
            "asset_tag": " BOARD-001 ",
            "type": " controller ",
            "maker": " Acme ",
            "model": " CTRL-1 ",
            "connection": ComConnection(port="COM3"),
        }
    )

    assert board.id == "board-1"
    assert board.asset_tag == "BOARD-001"
    assert board.type == "controller"

    with pytest.raises(ValidationError):
        BoardModel.model_validate(
            {
                "id": "board-2",
                "asset_tag": "BOARD-002",
                "type": " ",
                "maker": "Acme",
                "model": "CTRL-2",
                "connection": ComConnection(port="COM4"),
            }
        )


def test_repository_validates_constructed_table_models(repository: BoardCrud) -> None:
    """Persistence rejects invalid models created through SQLModel's constructor."""
    invalid = BoardModel(
        id="board-1",
        asset_tag="BOARD-001",
        type=" ",
        maker="Acme",
        model="CTRL-1",
        connection=ComConnection(port="COM3"),
    )

    with pytest.raises(ValidationError):
        repository.add(invalid)
