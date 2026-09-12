"""Base abstract class for all instruments."""

from abc import ABC, abstractmethod

from elims_instruments.database.instrument import InstrumentModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.CYAN)


class Instrument(ABC):
    """Abstract base class for all instruments."""

    def __init__(self, instrument: InstrumentModel) -> None:
        """Initialize instrument.

        Args:
            instrument: Instrument model from database)
        """
        self.instrument = instrument
        logger.debug(
            "Initialized {} driver for asset {}",
            type(self).__name__,
            instrument.asset_tag,
        )

    def report_header(self) -> list[str]:
        """Return the CSV headers for the instrument information."""
        return ["asset_tag", "calibration_date"]

    def report_value(self) -> list[str]:
        """Return the instrument information as CSV values."""
        return [
            self.instrument.asset_tag,
            ""
            if self.instrument.calibration_date is None
            else self.instrument.calibration_date.isoformat(),
        ]

    @abstractmethod
    def connect(self) -> None:
        """Open connection to instrument."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to instrument."""
        pass

    @abstractmethod
    def get_id(self) -> str:
        """Get instrument identification

        Returns:
            Identification string
        """
        pass
