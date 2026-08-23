"""Validated and persistent characterization-project definitions."""

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

from pydantic import StringConstraints, TypeAdapter
from sqlmodel import Field, Relationship, Session, SQLModel

from .board import BoardModel
from .crud import Crud, DebugLogger
from .dut import DutModel

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
    name: NonEmptyString = Field(unique=True, index=True)
    supported_duts: list[DutModel] = Relationship(
        link_model=ProjectDutLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    supported_boards: list[BoardModel] = Relationship(
        link_model=ProjectBoardLink,
        sa_relationship_kwargs={"lazy": "selectin"},
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
        names = [record.name for record in records]
        if len(names) != len(set(names)):
            raise ValueError("The record list contains duplicate project names")

        created = 0
        updated = 0
        with Session(self.engine) as session:
            for incoming in records:
                stored = session.get(ProjectModel, incoming.id)
                if stored is None:
                    stored = ProjectModel.model_validate(incoming.model_dump())
                    created += 1
                else:
                    stored.name = incoming.name
                    updated += 1
                stored.supported_duts = self._resolve_duts(
                    session,
                    incoming.supported_duts,
                )
                stored.supported_boards = self._resolve_boards(
                    session,
                    incoming.supported_boards,
                )
                session.add(stored)
            session.commit()
        return created, updated
