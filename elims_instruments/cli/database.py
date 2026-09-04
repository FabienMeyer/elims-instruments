"""Database migration commands."""

from pathlib import Path
from typing import Annotated

import typer

from elims_instruments.database.migrations import upgrade_database

app = typer.Typer(help="Manage the ELIMS database schema.", no_args_is_help=True)


@app.command()
def upgrade(
    configuration: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Bench TOML configuration file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("bench.toml"),
) -> None:
    """Upgrade the configured database to the latest schema."""
    upgrade_database(configuration)
    typer.echo("Database upgraded to head")
