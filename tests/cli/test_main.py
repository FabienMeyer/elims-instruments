"""Tests for the root CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from elims_instruments.cli import app as root_app


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
