"""Exceptions raised while resolving and creating instrument drivers."""

from collections.abc import Collection

from elims_instruments.database import InstrumentType


class InstrumentAssetNotFoundError(LookupError):
    """Indicate that a configured asset tag is absent from the database."""

    def __init__(self, asset_tag: str) -> None:
        """Create an error for the unresolved asset tag."""
        self.asset_tag = asset_tag
        super().__init__(f"Instrument asset tag not found: {asset_tag}")


class UnsupportedInstrumentTypeError(ValueError):
    """Indicate that no driver factory exists for an instrument type."""

    def __init__(
        self,
        instrument_type: InstrumentType,
        available_types: Collection[InstrumentType],
    ) -> None:
        """Create an error containing the requested and registered types."""
        self.instrument_type = instrument_type
        self.available_types = tuple(available_types)
        available = ", ".join(item.value for item in self.available_types)
        super().__init__(
            f"Unsupported instrument type: {instrument_type}. "
            f"Available types: {available or 'None registered'}"
        )
