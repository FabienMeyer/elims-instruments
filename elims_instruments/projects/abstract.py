"""Base representation for characterization projects."""

from abc import ABC, abstractmethod

from elims_instruments.database import ProjectModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.YELLOW)


class Project(ABC):
    """Base project object backed by a validated database model."""

    def __init__(self, project: ProjectModel) -> None:
        """Initialize the project from its persisted definition."""
        self.project = project
        logger.debug(
            "Initialized {} for project {}",
            type(self).__name__,
            project.name,
        )

    @abstractmethod
    def get_id(self) -> str:
        """Return the project identification."""
        pass
