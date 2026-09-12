"""Write an incremental CSV report from the outer-sweep example."""

from __future__ import annotations

from pathlib import Path

from elims_instruments.characterization import CsvReport
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.characterization.inner_sweep import create_inner_matrix, measure_current
from examples.characterization.outer_sweep import create_outer_matrix

logger = get_logger(__name__, LoggerHelper.Color.GREEN)
REPORT_PATH = Path(__file__).parents[1] / "reports" / "outer_sweep.csv"


def main() -> None:
    """Write the header before testing and append every completed sweep."""
    LOGGER_HELPER.configure()
    matrix = create_outer_matrix()
    first_outer_sweep = next(iter(matrix))
    first_inner_sweep = next(iter(create_inner_matrix(first_outer_sweep.dut)))
    report = CsvReport(REPORT_PATH, first_outer_sweep.dut)

    # The complete schema is written before any hardware operation starts.
    report.write_header(
        [
            *first_outer_sweep.report_header(),
            *first_inner_sweep.report_header(),
            "measured_current_a",
        ]
    )

    for outer_sweep in matrix:
        outer_sweep.reset()
        outer_sweep.set_temperature()
        outer_sweep.enable_temperature()
        outer_sweep.set_voltages()
        outer_sweep.power_up()
        try:
            for inner_sweep in create_inner_matrix(outer_sweep.dut):
                inner_sweep.reset()
                report.save_information(
                    [
                        *outer_sweep.report_value(),
                        *inner_sweep.report_value(),
                        f"{measure_current(inner_sweep):.4f}",
                    ]
                )
        finally:
            outer_sweep.power_down()
            outer_sweep.disable_temperature()

    logger.info("Wrote report to {}", report.path)


if __name__ == "__main__":
    main()
