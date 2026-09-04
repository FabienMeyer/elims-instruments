"""Typer command group for managing devices under test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from elims_instruments.database import (
    DuplicateAssetTagError,
    DutCrud,
    DutModel,
    parse_dut_list,
)
from elims_instruments.utils.logger import get_cli_logger

from .common import ConfigurationOption, managed_repository

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

app = typer.Typer(
    help="Manage the ELIMS DUT database.",
    no_args_is_help=True,
)


def _repository(configuration: Path) -> AbstractContextManager[DutCrud]:
    """Create a managed repository using the shared CLI logger."""
    logger = get_cli_logger()
    logger.debug("Opening DUT repository with {}", configuration)
    return managed_repository(DutCrud(logger, configuration))


def _write_dut(dut: DutModel) -> None:
    """Write one DUT as formatted JSON."""
    typer.echo(json.dumps(dut.model_dump(mode="json"), indent=2))


@app.command()
def add(
    dut_id: Annotated[str, typer.Argument(help="Unique DUT ID.")],
    asset_tag: Annotated[str, typer.Option(help="Unique DUT asset tag.")],
    project: Annotated[str, typer.Option(help="Owning project.")],
    corner: Annotated[str, typer.Option(help="Process corner.")],
    die_revision: Annotated[
        str,
        typer.Option(help="Die/base-layer revision, for example A."),
    ],
    configuration: ConfigurationOption = Path("bench.toml"),
    metal_revision: Annotated[
        int | None,
        typer.Option(min=0, help="Metal-layer revision, for example 0."),
    ] = None,
    package_revision: Annotated[
        str | None,
        typer.Option(help="Package revision, for example R1."),
    ] = None,
    serial_number: Annotated[str | None, typer.Option()] = None,
    lot_number: Annotated[str | None, typer.Option()] = None,
    wafer_id: Annotated[str | None, typer.Option()] = None,
    die_x: Annotated[int | None, typer.Option()] = None,
    die_y: Annotated[int | None, typer.Option()] = None,
) -> None:
    """Add a DUT."""
    try:
        dut = DutModel.model_validate(
            {
                "id": dut_id,
                "asset_tag": asset_tag,
                "project": project,
                "corner": corner,
                "die_revision": die_revision,
                "metal_revision": metal_revision,
                "package_revision": package_revision,
                "serial_number": serial_number,
                "lot_number": lot_number,
                "wafer_id": wafer_id,
                "die_x": die_x,
                "die_y": die_y,
            }
        )
        with _repository(configuration) as repository:
            stored = repository.add(dut)
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except DuplicateAssetTagError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    except IntegrityError as error:
        typer.echo(f"DUT ID already exists: {dut_id}", err=True)
        raise typer.Exit(code=1) from error
    _write_dut(stored)


@app.command("get")
def get_by_id(
    dut_id: Annotated[str, typer.Argument(help="DUT ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Get one DUT by ID."""
    with _repository(configuration) as repository:
        dut = repository.fetch("id", dut_id)
    if dut is None:
        typer.echo(f"DUT not found: {dut_id}", err=True)
        raise typer.Exit(code=1)
    _write_dut(dut)


@app.command("list")
def fetch_all(
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Fetch all DUTs."""
    with _repository(configuration) as repository:
        duts = repository.fetchall()
    typer.echo(json.dumps([dut.model_dump(mode="json") for dut in duts], indent=2))


@app.command("update")
def update_by_id(
    dut_id: Annotated[str, typer.Argument(help="DUT ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
    new_asset_tag: Annotated[str | None, typer.Option("--asset-tag")] = None,
    project: Annotated[str | None, typer.Option()] = None,
    corner: Annotated[str | None, typer.Option()] = None,
    die_revision: Annotated[str | None, typer.Option()] = None,
    metal_revision: Annotated[int | None, typer.Option(min=0)] = None,
    package_revision: Annotated[str | None, typer.Option()] = None,
    serial_number: Annotated[str | None, typer.Option()] = None,
    lot_number: Annotated[str | None, typer.Option()] = None,
    wafer_id: Annotated[str | None, typer.Option()] = None,
    die_x: Annotated[int | None, typer.Option()] = None,
    die_y: Annotated[int | None, typer.Option()] = None,
    clear_serial_number: Annotated[bool, typer.Option()] = False,
    clear_lot_number: Annotated[bool, typer.Option()] = False,
    clear_wafer_id: Annotated[bool, typer.Option()] = False,
    clear_die_position: Annotated[bool, typer.Option()] = False,
) -> None:
    """Update a DUT selected by ID."""
    changes: dict[str, object] = {
        field: value
        for field, value in {
            "asset_tag": new_asset_tag,
            "project": project,
            "corner": corner,
            "die_revision": die_revision,
            "metal_revision": metal_revision,
            "package_revision": package_revision,
            "serial_number": serial_number,
            "lot_number": lot_number,
            "wafer_id": wafer_id,
            "die_x": die_x,
            "die_y": die_y,
        }.items()
        if value is not None
    }
    for clear, field in (
        (clear_serial_number, "serial_number"),
        (clear_lot_number, "lot_number"),
        (clear_wafer_id, "wafer_id"),
    ):
        if clear:
            changes[field] = None
    if clear_die_position:
        changes.update({"die_x": None, "die_y": None})
    if not changes:
        raise typer.BadParameter("provide at least one field to update")

    try:
        with _repository(configuration) as repository:
            stored = repository.fetch("id", dut_id)
            dut = (
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
        typer.echo("DUT asset tag already exists", err=True)
        raise typer.Exit(code=1) from error
    if dut is None:
        typer.echo(f"DUT not found: {dut_id}", err=True)
        raise typer.Exit(code=1)
    _write_dut(dut)


@app.command("delete")
def delete_by_id(
    dut_id: Annotated[str, typer.Argument(help="DUT ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Delete one DUT by ID."""
    with _repository(configuration) as repository:
        removed = repository.remove("id", dut_id)
    if not removed:
        typer.echo(f"DUT not found: {dut_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Deleted DUT: {dut_id}")


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
    """Add or fully update every DUT in a YAML list by ID."""
    try:
        raw_data: object = yaml.safe_load(source.read_text(encoding="utf-8"))
        duts = parse_dut_list(raw_data)
        with _repository(configuration) as repository:
            created, updated = repository.upsert_many(duts)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as error:
        typer.echo(f"Invalid DUT YAML: {error}", err=True)
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
    """Export all DUTs to a YAML list."""
    if output.exists() and not force:
        typer.echo(f"File already exists: {output}; use --force to overwrite", err=True)
        raise typer.Exit(code=1)

    with _repository(configuration) as repository:
        duts = repository.fetchall()
    content = yaml.safe_dump(
        [dut.model_dump(mode="json") for dut in duts],
        allow_unicode=True,
        sort_keys=False,
    )
    try:
        output.write_text(content, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Could not write YAML file: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Exported {len(duts)} DUTs to {output}")
