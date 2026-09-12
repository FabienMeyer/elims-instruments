"""Tests for the characterization run coordinator."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from tests.characterization.sweep_helpers import RegisterDut

from elims_instruments.characterization import (
    Characterization,
    InnerMatrix,
    InnerSweep,
    OuterMatrix,
    Voltages,
    VoltageSetPoints,
)
from elims_instruments.utils.files import FileHelper
from elims_instruments.utils.timestamp import Timestamp

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Point(InnerSweep[RegisterDut]):
    def get_test_id(self) -> str:
        return f"{self.test_id}-{self.iteration}"

    def report_header(self) -> list[str]:
        return ["iteration"]

    def report_value(self) -> list[str]:
        return [str(self.iteration)]

    def run(self) -> tuple[str, list[str]]:
        return self.get_test_id(), [str(self.iteration)]


class Matrix(InnerMatrix[RegisterDut]):
    def __iter__(self) -> Iterator[Point]:
        for iteration in self.iterations:
            yield Point(self.test_id, self.dut, iteration)


def make_runner(path: Path) -> Characterization[RegisterDut]:
    dut = RegisterDut()
    outer = OuterMatrix(
        "MAIN",
        None,
        [None, None],
        Voltages([]),
        [VoltageSetPoints()],
    )
    return Characterization(
        file_helper=FileHelper(path.parent, path.stem, FileHelper.FileSuffix.CSV),
        bench=dut,
        outer_matrix=outer,
        inner_matrix=Matrix("MAIN-SUB", dut, 2),
        measurement_headers=["measurement"],
    )


def test_run_writes_every_completed_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = Timestamp(datetime(2026, 9, 19, 12, 34, 56, tzinfo=UTC))
    monkeypatch.setattr(Timestamp, "now", classmethod(lambda cls: captured))
    runner = make_runner(tmp_path / "result.csv")

    assert runner.run() == tmp_path / "result.csv"
    with (tmp_path / "result.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == [
        "test_id",
        "timestamp",
        "dut_id",
        "serial_number",
        "corner",
        "revision",
        "t_target",
        "t_actual",
        "iteration",
        "measurement",
    ]
    assert [(row[0], *row[-2:]) for row in rows[1:]] == [
        ("MAIN-SUB-1", "1", "1"),
        ("MAIN-SUB-2", "2", "2"),
        ("MAIN-SUB-1", "1", "1"),
        ("MAIN-SUB-2", "2", "2"),
    ]
    assert {row[1] for row in rows[1:]} == {"2026_09_19_12_34_56"}


def test_run_cleans_up_after_measurement_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(Voltages, "power_down", lambda self: calls.append("power_down"))

    def fail(self) -> list[str]:
        raise RuntimeError("measurement failed")

    runner = make_runner(tmp_path / "result.csv")
    monkeypatch.setattr(Point, "run", fail)
    with pytest.raises(RuntimeError, match="measurement failed"):
        runner.run()
    assert calls == ["power_down"]


def test_run_rejects_wrong_measurement_width(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = make_runner(tmp_path / "result.csv")
    monkeypatch.setattr(Point, "run", lambda self: (self.get_test_id(), []))
    with pytest.raises(ValueError, match="Measurement value count"):
        runner.run()
