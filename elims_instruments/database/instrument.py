"""Validated and persistent instrument definitions."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Self

from pydantic import StringConstraints, TypeAdapter, model_validator
from sqlalchemy import JSON, Column, Enum, event
from sqlalchemy.orm import object_session
from sqlmodel import Field, Session, SQLModel, select

from .connections import (
    Connection,
    ConnectionType,
)
from .crud import Crud, DebugLogger

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.engine import Connection as SqlAlchemyConnection
    from sqlalchemy.orm import Mapper


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
    POWER_SUPPLY = "power_supply"
    THERMAL_TEST_SYSTEM = "thermal_test_system"


class CalibrationStatus(StrEnum):
    """Calibration state recorded for a laboratory instrument."""

    UNKNOWN = "unknown"
    VALID = "valid"
    EXPIRED = "expired"
    NOT_REQUIRED = "not_required"


class InstrumentRevisionAction(StrEnum):
    """Database operation that produced an instrument revision."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


_INSTRUMENT_TYPE_DB = Enum(
    InstrumentType,
    values_callable=lambda enum: [member.value for member in enum],
    native_enum=False,
    validate_strings=True,
)
_CALIBRATION_STATUS_DB = Enum(
    CalibrationStatus,
    values_callable=lambda enum: [member.value for member in enum],
    native_enum=False,
    validate_strings=True,
)
_INSTRUMENT_REVISION_ACTION_DB = Enum(
    InstrumentRevisionAction,
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
    calibration_date: date | None = Field(default=None, index=True)
    calibration_due_date: date | None = Field(default=None, index=True)
    calibration_certificate_number: NonEmptyString | None = Field(
        default=None,
        index=True,
    )
    calibration_status: CalibrationStatus = Field(
        default=CalibrationStatus.UNKNOWN,
        sa_column=Column(_CALIBRATION_STATUS_DB, nullable=False, index=True),
    )
    connection: Connection = Field(
        sa_column=Column(ConnectionType(), nullable=False),
    )

    @model_validator(mode="after")
    def validate_calibration_dates(self) -> Self:
        """Require the calibration due date to follow its calibration date."""
        if (
            self.calibration_date is not None
            and self.calibration_due_date is not None
            and self.calibration_due_date < self.calibration_date
        ):
            raise ValueError("calibration_due_date cannot precede calibration_date")
        return self


class InstrumentRevisionModel(SQLModel, table=True):
    """Immutable snapshot of one persisted instrument state."""

    __tablename__ = "instrument_revisions"

    id: int | None = Field(default=None, primary_key=True)
    instrument_id: NonEmptyString = Field(index=True)
    asset_tag: AssetTag = Field(index=True)
    recorded_at: datetime = Field(index=True)
    action: InstrumentRevisionAction = Field(
        sa_column=Column(_INSTRUMENT_REVISION_ACTION_DB, nullable=False),
    )
    snapshot: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


def _record_instrument_revision(
    connection: SqlAlchemyConnection,
    target: InstrumentModel,
    action: InstrumentRevisionAction,
) -> None:
    """Insert an instrument snapshot in the active database transaction."""
    connection.execute(
        InstrumentRevisionModel.__table__.insert(),  # type: ignore[attr-defined]
        {
            "instrument_id": target.id,
            "asset_tag": target.asset_tag,
            "recorded_at": datetime.now(UTC),
            "action": action.value,
            "snapshot": target.model_dump(mode="json"),
        },
    )


def _record_instrument_created(
    _mapper: Mapper[InstrumentModel],
    connection: SqlAlchemyConnection,
    target: InstrumentModel,
) -> None:
    """Record a newly persisted instrument."""
    _record_instrument_revision(connection, target, InstrumentRevisionAction.CREATED)


def _record_instrument_updated(
    _mapper: Mapper[InstrumentModel],
    connection: SqlAlchemyConnection,
    target: InstrumentModel,
) -> None:
    """Record the resulting state of an instrument update."""
    session = object_session(target)
    if session is not None and not session.is_modified(
        target,
        include_collections=False,
    ):
        return
    _record_instrument_revision(connection, target, InstrumentRevisionAction.UPDATED)


def _record_instrument_deleted(
    _mapper: Mapper[InstrumentModel],
    connection: SqlAlchemyConnection,
    target: InstrumentModel,
) -> None:
    """Record the final state of an instrument before deletion."""
    _record_instrument_revision(connection, target, InstrumentRevisionAction.DELETED)


event.listen(InstrumentModel, "after_insert", _record_instrument_created)
event.listen(InstrumentModel, "after_update", _record_instrument_updated)
event.listen(InstrumentModel, "before_delete", _record_instrument_deleted)


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

    def history(self, asset_tag: str) -> list[InstrumentRevisionModel]:
        """Return every snapshot recorded for an asset tag in time order."""
        statement = select(InstrumentRevisionModel).where(
            InstrumentRevisionModel.asset_tag == asset_tag
        )
        with Session(self.engine) as session:
            revisions = list(session.exec(statement).all())
        return sorted(
            revisions,
            key=lambda revision: (revision.recorded_at, revision.id or 0),
        )

    def history_for_instrument(
        self,
        instrument_id: str,
    ) -> list[InstrumentRevisionModel]:
        """Return every snapshot for an instrument, including asset-tag changes."""
        statement = select(InstrumentRevisionModel).where(
            InstrumentRevisionModel.instrument_id == instrument_id
        )
        with Session(self.engine) as session:
            revisions = list(session.exec(statement).all())
        return sorted(
            revisions,
            key=lambda revision: (revision.recorded_at, revision.id or 0),
        )

    def fetch_at(self, asset_tag: str, recorded_at: datetime) -> InstrumentModel | None:
        """Return the instrument state applicable at a historical timestamp."""
        timestamp = (
            recorded_at.replace(tzinfo=UTC)
            if recorded_at.tzinfo is None
            else recorded_at.astimezone(UTC)
        )
        matching_revisions = [
            revision
            for revision in self.history(asset_tag)
            if (
                revision.recorded_at.replace(tzinfo=UTC)
                if revision.recorded_at.tzinfo is None
                else revision.recorded_at.astimezone(UTC)
            )
            <= timestamp
        ]
        if not matching_revisions:
            return None
        instrument_id = matching_revisions[-1].instrument_id
        instrument_revisions = [
            revision
            for revision in self.history_for_instrument(instrument_id)
            if (
                revision.recorded_at.replace(tzinfo=UTC)
                if revision.recorded_at.tzinfo is None
                else revision.recorded_at.astimezone(UTC)
            )
            <= timestamp
        ]
        latest = instrument_revisions[-1]
        if (
            latest.action is InstrumentRevisionAction.DELETED
            or latest.asset_tag != asset_tag
        ):
            return None
        return InstrumentModel.model_validate(latest.snapshot)
