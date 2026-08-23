"""Tests for the DUT CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from typer.testing import CliRunner

from elims_instruments.cli.duts import app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    """Create an isolated CLI database configuration."""
    path = tmp_path / "bench.toml"
    database = (tmp_path / "duts.db").as_posix()
    path.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return path


def test_cli_crud_lifecycle(configuration: Path) -> None:
    """Add, fetch, list, update, and delete a DUT."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "dut-1",
            "--asset-tag",
            "DUT-001",
            "--project",
            "demo-project",
            "--corner",
            "TT",
            "--revision",
            "A",
            "--lot-number",
            "LOT-001",
            "--die-x",
            "12",
            "--die-y",
            "8",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output
    assert json.loads(added.stdout)["project"] == "demo-project"

    fetched = runner.invoke(app, ["get", "dut-1", *common])
    assert fetched.exit_code == 0
    assert json.loads(fetched.stdout)["corner"] == "TT"

    listed = runner.invoke(app, ["gets", *common])
    assert listed.exit_code == 0
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        ["update", "DUT-001", "--revision", "B", "--clear-die-position", *common],
    )
    assert updated.exit_code == 0, updated.output
    updated_record = json.loads(updated.stdout)
    assert updated_record["revision"] == "B"
    assert updated_record["die_x"] is None
    assert updated_record["die_y"] is None

    deleted = runner.invoke(app, ["delete", "dut-1", *common])
    assert deleted.exit_code == 0
    assert "Deleted DUT: dut-1" in deleted.stdout


def test_export_and_sync_yaml(configuration: Path, tmp_path: Path) -> None:
    """Exported DUT YAML can be edited and synchronized."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "dut-1",
            "--asset-tag",
            "DUT-001",
            "--project",
            "demo-project",
            "--corner",
            "TT",
            "--revision",
            "A",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    yaml_path = tmp_path / "duts.yaml"
    exported = runner.invoke(app, ["export", str(yaml_path), *common])
    assert exported.exit_code == 0, exported.output
    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    records[0]["corner"] = "FF"
    records.append(
        {
            "id": "dut-2",
            "asset_tag": "DUT-002",
            "project": "demo-project",
            "corner": "SS",
            "revision": "A",
        }
    )
    yaml_path.write_text(yaml.safe_dump(records), encoding="utf-8")

    synced = runner.invoke(app, ["sync", str(yaml_path), *common])
    assert synced.exit_code == 0, synced.output
    assert "Created: 1; Updated: 1" in synced.stdout


def test_add_rejects_partial_die_position(configuration: Path) -> None:
    """The CLI reports an incomplete die position as invalid input."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "dut-1",
            "--asset-tag",
            "DUT-001",
            "--project",
            "demo-project",
            "--corner",
            "TT",
            "--revision",
            "A",
            "--die-x",
            "12",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "die_x and die_y must be provided together" in result.output
