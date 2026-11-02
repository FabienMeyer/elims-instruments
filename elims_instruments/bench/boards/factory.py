"""Create and collect board drivers independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import ClassVar

from elims_instruments.bench.factory import (
    NamedCollection,
    register_string_builder,
    resolve_assignments,
)
from elims_instruments.database import BoardCrud, BoardModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .abstract import Board
from .error import BoardAssetNotFoundError, UnsupportedBoardTypeError

BoardBuilder = Callable[[BoardModel], Board]
logger = get_logger(__name__, LoggerHelper.Color.GREEN)


class BoardFactory:
    """Create board drivers from explicit type registrations.

    The ``generic`` type maps to the base :class:`Board`. Every other board
    type must be registered before it can be created.
    """

    _registry: ClassVar[dict[str, BoardBuilder]] = {"generic": Board}

    @classmethod
    def register(
        cls,
        board_type: str,
        builder: BoardBuilder,
        *,
        replace: bool = False,
    ) -> None:
        """Register a driver builder for a normalized board type."""
        register_string_builder(
            cls._registry,
            board_type,
            builder,
            key_error="Board type must be a non-empty string",
            builder_error="Board builder must be callable",
            duplicate_error=lambda key: (
                f"Board type already has a registered builder: {key!r}"
            ),
            replace=replace,
        )
        logger.debug(
            "Registered board builder {} for type {}",
            getattr(builder, "__name__", type(builder).__name__),
            board_type,
        )

    @classmethod
    def create(cls, board: BoardModel) -> Board:
        """Create the driver registered for a board model's type.

        Raises:
            UnsupportedBoardTypeError: If the board type is not registered.
            TypeError: If the registered builder does not return a board driver.

        """
        board_type = board.type.strip().casefold()
        try:
            builder = cls._registry[board_type]
        except KeyError as error:
            raise UnsupportedBoardTypeError(board.type, cls._registry) from error
        logger.debug(
            "Creating {} driver for board asset {}",
            getattr(builder, "__name__", type(builder).__name__),
            board.asset_tag,
        )
        driver = builder(board)
        if not isinstance(driver, Board):
            raise TypeError("Board builders must return a Board driver")
        return driver


class BoardCollection(NamedCollection[Board]):
    """Read-only board collection supporting mapping and attribute access."""


def create_boards(
    assignments: Mapping[str, str],
    configuration: Path = Path("bench.toml"),
) -> BoardCollection:
    """Resolve assigned asset tags into a named collection of board drivers.

    Args:
        assignments: Mapping of bench role names to board asset tags.
        configuration: TOML file containing the database configuration.

    Returns:
        An immutable collection of constructed board drivers.

    Raises:
        BoardAssetNotFoundError: If an assigned asset tag does not exist.
        UnsupportedBoardTypeError: If a board type has no registered driver.

    """
    logger.info(
        "Creating {} board drivers using bench configuration {}",
        len(assignments),
        configuration,
    )
    if not assignments:
        logger.info("Created 0 board drivers")
        return BoardCollection({})

    with BoardCrud(logger, configuration, create_tables=False) as repository:
        boards = resolve_assignments(
            assignments,
            repository,
            lookup_field="asset_tag",
            builder=BoardFactory.create,
            not_found=BoardAssetNotFoundError,
        )
    collection = BoardCollection(boards)
    logger.info("Created {} board drivers", len(collection))
    return collection
