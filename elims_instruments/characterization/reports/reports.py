"""CSV reports produced by characterization tests."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from elims_instruments.bench.duts import Dut
    from elims_instruments.utils.timestamp import Timestamp


class CsvReport:
    """A CSV report associated with one test and one DUT."""

    def __init__(
        self,
        path: Path,
        dut: Dut,
        *,
        timestamp: Timestamp | None = None,
    ) -> None:
        """Initialize a report with an optional timestamped filename."""
        self.path = (
            path.with_name(f"{path.stem}_{timestamp.file()}{path.suffix}")
            if timestamp is not None
            else path
        )
        self.dut = dut
        self._header = list(dut.report_header())
        self._value = list(dut.report_value())
        if timestamp is not None:
            self._header.append("report_timestamp_iso")
            self._value.append(timestamp.iso())
        self._base_header = tuple(self._header)
        self._base_value = tuple(self._value)
        self._rows_written = 0
        self._write_header()

    def header(self) -> list[str]:
        """Return the complete CSV header for the assembled report."""
        return list(self._header)

    def value(self) -> list[str]:
        """Return the complete CSV value row for the assembled report."""
        return list(self._value)

    def write_header(self, headers: Sequence[str]) -> Path:
        """Add test columns and write the complete header before testing."""
        if self._rows_written:
            raise RuntimeError("Report header cannot change after data is saved")
        duplicate = set(self._header).intersection(headers)
        if duplicate or len(headers) != len(set(headers)):
            raise ValueError("Report headers must be unique")
        self._header.extend(headers)
        self._value.extend("" for _ in headers)
        return self._write_header()

    def save_information(self, values: Sequence[str]) -> Path:
        """Append values for one completed sweep to the report."""
        expected = len(self._header) - len(self._base_header)
        if len(values) != expected:
            raise ValueError(
                f"Report requires {expected} test values, received {len(values)}"
            )
        self._value = [*self._base_value, *values]
        with self.path.open("a", encoding="utf-8", newline="") as csv_file:
            csv.writer(csv_file).writerow(self._value)
        self._rows_written += 1
        return self.path

    def _write_header(self) -> Path:
        """Create the report and write its current header without a data row."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as csv_file:
            csv.writer(csv_file).writerow(self._header)
        return self.path
