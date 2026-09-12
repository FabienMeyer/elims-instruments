"""CSV reports produced by characterization tests."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, Sequence

    from elims_instruments.utils.files import FileHelper


@dataclass(frozen=True, slots=True)
class CsvSection:
    """One logical block of a CSV report, with its header and value provider."""

    header: Callable[[], list[str]]
    value: Callable[[], list[str]]


class WriteCsvReport:
    """A CSV report associated with one test and one configured bench."""

    def __init__(
        self,
        file: FileHelper,
        *,
        sections: Sequence[CsvSection],
    ) -> None:
        """Initialize a report from the logical CSV sections."""
        if len(sections) != 4:
            raise ValueError("WriteCsvReport requires exactly four CSV sections")

        self.sections = sections
        self.file = file
        self._header: list[str] | None = None
        self._rows_written = 0

    def header(self) -> list[str]:
        """Return the complete CSV header for the assembled report."""
        return [
            "test_id",
            "timestamp",
            *[item for section in self.sections for item in section.header()],
        ]

    def value(self, test_id: str, timestamp: str) -> list[str]:
        """Return the complete CSV value row for the assembled report."""
        return [
            test_id,
            timestamp,
            *[item for section in self.sections for item in section.value()],
        ]

    def write_header(self) -> None:
        """Add test columns and write the complete header before testing."""
        if self._rows_written:
            raise RuntimeError("Report header cannot change after data is saved")
        header = self.header()
        if len(header) != len(set(header)):
            raise ValueError("Report headers must be unique")
        self._write(header, mode="w")
        self._header = header

    def write_data(
        self,
        test_id: str,
        timestamp: str,
        values: Sequence[str],
    ) -> None:
        """Append values for one completed sweep to the report."""
        if self._header is None:
            raise RuntimeError("Report header must be written before data")
        row = [*self.value(test_id, timestamp), *values]
        if len(row) != len(self._header):
            raise ValueError("Report data does not match the header length")
        self._write(row, mode="a")
        self._rows_written += 1

    def _write(self, data: Sequence[str], *, mode: str) -> Path:
        """Write one CSV row using the requested file mode."""
        self.file.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file.file_path.open(mode, encoding="utf-8", newline="") as csv_file:
            csv.writer(csv_file).writerow(data)
        return self.file.file_path


class ReadCsvReport:
    """Find CSV reports and load them for analysis.

    Supply a complete column-to-Polars-type schema to disable type inference.
    """

    def __init__(
        self,
        path: Path | Sequence[Path],
        pattern: str = "*.csv",
        schema: Mapping[str, pl.DataType] | None = None,
    ) -> None:
        """Configure file or directory paths and a filename glob pattern."""
        self.path = path
        self.pattern = pattern
        self.schema = dict(schema) if schema is not None else None
        self._files: list[Path] | None = None

    def search(self) -> list[Path]:
        """Return matching files in stable order, without duplicates."""
        paths = [self.path] if isinstance(self.path, Path) else self.path
        matches: set[Path] = set()
        for path in paths:
            if path.is_dir():
                matches.update(
                    file for file in path.glob(self.pattern) if file.is_file()
                )
            elif path.is_file() and fnmatch(path.name, self.pattern):
                matches.add(path)
        self._files = sorted(matches)
        return list(self._files)

    def read(self) -> pl.DataFrame:
        """Read all matching CSV files into one DataFrame."""
        return self._reads(self.search())

    @staticmethod
    def _header(file: Path) -> list[str]:
        """Read and validate a CSV header without loading its data."""
        with file.open(encoding="utf-8", newline="") as csv_file:
            header = next(csv.reader(csv_file), None)
            if header is None:
                raise ValueError(f"Report has no header: {file}")
            if len(header) != len(set(header)):
                raise ValueError(f"Report has duplicate columns: {file}")
            return header

    def _schema(self, header: list[str], file: Path) -> dict[str, pl.DataType] | None:
        """Validate and order the declared types to match the CSV columns."""
        if self.schema is None:
            return None
        if set(self.schema) != set(header):
            raise ValueError(f"Report schema does not match columns: {file}")
        return {column: self.schema[column] for column in header}

    def _read(self, file: Path, header: list[str]) -> pl.DataFrame:
        """Read one CSV file using the declared schema when provided."""
        return pl.read_csv(file, schema=self._schema(header, file))

    def _reads(self, files: Sequence[Path]) -> pl.DataFrame:
        """Combine files with identical column order, retaining empty headers."""
        header: list[str] | None = None
        combined: pl.DataFrame | None = None
        for file in files:
            file_header = self._header(file)
            if header is not None and file_header != header:
                raise ValueError(f"Report columns do not match: {file}")
            header = file_header
            try:
                frame = self._read(file, file_header)
                if combined is None or (combined.is_empty() and not frame.is_empty()):
                    combined = frame
                elif not frame.is_empty():
                    combined = pl.concat([combined, frame])
            except pl.exceptions.PolarsError as exc:
                raise ValueError(
                    f"Cannot read or combine report {file}: {exc}"
                ) from exc
        return combined if combined is not None else pl.DataFrame(schema=self.schema)

    def iter_chunks(self, chunk_size: int = 100_000) -> Iterator[pl.DataFrame]:
        """Yield bounded row batches across matching files."""
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        header: list[str] | None = None
        for file in self.search():
            file_header = self._header(file)
            if header is not None and file_header != header:
                raise ValueError(f"Report columns do not match: {file}")
            header = file_header
            schema = self._schema(file_header, file)
            try:
                yield from pl.scan_csv(file, schema=schema).collect_batches(
                    chunk_size=chunk_size
                )
            except pl.exceptions.PolarsError as exc:
                raise ValueError(f"Cannot read report {file}: {exc}") from exc
