"""Keysight 53200 series counters base driver."""

from elims_instruments.intruments.counter.abstract import Counter


class Keysight53200(Counter):
    """Keysight 53200 series counters."""

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
