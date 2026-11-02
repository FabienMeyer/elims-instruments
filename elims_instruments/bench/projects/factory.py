"""Create and collect project objects independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import ClassVar

from elims_instruments.bench.factory import (
    NamedCollection,
    register_string_builder,
    resolve_assignments,
)
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
    def register(
        cls,
        name: str,
        builder: ProjectBuilder,
        *,
        replace: bool = False,
    ) -> None:
        """Register a specialized builder for a project name."""
        register_string_builder(
            cls._registry,
            name,
            builder,
            key_error="Project name must be a non-empty string",
            builder_error="Project builder must be callable",
            duplicate_error=lambda key: (
                f"Project already has a registered builder: {key!r}"
            ),
            replace=replace,
        )
        logger.debug(
            "Registered project builder {} for project {}",
            getattr(builder, "__name__", type(builder).__name__),
            name,
        )

    @classmethod
    def create(cls, project: ProjectModel) -> Project:
        """Create the concrete project registered for a database model."""
        project_key = project.internal_name.strip().casefold()
        if project_key not in cls._registry:
            available = ", ".join(cls._registry)
            raise ValueError(
                f"Unknown project: '{project.internal_name}'. "
                f"Available projects: {available or 'None registered yet'}"
            )
        builder = cls._registry[project_key]
        logger.debug(
            "Creating {} for project {}",
            getattr(builder, "__name__", type(builder).__name__),
            project.internal_name,
        )
        instance = builder(project)
        if not isinstance(instance, Project):
            raise TypeError("Project builders must return a Project object")
        return instance


class ProjectCollection(NamedCollection[Project]):
    """Read-only project collection supporting mapping and attribute access."""


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

    with ProjectCrud(logger, configuration, create_tables=False) as repository:
        projects = resolve_assignments(
            assignments,
            repository,
            lookup_field="internal_name",
            builder=ProjectFactory.create,
            not_found=ProjectNotFoundError,
        )
    collection = ProjectCollection(projects)
    logger.info("Created {} projects", len(collection))
    return collection
