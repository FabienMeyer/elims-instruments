"""Exceptions raised while resolving board drivers."""

from collections.abc import Collection


class BoardAssetNotFoundError(LookupError):
    """Indicate that a configured board asset tag is absent from the database."""

    def __init__(self, asset_tag: str) -> None:
        """Create an error for the unresolved asset tag."""
        self.asset_tag = asset_tag
        super().__init__(f"Board asset tag not found: {asset_tag}")


class UnsupportedBoardTypeError(ValueError):
    """Indicate that no driver is registered for a board type."""

    def __init__(
        self,
        board_type: str,
        available_types: Collection[str],
    ) -> None:
        """Create an error naming the unsupported and available types."""
        self.board_type = board_type
        available = ", ".join(sorted(available_types))
        super().__init__(
            f"Unsupported board type: {board_type!r}. "
            f"Available types: {available or 'none'}"
        )
