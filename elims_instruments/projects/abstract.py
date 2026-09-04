"""Base representation for characterization projects."""

from abc import ABC, abstractmethod

from elims_instruments.database import (
    DutModel,
    ProjectModel,
    ProjectRevisionSpecifications,
)
from elims_instruments.temperatures import TemperatureSpecification
from elims_instruments.utils.logger import LoggerHelper, get_logger
from elims_instruments.voltages import VoltageSpecification

logger = get_logger(__name__, LoggerHelper.Color.YELLOW)


class Project(ABC):
    """Base project object backed by a validated database model."""

    def __init__(self, project: ProjectModel) -> None:
        """Initialize the project from its persisted definition."""
        self.project = project
        logger.debug(
            "Initialized {} for project {}",
            type(self).__name__,
            project.internal_name,
        )

    @abstractmethod
    def get_id(self) -> str:
        """Return the project identification."""
        pass

    def specifications_for(self, dut: DutModel) -> ProjectRevisionSpecifications:
        """Return the revision-dependent electrical and thermal profile."""
        return self.project.specifications_for(dut)

    def voltage_specifications_for(
        self,
        dut: DutModel,
    ) -> tuple[VoltageSpecification, ...]:
        """Return voltage specifications for the exact DUT revision."""
        return self.specifications_for(dut).voltage_specifications

    def temperature_specifications_for(
        self,
        dut: DutModel,
    ) -> tuple[TemperatureSpecification, ...]:
        """Return temperature specifications for the exact DUT revision."""
        return self.specifications_for(dut).temperature_specifications
