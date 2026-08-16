"""Typer command group for managing boards."""

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
    BoardCrud,
    BoardModel,
    ComConnection,
    USBConnection,
    ConnectionKind,
    SocketConnection,
    validate_board_list,
)

app = typer.Typer(
    help="Manage the ELIMS board database.",
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


def _repository(configuration: Path) -> BoardCrud:
    return BoardCrud(logging.getLogger("elims_instruments.cli"), configuration)


def _write_board(board: BoardModel) -> None:
    typer.echo(json.dumps(board.model_dump(mode="json"), indent=2))


def _connection(
    kind: ConnectionKind,
    # socket
    ip_address: str | None,
    port: int | None,
    mac_address: str | None,
    # com
    com_port: str | None,
    baud_rate: int | None,
    bytesize: int | None,
    stop_bits: float | None,
    parity: str | None,
    # usb
    vendor_id: int | None,
    product_id: int | None,
    serial_number: str | None,
    interface: int | None,
    timeout_seconds: float | None,
) -> object:
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

        if kind is ConnectionKind.COM:
            if com_port is None:
                raise typer.BadParameter(
                    "com connections require --com-port",
                    param_hint="--connection",
                )
            return ComConnection(
                port=com_port,
                baud_rate=baud_rate or 9600,
                bytesize=bytesize or 8,
                stop_bits=stop_bits or 1.0,
                parity=parity or "N",
                timeout_seconds=timeout_seconds or 5.0,
            )

        if kind is ConnectionKind.USB:
            if vendor_id is None or product_id is None:
                raise typer.BadParameter(
                    "usb connections require --vendor-id and --product-id",
                    param_hint="--connection",
                )
            return USBConnection(
                vendor_id=vendor_id,
                product_id=product_id,
                serial_number=serial_number,
                interface=interface,
                timeout_seconds=timeout_seconds or 10.0,
            )

        raise typer.BadParameter("unknown connection kind", param_hint="--connection")
    except ValidationError as error:
        raise typer.BadParameter(str(error), param_hint="--connection") from error


@app.command()
def add(
    board_id: Annotated[str, typer.Argument(help="Unique board ID.")],
    board_type: Annotated[str, typer.Option("--type", help="Board type.")],
    maker: Annotated[str, typer.Option(help="Board manufacturer.")],
    model: Annotated[str, typer.Option(help="Board model name.")],
    connection: Annotated[
        ConnectionKind,
        typer.Option("--connection", help="Connection type."),
    ],
    configuration: ConfigurationOption = Path("database.toml"),
    serial_number: Annotated[str | None, typer.Option()] = None,
    ip_address: Annotated[str | None, typer.Option()] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    mac_address: Annotated[str | None, typer.Option()] = None,
    com_port: Annotated[str | None, typer.Option()] = None,
    baud_rate: Annotated[int | None, typer.Option()] = None,
    bytesize: Annotated[int | None, typer.Option()] = None,
    stop_bits: Annotated[float | None, typer.Option()] = None,
    parity: Annotated[str | None, typer.Option()] = None,
    vendor_id: Annotated[int | None, typer.Option()] = None,
    product_id: Annotated[int | None, typer.Option()] = None,
    interface: Annotated[int | None, typer.Option()] = None,
    timeout_seconds: Annotated[float | None, typer.Option(min=0.001)] = None,
) -> None:
    link = _connection(
        connection,
        ip_address,
        port,
        mac_address,
        com_port,
        baud_rate,
        bytesize,
        stop_bits,
        parity,
        vendor_id,
        product_id,
        serial_number,
        interface,
        timeout_seconds,
    )
    try:
        board = BoardModel.model_validate(
            {
                "id": board_id,
                "type": board_type,
                "maker": maker,
                "model": model,
                "serial_number": serial_number,
                "connection": link,
            }
        )
        stored = _repository(configuration).add(board)
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    except IntegrityError as error:
        typer.echo(f"Board already exists: {board_id}", err=True)
        raise typer.Exit(code=1) from error
    _write_board(stored)


@app.command("get")
def get_by_id(
    board_id: Annotated[str, typer.Argument(help="Board ID.")],
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    board = _repository(configuration).fetch("id", board_id)
    if board is None:
        typer.echo(f"Board not found: {board_id}", err=True)
        raise typer.Exit(code=1)
    _write_board(board)


@app.command("gets")
def fetch_all(
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    boards = _repository(configuration).fetchall()
    typer.echo(
        json.dumps([board.model_dump(mode="json") for board in boards], indent=2)
    )


@app.command("update")
def update_by_id(
    board_id: Annotated[str, typer.Argument(help="Board ID.")],
    configuration: ConfigurationOption = Path("database.toml"),
    board_type: Annotated[str | None, typer.Option("--type")] = None,
    maker: Annotated[str | None, typer.Option()] = None,
    model: Annotated[str | None, typer.Option()] = None,
    serial_number: Annotated[str | None, typer.Option()] = None,
    clear_serial_number: Annotated[bool, typer.Option()] = False,
    connection: Annotated[ConnectionKind | None, typer.Option("--connection")] = None,
    ip_address: Annotated[str | None, typer.Option()] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    mac_address: Annotated[str | None, typer.Option()] = None,
    com_port: Annotated[str | None, typer.Option()] = None,
    baud_rate: Annotated[int | None, typer.Option()] = None,
    bytesize: Annotated[int | None, typer.Option()] = None,
    stop_bits: Annotated[float | None, typer.Option()] = None,
    parity: Annotated[str | None, typer.Option()] = None,
    vendor_id: Annotated[int | None, typer.Option()] = None,
    product_id: Annotated[int | None, typer.Option()] = None,
    interface: Annotated[int | None, typer.Option()] = None,
    timeout_seconds: Annotated[float | None, typer.Option(min=0.001)] = None,
) -> None:
    changes: dict[str, object] = {
        field: value
        for field, value in {
            "type": board_type,
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
            com_port,
            baud_rate,
            bytesize,
            stop_bits,
            parity,
            vendor_id,
            product_id,
            serial_number,
            interface,
            timeout_seconds,
        )
    if not changes:
        raise typer.BadParameter("provide at least one field to update")

    try:
        board = _repository(configuration).update_by_id(board_id, changes)
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
    if board is None:
        typer.echo(f"Board not found: {board_id}", err=True)
        raise typer.Exit(code=1)
    _write_board(board)


@app.command("delete")
def delete_by_id(
    board_id: Annotated[str, typer.Argument(help="Board ID.")],
    configuration: ConfigurationOption = Path("database.toml"),
) -> None:
    if not _repository(configuration).remove("id", board_id):
        typer.echo(f"Board not found: {board_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Deleted board: {board_id}")


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
    try:
        raw_data: object = yaml.safe_load(source.read_text(encoding="utf-8"))
        boards = validate_board_list(raw_data)
        created, updated = _repository(configuration).upsert_many(boards)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as error:
        typer.echo(f"Invalid board YAML: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Created: {created}; Updated: {updated}")


@app.command("export")
def export_yaml(
    output: Annotated[Path, typer.Argument(help="Destination YAML file")],
    configuration: ConfigurationOption = Path("database.toml"),
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing YAML file."),
    ] = False,
) -> None:
    if output.exists() and not force:
        typer.echo(f"File already exists: {output}; use --force to overwrite", err=True)
        raise typer.Exit(code=1)

    boards = _repository(configuration).fetchall()
    content = yaml.safe_dump(
        [board.model_dump(mode="json") for board in boards],
        allow_unicode=True,
        sort_keys=False,
    )
    try:
        output.write_text(content, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Could not write YAML file: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Exported {len(boards)} boards to {output}")
