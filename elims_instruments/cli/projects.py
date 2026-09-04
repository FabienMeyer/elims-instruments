"""Typer command group for managing characterization projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, StatementError

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    ProjectCrud,
    ProjectModel,
    ProjectRevisionSpecifications,
    parse_project_list,
    parse_project_specifications,
)
from elims_instruments.utils.logger import get_cli_logger

from .common import ConfigurationOption, managed_repository

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

app = typer.Typer(
    help="Manage the ELIMS project database.",
    no_args_is_help=True,
)

SpecificationOption = Annotated[
    Path | None,
    typer.Option(
        "--specifications",
        help=(
            "YAML file containing all revision profiles; cannot be combined with "
            "inline specification options."
        ),
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
]


def _repository(configuration: Path) -> AbstractContextManager[ProjectCrud]:
    """Create a managed repository using the shared CLI logger."""
    logger = get_cli_logger()
    logger.debug("Opening project repository with {}", configuration)
    return managed_repository(ProjectCrud(logger, configuration))


def _project_data(project: ProjectModel) -> dict[str, object]:
    """Serialize a project together with its related resource models."""
    return {
        "id": project.id,
        "internal_name": project.internal_name,
        "datasheet_name": project.datasheet_name,
        "specifications": [
            specification.model_dump(mode="json")
            for specification in project.specifications
        ],
        "supported_duts": [
            dut.model_dump(mode="json") for dut in project.supported_duts
        ],
        "supported_boards": [
            board.model_dump(mode="json") for board in project.supported_boards
        ],
    }


def _read_specifications(path: Path) -> list[ProjectRevisionSpecifications]:
    """Read revision-dependent project specifications from YAML."""
    raw_data: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parse_project_specifications(raw_data)


def _resolve_specifications(
    specifications_file: Path | None,
    *,
    die_revision: str | None,
    metal_revision: int | None,
    package_revision: str | None,
    voltage_name: str | None,
    voltage_minimum: float | None,
    voltage_typical: float | None,
    voltage_maximum: float | None,
    current_minimum: float | None,
    current_typical: float | None,
    current_maximum: float | None,
    temperature_name: str | None,
    temperature_minimum: float | None,
    temperature_typical: float | None,
    temperature_maximum: float | None,
) -> list[ProjectRevisionSpecifications]:
    """Load a YAML file or construct one revision profile from CLI options."""
    inline_values = (
        die_revision,
        metal_revision,
        package_revision,
        voltage_name,
        voltage_minimum,
        voltage_typical,
        voltage_maximum,
        current_minimum,
        current_typical,
        current_maximum,
        temperature_name,
        temperature_minimum,
        temperature_typical,
        temperature_maximum,
    )
    has_inline_values = any(value is not None for value in inline_values)
    if specifications_file is not None:
        if has_inline_values:
            raise typer.BadParameter(
                "--specifications cannot be combined with inline specification options"
            )
        return _read_specifications(specifications_file)
    missing = [
        option
        for option, value in (
            ("--die-revision", die_revision),
            ("--voltage-typical", voltage_typical),
            ("--temperature-typical", temperature_typical),
        )
        if value is None
    ]
    if missing:
        raise typer.BadParameter(
            "provide --specifications or inline options; missing " + ", ".join(missing)
        )
    if current_typical is None and (
        current_minimum is not None or current_maximum is not None
    ):
        raise typer.BadParameter(
            "--current-typical is required with current limit bounds"
        )

    current_limits = (
        None
        if current_typical is None
        else {
            "minimum": current_minimum,
            "typical": current_typical,
            "maximum": current_maximum,
        }
    )
    return [
        ProjectRevisionSpecifications.model_validate(
            {
                "die_revision": die_revision,
                "metal_revision": metal_revision,
                "package_revision": package_revision,
                "voltage_specifications": [
                    {
                        "name": voltage_name or "VDD",
                        "voltage_limits": {
                            "minimum": voltage_minimum,
                            "typical": voltage_typical,
                            "maximum": voltage_maximum,
                        },
                        "current_limits": current_limits,
                    }
                ],
                "temperature_specifications": [
                    {
                        "name": temperature_name or "DUT",
                        "temperature_limits": {
                            "minimum": temperature_minimum,
                            "typical": temperature_typical,
                            "maximum": temperature_maximum,
                        },
                    }
                ],
            }
        )
    ]


def _write_project(project: ProjectModel) -> None:
    """Write one project as formatted JSON."""
    typer.echo(json.dumps(_project_data(project), indent=2))


def _resolve_duts(identifiers: list[str], configuration: Path) -> list[DutModel]:
    """Resolve DUT IDs or asset tags supplied on the command line."""
    logger = get_cli_logger()
    with managed_repository(DutCrud(logger, configuration)) as repository:
        duts: list[DutModel] = []
        for identifier in identifiers:
            dut = repository.fetch("id", identifier) or repository.fetch(
                "asset_tag",
                identifier,
            )
            if dut is None:
                raise typer.BadParameter(f"DUT not found: {identifier}")
            duts.append(dut)
    return duts


def _resolve_boards(
    identifiers: list[str],
    configuration: Path,
) -> list[BoardModel]:
    """Resolve board IDs or asset tags supplied on the command line."""
    logger = get_cli_logger()
    with managed_repository(BoardCrud(logger, configuration)) as repository:
        boards: list[BoardModel] = []
        for identifier in identifiers:
            board = repository.fetch("id", identifier) or repository.fetch(
                "asset_tag",
                identifier,
            )
            if board is None:
                raise typer.BadParameter(f"Board not found: {identifier}")
            boards.append(board)
    return boards


@app.command()
def add(
    project_id: Annotated[str, typer.Argument(help="Unique project ID.")],
    internal_name: Annotated[
        str,
        typer.Option(help="Unique internal project name."),
    ],
    datasheet_name: Annotated[
        str,
        typer.Option(help="Client-facing datasheet name."),
    ],
    specifications_file: SpecificationOption = None,
    die_revision: Annotated[
        str | None, typer.Option(help="Die/base-layer revision for the profile.")
    ] = None,
    metal_revision: Annotated[
        int | None, typer.Option(min=0, help="Metal-layer revision for the profile.")
    ] = None,
    package_revision: Annotated[
        str | None, typer.Option(help="Package revision for the profile.")
    ] = None,
    voltage_name: Annotated[
        str | None, typer.Option(help="Voltage rail name; defaults to VDD.")
    ] = None,
    voltage_minimum: Annotated[
        float | None, typer.Option(help="Minimum voltage in volts.")
    ] = None,
    voltage_typical: Annotated[
        float | None, typer.Option(help="Typical voltage in volts.")
    ] = None,
    voltage_maximum: Annotated[
        float | None, typer.Option(help="Maximum voltage in volts.")
    ] = None,
    current_minimum: Annotated[
        float | None, typer.Option(help="Minimum current in amperes.")
    ] = None,
    current_typical: Annotated[
        float | None, typer.Option(help="Typical current in amperes.")
    ] = None,
    current_maximum: Annotated[
        float | None, typer.Option(help="Maximum current in amperes.")
    ] = None,
    temperature_name: Annotated[
        str | None, typer.Option(help="Temperature condition name; defaults to DUT.")
    ] = None,
    temperature_minimum: Annotated[
        float | None, typer.Option(help="Minimum temperature in degrees Celsius.")
    ] = None,
    temperature_typical: Annotated[
        float | None, typer.Option(help="Typical temperature in degrees Celsius.")
    ] = None,
    temperature_maximum: Annotated[
        float | None, typer.Option(help="Maximum temperature in degrees Celsius.")
    ] = None,
    configuration: ConfigurationOption = Path("bench.toml"),
    supported_duts: Annotated[
        list[str] | None,
        typer.Option("--dut", help="Supported DUT ID or asset tag; repeatable."),
    ] = None,
    supported_boards: Annotated[
        list[str] | None,
        typer.Option("--board", help="Supported board ID or asset tag; repeatable."),
    ] = None,
) -> None:
    """Add a project referencing existing DUT and board records."""
    try:
        project = ProjectModel.model_validate(
            {
                "id": project_id,
                "internal_name": internal_name,
                "datasheet_name": datasheet_name,
                "specifications": _resolve_specifications(
                    specifications_file,
                    die_revision=die_revision,
                    metal_revision=metal_revision,
                    package_revision=package_revision,
                    voltage_name=voltage_name,
                    voltage_minimum=voltage_minimum,
                    voltage_typical=voltage_typical,
                    voltage_maximum=voltage_maximum,
                    current_minimum=current_minimum,
                    current_typical=current_typical,
                    current_maximum=current_maximum,
                    temperature_name=temperature_name,
                    temperature_minimum=temperature_minimum,
                    temperature_typical=temperature_typical,
                    temperature_maximum=temperature_maximum,
                ),
            }
        )
        project.supported_duts = _resolve_duts(
            supported_duts or [],
            configuration,
        )
        project.supported_boards = _resolve_boards(
            supported_boards or [],
            configuration,
        )
        with _repository(configuration) as repository:
            stored = repository.add(project)
    except (OSError, yaml.YAMLError, ValidationError, ValueError, LookupError) as error:
        raise typer.BadParameter(str(error)) from error
    except IntegrityError as error:
        typer.echo(
            f"Project ID or internal name already exists: {project_id}",
            err=True,
        )
        raise typer.Exit(code=1) from error
    except StatementError as error:
        raise typer.BadParameter(str(error.orig)) from error
    _write_project(stored)


@app.command("get")
def get_by_id(
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Get one project by ID."""
    with _repository(configuration) as repository:
        project = repository.fetch("id", project_id)
    if project is None:
        typer.echo(f"Project not found: {project_id}", err=True)
        raise typer.Exit(code=1)
    _write_project(project)


@app.command("list")
def fetch_all(
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Fetch all projects."""
    with _repository(configuration) as repository:
        projects = repository.fetchall()
    typer.echo(json.dumps([_project_data(project) for project in projects], indent=2))


@app.command("update")
def update_by_id(
    project_id: Annotated[
        str,
        typer.Argument(help="Project ID."),
    ],
    configuration: ConfigurationOption = Path("bench.toml"),
    new_internal_name: Annotated[
        str | None,
        typer.Option("--internal-name", help="Replacement unique internal name."),
    ] = None,
    datasheet_name: Annotated[
        str | None,
        typer.Option("--datasheet-name", help="Replacement client-facing name."),
    ] = None,
    specifications_file: Annotated[
        Path | None,
        typer.Option(
            "--specifications",
            help=(
                "Replace all revision profiles from YAML; cannot be combined "
                "with inline specification options."
            ),
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    die_revision: Annotated[
        str | None, typer.Option(help="Replacement die/base-layer revision.")
    ] = None,
    metal_revision: Annotated[
        int | None, typer.Option(min=0, help="Replacement metal-layer revision.")
    ] = None,
    package_revision: Annotated[
        str | None, typer.Option(help="Replacement package revision.")
    ] = None,
    voltage_name: Annotated[
        str | None, typer.Option(help="Replacement voltage rail name.")
    ] = None,
    voltage_minimum: Annotated[
        float | None, typer.Option(help="Replacement minimum voltage in volts.")
    ] = None,
    voltage_typical: Annotated[
        float | None, typer.Option(help="Replacement typical voltage in volts.")
    ] = None,
    voltage_maximum: Annotated[
        float | None, typer.Option(help="Replacement maximum voltage in volts.")
    ] = None,
    current_minimum: Annotated[
        float | None, typer.Option(help="Replacement minimum current in amperes.")
    ] = None,
    current_typical: Annotated[
        float | None, typer.Option(help="Replacement typical current in amperes.")
    ] = None,
    current_maximum: Annotated[
        float | None, typer.Option(help="Replacement maximum current in amperes.")
    ] = None,
    temperature_name: Annotated[
        str | None, typer.Option(help="Replacement temperature condition name.")
    ] = None,
    temperature_minimum: Annotated[
        float | None,
        typer.Option(help="Replacement minimum temperature in degrees Celsius."),
    ] = None,
    temperature_typical: Annotated[
        float | None,
        typer.Option(help="Replacement typical temperature in degrees Celsius."),
    ] = None,
    temperature_maximum: Annotated[
        float | None,
        typer.Option(help="Replacement maximum temperature in degrees Celsius."),
    ] = None,
    supported_duts: Annotated[
        list[str] | None,
        typer.Option("--dut", help="Replacement DUT ID or asset tag; repeatable."),
    ] = None,
    supported_boards: Annotated[
        list[str] | None,
        typer.Option(
            "--board",
            help="Replacement board ID or asset tag; repeatable.",
        ),
    ] = None,
    clear_duts: Annotated[bool, typer.Option()] = False,
    clear_boards: Annotated[bool, typer.Option()] = False,
) -> None:
    """Update a project by ID; specification options replace every profile."""
    if (
        new_internal_name is None
        and datasheet_name is None
        and specifications_file is None
        and die_revision is None
        and metal_revision is None
        and package_revision is None
        and voltage_name is None
        and voltage_minimum is None
        and voltage_typical is None
        and voltage_maximum is None
        and current_minimum is None
        and current_typical is None
        and current_maximum is None
        and temperature_name is None
        and temperature_minimum is None
        and temperature_typical is None
        and temperature_maximum is None
        and supported_duts is None
        and supported_boards is None
        and not clear_duts
        and not clear_boards
    ):
        raise typer.BadParameter("provide at least one field to update")

    try:
        with _repository(configuration) as repository:
            stored = repository.fetch("id", project_id)
            if stored is None:
                typer.echo(f"Project not found: {project_id}", err=True)
                raise typer.Exit(code=1)
            project = ProjectModel.model_validate(
                {
                    "id": stored.id,
                    "internal_name": new_internal_name or stored.internal_name,
                    "datasheet_name": datasheet_name or stored.datasheet_name,
                    "specifications": (
                        _resolve_specifications(
                            specifications_file,
                            die_revision=die_revision,
                            metal_revision=metal_revision,
                            package_revision=package_revision,
                            voltage_name=voltage_name,
                            voltage_minimum=voltage_minimum,
                            voltage_typical=voltage_typical,
                            voltage_maximum=voltage_maximum,
                            current_minimum=current_minimum,
                            current_typical=current_typical,
                            current_maximum=current_maximum,
                            temperature_name=temperature_name,
                            temperature_minimum=temperature_minimum,
                            temperature_typical=temperature_typical,
                            temperature_maximum=temperature_maximum,
                        )
                        if specifications_file is not None
                        or any(
                            value is not None
                            for value in (
                                die_revision,
                                metal_revision,
                                package_revision,
                                voltage_name,
                                voltage_minimum,
                                voltage_typical,
                                voltage_maximum,
                                current_minimum,
                                current_typical,
                                current_maximum,
                                temperature_name,
                                temperature_minimum,
                                temperature_typical,
                                temperature_maximum,
                            )
                        )
                        else stored.specifications
                    ),
                }
            )
            project.supported_duts = (
                _resolve_duts(supported_duts, configuration)
                if supported_duts is not None
                else ([] if clear_duts else stored.supported_duts)
            )
            project.supported_boards = (
                _resolve_boards(supported_boards, configuration)
                if supported_boards is not None
                else ([] if clear_boards else stored.supported_boards)
            )
            repository.upsert_many([project])
            updated = repository.fetch("id", project.id)
    except (OSError, yaml.YAMLError, ValidationError, ValueError, LookupError) as error:
        raise typer.BadParameter(str(error)) from error
    except IntegrityError as error:
        typer.echo("Internal project name already exists", err=True)
        raise typer.Exit(code=1) from error
    except StatementError as error:
        raise typer.BadParameter(str(error.orig)) from error
    if updated is None:  # pragma: no cover - upsert guarantees the row
        raise RuntimeError("Project update did not persist")
    _write_project(updated)


@app.command("delete")
def delete_by_id(
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Delete one project by ID."""
    with _repository(configuration) as repository:
        removed = repository.remove("id", project_id)
    if not removed:
        typer.echo(f"Project not found: {project_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Deleted project: {project_id}")


@app.command("sync")
def sync_yaml(
    source: Annotated[
        Path,
        typer.Argument(
            help="YAML list with nested DUT and board records.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Add or update projects and their existing resource relationships."""
    try:
        raw_data: object = yaml.safe_load(source.read_text(encoding="utf-8"))
        projects = parse_project_list(raw_data)
        with _repository(configuration) as repository:
            created, updated = repository.upsert_many(projects)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as error:
        typer.echo(f"Invalid project YAML: {error}", err=True)
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
    """Export projects and their related resource records to YAML."""
    if output.exists() and not force:
        typer.echo(f"File already exists: {output}; use --force to overwrite", err=True)
        raise typer.Exit(code=1)

    with _repository(configuration) as repository:
        projects = repository.fetchall()
    content = yaml.safe_dump(
        [_project_data(project) for project in projects],
        allow_unicode=True,
        sort_keys=False,
    )
    try:
        output.write_text(content, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Could not write YAML file: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Exported {len(projects)} projects to {output}")
