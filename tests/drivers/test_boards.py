"""Tests for board driver creation and collection access."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from elims_instruments.boards import (
    Board,
    BoardAssetNotFoundError,
    BoardFactory,
    create_boards,
)
from elims_instruments.database import BoardCrud, BoardModel, USBConnection

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def bench_configuration(tmp_path: Path) -> Path:
    """Create a database containing a single board."""
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "boards.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    repository = BoardCrud(logging.getLogger(__name__), configuration)
    repository.add(
        BoardModel(
            id="board-1",
            asset_tag="BRD-001",
            type="fixture",
            maker="ELIMS",
            model="Fixture A",
            connection=USBConnection(vendor_id=1, product_id=2),
        )
    )
    return configuration


def test_create_boards_uses_base_driver(
    bench_configuration: Path,
) -> None:
    """An unregistered board type uses the base board driver."""
    boards = create_boards(
        {"characterization_board": "BRD-001"},
        bench_configuration,
    )

    assert type(boards.characterization_board) is Board
    assert boards["characterization_board"].board.asset_tag == "BRD-001"
    assert list(boards) == ["characterization_board"]


def test_create_boards_uses_registered_driver() -> None:
    """A registered board type can replace the base driver."""

    class FixtureBoard(Board):
        pass

    model = BoardModel(
        id="board-2",
        asset_tag="BRD-002",
        type="registered-fixture",
        maker="ELIMS",
        model="Fixture B",
        connection=USBConnection(vendor_id=1, product_id=3),
    )
    BoardFactory.register(" Registered-Fixture ", FixtureBoard)

    assert isinstance(BoardFactory.create(model), FixtureBoard)


def test_factory_rejects_invalid_registration() -> None:
    """Factory registration fails clearly for invalid inputs."""
    with pytest.raises(ValueError, match="non-empty"):
        BoardFactory.register(" ", Board)

    with pytest.raises(TypeError, match="callable"):
        BoardFactory.register("fixture", None)  # type: ignore[arg-type]


def test_create_boards_rejects_missing_asset(
    bench_configuration: Path,
) -> None:
    """A missing board asset tag raises a board-specific error."""
    with pytest.raises(BoardAssetNotFoundError, match="BRD-999"):
        create_boards({"missing": "BRD-999"}, bench_configuration)
