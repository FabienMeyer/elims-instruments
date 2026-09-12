"""Run a complete characterization using the public coordinator API."""

from __future__ import annotations

from pathlib import Path

from elims_instruments.characterization import Characterization
from elims_instruments.utils.files import FileHelper
from elims_instruments.utils.logger import LOGGER_HELPER, LoggerHelper, get_logger
from examples.bench_setup.dut import create_example_dut
from examples.characterization.inner_sweep import SUB_BLOCK, BandgapMatrix
from examples.characterization.outer_sweep import MAIN_BLOCK, create_outer_matrix

logger = get_logger(__name__, LoggerHelper.Color.GREEN)
REPORT_PATH = Path(__file__).parents[1] / "reports" / "characterization.csv"


def create_characterization() -> Characterization:
    """Build a deterministic characterization with simulated hardware."""
    dut = create_example_dut()
    outer_matrix = create_outer_matrix()
    inner_matrix = BandgapMatrix(
        dut=dut,
        iterations=2,
        main_block=MAIN_BLOCK,
        sub_block=SUB_BLOCK,
    )
    file_helper = FileHelper(
        REPORT_PATH.parent,
        REPORT_PATH.stem,
        FileHelper.FileSuffix.CSV,
    )
    return Characterization(
        file_helper=file_helper,
        bench=dut,
        outer_matrix=outer_matrix,
        inner_matrix=inner_matrix,
        measurement_headers=["result_unit", "result"],
    )


def main() -> None:
    """Run the characterization and log the generated report path."""
    LOGGER_HELPER.configure()
    report_path = create_characterization().run()
    logger.info("Wrote characterization report to {}", report_path)


if __name__ == "__main__":
    main()
