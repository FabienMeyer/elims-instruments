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
        return f"{self.dut.project}_{self.dut.serial_number}"

    def report_header(self) -> list[str]:
        """Return the CSV headers for the persisted DUT information."""
        return ["dut_id", "serial_number", "corner", "revision"]

    def report_value(self) -> list[str]:
        """Return the persisted DUT information as CSV values."""
        return [
            self.dut.asset_tag,
            str(self.dut.serial_number),
            str(self.dut.corner),
            f"{self.dut.die_revision}{self.dut.metal_revision or ''}{self.dut.package_revision}",
        ]

    @abstractmethod
    def reset(self) -> None:
        """Reset the DUT to a known state."""
        logger.debug("Resetting DUT asset {}", self.dut.asset_tag)
