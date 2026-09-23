"""Load example projects from the database and create their runtime drivers."""

from __future__ import annotations

import logging

from elims_instruments.bench import Project, ProjectFactory
from elims_instruments.database import ProjectCrud, ProjectModel
from examples.bench_setup.dut import get_duts
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

def get_projects() -> list[ProjectModel]:
    repository = ProjectCrud(logging.getLogger(__name__), BENCH_CONFIGURATION)
    try:
        projects = repository.fetchall()
    finally:
        repository.engine.dispose()
    return projects

def main() -> None:
    """Load project records, create their drivers, and display them."""
    LOGGER_HELPER.configure()

    for dut in get_duts():
        for project in get_projects():
            driver = ProjectFactory.create(project)
            logger.info(driver.voltage_specifications_for(dut))
            logger.info(driver.temperature_specifications_for(dut))
        


if __name__ == "__main__":
    main()
