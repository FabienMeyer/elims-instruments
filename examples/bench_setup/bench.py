"""Load and display the example project."""

from __future__ import annotations

from elims_instruments.bench import Bench
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.board import ExampleBoard
from examples.bench_setup.constants import (
    BENCH_CONFIGURATION,
    BoardName,
    DutName,
    InstrumentName,
    ProjectName,
)
from examples.bench_setup.dut import ExampleDut
from examples.bench_setup.project import ExampleProject

logger = get_logger(__name__)


def create_bench() -> Bench:
    """Create the complete bench from the preceding example definitions."""
    return Bench(
        BENCH_CONFIGURATION,
        authorized_board_names=BoardName,
        authorized_dut_names=DutName,
        authorized_project_names=ProjectName,
        authorized_instrument_names=InstrumentName,
    )


def main() -> None:
    """Resolve database records, build drivers, and print their metadata."""
    LOGGER_HELPER.configure()

    bench = create_bench()

    board = bench.boards.characterization_board
    assert isinstance(board, ExampleBoard)

    logger.info(f"Board ID: {board.get_id()}")

    dut = bench.duts.characterized_ic
    assert isinstance(dut, ExampleDut)

    logger.info(f"DUT ID: {dut.get_id()}")

    project = bench.projects.characterization
    assert isinstance(project, ExampleProject)

    logger.info(f"Project ID: {project.get_id()}")
    logger.info(f"Project Description: {project.describe()}")
    logger.info(f"Datasheet Name: {project.project.datasheet_name}")
    logger.info(f"Internal Name: {project.project.internal_name}")

    instruments = bench.instruments
    for instrument_name, driver in instruments.items():
        instrument = driver.instrument
        logger.info(
            f"{instrument_name}: {type(driver).__name__} for "
            f"{instrument.maker} {instrument.model} "
            f"(asset tag: {instrument.asset_tag})"
        )


if __name__ == "__main__":
    main()
