"""Typer command group for managing instruments."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from elims_instruments.database import (
    Connection,
    ConnectionKind,
    InstrumentCrud,
    InstrumentModel,
    SocketConnection,
    VisaConnection,
    validate_instrument_list,
)

app = typer.Typer(
    help="Manage the ELIMS instrument database.",
    no_args_is_help=True,
)

ConfigurationOption = Annotated[
    Path,
    typer.Option(
        "--config",
        "-c",
        help="Database TOML configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
]


def _repository(configuration: Path) -> InstrumentCrud:
    """Create a repository for a CLI command."""
    return InstrumentCrud(logging.getLogger("elims_instruments.cli"), configuration)


def _write_instrument(instrument: InstrumentModel) -> None:
    """Write one instrument as formatted JSON."""
    typer.echo(json.dumps(instrument.model_dump(mode="json"), indent=2))


def _connection(
    kind: ConnectionKind,
    ip_address: str | None,
    port: int | None,
    mac_address: str | None,
    resource_name: str | None,
    timeout_seconds: float | None,
) -> Connection:
    """Build and validate a connection from command options."""
    try:
        if kind is ConnectionKind.SOCKET:
            if ip_address is None or port is None:
                raise typer.BadParameter(
                    "socket connections require --ip-address and --port",
                    param_hint="--connection",
                )
            return SocketConnection(
                ip_address=ip_address,
                port=port,
                mac_address=mac_address,
                timeout_seconds=timeout_seconds or 5.0,
            )

        if resource_name is None:
            raise typer.BadParameter(
                "VISA connections require --resource-name",
                param_hint="--connection",
            )
        return VisaConnection(
            resource_name=resource_name,
            timeout_seconds=timeout_seconds or 30.0,
        )
    except ValidationError as error:
        raise typer.BadParameter(str(error), param_hint="--connection") from error


@app.command()
def add(
    instrument_id: Annotated[str, typer.Argument(help="Unique instrument ID.")],
    instrument_type: Annotated[str, typer.Option("--type", help="Instrument type.")],
    maker: Annotated[str, typer.Option(help="Instrument manufacturer.")],
    model: Annotated[str, typer.Option(help="Instrument model name.")],
    connection: Annotated[
        ConnectionKind,
        typer.Option("--connection", help="Connection type."),
    ],
    configuration: ConfigurationOption = Path("database.toml"),
    serial_number: Annotated[str | None, typer.Option()] = None,
    ip_address: Annotated[str | None, typer.Option()] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    mac_address: Annotated[str | None, typer.Option()] = None,
    resource_name: Annotated[str | None, typer.Option()] = None,
    timeout_seconds: Annotated[float | None, typer.Option(min=0.001)] = None,
) -> None:
    """Add an instrument."""
    link = _connection(
        connection,
        ip_address,
        port,
        mac_address,
        resource_name,
        timeout_seconds,
    )
    try:
        instrument = InstrumentModel.model_validate(
            {
                "id": instrument_id,
                "type": instrument_type,
                "maker": maker,
                "model": model,
                "serial_number": serial_number,
                "connection": link,
            }
        )
        stored = _repository(configuration).add(instrument)
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except IntegrityError as error:
        typer.echo(f"Instrument already exists: {instrument_id}", err=True)
        raise typer.Exit(code=1) from error
    _write_instrument(stored)


@app.command("get")
def get_by_id(
    instrument_id: Annotated[str, typer.Argument(help="Instrument ID.")],
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    """Get one instrument by ID."""
    instrument = _repository(configuration).fetch("id", instrument_id)
    if instrument is None:
        typer.echo(f"Instrument not found: {instrument_id}", err=True)
        raise typer.Exit(code=1)
    _write_instrument(instrument)


@app.command("gets")
def fetch_all(
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    """Fetch all instruments."""
    instruments = _repository(configuration).fetchall()
    typer.echo(
        json.dumps(
            [instrument.model_dump(mode="json") for instrument in instruments],
            indent=2,
        )
    )


@app.command("update")
def update_by_id(
    instrument_id: Annotated[str, typer.Argument(help="Instrument ID.")],
    configuration: ConfigurationOption = Path("database.toml"),
    instrument_type: Annotated[str | None, typer.Option("--type")] = None,
    maker: Annotated[str | None, typer.Option()] = None,
    model: Annotated[str | None, typer.Option()] = None,
    serial_number: Annotated[str | None, typer.Option()] = None,
    clear_serial_number: Annotated[bool, typer.Option()] = False,
    connection: Annotated[ConnectionKind | None, typer.Option("--connection")] = None,
    ip_address: Annotated[str | None, typer.Option()] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    mac_address: Annotated[str | None, typer.Option()] = None,
    resource_name: Annotated[str | None, typer.Option()] = None,
    timeout_seconds: Annotated[float | None, typer.Option(min=0.001)] = None,
) -> None:
    """Update selected fields on an instrument identified by ID."""
    changes: dict[str, object] = {
        field: value
        for field, value in {
            "type": instrument_type,
            "maker": maker,
            "model": model,
            "serial_number": serial_number,
        }.items()
        if value is not None
    }
    if clear_serial_number:
        changes["serial_number"] = None
    if connection is not None:
        changes["connection"] = _connection(
            connection,
            ip_address,
            port,
            mac_address,
            resource_name,
            timeout_seconds,
        )
    if not changes:
        raise typer.BadParameter("provide at least one field to update")

    try:
        instrument = _repository(configuration).update_by_id(
            instrument_id,
            changes,
        )
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    if instrument is None:
        typer.echo(f"Instrument not found: {instrument_id}", err=True)
        raise typer.Exit(code=1)
    _write_instrument(instrument)


@app.command("delete")
def delete_by_id(
    instrument_id: Annotated[str, typer.Argument(help="Instrument ID.")],
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    """Delete one instrument by ID."""
    if not _repository(configuration).remove("id", instrument_id):
        typer.echo(f"Instrument not found: {instrument_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Deleted instrument: {instrument_id}")


@app.command("sync")
def sync_yaml(
    source: Annotated[
        Path,
        typer.Argument(
            help="YAML list to validate and apply.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    """Add or fully update every instrument in a YAML list by ID."""
    try:
        raw_data: object = yaml.safe_load(source.read_text(encoding="utf-8"))
        instruments = validate_instrument_list(raw_data)
        created, updated = _repository(configuration).upsert_many(instruments)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as error:
        typer.echo(f"Invalid instrument YAML: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Created: {created}; Updated: {updated}")


@app.command("export")
def export_yaml(
    output: Annotated[Path, typer.Argument(help="Destination YAML file.")],
    configuration: ConfigurationOption = Path("database.toml"),
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing YAML file."),
    ] = False,
) -> None:
    """Export all instruments to a YAML list."""
    if output.exists() and not force:
        typer.echo(f"File already exists: {output}; use --force to overwrite", err=True)
        raise typer.Exit(code=1)

    instruments = _repository(configuration).fetchall()
    content = yaml.safe_dump(
        [instrument.model_dump(mode="json") for instrument in instruments],
        allow_unicode=True,
        sort_keys=False,
    )
    try:
        output.write_text(content, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Could not write YAML file: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Exported {len(instruments)} instruments to {output}")
