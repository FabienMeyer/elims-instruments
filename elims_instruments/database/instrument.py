"""Validated and persistent instrument definitions."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

from pydantic import StringConstraints, TypeAdapter
from sqlalchemy import Column, Enum
from sqlmodel import Field, SQLModel

from .connections import (
    Connection,
    ConnectionType,
)
from .crud import Crud, DebugLogger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


# Connection models come from database.connections


_RAW_INSTRUMENT_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AssetTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]


class InstrumentType(StrEnum):
    """Supported laboratory instrument categories."""

    COUNTER = "counter"
    MULTIMETER = "multimeter"
    OSCILLOSCOPE = "oscilloscope"


_INSTRUMENT_TYPE_DB = Enum(
    InstrumentType,
    values_callable=lambda enum: [member.value for member in enum],
    native_enum=False,
    validate_strings=True,
)


class InstrumentModel(SQLModel, table=True):
    """An instrument record and its connection settings."""

    __tablename__ = "instruments"

    id: NonEmptyString = Field(primary_key=True)
    asset_tag: AssetTag = Field(unique=True, index=True)
    type: InstrumentType = Field(
        sa_column=Column(_INSTRUMENT_TYPE_DB, nullable=False, index=True)
    )
    maker: NonEmptyString
    model: NonEmptyString
    serial_number: NonEmptyString | None = Field(default=None, index=True)
    connection: Connection = Field(
        sa_column=Column(ConnectionType(), nullable=False),
    )


def parse_instrument_list(raw_data: object) -> list[InstrumentModel]:
    """Parse raw instrument mappings into validated models.

    Args:
        raw_data: Untrusted decoded data, typically loaded from YAML or JSON.

    Returns:
        Fully validated instrument table models.
    """
    # SQLModel table construction skips Pydantic's required-field validation.
    # Validate each raw mapping explicitly to keep imports strict.
    records = _RAW_INSTRUMENT_LIST_ADAPTER.validate_python(raw_data)
    return [InstrumentModel.model_validate(record) for record in records]


class InstrumentCrud(Crud[InstrumentModel]):
    """CRUD repository specialized for instrument records."""

    def __init__(
        self,
        logger: DebugLogger,
        toml_path: Path,
        *,
        create_tables: bool = True,
    ) -> None:
        """Initialize the instrument repository."""
        super().__init__(
            logger,
            toml_path,
            InstrumentModel,
            create_tables=create_tables,
        )

    def add(self, data: InstrumentModel) -> InstrumentModel:
        """Validate a table-model instance before persisting it."""
        validated = InstrumentModel.model_validate(data.model_dump())
        return super().add(validated)

    def upsert_many(
        self,
        records: Sequence[InstrumentModel],
    ) -> tuple[int, int]:
        """Validate every table-model instance before applying the batch."""
        validated = [
            InstrumentModel.model_validate(record.model_dump())
            for record in records
        ]
        return super().upsert_many(validated)
