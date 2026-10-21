"""Tests for the root CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click import unstyle
from typer.testing import CliRunner

from elims_instruments.cli import app as root_app

if TYPE_CHECKING:
    from pathlib import Path


def test_root_cli_registers_instruments_module() -> None:
    """The root CLI exposes instruments as an independent command group."""
    result = CliRunner().invoke(root_app, ["instruments", "--help"])

    assert result.exit_code == 0
    assert "Manage the ELIMS instrument database" in result.output
    assert "sync" in result.output


def test_root_cli_registers_duts_module() -> None:
    """The root CLI exposes DUT database commands."""
    result = CliRunner().invoke(root_app, ["duts", "--help"])

    assert result.exit_code == 0
    assert "Manage the ELIMS DUT database" in result.output
    assert "sync" in result.output


def test_root_cli_registers_projects_module() -> None:
    """The root CLI exposes project database commands."""
    result = CliRunner().invoke(root_app, ["projects", "--help"])

    assert result.exit_code == 0
    assert "Manage the ELIMS project database" in result.output
    assert "sync" in result.output


def test_root_cli_registers_database_module() -> None:
    """The root CLI exposes schema migration commands."""
    result = CliRunner().invoke(root_app, ["database", "--help"])

    assert result.exit_code == 0
    assert "Manage the ELIMS database schema" in result.output
    assert "upgrade" in result.output


def test_database_upgrade_reports_invalid_configuration(tmp_path: Path) -> None:
    """Migration configuration failures are presented as CLI errors."""
    configuration = tmp_path / "invalid.toml"
    configuration.write_text("[wrong]\n", encoding="utf-8")

    result = CliRunner().invoke(
        root_app,
        ["database", "upgrade", "--config", str(configuration)],
    )

    assert result.exit_code == 2
    assert "Invalid database configuration" in unstyle(result.output)
