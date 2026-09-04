"""Tests for the project SQLModel and CRUD repository."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    ProjectCrud,
    ProjectModel,
    ProjectRevisionSpecifications,
    USBConnection,
    parse_project_list,
)
from elims_instruments.temperatures import TemperatureSpecification
from elims_instruments.utils import Limits
from elims_instruments.voltages import VoltageSpecification

if TYPE_CHECKING:
    from pathlib import Path


def revision_specifications(
    die_revision: str = "A",
    metal_revision: int | None = None,
    package_revision: str | None = None,
    *,
    voltage: float = 1.2,
    temperature: float = 25,
) -> list[ProjectRevisionSpecifications]:
    """Build one representative revision-dependent project profile."""
    return [
        ProjectRevisionSpecifications(
            die_revision=die_revision,
            metal_revision=metal_revision,
            package_revision=package_revision,
            voltage_specifications=(
                VoltageSpecification("VDD", Limits(typical=voltage)),
            ),
            temperature_specifications=(
                TemperatureSpecification("DUT", Limits(typical=temperature)),
            ),
        )
    ]


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
                die_revision="A",
            )
        )
        second_dut = dut_repository.add(
            DutModel(
                id="dut-2",
                asset_tag="DUT-002",
                project="demo-project",
                corner="FF",
                die_revision="A",
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
    project = ProjectModel(
        id="project-1",
        internal_name="demo-project",
        datasheet_name="Demo IC",
        specifications=revision_specifications(),
    )
    project.supported_duts = [first_dut, second_dut]
    project.supported_boards = [board]

    repository.add(project)
    stored = repository.fetch("internal_name", "demo-project")

    assert stored is not None
    assert [dut.id for dut in stored.supported_duts] == ["dut-1", "dut-2"]
    assert [item.id for item in stored.supported_boards] == ["board-1"]
    assert all(isinstance(dut, DutModel) for dut in stored.supported_duts)
    assert isinstance(stored.supported_boards[0], BoardModel)
    assert stored.specifications[0].voltage_specifications[0].name == "VDD"
    assert stored.specifications[0].temperature_specifications[0].name == "DUT"


def test_temperature_limits_are_stored_as_integer_deci_degrees(
    repository: ProjectCrud,
) -> None:
    """Database JSON uses integers while the public model exposes Celsius floats."""
    project = ProjectModel(
        id="project-1",
        internal_name="demo-project",
        datasheet_name="Demo IC",
        specifications=revision_specifications(temperature=100.1),
    )

    repository.add(project)

    with repository.engine.connect() as connection:
        raw_specifications = connection.execute(
            text("SELECT specifications FROM projects WHERE id = 'project-1'")
        ).scalar_one()
    stored_json = json.loads(raw_specifications)
    stored_temperature = stored_json[0]["temperature_specifications"][0][
        "temperature_limits"
    ]["typical"]
    assert stored_temperature == 1001
    assert type(stored_temperature) is int

    stored = repository.fetch("id", "project-1")
    assert stored is not None
    temperature = stored.specifications[0].temperature_specifications[0]
    assert temperature.temperature_limits.typical == 100.1
    assert type(temperature.temperature_limits.typical) is float


def test_project_validation_normalizes_identity() -> None:
    """Project IDs and names are trimmed and cannot be empty."""
    project = ProjectModel.model_validate(
        {
            "id": " project-1 ",
            "internal_name": " demo-project ",
            "datasheet_name": " Demo IC ",
            "specifications": revision_specifications(),
        }
    )

    assert project.id == "project-1"
    assert project.internal_name == "demo-project"
    assert project.datasheet_name == "Demo IC"

    with pytest.raises(ValidationError):
        ProjectModel.model_validate(
            {
                "id": "project-2",
                "internal_name": " ",
                "datasheet_name": "Demo IC",
                "specifications": revision_specifications(),
            }
        )


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
                "internal_name": "demo-project",
                "datasheet_name": "Demo IC",
                "specifications": [
                    specification.model_dump(mode="json")
                    for specification in revision_specifications()
                ],
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
    project = ProjectModel(
        id="project-1",
        internal_name="demo-project",
        datasheet_name="Demo IC",
        specifications=revision_specifications(),
    )
    project.supported_duts = [
        DutModel(
            id="missing-dut",
            asset_tag="DUT-999",
            project="demo-project",
            corner="TT",
            die_revision="A",
        )
    ]

    with pytest.raises(ValueError, match="Supported DUT not found"):
        repository.add(project)


def test_project_rejects_supported_dut_without_revision_profile(
    repository: ProjectCrud,
    resources: tuple[DutModel, DutModel, BoardModel],
) -> None:
    """Every supported DUT must resolve to an exact operating profile."""
    first_dut, _, _ = resources
    project = ProjectModel(
        id="project-1",
        internal_name="demo-project",
        datasheet_name="Demo IC",
        specifications=revision_specifications("B"),
    )
    project.supported_duts = [first_dut]

    with pytest.raises(LookupError, match="No project specifications"):
        repository.add(project)


def test_project_resolves_specs_for_exact_dut_revision() -> None:
    """Die, metal, and package revisions select different operating values."""
    project = ProjectModel.model_validate(
        {
            "id": "project-1",
            "internal_name": "demo-project",
            "datasheet_name": "Demo IC",
            "specifications": [
                *revision_specifications("A", 0, "R1", voltage=1.2),
                *revision_specifications("A", 1, "R1", voltage=1.1),
            ],
        }
    )
    dut = DutModel.model_validate(
        {
            "id": "dut-1",
            "asset_tag": "DUT-001",
            "project": "demo-project",
            "corner": "TT",
            "die_revision": "A",
            "metal_revision": 1,
            "package_revision": "R1",
        }
    )

    selected = project.specifications_for(dut)

    assert selected.voltage_specifications[0].voltage_limits.typical == 1.1
    assert selected.temperature_specifications[0].temperature_limits.typical == 25


def test_project_requires_unique_revision_profiles() -> None:
    """A project cannot omit profiles or define an ambiguous revision tuple."""
    with pytest.raises(ValidationError, match="At least one project revision"):
        ProjectModel.model_validate(
            {
                "id": "project-1",
                "internal_name": "demo-project",
                "datasheet_name": "Demo IC",
                "specifications": [],
            }
        )

    profile = revision_specifications()[0]
    with pytest.raises(ValidationError, match="Duplicate project revision"):
        ProjectModel.model_validate(
            {
                "id": "project-1",
                "internal_name": "demo-project",
                "datasheet_name": "Demo IC",
                "specifications": [profile, profile],
            }
        )


def test_project_rejects_incomplete_or_unmatched_specifications() -> None:
    """Profiles need both spec kinds and must exactly match a project DUT."""
    with pytest.raises(ValidationError, match="temperature specification"):
        ProjectRevisionSpecifications.model_validate(
            {
                "die_revision": "A",
                "voltage_specifications": [
                    VoltageSpecification("VDD", Limits(typical=1.2))
                ],
                "temperature_specifications": [],
            }
        )

    project = ProjectModel.model_validate(
        {
            "id": "project-1",
            "internal_name": "demo-project",
            "datasheet_name": "Demo IC",
            "specifications": revision_specifications("A", 0, "R1"),
        }
    )
    unmatched = DutModel.model_validate(
        {
            "id": "dut-1",
            "asset_tag": "DUT-001",
            "project": "demo-project",
            "corner": "TT",
            "die_revision": "A",
            "metal_revision": 1,
            "package_revision": "R1",
        }
    )
    with pytest.raises(LookupError, match="No project specifications"):
        project.specifications_for(unmatched)
