"""Execute a characterization matrix and write its completed measurements."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from elims_instruments.characterization.reports import CsvSection, WriteCsvReport
from elims_instruments.utils.timestamp import Timestamp

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from elims_instruments.bench import Bench
    from elims_instruments.bench.duts import Dut
    from elims_instruments.characterization.sweeps import (
        InnerMatrix,
        InnerSweep,
        OuterMatrix,
        OuterSweep,
    )
    from elims_instruments.utils.files import FileHelper

DutT = TypeVar("DutT", bound="Dut")


class Characterization(Generic[DutT]):
    """Run nested sweeps and append one CSV row per completed measurement."""

    def __init__(
        self,
        file_helper: FileHelper,
        bench: Bench,
        outer_matrix: OuterMatrix,
        inner_matrix: InnerMatrix[DutT],
        measurement_headers: Sequence[str],
    ) -> None:
        self.file_helper = file_helper
        self.bench = bench
        self.outer_matrix = outer_matrix
        self.inner_matrix = inner_matrix
        self.measurement_headers = tuple(measurement_headers)
        self._current_outer = self._first_outer_sweep()
        self._current_inner = self._first_inner_sweep()
        self.report = self.configure_report()

    def configure_report(self) -> WriteCsvReport:
        """Build the report from the bench and the current sweep points."""
        return WriteCsvReport(
            file=self.file_helper,
            sections=[
                CsvSection(self.bench.report_header, self.bench.report_value),
                CsvSection(
                    self._current_outer.report_header,
                    lambda: self._current_outer.report_value(),
                ),
                CsvSection(
                    self._current_inner.report_header,
                    lambda: self._current_inner.report_value(),
                ),
                CsvSection(
                    lambda: list(self.measurement_headers),
                    lambda: [],
                ),
            ],
        )

    def outer_run(self) -> Path:
        """Run every outer point and clean up hardware after each point."""
        self.report.write_header()
        for outer_sweep in self.outer_matrix:
            self._current_outer = outer_sweep
            try:
                outer_sweep.set_temperature()
                outer_sweep.enable_temperature()
                outer_sweep.set_voltages()
                outer_sweep.power_up()
                self.inner_run()
            finally:
                outer_sweep.power_down()
                outer_sweep.disable_temperature()
        return self.report.file.file_path

    def inner_run(self) -> Path:
        """Run every inner point and append completed measurement rows."""
        for inner_sweep in self.inner_matrix:
            self._current_inner = inner_sweep
            inner_sweep.reset()
            test_id, data = inner_sweep.run()
            timestamp = Timestamp.now().file()
            if len(data) != len(self.measurement_headers):
                raise ValueError("Measurement value count does not match headers")
            self.report.write_data(test_id, timestamp, data)
        return self.report.file.file_path

    def run(self) -> Path:
        """Write the report and run all configured characterization points."""
        return self.outer_run()

    def _first_outer_sweep(self) -> OuterSweep:
        try:
            return next(iter(self.outer_matrix))
        except StopIteration as error:
            raise ValueError("Outer matrix has no operating points") from error

    def _first_inner_sweep(self) -> InnerSweep[DutT]:
        try:
            return next(iter(self.inner_matrix))
        except StopIteration as error:
            raise ValueError("Inner matrix has no test points") from error
