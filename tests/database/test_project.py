"""Tests for the project SQLModel and CRUD repository."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    ProjectCrud,
    ProjectModel,
    USBConnection,
    parse_project_list,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    """Create an isolated SQLite project configuration."""
    path = tmp_path / "bench.toml"
    database = (tmp_path / "projects.db").as_posix()
    path.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def resources(configuration: Path) -> tuple[DutModel, DutModel, BoardModel]:
    """Persist DUT and board models that projects can reference."""
    logger = logging.getLogger(__name__)
    dut_repository = DutCrud(logger, configuration)
    board_repository = BoardCrud(logger, configuration)
    try:
        first_dut = dut_repository.add(
            DutModel(
                id="dut-1",
                asset_tag="DUT-001",
                project="demo-project",
                corner="TT",
                revision="A",
            )
        )
        second_dut = dut_repository.add(
            DutModel(
                id="dut-2",
                asset_tag="DUT-002",
                project="demo-project",
                corner="FF",
                revision="A",
            )
        )
        board = board_repository.add(
            BoardModel(
                id="board-1",
                asset_tag="BOARD-001",
                type="characterization",
                maker="ELIMS",
                model="Demo Board",
                connection=USBConnection(vendor_id=1, product_id=2),
            )
        )
    finally:
        dut_repository.engine.dispose()
        board_repository.engine.dispose()
    return first_dut, second_dut, board


@pytest.fixture
def repository(configuration: Path) -> ProjectCrud:
    """Create a project repository."""
    return ProjectCrud(logging.getLogger(__name__), configuration)


def test_project_relationships_round_trip(
    repository: ProjectCrud,
    resources: tuple[DutModel, DutModel, BoardModel],
) -> None:
    """Projects expose supported resources as their database model types."""
    first_dut, second_dut, board = resources
    project = ProjectModel(id="project-1", name="demo-project")
    project.supported_duts = [first_dut, second_dut]
    project.supported_boards = [board]

    repository.add(project)
    stored = repository.fetch("name", "demo-project")

    assert stored is not None
    assert [dut.id for dut in stored.supported_duts] == ["dut-1", "dut-2"]
    assert [item.id for item in stored.supported_boards] == ["board-1"]
    assert all(isinstance(dut, DutModel) for dut in stored.supported_duts)
    assert isinstance(stored.supported_boards[0], BoardModel)


def test_project_validation_normalizes_identity() -> None:
    """Project IDs and names are trimmed and cannot be empty."""
    project = ProjectModel.model_validate(
        {"id": " project-1 ", "name": " demo-project "}
    )

    assert project.id == "project-1"
    assert project.name == "demo-project"

    with pytest.raises(ValidationError):
        ProjectModel.model_validate({"id": "project-2", "name": " "})


def test_parse_and_upsert_project_relationships(
    repository: ProjectCrud,
    resources: tuple[DutModel, DutModel, BoardModel],
) -> None:
    """Nested resource models validate and can be bulk-upserted."""
    first_dut, second_dut, board = resources
    projects = parse_project_list(
        [
            {
                "id": "project-1",
                "name": "demo-project",
                "supported_duts": [first_dut.model_dump(mode="json")],
                "supported_boards": [board.model_dump(mode="json")],
            }
        ]
    )

    assert repository.upsert_many(projects) == (1, 0)
    projects[0].supported_duts = [second_dut]
    assert repository.upsert_many(projects) == (0, 1)
    stored = repository.fetch("id", "project-1")
    assert stored is not None
    assert [dut.id for dut in stored.supported_duts] == ["dut-2"]


def test_project_rejects_unstored_supported_resource(
    repository: ProjectCrud,
) -> None:
    """Relationships must point to existing resource records."""
    project = ProjectModel(id="project-1", name="demo-project")
    project.supported_duts = [
        DutModel(
            id="missing-dut",
            asset_tag="DUT-999",
            project="demo-project",
            corner="TT",
            revision="A",
        )
    ]

    with pytest.raises(ValueError, match="Supported DUT not found"):
        repository.add(project)
