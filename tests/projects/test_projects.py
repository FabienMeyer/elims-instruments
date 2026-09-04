"""Tests for project creation and collection access."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from elims_instruments.database import ProjectCrud, ProjectModel
from elims_instruments.projects import (
    Project,
    ProjectFactory,
    ProjectNotFoundError,
    create_projects,
)


class CharacterizationProject(Project):
    """Concrete project used by factory tests."""

    def get_id(self) -> str:
        """Return the database project ID."""
        return self.project.id


@pytest.fixture
def bench_configuration(tmp_path: Path) -> Path:
    """Create a database containing one project."""
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "projects.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    repository = ProjectCrud(logging.getLogger(__name__), configuration)
    repository.add(
        ProjectModel(
            id="project-1",
            name="demo-project",
        )
    )
    return configuration


def test_project_wraps_project_model() -> None:
    """A project retains its validated database definition."""
    model = ProjectModel(
        id="project-1",
        name="demo-project",
    )

    project = CharacterizationProject(model)

    assert project.project is model
    assert project.get_id() == "project-1"


def test_create_projects_uses_registered_builder(bench_configuration: Path) -> None:
    """A registered builder creates a project resolved from the database."""
    ProjectFactory.register("demo-project", CharacterizationProject)
    projects = create_projects(
        {"characterization": "demo-project"},
        bench_configuration,
    )

    assert type(projects.characterization) is CharacterizationProject
    assert projects["characterization"].project.name == "demo-project"
    assert list(projects) == ["characterization"]


def test_factory_normalizes_registered_name() -> None:
    """A registered project name can replace the base object."""

    model = ProjectModel(id="project-2", name="registered-project")
    ProjectFactory.register(" Registered-Project ", CharacterizationProject)

    assert isinstance(ProjectFactory.create(model), CharacterizationProject)


def test_factory_rejects_unregistered_project() -> None:
    """A project without a concrete builder is rejected."""
    model = ProjectModel(id="project-4", name="unregistered-project")

    with pytest.raises(ValueError, match="Unknown project"):
        ProjectFactory.create(model)


def test_factory_rejects_invalid_registration() -> None:
    """Factory registration fails clearly for invalid inputs."""
    with pytest.raises(ValueError, match="non-empty"):
        ProjectFactory.register(" ", CharacterizationProject)

    with pytest.raises(TypeError, match="callable"):
        ProjectFactory.register("demo-project", None)  # type: ignore[arg-type]


def test_factory_rejects_invalid_builder_result() -> None:
    """A project builder must return a project object."""
    model = ProjectModel(id="project-3", name="invalid-builder-project")
    ProjectFactory.register(
        model.name,
        lambda project: object(),  # type: ignore[arg-type,return-value]
    )

    with pytest.raises(TypeError, match="Project object"):
        ProjectFactory.create(model)


def test_create_projects_rejects_missing_name(
    bench_configuration: Path,
) -> None:
    """A missing project name raises a project-specific error."""
    with pytest.raises(ProjectNotFoundError, match="missing-project"):
        create_projects({"missing": "missing-project"}, bench_configuration)


def test_empty_assignments_need_no_database_configuration() -> None:
    """An empty project collection does not open a database."""
    projects = create_projects({}, Path("missing-bench.toml"))

    assert len(projects) == 0
