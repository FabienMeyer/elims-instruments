"""Validated and persistent instrument definitions."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import TypeAdapter
from sqlalchemy import Column
from sqlmodel import Field, Session, SQLModel, select

from .crud import Crud
from .connections import (
    Connection,
    ConnectionKind,
    ConnectionType,
    SocketConnection,
    VisaConnection,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from logging import Logger
    from pathlib import Path

    from sqlalchemy.engine.interfaces import Dialect


# Connection models come from database.connections


_RAW_INSTRUMENT_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)

# reuse ConnectionType and adapters from connections.py via imports
_CONNECTION_ADAPTER: TypeAdapter[Connection] = TypeAdapter(Connection)


class InstrumentModel(SQLModel, table=True):
    """An instrument record and its connection settings."""

    __tablename__ = "instruments"

    id: str = Field(primary_key=True, min_length=1)
    type: str = Field(min_length=1, index=True)
    maker: str = Field(min_length=1)
    model: str = Field(min_length=1)
    serial_number: str | None = Field(default=None, index=True)
    connection: Connection = Field(
        sa_column=Column(ConnectionType(), nullable=False),
    )


def validate_instrument_list(raw_data: object) -> list[InstrumentModel]:
    """Validate raw instrument mappings and their discriminated connections.

    Args:
        raw_data: Untrusted decoded data, typically loaded from YAML or JSON.

    Returns:
        Fully validated instrument table models.
    """
    records = _RAW_INSTRUMENT_LIST_ADAPTER.validate_python(raw_data)
    instruments: list[InstrumentModel] = []
    for record in records:
        values = dict(record)
        values["connection"] = _CONNECTION_ADAPTER.validate_python(
            values.get("connection")
        )
        instruments.append(InstrumentModel.model_validate(values))
    return instruments


class InstrumentCrud(Crud[InstrumentModel]):
    """CRUD repository specialized for instrument records."""

    def __init__(
        self,
        logger: Logger,
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

    def update_by_id(
        self,
        instrument_id: str,
        changes: Mapping[str, object],
    ) -> InstrumentModel | None:
        """Atomically update an instrument selected by its ID.

        Args:
            instrument_id: ID of the instrument to update.
            changes: Instrument fields and their replacement values.

        Returns:
            The updated instrument, or ``None`` when the ID does not exist.
        """
        invalid_fields = set(changes) - set(InstrumentModel.model_fields)
        if invalid_fields:
            fields = ", ".join(sorted(invalid_fields))
            raise ValueError(f"Unknown InstrumentModel fields: {fields}")
        if "id" in changes:
            raise ValueError("The instrument ID cannot be changed")

        statement = select(InstrumentModel).where(InstrumentModel.id == instrument_id)
        with Session(self.engine) as session:
            instrument = session.exec(statement).first()
            if instrument is None:
                return None

            values = instrument.model_dump()
            values.update(changes)
            validated = InstrumentModel.model_validate(values)
            for field in changes:
                setattr(instrument, field, getattr(validated, field))
            session.add(instrument)
            session.commit()
            session.refresh(instrument)
            return instrument

    def upsert_many(
        self,
        instruments: Sequence[InstrumentModel],
    ) -> tuple[int, int]:
        """Insert missing instruments and replace existing records by ID.

        All records are applied in one transaction. Existing records receive every
        field from the supplied model, including ``None`` values.

        Args:
            instruments: Fully validated instrument records to apply.

        Returns:
            A ``(created, updated)`` count tuple.

        Raises:
            ValueError: If the input contains a duplicate instrument ID.
        """
        identifiers = [instrument.id for instrument in instruments]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("The instrument list contains duplicate IDs")

        created = 0
        updated = 0
        with Session(self.engine) as session:
            for incoming in instruments:
                stored = session.get(InstrumentModel, incoming.id)
                if stored is None:
                    session.add(incoming)
                    created += 1
                    continue

                for field in InstrumentModel.model_fields:
                    if field != "id":
                        setattr(stored, field, getattr(incoming, field))
                session.add(stored)
                updated += 1
            session.commit()
        return created, updated
