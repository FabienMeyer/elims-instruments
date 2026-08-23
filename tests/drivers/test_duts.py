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


def test_create_duts_uses_base_object(bench_configuration: Path) -> None:
    """An unregistered DUT type uses the base DUT object."""
    duts = create_duts({"characterized_ic": "DUT-001"}, bench_configuration)

    assert type(duts.characterized_ic) is Dut
    assert duts["characterized_ic"].dut.asset_tag == "DUT-001"
    assert list(duts) == ["characterized_ic"]


def test_create_duts_uses_registered_project() -> None:
    """A registered DUT project can replace the base object."""

    class CharacterizationDut(Dut):
        pass

    model = DutModel(
        id="dut-2",
        asset_tag="DUT-002",
        project="registered-project",
        corner="SS",
        revision="B",
    )
    DutFactory.register(" Registered-Project ", CharacterizationDut)

    assert isinstance(DutFactory.create(model), CharacterizationDut)


def test_factory_rejects_invalid_registration() -> None:
    """Factory registration fails clearly for invalid inputs."""
    with pytest.raises(ValueError, match="non-empty"):
        DutFactory.register(" ", Dut)

    with pytest.raises(TypeError, match="callable"):
        DutFactory.register("demo-project", None)  # type: ignore[arg-type]


def test_create_duts_rejects_missing_asset(bench_configuration: Path) -> None:
    """A missing DUT asset tag raises a DUT-specific error."""
    with pytest.raises(DutAssetNotFoundError, match="DUT-999"):
        create_duts({"missing": "DUT-999"}, bench_configuration)
