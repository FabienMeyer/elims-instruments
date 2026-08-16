"""Validated and persistent board definitions."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import TypeAdapter
from sqlalchemy import JSON, Column
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, Session, SQLModel, select

from .crud import Crud

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from logging import Logger
    from pathlib import Path

    from sqlalchemy.engine.interfaces import Dialect


class ComConnection(SQLModel):
    """Serial (COM) connection settings."""

    kind: Literal["com"] = "com"
    port: str = Field(min_length=1)
    baud_rate: int = Field(default=9600, ge=110, le=460800)
    bytesize: int = Field(default=8, ge=5, le=8)
    stop_bits: float = Field(default=1.0, gt=0)
    parity: str | None = Field(default="N", min_length=1, max_length=1)
    timeout_seconds: float = Field(default=5.0, gt=0)


class USBConnection(SQLModel):
    """USB connection settings."""

    kind: Literal["usb"] = "usb"
    vendor_id: int = Field(ge=0)
    product_id: int = Field(ge=0)
    serial_number: str | None = Field(default=None, min_length=1)
    interface: int | None = Field(default=None, ge=0)
    timeout_seconds: float = Field(default=10.0, gt=0)


from .connections import Connection, ConnectionKind, SocketConnection


_CONNECTION_ADAPTER: TypeAdapter[Connection] = TypeAdapter(Connection)
_RAW_BOARD_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)


class ConnectionType(TypeDecorator[Connection]):
    """Store a validated connection model in a JSON database column."""

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self,
        value: Connection | None,
        dialect: Dialect,
    ) -> dict[str, Any] | None:
        """Convert a connection model to JSON-compatible data."""
        del dialect
        return None if value is None else value.model_dump(mode="json")

    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> Connection | None:
        """Validate JSON data read from the database."""
        del dialect
        return None if value is None else _CONNECTION_ADAPTER.validate_python(value)


class BoardModel(SQLModel, table=True):
    """A board record and its connection settings."""

    __tablename__ = "boards"

    id: str = Field(primary_key=True, min_length=1)
    type: str = Field(min_length=1, index=True)
    maker: str = Field(min_length=1)
    model: str = Field(min_length=1)
    serial_number: str | None = Field(default=None, index=True)
    connection: Connection = Field(
        sa_column=Column(ConnectionType(), nullable=False),
    )


def validate_board_list(raw_data: object) -> list[BoardModel]:
    """Validate raw board mappings and their discriminated connections.

    Args:
        raw_data: Untrusted decoded data, typically loaded from YAML or JSON.

    Returns:
        Fully validated board table models.
    """
    records = _RAW_BOARD_LIST_ADAPTER.validate_python(raw_data)
    boards: list[BoardModel] = []
    for record in records:
        values = dict(record)
        values["connection"] = _CONNECTION_ADAPTER.validate_python(
            values.get("connection")
        )
        boards.append(BoardModel.model_validate(values))
    return boards


class BoardCrud(Crud[BoardModel]):
    """CRUD repository specialized for board records."""

    def __init__(
        self,
        logger: Logger,
        toml_path: Path,
        *,
        create_tables: bool = True,
    ) -> None:
        """Initialize the board repository."""
        super().__init__(
            logger,
            toml_path,
            BoardModel,
            create_tables=create_tables,
        )

    def update_by_id(
        self,
        board_id: str,
        changes: Mapping[str, object],
    ) -> BoardModel | None:
        """Atomically update a board selected by its ID.

        Args:
            board_id: ID of the board to update.
            changes: Board fields and their replacement values.

        Returns:
            The updated board, or ``None`` when the ID does not exist.
        """
        invalid_fields = set(changes) - set(BoardModel.model_fields)
        if invalid_fields:
            fields = ", ".join(sorted(invalid_fields))
            raise ValueError(f"Unknown BoardModel fields: {fields}")
        if "id" in changes:
            raise ValueError("The board ID cannot be changed")

        statement = select(BoardModel).where(BoardModel.id == board_id)
        with Session(self.engine) as session:
            board = session.exec(statement).first()
            if board is None:
                return None

            values = board.model_dump()
            values.update(changes)
            validated = BoardModel.model_validate(values)
            for field in changes:
                setattr(board, field, getattr(validated, field))
            session.add(board)
            session.commit()
            session.refresh(board)
            return board

    def upsert_many(
        self,
        boards: Sequence[BoardModel],
    ) -> tuple[int, int]:
        """Insert missing boards and replace existing records by ID.

        All records are applied in one transaction. Existing records receive every
        field from the supplied model, including ``None`` values.

        Args:
            boards: Fully validated board records to apply.

        Returns:
            A ``(created, updated)`` count tuple.

        Raises:
            ValueError: If the input contains a duplicate board ID.
        """
        identifiers = [board.id for board in boards]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("The board list contains duplicate IDs")

        created = 0
        updated = 0
        with Session(self.engine) as session:
            for incoming in boards:
                stored = session.get(BoardModel, incoming.id)
                if stored is None:
                    session.add(incoming)
                    created += 1
                    continue

                for field in BoardModel.model_fields:
                    if field != "id":
                        setattr(stored, field, getattr(incoming, field))
                session.add(stored)
                updated += 1
            session.commit()
        return created, updated
