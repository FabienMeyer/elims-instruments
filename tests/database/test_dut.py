"""Tests for the DUT SQLModel and CRUD repository."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from elims_instruments.database import DutCrud, DutModel, parse_dut_list

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository(tmp_path: Path) -> DutCrud:
    """Create an isolated SQLite DUT repository."""
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "duts.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return DutCrud(logging.getLogger(__name__), configuration)


def test_ic_dut_round_trip(repository: DutCrud) -> None:
    """IC traceability fields survive persistence."""
    dut = DutModel(
        id="dut-1",
        asset_tag="DUT-001",
        project="demo-project",
        corner="TT",
        revision="A",
        lot_number="LOT-001",
        wafer_id="W01",
        die_x=12,
        die_y=8,
    )

    repository.add(dut)
    stored = repository.fetch("asset_tag", "DUT-001")

    assert stored is not None
    assert stored.project == "demo-project"
    assert stored.corner == "TT"
    assert stored.revision == "A"
    assert stored.lot_number == "LOT-001"
    assert (stored.die_x, stored.die_y) == (12, 8)


def test_parse_dut_list_validates_records() -> None:
    """Raw DUT lists use the same model validation as CRUD operations."""
    records = parse_dut_list(
        [
            {
                "id": "dut-2",
                "asset_tag": "DUT-002",
                "project": "demo-project",
                "corner": "FF",
                "revision": "B",
            }
        ]
    )

    assert records[0].asset_tag == "DUT-002"

    with pytest.raises(ValidationError):
        parse_dut_list([{"id": "dut-3", "asset_tag": "bad"}])


def test_dut_validation_normalizes_identity() -> None:
    """Identity values are trimmed and cannot contain only whitespace."""
    dut = DutModel.model_validate(
        {
            "id": " dut-1 ",
            "asset_tag": " DUT-001 ",
            "project": " demo-project ",
            "corner": " TT ",
            "revision": " A ",
        }
    )

    assert dut.id == "dut-1"
    assert dut.asset_tag == "DUT-001"
    assert dut.project == "demo-project"

    with pytest.raises(ValidationError):
        DutModel.model_validate(
            {
                "id": "dut-2",
                "asset_tag": "DUT-002",
                "project": " ",
                "corner": "TT",
                "revision": "A",
            }
        )


def test_dut_validation_requires_complete_die_position() -> None:
    """A die location is either complete or absent."""
    with pytest.raises(ValidationError, match="provided together"):
        DutModel.model_validate(
            {
                "id": "dut-1",
                "asset_tag": "DUT-001",
                "project": "demo-project",
                "corner": "TT",
                "revision": "A",
                "die_x": 12,
            }
        )


def test_repository_validates_constructed_table_models(repository: DutCrud) -> None:
    """Persistence rejects invalid models created through SQLModel's constructor."""
    incomplete = DutModel(
        id="dut-1",
        asset_tag="DUT-001",
        project="demo-project",
        corner="TT",
        revision="A",
        die_x=12,
    )

    with pytest.raises(ValidationError, match="provided together"):
        repository.add(incomplete)
