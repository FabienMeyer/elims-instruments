"""Base representation for devices under test."""

from abc import ABC, abstractmethod

from elims_instruments.database import DutModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.YELLOW)


class Dut(ABC):
    """Base DUT object backed by a validated database model."""

    def __init__(self, dut: DutModel) -> None:
        """Initialize the DUT from its persisted identity."""
        self.dut = dut
        logger.debug(
            "Initialized {} for DUT asset {}",
            type(self).__name__,
            dut.asset_tag,
        )

    @abstractmethod
    def get_id(self) -> str:
        """Return the DUT identification."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the DUT to a known state."""
        logger.debug("Resetting DUT asset {}", self.dut.asset_tag)
