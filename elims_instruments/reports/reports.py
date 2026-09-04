"""CSV reports produced by characterization tests."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from elims_instruments.duts import Dut
from elims_instruments.instruments.abstract import Instrument

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from elims_instruments.database import DutModel, InstrumentModel
    from elims_instruments.temperatures import Temperature
    from elims_instruments.utils.timestamp import Timestamp
    from elims_instruments.voltages import AdjustableVoltage, FixedVoltage


class CsvReport:
    """A CSV report associated with one test and one DUT."""

    def __init__(
        self,
        path: Path,
        dut: Dut | DutModel,
        *,
        timestamp: Timestamp | None = None,
    ) -> None:
        """Initialize a report with an optional timestamped filename."""
        self.path = (
            path.with_name(f"{path.stem}_{timestamp.file()}{path.suffix}")
            if timestamp is not None
            else path
        )
        self.dut = dut.dut if isinstance(dut, Dut) else dut
        self._dut_information: dict[str, object] = self.dut.model_dump(mode="json")
        if timestamp is not None:
            self._dut_information["report_timestamp_iso"] = timestamp.iso()
        self._information = dict(self._dut_information)

    def save_dut_information(self) -> Path:
        """Write the persisted DUT fields as the first report record."""
        self._information = dict(self._dut_information)
        return self._write_information()

    def save_temperature_information(
        self,
        temperature_condition: tuple[Temperature, float] | None,
    ) -> Path:
        """Write the target and actual temperature information."""
        if temperature_condition is None:
            self._information.update(
                temperature_target_c=None,
                temperature_actual_c=None,
            )
        else:
            temperature, target = temperature_condition
            self._information.update(
                temperature_target_c=target,
                temperature_actual_c=temperature.get_temperature(),
            )
        return self._write_information()

    def save_voltage_information(
        self,
        voltages: dict[AdjustableVoltage | FixedVoltage, float],
    ) -> Path:
        """Write each supply name and its target and actual voltage."""
        for field in tuple(self._information):
            if field.startswith("supply_"):
                del self._information[field]

        for index, (voltage, target) in enumerate(voltages.items(), start=1):
            column_prefix = f"supply_{index}"
            self._information[f"{column_prefix}_name"] = voltage.name
            self._information[f"{column_prefix}_target_v"] = target
            self._information[f"{column_prefix}_actual_v"] = voltage.get_voltage()

        return self._write_information()

    def save_instrument_information(
        self,
        instruments: Mapping[str, Instrument | InstrumentModel],
    ) -> Path:
        """Write the asset tag of every instrument used by the test."""
        for field in tuple(self._information):
            if field.startswith("instrument_"):
                del self._information[field]

        for index, instrument in enumerate(instruments.values(), start=1):
            model = (
                instrument.instrument
                if isinstance(instrument, Instrument)
                else instrument
            )
            self._information[f"instrument_{index}_asset_tag"] = model.asset_tag

        return self._write_information()

    def _write_information(self) -> Path:
        """Write the accumulated report information as one CSV record."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self._information)
            writer.writeheader()
            writer.writerow(self._information)

        return self.path
