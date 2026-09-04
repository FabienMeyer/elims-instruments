"""Create and collect project objects independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from elims_instruments.database import ProjectCrud, ProjectModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .abstract import Project
from .error import ProjectNotFoundError

ProjectBuilder = Callable[[ProjectModel], Project]
logger = get_logger(__name__, LoggerHelper.Color.YELLOW)


class ProjectFactory:
    """Create registered project objects from database models."""

    _registry: ClassVar[dict[str, ProjectBuilder]] = {}

    @classmethod
    def register(cls, name: str, builder: ProjectBuilder) -> None:
        """Register a specialized builder for a project name."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Project name must be a non-empty string")
        if not callable(builder):
            raise TypeError("Project builder must be callable")
        normalized_name = name.strip().casefold()
        cls._registry[normalized_name] = builder
        logger.debug(
            "Registered project builder {} for project {}",
            getattr(builder, "__name__", type(builder).__name__),
            name,
        )

    @classmethod
    def create(cls, project: ProjectModel) -> Project:
        """Create the concrete project registered for a database model."""
        project_key = project.name.strip().casefold()
        if project_key not in cls._registry:
            available = ", ".join(cls._registry)
            raise ValueError(
                f"Unknown project: '{project.name}'. "
                f"Available projects: {available or 'None registered yet'}"
            )
        builder = cls._registry[project_key]
        logger.debug(
            "Creating {} for project {}",
            getattr(builder, "__name__", type(builder).__name__),
            project.name,
        )
        instance = builder(project)
        if not isinstance(instance, Project):
            raise TypeError("Project builders must return a Project object")
        return instance


class ProjectCollection(Mapping[str, Project]):
    """Read-only project collection supporting mapping and attribute access."""

    def __init__(self, projects: Mapping[str, Project]) -> None:
        """Store named project objects in an immutable mapping."""
        self._projects = MappingProxyType(dict(projects))

    def __getitem__(self, name: str) -> Project:
        """Return the project assigned to *name*."""
        return self._projects[name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over configured project names."""
        return iter(self._projects)

    def __len__(self) -> int:
        """Return the number of configured projects."""
        return len(self._projects)

    def __getattr__(self, name: str) -> Project:
        """Allow attribute access such as ``projects.characterization``."""
        try:
            return self._projects[name]
        except KeyError as error:
            raise AttributeError(name) from error


def create_projects(
    assignments: Mapping[str, str],
    configuration: Path = Path("bench.toml"),
) -> ProjectCollection:
    """Resolve database names and create a named collection of projects."""
    logger.info(
        "Creating {} projects using bench configuration {}",
        len(assignments),
        configuration,
    )
    if not assignments:
        logger.info("Created 0 projects")
        return ProjectCollection({})

    repository = ProjectCrud(logger, configuration)
    projects: dict[str, Project] = {}
    try:
        for name, project_name in assignments.items():
            logger.debug("Resolving project {} from name {}", name, project_name)
            project = repository.fetch("name", project_name)
            if project is None:
                raise ProjectNotFoundError(project_name)
            projects[name] = ProjectFactory.create(project)
    finally:
        repository.engine.dispose()
    collection = ProjectCollection(projects)
    logger.info("Created {} projects", len(collection))
    return collection
