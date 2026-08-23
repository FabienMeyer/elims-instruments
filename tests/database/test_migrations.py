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
        dut_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(duts)")
        }
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()

    assert {"instruments", "boards", "duts"} <= tables
    assert {"project", "corner", "revision"} <= dut_columns
    assert {"type", "maker", "model"}.isdisjoint(dut_columns)
    assert revision == ("0001",)
