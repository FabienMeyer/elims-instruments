"""Base driver for laboratory boards."""

from elims_instruments.database import BoardModel
from elims_instruments.utils.logger import get_logger

logger = get_logger(__name__)


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
