"""Base representation for devices under test."""

from elims_instruments.database import DutModel
from elims_instruments.utils.logger import get_logger

logger = get_logger(__name__)


class Dut:
    """Base DUT object backed by a validated IC database model.

    Specialized DUT classes can add register maps, limits, or characterization
    metadata. Communication remains the responsibility of the board fixture.
    """

    def __init__(self, dut: DutModel) -> None:
        """Initialize the DUT from its persisted identity."""
        self.dut = dut
        logger.debug(
            "Initialized {} for DUT asset {}",
            type(self).__name__,
            dut.asset_tag,
        )
