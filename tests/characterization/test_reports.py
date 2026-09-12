"""Tests for incremental CSV report persistence."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import polars as pl
import pytest

from elims_instruments.characterization import ReadCsvReport, WriteCsvReport
from elims_instruments.characterization.reports.reports import CsvSection
from elims_instruments.utils.files import FileHelper

if TYPE_CHECKING:
    from pathlib import Path


def read_csv(path: Path) -> list[list[str]]:
    """Read all records from a generated CSV report."""
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.reader(csv_file))


def test_write_report_preserves_header_and_completed_rows(tmp_path: Path) -> None:
    """The provider based report appends rows without replacing earlier data."""
    file = FileHelper(tmp_path, "report", FileHelper.FileSuffix.CSV)

    def empty() -> list[str]:
        return []

    class BenchStub:
        def report_header(self) -> list[str]:
            return ["dut"]

        def report_value(self) -> list[str]:
            return ["DUT-001"]

    report = WriteCsvReport(
        file,
        sections=[
            CsvSection(BenchStub().report_header, BenchStub().report_value),
            CsvSection(empty, empty),
            CsvSection(empty, empty),
            CsvSection(lambda: ["current"], lambda: []),
        ],
    )

    with pytest.raises(RuntimeError, match="header must be written"):
        report.write_data("MAIN-SUB-1", "2026_09_19_12_34_56", ["0.12"])
    report.write_header()
    assert read_csv(file.file_path) == [["test_id", "timestamp", "dut", "current"]]

    report.write_data("MAIN-SUB-1", "2026_09_19_12_34_56", ["0.12"])
    report.write_data("MAIN-SUB-1", "2026_09_19_12_34_57", ["0.18"])
    assert read_csv(file.file_path) == [
        ["test_id", "timestamp", "dut", "current"],
        ["MAIN-SUB-1", "2026_09_19_12_34_56", "DUT-001", "0.12"],
        ["MAIN-SUB-1", "2026_09_19_12_34_57", "DUT-001", "0.18"],
    ]
    with pytest.raises(RuntimeError, match="header cannot change"):
        report.write_header()


def test_write_report_accepts_bench_aggregate_columns(tmp_path: Path) -> None:
    """The bench object can supply the DUT and asset columns directly."""

    class BenchStub:
        def report_header(self) -> list[str]:
            return ["bench_id", "bench_name"]

        def report_value(self) -> list[str]:
            return ["BENCH-1", "example"]

    file = FileHelper(tmp_path, "bench_report", FileHelper.FileSuffix.CSV)
    report = WriteCsvReport(
        file,
        sections=[
            CsvSection(BenchStub().report_header, BenchStub().report_value),
            CsvSection(lambda: ["mode"], lambda: ["slow"]),
            CsvSection(lambda: ["iteration"], lambda: ["1"]),
            CsvSection(lambda: ["current"], lambda: []),
        ],
    )

    report.write_header()
    report.write_data("MAIN-SUB-1", "2026_09_19_12_34_56", ["0.12"])
    assert read_csv(file.file_path) == [
        [
            "test_id",
            "timestamp",
            "bench_id",
            "bench_name",
            "mode",
            "iteration",
            "current",
        ],
        [
            "MAIN-SUB-1",
            "2026_09_19_12_34_56",
            "BENCH-1",
            "example",
            "slow",
            "1",
            "0.12",
        ],
    ]


def test_read_report_finds_and_combines_csv_files(tmp_path: Path) -> None:
    """Reading preserves quoted values and uses a stable file order."""
    (tmp_path / "b.csv").write_text('dut,current\n"B,2",0.2\n', encoding="utf-8")
    (tmp_path / "a.csv").write_text("dut,current\nA,0.1\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("other\n", encoding="utf-8")

    report = ReadCsvReport([tmp_path, tmp_path / "a.csv"])
    assert [file.name for file in report.search()] == ["a.csv", "b.csv"]
    frame = report.read()
    assert frame["dut"].to_list() == ["A", "B,2"]
    assert frame["current"].to_list() == [0.1, 0.2]
    assert [len(chunk) for chunk in report.iter_chunks(chunk_size=1)] == [1, 1]


def test_read_report_rejects_inconsistent_columns(tmp_path: Path) -> None:
    """Merging reports with different schemas would mislabel measurements."""
    (tmp_path / "a.csv").write_text("dut,current\nA,0.1\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("dut,voltage\nB,1.2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="columns do not match"):
        ReadCsvReport(tmp_path).read()


def test_read_report_uses_declared_schema_for_all_files(tmp_path: Path) -> None:
    """A declared type handles values that infer differently by file."""
    (tmp_path / "a.csv").write_text("dut,current\nA,1\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("dut,current\nB,0.2\n", encoding="utf-8")

    report = ReadCsvReport(tmp_path, schema={"current": pl.Float64, "dut": pl.String})
    frame = report.read()
    assert frame.schema == {"dut": pl.String, "current": pl.Float64}
    assert frame["current"].to_list() == [1.0, 0.2]
    assert [chunk.schema for chunk in report.iter_chunks(chunk_size=1)] == [
        frame.schema,
        frame.schema,
    ]


def test_read_report_rejects_incomplete_schema(tmp_path: Path) -> None:
    """Explicit schemas must cover every CSV column."""
    (tmp_path / "a.csv").write_text("dut,current\nA,1\n", encoding="utf-8")
    report = ReadCsvReport(tmp_path, schema={"current": pl.Float64})

    with pytest.raises(ValueError, match="schema does not match columns"):
        report.read()


def test_read_report_chunks_keep_row_order_and_size(tmp_path: Path) -> None:
    """A single file spanning batches yields every row in order."""
    (tmp_path / "report.csv").write_text("value\n0\n1\n2\n3\n4\n", encoding="utf-8")
    chunks = list(ReadCsvReport(tmp_path).iter_chunks(chunk_size=2))

    assert all(0 < len(chunk) <= 2 for chunk in chunks)
    assert sum(len(chunk) for chunk in chunks) == 5
    assert [value for chunk in chunks for value in chunk["value"]] == list(range(5))


def test_read_report_empty_files_preserve_columns(tmp_path: Path) -> None:
    """Header-only files keep columns and do not change nonempty inferred types."""
    (tmp_path / "a.csv").write_text("dut,current\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("dut,current\nA,0.2\n", encoding="utf-8")

    frame = ReadCsvReport(tmp_path).read()
    assert frame.schema == {"dut": pl.String, "current": pl.Float64}
    assert frame.height == 1

    (tmp_path / "b.csv").write_text("dut,current\n", encoding="utf-8")
    empty = ReadCsvReport(tmp_path).read()
    assert empty.shape == (0, 2)
    assert empty.columns == ["dut", "current"]
    assert list(ReadCsvReport(tmp_path).iter_chunks()) == []


def test_read_report_no_matches_is_empty(tmp_path: Path) -> None:
    """No matching files yield an empty frame and no chunks."""
    report = ReadCsvReport(tmp_path, schema={"dut": pl.String})
    assert report.read().schema == {"dut": pl.String}
    assert report.read().height == 0
    assert list(report.iter_chunks()) == []


def test_read_report_type_conflict_identifies_file(tmp_path: Path) -> None:
    """Inferred types that cannot be combined identify the later file."""
    (tmp_path / "a.csv").write_text("value\n1\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("value\ntext\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"b\.csv"):
        ReadCsvReport(tmp_path).read()


def test_read_report_parse_error_identifies_file(tmp_path: Path) -> None:
    """Malformed data names its source in full and chunked reads."""
    (tmp_path / "bad.csv").write_text("value\n1,2\n", encoding="utf-8")
    report = ReadCsvReport(tmp_path)

    with pytest.raises(ValueError, match=r"bad\.csv"):
        report.read()
    with pytest.raises(ValueError, match=r"bad\.csv"):
        list(report.iter_chunks())
