"""Timestamp module."""

import dataclasses
from datetime import datetime


@dataclasses.dataclass(frozen=True, slots=True)
class Timestamp:
    """Timestamp."""

    value: datetime

    @classmethod
    def now(cls) -> "Timestamp":
        """Return the current timestamp.

        Returns:
            Current timestamp.
        """
        return cls(datetime.now().astimezone())

    def iso(self) -> str:
        """Return ISO 8601 representation.

        Returns:
            ISO 8601 representation of the timestamp.
        """
        return self.value.isoformat(timespec="microseconds")

    def file(self) -> str:
        """Return file representation.

        Returns:
            File representation of the timestamp.
        """
        return self.value.strftime("%Y_%m_%d_%H_%M_%S")
