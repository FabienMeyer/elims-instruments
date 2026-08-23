"""Create and collect board drivers independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from elims_instruments.database import BoardCrud, BoardModel
from elims_instruments.utils.logger import get_logger

from .abstract import Board
from .error import BoardAssetNotFoundError

BoardBuilder = Callable[[BoardModel], Board]
logger = get_logger(__name__)


class BoardFactory:
    """Create base or specialized board drivers from database models."""

    _registry: ClassVar[dict[str, BoardBuilder]] = {}

    @classmethod
    def register(cls, board_type: str, builder: BoardBuilder) -> None:
        """Register a specialized driver builder for a board type."""
        if not isinstance(board_type, str) or not board_type.strip():
            raise ValueError("Board type must be a non-empty string")
        if not callable(builder):
            raise TypeError("Board builder must be callable")
        normalized_type = board_type.strip().casefold()
        cls._registry[normalized_type] = builder
        logger.debug(
            "Registered board builder {} for type {}",
            getattr(builder, "__name__", type(builder).__name__),
            board_type,
        )

    @classmethod
    def create(cls, board: BoardModel) -> Board:
        """Create the registered driver, falling back to the base driver."""
        builder = cls._registry.get(board.type.strip().casefold(), Board)
        logger.debug(
            "Creating {} driver for board asset {}",
            getattr(builder, "__name__", type(builder).__name__),
            board.asset_tag,
        )
        driver = builder(board)
        if not isinstance(driver, Board):
            raise TypeError("Board builders must return a Board driver")
        return driver


class BoardCollection(Mapping[str, Board]):
    """Read-only board collection supporting mapping and attribute access."""

    def __init__(self, boards: Mapping[str, Board]) -> None:
        """Store named board drivers in an immutable mapping."""
        self._drivers = MappingProxyType(dict(boards))

    def __getitem__(self, name: str) -> Board:
        """Return the board assigned to *name*."""
        return self._drivers[name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over configured board names."""
        return iter(self._drivers)

    def __len__(self) -> int:
        """Return the number of configured boards."""
        return len(self._drivers)

    def __getattr__(self, name: str) -> Board:
        """Allow attribute access such as ``boards.characterization_board``."""
        try:
            return self._drivers[name]
        except KeyError as error:
            raise AttributeError(name) from error


def create_boards(
    assignments: Mapping[str, str],
    configuration: Path = Path("bench.toml"),
) -> BoardCollection:
    """Resolve asset tags and create a named collection of board drivers."""
    logger.info(
        "Creating {} board drivers using bench configuration {}",
        len(assignments),
        configuration,
    )
    if not assignments:
        logger.info("Created 0 board drivers")
        return BoardCollection({})

    repository = BoardCrud(logger, configuration)
    boards: dict[str, Board] = {}
    try:
        for name, asset_tag in assignments.items():
            logger.debug("Resolving board {} from asset {}", name, asset_tag)
            board = repository.fetch("asset_tag", asset_tag)
            if board is None:
                raise BoardAssetNotFoundError(asset_tag)
            boards[name] = BoardFactory.create(board)
    finally:
        repository.engine.dispose()
    collection = BoardCollection(boards)
    logger.info("Created {} board drivers", len(collection))
    return collection
