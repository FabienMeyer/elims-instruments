"""Tests for portable database configuration and schema migrations."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from elims_instruments.database import BoardCrud, upgrade_database

if TYPE_CHECKING:
    from pathlib import Path


def _configuration(tmp_path: Path, database_name: str = "assets.db") -> Path:
    configuration = tmp_path / "bench.toml"
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database_name}"\necho = false\n',
        encoding="utf-8",
    )
    return configuration


def test_relative_sqlite_path_is_resolved_beside_configuration(
    tmp_path: Path,
) -> None:
    """A relative SQLite URL does not depend on the process working directory."""
    configuration_directory = tmp_path / "project"
    configuration_directory.mkdir()
    configuration = _configuration(configuration_directory)

    repository = BoardCrud(logging.getLogger(__name__), configuration)
    repository.engine.dispose()

    assert (configuration_directory / "assets.db").exists()


def test_upgrade_creates_current_schema(tmp_path: Path) -> None:
    """An empty database can be created entirely from migrations."""
    configuration = _configuration(tmp_path)

    upgrade_database(configuration)

    with sqlite3.connect(tmp_path / "assets.db") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        dut_columns = {row[1] for row in connection.execute("PRAGMA table_info(duts)")}
        instrument_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(instruments)")
        }
        instrument_revision_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(instrument_revisions)")
        }
        project_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(projects)")
        }
        project_dut_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(project_supported_duts)")
        }
        project_board_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(project_supported_boards)")
        }
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()

    assert {
        "instruments",
        "instrument_revisions",
        "boards",
        "duts",
        "projects",
        "project_supported_duts",
        "project_supported_boards",
    } <= tables
    assert {
        "project",
        "corner",
        "die_revision",
        "metal_revision",
        "package_revision",
    } <= dut_columns
    assert "revision" not in dut_columns
    assert {"type", "maker", "model"}.isdisjoint(dut_columns)
    assert {
        "calibration_date",
        "calibration_due_date",
        "calibration_certificate_number",
        "calibration_status",
    } <= instrument_columns
    assert instrument_revision_columns == {
        "id",
        "instrument_id",
        "asset_tag",
        "recorded_at",
        "action",
        "snapshot",
    }
    assert project_columns == {
        "id",
        "internal_name",
        "datasheet_name",
        "specifications",
    }
    assert project_dut_columns == {"project_id", "dut_id"}
    assert project_board_columns == {"project_id", "board_id"}
    assert revision == ("0001",)
