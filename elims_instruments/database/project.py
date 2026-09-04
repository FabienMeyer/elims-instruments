"""Validated and persistent characterization-project definitions."""

from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Self, cast

from pydantic import StringConstraints, TypeAdapter, model_validator
from sqlalchemy import JSON, Column
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, Relationship, Session, SQLModel

from elims_instruments.temperatures import TemperatureSpecification
from elims_instruments.utils import Limits
from elims_instruments.voltages import VoltageSpecification

from .board import BoardModel
from .crud import Crud, DebugLogger
from .dut import DieRevision, DutModel, PackageRevision

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProjectRevisionSpecifications(SQLModel):
    """Electrical and thermal specifications for one exact DUT revision."""

    die_revision: DieRevision
    metal_revision: int | None = Field(default=None, ge=0)
    package_revision: PackageRevision | None = None
    voltage_specifications: tuple[VoltageSpecification, ...]
    temperature_specifications: tuple[TemperatureSpecification, ...]

    @model_validator(mode="after")
    def validate_specifications(self) -> Self:
        """Require named voltage and temperature specifications without duplicates."""
        for kind, specifications in (
            ("voltage", self.voltage_specifications),
            ("temperature", self.temperature_specifications),
        ):
            if not specifications:
                raise ValueError(f"At least one {kind} specification is required")
            names = [
                specification.name.strip().casefold()
                for specification in specifications
            ]
            if any(not name for name in names):
                raise ValueError(
                    f"{kind.capitalize()} specification names cannot be empty"
                )
            if len(names) != len(set(names)):
                raise ValueError(f"Duplicate {kind} specification names")
        return self


ProjectRevisionSpecifications.model_rebuild(_types_namespace={"Limits": Limits})
_PROJECT_SPECIFICATIONS_ADAPTER: TypeAdapter[list[ProjectRevisionSpecifications]] = (
    TypeAdapter(list[ProjectRevisionSpecifications])
)


def _encode_temperature_degrees(value: object) -> int | None:
    """Encode a Celsius limit as an integer number of deci-degrees."""
    if value is None:
        return None
    deci_degrees = Decimal(str(value)) * 10
    if deci_degrees != deci_degrees.to_integral_value():
        raise ValueError(f"Temperature limit {value!r} is not representable in 0.1 °C")
    return int(deci_degrees)


def _decode_temperature_degrees(value: object) -> float | None:
    """Decode an integer number of deci-degrees to Celsius."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Stored temperature limits must be integer deci-degrees")
    return value / 10.0


def _convert_stored_temperatures(
    profiles: list[dict[str, Any]],
    converter: Callable[[object], int | float | None],
) -> None:
    """Convert every temperature limit value in serialized profiles in place."""
    for profile in profiles:
        for specification in profile["temperature_specifications"]:
            limits = specification["temperature_limits"]
            for name, value in limits.items():
                limits[name] = converter(value)


class ProjectSpecificationsType(TypeDecorator[list[ProjectRevisionSpecifications]]):
    """Store validated revision profiles in a JSON database column."""

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self,
        value: list[ProjectRevisionSpecifications] | None,
        dialect: Dialect,
    ) -> list[dict[str, Any]] | None:
        """Convert revision profiles to JSON-compatible data."""
        del dialect
        if value is None:
            return None
        dumped = _PROJECT_SPECIFICATIONS_ADAPTER.dump_python(value, mode="json")
        profiles = cast("list[dict[str, Any]]", dumped)
        _convert_stored_temperatures(profiles, _encode_temperature_degrees)
        return profiles

    def process_result_value(
        self,
        value: list[dict[str, Any]] | None,
        dialect: Dialect,
    ) -> list[ProjectRevisionSpecifications] | None:
        """Validate revision profiles read from the database."""
        del dialect
        if value is None:
            return None
        _convert_stored_temperatures(value, _decode_temperature_degrees)
        return _PROJECT_SPECIFICATIONS_ADAPTER.validate_python(value)


def parse_project_specifications(
    raw_data: object,
) -> list[ProjectRevisionSpecifications]:
    """Parse and validate a list of revision-dependent specifications."""
    return _PROJECT_SPECIFICATIONS_ADAPTER.validate_python(raw_data)


class ProjectDutLink(SQLModel, table=True):
    """Associate a project with one supported DUT."""

    __tablename__ = "project_supported_duts"

    project_id: str = Field(foreign_key="projects.id", primary_key=True)
    dut_id: str = Field(foreign_key="duts.id", primary_key=True)


class ProjectBoardLink(SQLModel, table=True):
    """Associate a project with one supported board."""

    __tablename__ = "project_supported_boards"

    project_id: str = Field(foreign_key="projects.id", primary_key=True)
    board_id: str = Field(foreign_key="boards.id", primary_key=True)


class ProjectModel(SQLModel, table=True):
    """A project and the DUT and board models that it supports."""

    __tablename__ = "projects"

    id: NonEmptyString = Field(primary_key=True)
    internal_name: NonEmptyString = Field(unique=True, index=True)
    datasheet_name: NonEmptyString
    specifications: list[ProjectRevisionSpecifications] = Field(
        sa_column=Column(ProjectSpecificationsType(), nullable=False)
    )
    supported_duts: list[DutModel] = Relationship(
        link_model=ProjectDutLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    supported_boards: list[BoardModel] = Relationship(
        link_model=ProjectBoardLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @model_validator(mode="after")
    def validate_revision_profiles(self) -> Self:
        """Require one unambiguous profile for every configured revision tuple."""
        if not self.specifications:
            raise ValueError("At least one project revision specification is required")
        keys = [
            (
                specification.die_revision,
                specification.metal_revision,
                specification.package_revision,
            )
            for specification in self.specifications
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate project revision specification")
        return self

    def specifications_for(self, dut: DutModel) -> ProjectRevisionSpecifications:
        """Return the exact voltage and temperature profile for *dut*."""
        revision = (
            dut.die_revision,
            dut.metal_revision,
            dut.package_revision,
        )
        for specification in self.specifications:
            if revision == (
                specification.die_revision,
                specification.metal_revision,
                specification.package_revision,
            ):
                return specification
        raise LookupError(
            "No project specifications for DUT revisions "
            f"{dut.die_revision}/{dut.metal_revision}/{dut.package_revision}"
        )


_RAW_PROJECT_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)
_DUT_LIST_ADAPTER: TypeAdapter[list[DutModel]] = TypeAdapter(list[DutModel])
_BOARD_LIST_ADAPTER: TypeAdapter[list[BoardModel]] = TypeAdapter(list[BoardModel])


def parse_project_list(raw_data: object) -> list[ProjectModel]:
    """Parse project mappings containing nested DUT and board records."""
    records = _RAW_PROJECT_LIST_ADAPTER.validate_python(raw_data)
    projects: list[ProjectModel] = []
    for record in records:
        values = dict(record)
        raw_duts = values.pop("supported_duts", [])
        raw_boards = values.pop("supported_boards", [])
        project = ProjectModel.model_validate(values)
        project.supported_duts = _DUT_LIST_ADAPTER.validate_python(raw_duts)
        project.supported_boards = _BOARD_LIST_ADAPTER.validate_python(raw_boards)
        projects.append(project)
    return projects


class ProjectCrud(Crud[ProjectModel]):
    """CRUD repository specialized for project records."""

    def __init__(
        self,
        logger: DebugLogger,
        toml_path: Path,
        *,
        create_tables: bool = True,
    ) -> None:
        """Initialize the project repository."""
        super().__init__(
            logger,
            toml_path,
            ProjectModel,
            create_tables=create_tables,
        )

    @staticmethod
    def _resolve_duts(session: Session, duts: Sequence[DutModel]) -> list[DutModel]:
        """Resolve supported DUTs to records in the current session."""
        resolved: list[DutModel] = []
        for dut in duts:
            stored = session.get(DutModel, dut.id)
            if stored is None:
                raise ValueError(f"Supported DUT not found: {dut.id}")
            resolved.append(stored)
        return resolved

    @staticmethod
    def _resolve_boards(
        session: Session,
        boards: Sequence[BoardModel],
    ) -> list[BoardModel]:
        """Resolve supported boards to records in the current session."""
        resolved: list[BoardModel] = []
        for board in boards:
            stored = session.get(BoardModel, board.id)
            if stored is None:
                raise ValueError(f"Supported board not found: {board.id}")
            resolved.append(stored)
        return resolved

    def add(self, data: ProjectModel) -> ProjectModel:
        """Persist a project and its supported resource relationships."""
        self.logger.debug(self.add.__name__)
        validated = ProjectModel.model_validate(data.model_dump())
        with Session(self.engine, expire_on_commit=False) as session:
            validated.supported_duts = self._resolve_duts(
                session,
                data.supported_duts,
            )
            validated.supported_boards = self._resolve_boards(
                session,
                data.supported_boards,
            )
            for dut in validated.supported_duts:
                validated.specifications_for(dut)
            session.add(validated)
            session.commit()
        return validated

    def upsert_many(
        self,
        records: Sequence[ProjectModel],
    ) -> tuple[int, int]:
        """Insert or update projects and their supported relationships by ID."""
        identifiers = [record.id for record in records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("The record list contains duplicate IDs")
        internal_names = [record.internal_name for record in records]
        if len(internal_names) != len(set(internal_names)):
            raise ValueError("The record list contains duplicate internal names")

        created = 0
        updated = 0
        with Session(self.engine) as session:
            for incoming in records:
                stored = session.get(ProjectModel, incoming.id)
                if stored is None:
                    stored = ProjectModel.model_validate(incoming.model_dump())
                    created += 1
                else:
                    stored.internal_name = incoming.internal_name
                    stored.datasheet_name = incoming.datasheet_name
                    stored.specifications = incoming.specifications
                    updated += 1
                supported_duts = self._resolve_duts(
                    session,
                    incoming.supported_duts,
                )
                for dut in supported_duts:
                    incoming.specifications_for(dut)
                stored.supported_duts = supported_duts
                stored.supported_boards = self._resolve_boards(
                    session,
                    incoming.supported_boards,
                )
                session.add(stored)
            session.commit()
        return created, updated
