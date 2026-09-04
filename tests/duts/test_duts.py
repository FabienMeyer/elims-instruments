"""Tests for DUT creation and collection access."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from elims_instruments.database import DutCrud, DutModel
from elims_instruments.duts import (
    Dut,
    DutAssetNotFoundError,
    DutFactory,
    create_duts,
)

if TYPE_CHECKING:
    from pathlib import Path


class CharacterizationDut(Dut):
    """Concrete DUT used by factory tests."""

    def get_id(self) -> str:
        """Return the database DUT ID."""
        return self.dut.id


@pytest.fixture
def bench_configuration(tmp_path: Path) -> Path:
    """Create a database containing one IC DUT."""
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "duts.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    repository = DutCrud(logging.getLogger(__name__), configuration)
    repository.add(
        DutModel(
            id="dut-1",
            asset_tag="DUT-001",
            project="demo-project",
            corner="TT",
            revision="A",
            lot_number="LOT-001",
        )
    )
    return configuration


def test_create_duts_uses_registered_project(bench_configuration: Path) -> None:
    """A registered project creates a concrete DUT object."""
    DutFactory.register("demo-project", CharacterizationDut)
    duts = create_duts({"characterized_ic": "DUT-001"}, bench_configuration)

    assert type(duts.characterized_ic) is CharacterizationDut
    assert duts.characterized_ic.get_id() == "dut-1"
    assert duts["characterized_ic"].dut.asset_tag == "DUT-001"
    assert list(duts) == ["characterized_ic"]


def test_factory_normalizes_registered_project() -> None:
    """Project lookup ignores surrounding whitespace and letter case."""
    model = DutModel(
        id="dut-2",
        asset_tag="DUT-002",
        project="registered-project",
        corner="SS",
        revision="B",
    )
    DutFactory.register(" Registered-Project ", CharacterizationDut)

    assert isinstance(DutFactory.create(model), CharacterizationDut)


def test_factory_rejects_unregistered_project() -> None:
    """A DUT whose project has no concrete builder is rejected."""
    model = DutModel(
        id="dut-3",
        asset_tag="DUT-003",
        project="unregistered-project",
        corner="TT",
        revision="A",
    )

    with pytest.raises(ValueError, match="Unknown DUT project"):
        DutFactory.create(model)


def test_factory_rejects_invalid_registration() -> None:
    """Factory registration fails clearly for invalid inputs."""
    with pytest.raises(ValueError, match="non-empty"):
        DutFactory.register(" ", CharacterizationDut)

    with pytest.raises(TypeError, match="callable"):
        DutFactory.register("demo-project", None)  # type: ignore[arg-type]


def test_create_duts_rejects_missing_asset(bench_configuration: Path) -> None:
    """A missing DUT asset tag raises a DUT-specific error."""
    with pytest.raises(DutAssetNotFoundError, match="DUT-999"):
        create_duts({"missing": "DUT-999"}, bench_configuration)
