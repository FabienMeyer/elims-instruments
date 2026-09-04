"""Database migration commands."""

from pathlib import Path

import typer

from elims_instruments.database.migrations import upgrade_database

from .common import ConfigurationOption

app = typer.Typer(help="Manage the ELIMS database schema.", no_args_is_help=True)


@app.command()
def upgrade(
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Upgrade the configured database to the latest schema."""
    upgrade_database(configuration)
    typer.echo("Database upgraded to head")
