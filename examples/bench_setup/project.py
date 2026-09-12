"""Load example projects from the database and create their runtime drivers."""

from __future__ import annotations

import logging

from elims_instruments.bench import Project, ProjectFactory
from elims_instruments.database import ProjectCrud
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.constants import (
    BENCH_CONFIGURATION,
    PROJECT_DRIVER_NAME,
)

logger = get_logger(__name__)


class ExampleProject(Project):
    """Runtime behavior backed by a project record from the database."""

    def get_id(self) -> str:
        """Return the persistent project identifier."""
        return self.project.id

    def describe(self) -> str:
        """Return a human-readable description of the persisted project."""
        return (
            f"{self.project.datasheet_name} "
            f"(internal name: {self.project.internal_name})"
        )


# ProjectModel records identify their runtime driver by ``internal_name``.
ProjectFactory.register(PROJECT_DRIVER_NAME, ExampleProject)


def main() -> None:
    """Load project records, create their drivers, and display them."""
    LOGGER_HELPER.configure()
    repository = ProjectCrud(logging.getLogger(__name__), BENCH_CONFIGURATION)
    try:
        projects = repository.fetchall()
    finally:
        repository.engine.dispose()

    for project in projects:
        driver = ProjectFactory.create(project)
        logger.info(
            f"{driver.get_id()}: {type(driver).__name__} for "
            f"{driver.describe()}"
        )


if __name__ == "__main__":
    main()
