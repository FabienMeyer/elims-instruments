"""Validated and persistent board definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import StringConstraints, TypeAdapter
from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from .connections import Connection, ConnectionType
from .crud import Crud, DebugLogger

if TYPE_CHECKING:
    from pathlib import Path


_RAW_BOARD_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AssetTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]


class BoardModel(SQLModel, table=True):
    """A board record and its connection settings."""

    __tablename__ = "boards"

    id: NonEmptyString = Field(primary_key=True)
    asset_tag: AssetTag = Field(unique=True, index=True)
    type: NonEmptyString = Field(index=True)
    maker: NonEmptyString
    model: NonEmptyString
    serial_number: NonEmptyString | None = Field(default=None, index=True)
    connection: Connection = Field(
        sa_column=Column(ConnectionType(), nullable=False),
    )


def parse_board_list(raw_data: object) -> list[BoardModel]:
    """Parse raw board mappings into validated models.

    Args:
        raw_data: Untrusted decoded data, typically loaded from YAML or JSON.

    Returns:
        Fully validated board table models.
    """
    # SQLModel table construction skips Pydantic's required-field validation.
    # Validate each raw mapping explicitly to keep imports strict.
    records = _RAW_BOARD_LIST_ADAPTER.validate_python(raw_data)
    return [BoardModel.model_validate(record) for record in records]


class BoardCrud(Crud[BoardModel]):
    """CRUD repository specialized for board records."""

    def __init__(
        self,
        logger: DebugLogger,
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
