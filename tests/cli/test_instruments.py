"""Tests for the instrument CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from click import unstyle
from typer.testing import CliRunner

from elims_instruments.cli.instruments import app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    """Create an isolated CLI database configuration."""
    path = tmp_path / "bench.toml"
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
        "list",
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
            "--asset-tag",
            "SCOPE-001",
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
            "--calibration-date",
            "2026-01-15",
            "--calibration-due-date",
            "2027-01-15",
            "--calibration-certificate-number",
            "CERT-42",
            "--calibration-status",
            "valid",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output
    added_record = json.loads(added.stdout)
    assert added_record["id"] == "scope-1"
    assert added_record["calibration_date"] == "2026-01-15"
    assert added_record["calibration_status"] == "valid"

    fetched = runner.invoke(app, ["get", "scope-1", *common])
    assert fetched.exit_code == 0
    assert json.loads(fetched.stdout)["model"] == "DSOX1204G"

    listed = runner.invoke(app, ["list", *common])
    assert listed.exit_code == 0
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        [
            "update",
            "scope-1",
            "--model",
            "DSOX1204A",
            "--calibration-status",
            "expired",
            "--clear-calibration-certificate-number",
            *common,
        ],
    )
    assert updated.exit_code == 0, updated.output
    updated_record = json.loads(updated.stdout)
    assert updated_record["model"] == "DSOX1204A"
    assert updated_record["calibration_status"] == "expired"
    assert updated_record["calibration_certificate_number"] is None

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
            "--asset-tag",
            "SCOPE-001",
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
    output = unstyle(result.output)
    assert "ip-address" in output
    assert "port" in output


def test_instruments_only_offer_supported_connection_types() -> None:
    """Instrument help does not advertise board-only connection types."""
    result = CliRunner().invoke(app, ["add", "--help"])

    assert result.exit_code == 0
    output = unstyle(result.output)
    assert "<socket|visa>" in output
    assert "<socket|visa|com|usb>" not in output


def test_connection_options_must_match_selected_type(configuration: Path) -> None:
    """Type-specific options cannot be silently discarded."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "dmm-1",
            "--asset-tag",
            "DMM-001",
            "--type",
            "multimeter",
            "--maker",
            "Keysight",
            "--model",
            "34461A",
            "--connection",
            "visa",
            "--resource-name",
            "GPIB0::1::INSTR",
            "--ip-address",
            "192.168.1.10",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "visa connections do not accept --ip-address" in unstyle(result.output)


def test_update_requires_connection_type_for_connection_options(
    configuration: Path,
) -> None:
    """A connection field cannot be supplied without selecting its type."""
    result = CliRunner().invoke(
        app,
        [
            "update",
            "dmm-1",
            "--resource-name",
            "GPIB0::1::INSTR",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "--connection is required" in unstyle(result.output)


def test_update_rejects_setting_and_clearing_calibration_value(
    configuration: Path,
) -> None:
    """Contradictory calibration updates are rejected."""
    result = CliRunner().invoke(
        app,
        [
            "update",
            "dmm-1",
            "--calibration-date",
            "2026-01-15",
            "--clear-calibration-date",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "cannot set and clear calibration date" in unstyle(result.output)


def test_add_rejects_short_asset_tag(configuration: Path) -> None:
    """The CLI rejects asset tags shorter than five characters."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "scope-1",
            "--asset-tag",
            "1234",
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
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "string_too_short" in result.output


def test_add_rejects_duplicate_asset_tag(configuration: Path) -> None:
    """The CLI reports a duplicate laboratory asset tag clearly."""
    runner = CliRunner()
    common_options = [
        "--asset-tag",
        "DMM-001",
        "--type",
        "multimeter",
        "--maker",
        "Keysight",
        "--model",
        "34461A",
        "--connection",
        "visa",
        "--resource-name",
        "GPIB0::1::INSTR",
        "--config",
        str(configuration),
    ]

    first = runner.invoke(app, ["add", "dmm-1", *common_options])
    duplicate = runner.invoke(app, ["add", "dmm-2", *common_options])

    assert first.exit_code == 0, first.output
    assert duplicate.exit_code == 1
    assert "Asset tag already exists: DMM-001" in duplicate.output


def test_export_and_sync_yaml(configuration: Path, tmp_path: Path) -> None:
    """A YAML export can update existing IDs and add missing IDs."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "scope-1",
            "--asset-tag",
            "SCOPE-001",
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
            "asset_tag": "DMM-001",
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

    listed = runner.invoke(app, ["list", *common])
    stored = {item["id"]: item for item in json.loads(listed.stdout)}
    assert stored["scope-1"]["model"] == "new-model"
    assert stored["dmm-1"]["connection"]["kind"] == "visa"
