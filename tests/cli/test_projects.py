"""Tests for the projects CLI."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest
import yaml
from typer.testing import CliRunner

from elims_instruments.cli.projects import app
from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    USBConnection,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    """Create a database with resources that projects can reference."""
    path = tmp_path / "bench.toml"
    database = (tmp_path / "projects.db").as_posix()
    path.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    logger = logging.getLogger(__name__)
    dut_repository = DutCrud(logger, path)
    board_repository = BoardCrud(logger, path)
    try:
        dut_repository.add(
            DutModel(
                id="dut-1",
                asset_tag="DUT-001",
                project="demo-project",
                corner="TT",
                revision="A",
            )
        )
        board_repository.add(
            BoardModel(
                id="board-1",
                asset_tag="BOARD-001",
                type="characterization",
                maker="ELIMS",
                model="Demo Board",
                connection=USBConnection(vendor_id=1, product_id=2),
            )
        )
    finally:
        dut_repository.engine.dispose()
        board_repository.engine.dispose()
    return path


def test_cli_crud_lifecycle(configuration: Path) -> None:
    """Add, fetch, list, update, and delete a relational project."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "project-1",
            "--name",
            "demo-project",
            "--dut",
            "DUT-001",
            "--board",
            "board-1",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output
    added_project = json.loads(added.stdout)
    assert added_project["name"] == "demo-project"
    assert added_project["supported_duts"][0]["id"] == "dut-1"
    assert added_project["supported_boards"][0]["id"] == "board-1"

    fetched = runner.invoke(app, ["get", "project-1", *common])
    assert fetched.exit_code == 0, fetched.output
    assert json.loads(fetched.stdout)["name"] == "demo-project"

    listed = runner.invoke(app, ["gets", *common])
    assert listed.exit_code == 0, listed.output
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        [
            "update",
            "demo-project",
            "--name",
            "renamed-project",
            "--clear-boards",
            *common,
        ],
    )
    assert updated.exit_code == 0, updated.output
    updated_project = json.loads(updated.stdout)
    assert updated_project["name"] == "renamed-project"
    assert updated_project["supported_boards"] == []

    deleted = runner.invoke(app, ["delete", "project-1", *common])
    assert deleted.exit_code == 0, deleted.output
    assert "Deleted project: project-1" in deleted.stdout


def test_export_and_sync_yaml(configuration: Path, tmp_path: Path) -> None:
    """Exported relational project YAML can be edited and synchronized."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "project-1",
            "--name",
            "demo-project",
            "--dut",
            "dut-1",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    yaml_path = tmp_path / "projects.yaml"
    exported = runner.invoke(app, ["export", str(yaml_path), *common])
    assert exported.exit_code == 0, exported.output
    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    records[0]["name"] = "updated-project"
    yaml_path.write_text(yaml.safe_dump(records), encoding="utf-8")

    synced = runner.invoke(app, ["sync", str(yaml_path), *common])
    assert synced.exit_code == 0, synced.output
    assert "Created: 0; Updated: 1" in synced.stdout


def test_add_rejects_missing_resource(configuration: Path) -> None:
    """Project resources must already exist in the asset database."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "project-1",
            "--name",
            "demo-project",
            "--dut",
            "DUT-999",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "DUT not found: DUT-999" in result.output
