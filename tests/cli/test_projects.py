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
                die_revision="A",
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


@pytest.fixture
def specifications(tmp_path: Path) -> Path:
    """Create revision-dependent project specifications for CLI commands."""
    path = tmp_path / "specifications.yaml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "die_revision": "A",
                    "metal_revision": None,
                    "package_revision": None,
                    "voltage_specifications": [
                        {
                            "name": "VDD",
                            "voltage_limits": {"typical": 1.2},
                            "current_limits": None,
                        }
                    ],
                    "temperature_specifications": [
                        {
                            "name": "DUT",
                            "temperature_limits": {"typical": 25},
                        }
                    ],
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_cli_crud_lifecycle(configuration: Path, specifications: Path) -> None:
    """Add, fetch, list, update, and delete a relational project."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "project-1",
            "--internal-name",
            "demo-project",
            "--datasheet-name",
            "Demo IC",
            "--specifications",
            str(specifications),
            "--dut",
            "DUT-001",
            "--board",
            "board-1",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output
    added_project = json.loads(added.stdout)
    assert added_project["internal_name"] == "demo-project"
    assert added_project["datasheet_name"] == "Demo IC"
    assert (
        added_project["specifications"][0]["voltage_specifications"][0][
            "voltage_limits"
        ]["typical"]
        == 1.2
    )
    assert added_project["supported_duts"][0]["id"] == "dut-1"
    assert added_project["supported_boards"][0]["id"] == "board-1"

    fetched = runner.invoke(app, ["get", "project-1", *common])
    assert fetched.exit_code == 0, fetched.output
    assert json.loads(fetched.stdout)["internal_name"] == "demo-project"

    listed = runner.invoke(app, ["list", *common])
    assert listed.exit_code == 0, listed.output
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        [
            "update",
            "project-1",
            "--internal-name",
            "renamed-project",
            "--datasheet-name",
            "Renamed Demo IC",
            "--clear-duts",
            "--clear-boards",
            *common,
        ],
    )
    assert updated.exit_code == 0, updated.output
    updated_project = json.loads(updated.stdout)
    assert updated_project["internal_name"] == "renamed-project"
    assert updated_project["datasheet_name"] == "Renamed Demo IC"
    assert updated_project["supported_duts"] == []
    assert updated_project["supported_boards"] == []

    deleted = runner.invoke(app, ["delete", "project-1", *common])
    assert deleted.exit_code == 0, deleted.output
    assert "Deleted project: project-1" in deleted.stdout


def test_add_accepts_inline_revision_specifications(configuration: Path) -> None:
    """A project can be created without an external specifications file."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "project-1",
            "--internal-name",
            "demo-project",
            "--datasheet-name",
            "Demo IC",
            "--die-revision",
            "A",
            "--voltage-name",
            "VDD",
            "--voltage-minimum",
            "1.1",
            "--voltage-typical",
            "1.2",
            "--voltage-maximum",
            "1.3",
            "--temperature-name",
            "DUT",
            "--temperature-minimum",
            "-40",
            "--temperature-typical",
            "25",
            "--temperature-maximum",
            "100.1",
            "--dut",
            "DUT-001",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 0, result.output
    project = json.loads(result.stdout)
    profile = project["specifications"][0]
    assert profile["die_revision"] == "A"
    assert profile["voltage_specifications"][0]["voltage_limits"]["typical"] == 1.2
    assert (
        profile["temperature_specifications"][0]["temperature_limits"]["maximum"]
        == 100.1
    )

    updated = CliRunner().invoke(
        app,
        [
            "update",
            "project-1",
            "--die-revision",
            "A",
            "--voltage-typical",
            "1.1",
            "--temperature-typical",
            "30",
            "--config",
            str(configuration),
        ],
    )
    assert updated.exit_code == 0, updated.output
    updated_profile = json.loads(updated.stdout)["specifications"][0]
    assert (
        updated_profile["voltage_specifications"][0]["voltage_limits"]["typical"] == 1.1
    )
    assert (
        updated_profile["temperature_specifications"][0]["temperature_limits"][
            "typical"
        ]
        == 30.0
    )


def test_export_and_sync_yaml(
    configuration: Path,
    specifications: Path,
    tmp_path: Path,
) -> None:
    """Exported relational project YAML can be edited and synchronized."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "project-1",
            "--internal-name",
            "demo-project",
            "--datasheet-name",
            "Demo IC",
            "--specifications",
            str(specifications),
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
    records[0]["datasheet_name"] = "Updated Demo IC"
    yaml_path.write_text(yaml.safe_dump(records), encoding="utf-8")

    synced = runner.invoke(app, ["sync", str(yaml_path), *common])
    assert synced.exit_code == 0, synced.output
    assert "Created: 0; Updated: 1" in synced.stdout


def test_sync_reports_unmatched_dut_revision(
    configuration: Path,
    specifications: Path,
    tmp_path: Path,
) -> None:
    """A revision mismatch is reported without leaking an exception."""
    profiles = yaml.safe_load(specifications.read_text(encoding="utf-8"))
    profiles[0]["die_revision"] = "B"
    source = tmp_path / "projects.yaml"
    source.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "project-1",
                    "internal_name": "demo-project",
                    "datasheet_name": "Demo IC",
                    "specifications": profiles,
                    "supported_duts": [
                        {
                            "id": "dut-1",
                            "asset_tag": "DUT-001",
                            "project": "demo-project",
                            "corner": "TT",
                            "die_revision": "A",
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["sync", str(source), "--config", str(configuration)],
    )

    assert result.exit_code == 1
    assert "Invalid project YAML" in result.output
    assert "No project specifications for DUT revisions" in result.output
    assert result.exception is not None
    assert "Traceback" not in result.output


def test_sync_reports_internal_name_conflict(
    configuration: Path,
    specifications: Path,
    tmp_path: Path,
) -> None:
    """A database uniqueness conflict is reported without a traceback."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "project-1",
            "--internal-name",
            "demo-project",
            "--datasheet-name",
            "Demo IC",
            "--specifications",
            str(specifications),
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    source = tmp_path / "projects.yaml"
    source.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "project-2",
                    "internal_name": "demo-project",
                    "datasheet_name": "Conflicting Demo IC",
                    "specifications": yaml.safe_load(
                        specifications.read_text(encoding="utf-8")
                    ),
                }
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["sync", str(source), *common])

    assert result.exit_code == 1
    assert "Could not synchronize projects" in result.output
    assert "project ID or internal name already exists" in result.output
    assert result.exception is not None
    assert "Traceback" not in result.output


def test_update_rejects_rename_with_attached_dut(
    configuration: Path,
    specifications: Path,
) -> None:
    """Renaming cannot leave an attached DUT assigned to the previous name."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "project-1",
            "--internal-name",
            "demo-project",
            "--datasheet-name",
            "Demo IC",
            "--specifications",
            str(specifications),
            "--dut",
            "dut-1",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    result = runner.invoke(
        app,
        ["update", "project-1", "--internal-name", "renamed-project", *common],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 2
    assert (
        "DUT dut-1 belongs to project 'demo-project', not 'renamed-project'"
        in result.output
    )


@pytest.mark.parametrize(
    ("replacement_option", "identifier", "clear_option"),
    [
        ("--dut", "dut-1", "--clear-duts"),
        ("--board", "board-1", "--clear-boards"),
    ],
)
def test_update_rejects_replacement_with_clear_flag(
    configuration: Path,
    replacement_option: str,
    identifier: str,
    clear_option: str,
) -> None:
    """A relationship cannot be replaced and cleared in the same update."""
    result = CliRunner().invoke(
        app,
        [
            "update",
            "project-1",
            replacement_option,
            identifier,
            clear_option,
            "--config",
            str(configuration),
        ],
        env={"COLUMNS": "120"},
    )

    assert result.exit_code == 2
    assert (
        f"{replacement_option} cannot be combined with {clear_option}"
        in result.output
    )


def test_add_rejects_missing_resource(
    configuration: Path,
    specifications: Path,
) -> None:
    """Project resources must already exist in the asset database."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "project-1",
            "--internal-name",
            "demo-project",
            "--datasheet-name",
            "Demo IC",
            "--specifications",
            str(specifications),
            "--dut",
            "DUT-999",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "DUT not found: DUT-999" in result.output


def test_project_specification_errors_are_cli_errors(
    configuration: Path,
    specifications: Path,
) -> None:
    """Invalid or ambiguous specification inputs produce parameter errors."""
    runner = CliRunner()
    common = [
        "add",
        "project-1",
        "--internal-name",
        "demo-project",
        "--datasheet-name",
        "Demo IC",
        "--config",
        str(configuration),
    ]

    mixed_sources = runner.invoke(
        app,
        [
            *common,
            "--specifications",
            str(specifications),
            "--voltage-name",
            "CORE",
        ],
    )
    assert mixed_sources.exit_code == 2
    assert "cannot be combined" in mixed_sources.output

    incomplete_inline = runner.invoke(
        app,
        [*common, "--voltage-name", "CORE"],
    )
    assert incomplete_inline.exit_code == 2
    assert "provide --specifications" in incomplete_inline.output
    assert "die-revision" in incomplete_inline.output

    unsupported_revision = runner.invoke(
        app,
        [
            *common,
            "--die-revision",
            "B",
            "--voltage-typical",
            "1.2",
            "--temperature-typical",
            "25",
            "--dut",
            "DUT-001",
        ],
    )
    assert unsupported_revision.exit_code == 2
    assert "No project specifications for DUT revisions" in unsupported_revision.output

    unsupported_precision = runner.invoke(
        app,
        [
            *common,
            "--die-revision",
            "A",
            "--voltage-typical",
            "1.2",
            "--temperature-typical",
            "25.05",
        ],
    )
    assert unsupported_precision.exit_code == 2
    assert "not representable in 0.1" in unsupported_precision.output
