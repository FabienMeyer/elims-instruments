"""Typer command group for managing instruments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from elims_instruments.database import (
    CalibrationStatus,
    DuplicateAssetTagError,
    InstrumentCrud,
    InstrumentModel,
    InstrumentType,
    parse_instrument_list,
)
from elims_instruments.utils.logger import get_cli_logger

from .common import (
    ConfigurationOption,
    apply_optional_change,
    collect_changes,
    managed_repository,
)
from .connections import (
    InstrumentConnectionKind,
    SocketConnectionOptions,
    VisaConnectionOptions,
    build_connection,
    build_optional_connection,
)

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

app = typer.Typer(
    help="Manage the ELIMS instrument database.",
    no_args_is_help=True,
)


def _repository(configuration: Path) -> AbstractContextManager[InstrumentCrud]:
    """Create a managed repository using the shared CLI logger."""
    logger = get_cli_logger()
    logger.debug("Opening instrument repository with {}", configuration)
    return managed_repository(lambda: InstrumentCrud(logger, configuration))


def _write_instrument(instrument: InstrumentModel) -> None:
    """Write one instrument as formatted JSON."""
    typer.echo(json.dumps(instrument.model_dump(mode="json"), indent=2))


@app.command()
def add(
    instrument_id: Annotated[str, typer.Argument(help="Unique instrument ID.")],
    asset_tag: Annotated[
        str,
        typer.Option(help="Unique laboratory asset tag."),
    ],
    instrument_type: Annotated[
        InstrumentType,
        typer.Option("--type", help="Instrument type."),
    ],
    maker: Annotated[str, typer.Option(help="Instrument manufacturer.")],
    model: Annotated[str, typer.Option(help="Instrument model name.")],
    connection: Annotated[
        InstrumentConnectionKind,
        typer.Option("--connection", help="Connection type."),
    ],
    configuration: ConfigurationOption = Path("bench.toml"),
    serial_number: Annotated[str | None, typer.Option()] = None,
    calibration_date: Annotated[
        str | None,
        typer.Option(help="Calibration date in YYYY-MM-DD format."),
    ] = None,
    calibration_due_date: Annotated[
        str | None,
        typer.Option(help="Calibration due date in YYYY-MM-DD format."),
    ] = None,
    calibration_certificate_number: Annotated[str | None, typer.Option()] = None,
    calibration_status: Annotated[
        CalibrationStatus,
        typer.Option(),
    ] = CalibrationStatus.UNKNOWN,
    ip_address: Annotated[str | None, typer.Option()] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    mac_address: Annotated[str | None, typer.Option()] = None,
    resource_name: Annotated[str | None, typer.Option()] = None,
    timeout_seconds: Annotated[float | None, typer.Option(min=0.001)] = None,
) -> None:
    """Add an instrument."""
    link = build_connection(
        connection,
        socket=SocketConnectionOptions(
            ip_address=ip_address,
            port=port,
            mac_address=mac_address,
            timeout_seconds=timeout_seconds,
        ),
        visa=VisaConnectionOptions(
            resource_name=resource_name,
            timeout_seconds=timeout_seconds,
        ),
    )
    try:
        instrument = InstrumentModel.model_validate(
            {
                "id": instrument_id,
                "asset_tag": asset_tag,
                "type": instrument_type,
                "maker": maker,
                "model": model,
                "serial_number": serial_number,
                "calibration_date": calibration_date,
                "calibration_due_date": calibration_due_date,
                "calibration_certificate_number": calibration_certificate_number,
                "calibration_status": calibration_status,
                "connection": link,
            }
        )
        with _repository(configuration) as repository:
            stored = repository.add(instrument)
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except DuplicateAssetTagError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    except IntegrityError as error:
        typer.echo(f"Instrument ID already exists: {instrument_id}", err=True)
        raise typer.Exit(code=1) from error
    _write_instrument(stored)


@app.command("get")
def get_by_id(
    instrument_id: Annotated[str, typer.Argument(help="Instrument ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Get one instrument by ID."""
    with _repository(configuration) as repository:
        instrument = repository.fetch("id", instrument_id)
    if instrument is None:
        typer.echo(f"Instrument not found: {instrument_id}", err=True)
        raise typer.Exit(code=1)
    _write_instrument(instrument)


@app.command("list")
def fetch_all(
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Fetch all instruments."""
    with _repository(configuration) as repository:
        instruments = repository.fetchall()
    typer.echo(
        json.dumps(
            [instrument.model_dump(mode="json") for instrument in instruments],
            indent=2,
        )
    )


@app.command("update")
def update_by_id(
    instrument_id: Annotated[str, typer.Argument(help="Instrument ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
    new_asset_tag: Annotated[str | None, typer.Option("--asset-tag")] = None,
    instrument_type: Annotated[
        InstrumentType | None,
        typer.Option("--type"),
    ] = None,
    maker: Annotated[str | None, typer.Option()] = None,
    model: Annotated[str | None, typer.Option()] = None,
    serial_number: Annotated[str | None, typer.Option()] = None,
    clear_serial_number: Annotated[bool, typer.Option()] = False,
    calibration_date: Annotated[
        str | None,
        typer.Option(help="Calibration date in YYYY-MM-DD format."),
    ] = None,
    clear_calibration_date: Annotated[bool, typer.Option()] = False,
    calibration_due_date: Annotated[
        str | None,
        typer.Option(help="Calibration due date in YYYY-MM-DD format."),
    ] = None,
    clear_calibration_due_date: Annotated[bool, typer.Option()] = False,
    calibration_certificate_number: Annotated[str | None, typer.Option()] = None,
    clear_calibration_certificate_number: Annotated[bool, typer.Option()] = False,
    calibration_status: Annotated[CalibrationStatus | None, typer.Option()] = None,
    connection: Annotated[
        InstrumentConnectionKind | None,
        typer.Option("--connection"),
    ] = None,
    ip_address: Annotated[str | None, typer.Option()] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    mac_address: Annotated[str | None, typer.Option()] = None,
    resource_name: Annotated[str | None, typer.Option()] = None,
    timeout_seconds: Annotated[float | None, typer.Option(min=0.001)] = None,
) -> None:
    """Update an instrument selected by ID."""
    changes = collect_changes(
        asset_tag=new_asset_tag,
        type=instrument_type,
        maker=maker,
        model=model,
        calibration_status=calibration_status,
    )
    for field, value, clear in (
        ("serial_number", serial_number, clear_serial_number),
        ("calibration_date", calibration_date, clear_calibration_date),
        (
            "calibration_due_date",
            calibration_due_date,
            clear_calibration_due_date,
        ),
        (
            "calibration_certificate_number",
            calibration_certificate_number,
            clear_calibration_certificate_number,
        ),
    ):
        apply_optional_change(changes, field, value, clear=clear)
    link = build_optional_connection(
        connection,
        socket=SocketConnectionOptions(
            ip_address=ip_address,
            port=port,
            mac_address=mac_address,
            timeout_seconds=timeout_seconds,
        ),
        visa=VisaConnectionOptions(
            resource_name=resource_name,
            timeout_seconds=timeout_seconds,
        ),
    )
    if link is not None:
        changes["connection"] = link
    if not changes:
        raise typer.BadParameter("provide at least one field to update")

    try:
        with _repository(configuration) as repository:
            stored = repository.fetch("id", instrument_id)
            instrument = (
                None
                if stored is None
                else repository.update_by_asset_tag(stored.asset_tag, changes)
            )
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except DuplicateAssetTagError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    except IntegrityError as error:
        typer.echo("Instrument asset tag already exists", err=True)
        raise typer.Exit(code=1) from error
    if instrument is None:
        typer.echo(f"Instrument not found: {instrument_id}", err=True)
        raise typer.Exit(code=1)
    _write_instrument(instrument)


@app.command("delete")
def delete_by_id(
    instrument_id: Annotated[str, typer.Argument(help="Instrument ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Delete one instrument by ID."""
    with _repository(configuration) as repository:
        removed = repository.remove("id", instrument_id)
    if not removed:
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
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Add or fully update every instrument in a YAML list by ID."""
    try:
        raw_data: object = yaml.safe_load(source.read_text(encoding="utf-8"))
        instruments = parse_instrument_list(raw_data)
        with _repository(configuration) as repository:
            created, updated = repository.upsert_many(instruments)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as error:
        typer.echo(f"Invalid instrument YAML: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Created: {created}; Updated: {updated}")


@app.command("export")
def export_yaml(
    output: Annotated[Path, typer.Argument(help="Destination YAML file.")],
    configuration: ConfigurationOption = Path("bench.toml"),
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing YAML file."),
    ] = False,
) -> None:
    """Export all instruments to a YAML list."""
    if output.exists() and not force:
        typer.echo(f"File already exists: {output}; use --force to overwrite", err=True)
        raise typer.Exit(code=1)

    with _repository(configuration) as repository:
        instruments = repository.fetchall()
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
