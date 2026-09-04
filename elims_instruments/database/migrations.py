"""Programmatic Alembic migration entry point."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from .crud import read_database_settings


def _alembic_config() -> Config:
    """Build an Alembic configuration without a machine-specific INI file."""
    configuration = Config()
    configuration.set_main_option(
        "script_location",
        str(Path(__file__).with_name("migration_scripts")),
    )
    return configuration


def upgrade_database(toml_path: Path, revision: str = "head") -> None:
    """Upgrade the configured database to a migration revision."""
    settings = read_database_settings(toml_path)
    engine = create_engine(settings.url, echo=settings.echo)
    try:
        with engine.begin() as connection:
            configuration = _alembic_config()
            configuration.attributes["connection"] = connection
            command.upgrade(configuration, revision)
    finally:
        engine.dispose()
