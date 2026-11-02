"""Narrow structural interfaces shared by characterization services."""

from typing import Protocol


class Reportable(Protocol):
    """Provide one stable block of report columns and values."""

    def report_header(self) -> list[str]:
        """Return report column names in stable order."""
        ...

    def report_value(self) -> list[str]:
        """Return report values in the same order as the headers."""
        ...
