"""Tests for the boards CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from click import unstyle
from typer.testing import CliRunner

from elims_instruments.cli.boards import app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    path = tmp_path / "bench.toml"
    database = (tmp_path / "boards.db").as_posix()
    path.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return path


def test_cli_crud_lifecycle(configuration: Path) -> None:
    runner = CliRunner()
    common = ["--config", str(configuration)]

    added = runner.invoke(
        app,
        [
            "add",
            "board-1",
            "--asset-tag",
            "BOARD-001",
            "--type",
            "controller",
            "--maker",
            "Acme",
            "--model",
            "CTRL-1",
            "--connection",
            "com",
            "--com-port",
            "COM3",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output
    assert json.loads(added.stdout)["id"] == "board-1"

    fetched = runner.invoke(app, ["get", "board-1", *common])
    assert fetched.exit_code == 0
    assert json.loads(fetched.stdout)["model"] == "CTRL-1"

    listed = runner.invoke(app, ["list", *common])
    assert listed.exit_code == 0
    assert len(json.loads(listed.stdout)) == 1

    updated = runner.invoke(
        app,
        ["update", "board-1", "--model", "CTRL-2", *common],
    )
    assert updated.exit_code == 0
    assert json.loads(updated.stdout)["model"] == "CTRL-2"

    deleted = runner.invoke(app, ["delete", "board-1", *common])
    assert deleted.exit_code == 0
    assert "Deleted board: board-1" in deleted.stdout


@pytest.mark.parametrize(
    ("command", "description"),
    [
        ("delete", "Delete one board by ID."),
        ("sync", "Add or fully update every board in a YAML list by ID."),
        ("export", "Export all boards to a YAML list."),
    ],
)
def test_command_help_describes_the_board_operation(
    command: str,
    description: str,
) -> None:
    """Each board subcommand exposes its matching operation description."""
    result = CliRunner().invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert description in unstyle(result.output)


def test_add_rejects_incomplete_socket_connection(configuration: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "add",
            "board-1",
            "--asset-tag",
            "BOARD-001",
            "--type",
            "controller",
            "--maker",
            "Acme",
            "--model",
            "CTRL-1",
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


def test_usb_and_board_serial_numbers_are_independent(configuration: Path) -> None:
    """Board identity and the USB descriptor retain distinct serial numbers."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "board-1",
            "--asset-tag",
            "BOARD-001",
            "--type",
            "controller",
            "--maker",
            "Acme",
            "--model",
            "CTRL-1",
            "--serial-number",
            "BOARD-SN-42",
            "--connection",
            "usb",
            "--vendor-id",
            "1234",
            "--product-id",
            "5678",
            "--usb-serial-number",
            "USB-SN-99",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 0, result.output
    board = json.loads(result.stdout)
    assert board["serial_number"] == "BOARD-SN-42"
    assert board["connection"]["serial_number"] == "USB-SN-99"


def test_update_keeps_usb_and_board_serial_numbers_independent(
    configuration: Path,
) -> None:
    """Clearing board metadata does not clear the replacement USB descriptor."""
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "board-1",
            "--asset-tag",
            "BOARD-001",
            "--type",
            "controller",
            "--maker",
            "Acme",
            "--model",
            "CTRL-1",
            "--serial-number",
            "BOARD-SN-42",
            "--connection",
            "com",
            "--com-port",
            "COM3",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    updated = runner.invoke(
        app,
        [
            "update",
            "board-1",
            "--clear-serial-number",
            "--connection",
            "usb",
            "--vendor-id",
            "1234",
            "--product-id",
            "5678",
            "--usb-serial-number",
            "USB-SN-99",
            *common,
        ],
    )

    assert updated.exit_code == 0, updated.output
    board = json.loads(updated.stdout)
    assert board["serial_number"] is None
    assert board["connection"]["serial_number"] == "USB-SN-99"


def test_explicit_invalid_connection_value_is_not_replaced_by_default(
    configuration: Path,
) -> None:
    """An explicitly supplied falsey value reaches model validation."""
    result = CliRunner().invoke(
        app,
        [
            "add",
            "board-1",
            "--asset-tag",
            "BOARD-001",
            "--type",
            "controller",
            "--maker",
            "Acme",
            "--model",
            "CTRL-1",
            "--connection",
            "com",
            "--com-port",
            "COM3",
            "--baud-rate",
            "0",
            "--config",
            str(configuration),
        ],
    )

    assert result.exit_code == 2
    assert "greater than or equal to 110" in unstyle(result.output)


def test_export_and_sync_yaml(configuration: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    common = ["--config", str(configuration)]
    added = runner.invoke(
        app,
        [
            "add",
            "board-1",
            "--asset-tag",
            "BOARD-001",
            "--type",
            "controller",
            "--maker",
            "Acme",
            "--model",
            "old",
            "--connection",
            "com",
            "--com-port",
            "COM3",
            *common,
        ],
    )
    assert added.exit_code == 0, added.output

    yaml_path = tmp_path / "boards.yaml"
    exported = runner.invoke(app, ["export", str(yaml_path), *common])
    assert exported.exit_code == 0, exported.output

    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    records[0]["model"] = "new-model"
    records.append(
        {
            "id": "dev-1",
            "asset_tag": "BOARD-002",
            "type": "sensor",
            "maker": "Acme",
            "model": "SEN-1",
            "serial_number": None,
            "connection": {
                "kind": "usb",
                "vendor_id": 1,
                "product_id": 2,
                "timeout_seconds": 10.0,
            },
        }
    )
    yaml_path.write_text(yaml.safe_dump(records), encoding="utf-8")

    synced = runner.invoke(app, ["sync", str(yaml_path), *common])
    assert synced.exit_code == 0, synced.output
    assert "Created: 1; Updated: 1" in synced.stdout
