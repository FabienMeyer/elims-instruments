"""Keysight 34400 series multimeters base driver."""

from elims_instruments.instruments.multimeter.abstract import Multimeter


class Keysight34400(Multimeter):
    """Keysight 34400 series multimeters."""

    def connect(self) -> None:
        """Open connection to instrument."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Close connection to instrument."""
        raise NotImplementedError

    def get_id(self) -> str:
        """Get instrument identification

        Returns:
            Identification string
        """
        raise NotImplementedError
