"""Tests for incremental CSV report persistence."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import pytest

from elims_instruments.bench import Dut
from elims_instruments.characterization import CsvReport
from elims_instruments.database import DutModel

if TYPE_CHECKING:
    from pathlib import Path


class ReportDut(Dut):
    """Minimal DUT used to exercise report output."""

    def __init__(self) -> None:
        """Create a DUT with stable report values."""
        super().__init__(
            DutModel(
                id="dut-1",
                asset_tag="DUT-001",
                project="demo-project",
                corner="TT",
                die_revision="A",
                serial_number="42",
            )
        )

    def get_id(self) -> str:
        """Return the database identifier."""
        return self.dut.id

    def reset(self) -> None:
        """Reset this test DUT."""


def read_csv(path: Path) -> list[list[str]]:
    """Read all records from a generated CSV report."""
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.reader(csv_file))


def test_report_is_created_with_a_header_before_test_data(tmp_path: Path) -> None:
    """Test setup creates a usable header-only report immediately."""
    path = tmp_path / "report.csv"

    report = CsvReport(path, ReportDut())
    report.write_header(["iteration", "frequency", "current"])

    assert read_csv(path) == [
        [
            "dut_id",
            "serial_number",
            "corner",
            "revision",
            "iteration",
            "frequency",
            "current",
        ]
    ]


def test_each_completed_inner_sweep_is_appended(tmp_path: Path) -> None:
    """Saving a completed sweep preserves all previously written sweep rows."""
    path = tmp_path / "report.csv"
    report = CsvReport(path, ReportDut())
    report.write_header(["iteration", "frequency", "current"])

    report.save_information(["1", "1000000", "0.12"])
    report.save_information(["2", "2000000", "0.18"])

    assert read_csv(path) == [
        [
            "dut_id",
            "serial_number",
            "corner",
            "revision",
            "iteration",
            "frequency",
            "current",
        ],
        ["DUT-001", "42", "TT", "A", "1", "1000000", "0.12"],
        ["DUT-001", "42", "TT", "A", "2", "2000000", "0.18"],
    ]


def test_header_cannot_change_after_inner_sweep_is_saved(tmp_path: Path) -> None:
    """A late schema change cannot corrupt rows already in the report."""
    report = CsvReport(tmp_path / "report.csv", ReportDut())
    report.write_header(["iteration"])
    report.save_information(["1"])

    with pytest.raises(RuntimeError, match="header cannot change"):
        report.write_header(["current"])
