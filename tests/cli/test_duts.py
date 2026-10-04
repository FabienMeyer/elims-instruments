"""Tests for the DUT CLI."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest
import yaml
from sqlalchemy import text
from typer.testing import CliRunner

from elims_instruments.cli.duts import app
from elims_instruments.database import DutCrud

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
            "--die-revision",
            "A",
            "--metal-revision",
            "0",
            "--package-revision",
            "R1",
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

    listed = runner.invoke(app, ["list", *common])
    assert listed.exit_code == 0
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        [
            "update",
            "dut-1",
            "--die-revision",
            "B",
            "--metal-revision",
            "1",
            "--package-revision",
            "R2",
            "--clear-die-position",
            *common,
        ],
    )
    assert updated.exit_code == 0, updated.output
    updated_record = json.loads(updated.stdout)
    assert updated_record["die_revision"] == "B"
    assert updated_record["metal_revision"] == 1
    assert updated_record["package_revision"] == "R2"
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
            "--die-revision",
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
            "die_revision": "A",
            "metal_revision": 2,
            "package_revision": "R3",
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
            "--die-revision",
            "A",
            "--die-x",
            "12",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "die_x and die_y must be provided together" in result.output


def test_update_clears_optional_revisions(configuration: Path) -> None:
    """Optional metal and package revisions can be removed through the CLI."""
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
            "--die-revision",
            "A",
            "--metal-revision",
            "1",
            "--package-revision",
            "R1",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    updated = runner.invoke(
        app,
        [
            "update",
            "dut-1",
            "--clear-metal-revision",
            "--clear-package-revision",
            *common,
        ],
    )

    assert updated.exit_code == 0, updated.output
    record = json.loads(updated.stdout)
    assert record["metal_revision"] is None
    assert record["package_revision"] is None


@pytest.mark.parametrize(
    "options",
    [
        ["--metal-revision", "1", "--clear-metal-revision"],
        ["--package-revision", "R1", "--clear-package-revision"],
    ],
)
def test_update_rejects_setting_and_clearing_revision(
    configuration: Path,
    options: list[str],
) -> None:
    """A revision cannot be assigned and cleared in the same command."""
    result = CliRunner().invoke(
        app,
        ["update", "dut-1", *options, "--config", str(configuration)],
    )

    assert result.exit_code == 2
    assert "cannot set and clear" in result.output


def test_delete_rejects_dut_referenced_by_project(configuration: Path) -> None:
    """The CLI explains why a project-supported DUT cannot be deleted."""
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
            "--die-revision",
            "A",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    repository = DutCrud(logging.getLogger(__name__), configuration)
    try:
        with repository.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects "
                    "(id, internal_name, datasheet_name, specifications) "
                    "VALUES ('project-1', 'demo-project', 'Demo Project', '[]')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO project_supported_duts (project_id, dut_id) "
                    "VALUES ('project-1', 'dut-1')"
                )
            )
    finally:
        repository.engine.dispose()

    deleted = runner.invoke(app, ["delete", "dut-1", *common])

    assert deleted.exit_code == 1
    assert (
        "DUT is referenced by a project and cannot be deleted: dut-1"
        in deleted.output
    )
