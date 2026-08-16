"""Tests for the instrument CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from typer.testing import CliRunner

from elims_instruments.cli.instruments import app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    """Create an isolated CLI database configuration."""
    path = tmp_path / "database.toml"
    database = (tmp_path / "instruments.db").as_posix()
    path.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return path


def test_commands_follow_instrument_workflow_order() -> None:
    """Help lists commands in their expected workflow order."""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    commands = [
        "add",
        "get",
        "gets",
        "update",
        "delete",
        "sync",
        "export",
    ]
    positions = [result.output.index(command) for command in commands]
    assert positions == sorted(positions)


def test_cli_crud_lifecycle(configuration: Path) -> None:
    """CLI commands add, get, get all, update, and delete by ID."""
    runner = CliRunner()
    common = ["--config", str(configuration)]

    added = runner.invoke(
        app,
        [
            "add",
            "scope-1",
            "--type",
            "oscilloscope",
            "--maker",
            "Keysight",
            "--model",
            "DSOX1204G",
            "--connection",
            "socket",
            "--ip-address",
            "192.168.1.10",
            "--port",
            "5025",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output
    assert json.loads(added.stdout)["id"] == "scope-1"

    fetched = runner.invoke(app, ["get", "scope-1", *common])
    assert fetched.exit_code == 0
    assert json.loads(fetched.stdout)["model"] == "DSOX1204G"

    listed = runner.invoke(app, ["gets", *common])
    assert listed.exit_code == 0
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        ["update", "scope-1", "--model", "DSOX1204A", *common],
    )
    assert updated.exit_code == 0, updated.output
    assert json.loads(updated.stdout)["model"] == "DSOX1204A"

    deleted = runner.invoke(app, ["delete", "scope-1", *common])
    assert deleted.exit_code == 0
    assert "Deleted instrument: scope-1" in deleted.stdout

    missing = runner.invoke(app, ["get", "scope-1", *common])
    assert missing.exit_code == 1
    assert "Instrument not found: scope-1" in missing.output


def test_add_rejects_incomplete_socket_connection(configuration: Path) -> None:
    """Socket additions require an address and port."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "scope-1",
            "--type",
            "oscilloscope",
            "--maker",
            "Keysight",
            "--model",
            "DSOX1204G",
            "--connection",
            "socket",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "ip-address" in result.output
    assert "port" in result.output


def test_export_and_sync_yaml(configuration: Path, tmp_path: Path) -> None:
    """A YAML export can update existing IDs and add missing IDs."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "scope-1",
            "--type",
            "oscilloscope",
            "--maker",
            "Keysight",
            "--model",
            "old-model",
            "--connection",
            "socket",
            "--ip-address",
            "192.168.1.10",
            "--port",
            "5025",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    yaml_path = tmp_path / "instruments.yaml"
    exported = runner.invoke(app, ["export", str(yaml_path), *common])
    assert exported.exit_code == 0, exported.output

    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    records[0]["model"] = "new-model"
    records.append(
        {
            "id": "dmm-1",
            "type": "multimeter",
            "maker": "Keysight",
            "model": "34461A",
            "serial_number": None,
            "connection": {
                "kind": "visa",
                "resource_name": "TCPIP0::dmm::INSTR",
                "timeout_seconds": 30.0,
                "read_termination": "\n",
                "write_termination": "\n",
            },
        }
    )
    yaml_path.write_text(yaml.safe_dump(records), encoding="utf-8")

    synced = runner.invoke(app, ["sync", str(yaml_path), *common])
    assert synced.exit_code == 0, synced.output
    assert "Created: 1; Updated: 1" in synced.stdout

    listed = runner.invoke(app, ["gets", *common])
    stored = {item["id"]: item for item in json.loads(listed.stdout)}
    assert stored["scope-1"]["model"] == "new-model"
    assert stored["dmm-1"]["connection"]["kind"] == "visa"
