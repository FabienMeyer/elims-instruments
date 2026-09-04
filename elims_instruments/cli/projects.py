"""Typer command group for managing characterization projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    ProjectCrud,
    ProjectModel,
    parse_project_list,
)
from elims_instruments.utils.logger import get_cli_logger

from .common import managed_repository

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

app = typer.Typer(
    help="Manage the ELIMS project database.",
    no_args_is_help=True,
)

ConfigurationOption = Annotated[
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
        "name": project.name,
        "supported_duts": [
            dut.model_dump(mode="json") for dut in project.supported_duts
        ],
        "supported_boards": [
            board.model_dump(mode="json") for board in project.supported_boards
        ],
    }


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
    name: Annotated[str, typer.Option(help="Unique project name.")],
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
        project = ProjectModel.model_validate({"id": project_id, "name": name})
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
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except IntegrityError as error:
        typer.echo(f"Project ID or name already exists: {project_id}", err=True)
        raise typer.Exit(code=1) from error
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


@app.command("gets")
def fetch_all(
    configuration: ConfigurationOption = Path("bench.toml"),
) -> None:
    """Fetch all projects."""
    with _repository(configuration) as repository:
        projects = repository.fetchall()
    typer.echo(json.dumps([_project_data(project) for project in projects], indent=2))


@app.command("update")
def update_by_name(
    name: Annotated[str, typer.Argument(help="Current project name.")],
    configuration: ConfigurationOption = Path("bench.toml"),
    new_name: Annotated[str | None, typer.Option("--name")] = None,
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
    """Update a project selected by its current name."""
    if (
        new_name is None
        and supported_duts is None
        and supported_boards is None
        and not clear_duts
        and not clear_boards
    ):
        raise typer.BadParameter("provide at least one field to update")

    try:
        with _repository(configuration) as repository:
            stored = repository.fetch("name", name)
            if stored is None:
                typer.echo(f"Project not found: {name}", err=True)
                raise typer.Exit(code=1)
            project = ProjectModel.model_validate(
                {"id": stored.id, "name": new_name or stored.name}
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
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except IntegrityError as error:
        typer.echo("Project name already exists", err=True)
        raise typer.Exit(code=1) from error
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
