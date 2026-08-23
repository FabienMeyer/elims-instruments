"""Exceptions raised while resolving DUTs."""


class DutAssetNotFoundError(LookupError):
    """Indicate that a configured DUT asset tag is absent from the database."""

    def __init__(self, asset_tag: str) -> None:
        """Create an error for the unresolved asset tag."""
        self.asset_tag = asset_tag
        super().__init__(f"DUT asset tag not found: {asset_tag}")
