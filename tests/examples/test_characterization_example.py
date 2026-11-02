"""End-to-end tests for the documented characterization examples."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from examples.bench_setup import bench as bench_example
from examples.characterization import characterization as characterization_example
from examples.characterization import inner_sweep as inner_sweep_example
from examples.characterization import outer_sweep as outer_sweep_example
from examples.characterization import report as report_example
from examples.characterization import specifications as specifications_example
from examples.characterization import temperature as temperature_example
from examples.characterization import voltage as voltage_example
from examples.characterization import voltages as voltages_example

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_complete_characterization_writes_every_operating_point(
    tmp_path: Path,
) -> None:
    """The documented report path composes runtime drivers and completes."""
    report_path = tmp_path / "characterization.csv"

    result = characterization_example.create_characterization(report_path).run()

    assert result == report_path
    with report_path.open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    assert len(rows) == 17
    assert rows[0][-4:] == ["iteration", "frequency_hz", "result_unit", "result"]
    assert {row[0] for row in rows[1:]} == {
        "com-bandgap-iref-1",
        "com-bandgap-iref-2",
        "com-bandgap-vref-1",
        "com-bandgap-vref-2",
    }


def test_sweep_conditions_come_from_persisted_revision_profile() -> None:
    """The bench profile supplies all simulated source limits and setpoints."""
    setup = bench_example.create_characterization_setup()
    sweeps = list(outer_sweep_example.create_outer_matrix(setup.specifications))

    assert [sweep.temperature_setpoint for sweep in sweeps] == [-40, -40, 25, 25]
    assert [sweep.voltage_setpoints.as_dict() for sweep in sweeps] == [
        {"vdda": 1.1},
        {"vdda": 1.3},
        {"vdda": 1.1},
        {"vdda": 1.3},
    ]
    assert sweeps[0].voltages.vdda.voltage_limits == (
        setup.specifications.voltage_specifications[0].voltage_limits
    )
    assert sweeps[0].voltages.vddd.voltage_limits == (
        setup.specifications.voltage_specifications[1].voltage_limits
    )


def test_documented_example_entry_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every command listed in the examples guide executes successfully."""
    monkeypatch.setattr(bench_example.LOGGER_HELPER, "configure", lambda: None)
    monkeypatch.setattr(
        report_example,
        "run_example",
        lambda: characterization_example.create_characterization(
            tmp_path / "documented-report.csv"
        ).run(),
    )

    bench_example.main()
    specifications_example.main()
    temperature_example.main()
    voltage_example.main()
    voltages_example.main()
    outer_sweep_example.main()
    inner_sweep_example.main()
    report_example.main()

    assert (tmp_path / "documented-report.csv").is_file()
