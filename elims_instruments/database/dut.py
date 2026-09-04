"""Validated and persistent DUT definitions for IC characterization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Self

from pydantic import BeforeValidator, StringConstraints, TypeAdapter, model_validator
from sqlmodel import Field, SQLModel

from .crud import Crud, DebugLogger

if TYPE_CHECKING:
    from pathlib import Path


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AssetTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]


def _normalize_revision(value: object) -> object:
    """Normalize string revision values before pattern validation."""
    return value.strip().upper() if isinstance(value, str) else value


DieRevision = Annotated[
    str,
    BeforeValidator(_normalize_revision),
    StringConstraints(pattern=r"^[A-Z]+$"),
]
PackageRevision = Annotated[
    str,
    BeforeValidator(_normalize_revision),
    StringConstraints(pattern=r"^R[1-9]\d*$"),
]


class DutModel(SQLModel, table=True):
    """An IC DUT record and its manufacturing traceability."""

    __tablename__ = "duts"

    id: NonEmptyString = Field(primary_key=True)
    asset_tag: AssetTag = Field(unique=True, index=True)
    project: NonEmptyString = Field(index=True)
    corner: NonEmptyString = Field(index=True)
    die_revision: DieRevision = Field(index=True)
    metal_revision: int | None = Field(default=None, ge=0, index=True)
    package_revision: PackageRevision | None = Field(default=None, index=True)
    serial_number: NonEmptyString | None = Field(default=None, index=True)
    lot_number: NonEmptyString | None = Field(default=None, index=True)
    wafer_id: NonEmptyString | None = Field(default=None, index=True)
    die_x: int | None = None
    die_y: int | None = None

    @model_validator(mode="after")
    def validate_die_position(self) -> Self:
        """Require both coordinates when identifying a die."""
        if (self.die_x is None) != (self.die_y is None):
            raise ValueError("die_x and die_y must be provided together")
        return self


_RAW_DUT_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)


def parse_dut_list(raw_data: object) -> list[DutModel]:
    """Parse raw mappings into validated DUT models."""
    # SQLModel table construction skips Pydantic's required-field validation.
    # Validate each raw mapping explicitly to keep imports strict.
    records = _RAW_DUT_LIST_ADAPTER.validate_python(raw_data)
    return [DutModel.model_validate(record) for record in records]


class DutCrud(Crud[DutModel]):
    """CRUD repository specialized for DUT records."""

    def __init__(
        self,
        logger: DebugLogger,
        toml_path: Path,
        *,
        create_tables: bool = True,
    ) -> None:
        """Initialize the DUT repository."""
        super().__init__(
            logger,
            toml_path,
            DutModel,
            create_tables=create_tables,
        )
