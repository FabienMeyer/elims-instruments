"""Base driver for laboratory boards."""

from elims_instruments.database import BoardModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.GREEN)


class Board:
    """Base characterization-board driver backed by a database model.

    Concrete board drivers can inherit from this class and add their own
    communication and measurement methods. The board is the fixture or
    interface used to characterize an IC; it does not represent the DUT.
    """

    def __init__(self, board: BoardModel) -> None:
        """Initialize the driver for *board*."""
        self.board = board
        logger.debug(
            "Initialized {} driver for board asset {}",
            type(self).__name__,
            board.asset_tag,
        )

    def report_header(self) -> list[str]:
        """Return the CSV headers for the instrument information."""
        return ["asset_tag"]

    def report_value(self) -> list[str]:
        """Return the board information as CSV values."""
        return [self.board.asset_tag]