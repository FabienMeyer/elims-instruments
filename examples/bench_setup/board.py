"""Load example boards from the database and create their runtime drivers."""

from __future__ import annotations

import logging

from elims_instruments.bench import Board, BoardFactory
from elims_instruments.database import BoardCrud
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.constants import (
    BENCH_CONFIGURATION,
    BOARD_DRIVER_NAME,
)

logger = get_logger(__name__)


class ExampleBoard(Board):
    """Runtime behavior backed by a board record from the database."""

    def get_id(self) -> str:
        """Return the persistent database identifier."""
        return self.board.id

    def reset(self) -> None:
        """Reset the board to its known initial state.

        Replace this placeholder with the board-specific reset sequence when
        the example is connected to hardware.
        """


# BoardModel records identify their runtime driver by ``type``.
BoardFactory.register(BOARD_DRIVER_NAME, ExampleBoard)


def main() -> None:
    """Load board records, create their drivers, and display them."""
    LOGGER_HELPER.configure()
    repository = BoardCrud(logging.getLogger(__name__), BENCH_CONFIGURATION)
    try:
        boards = repository.fetchall()
    finally:
        repository.engine.dispose()

    for board in boards:
        driver = BoardFactory.create(board)
        logger.info(
            f"{driver.get_id()}: {type(driver).__name__} for "
            f"{driver.board.maker} {driver.board.model} "
            f"(asset tag: {driver.board.asset_tag}, "
            f"type: {driver.board.type})"
        )


if __name__ == "__main__":
    main()
