"""Skeleton for an IC-characterization script using a configured bench."""

from show_bench import configure_example_logging, load_example_bench

from elims_instruments.bench import Bench
from elims_instruments.utils.logger import LoggerHelper, get_logger

dut_logger = get_logger("dut", LoggerHelper.Color.YELLOW)
board_logger = get_logger("board", LoggerHelper.Color.GREEN)
instrument_logger = get_logger("instrument", LoggerHelper.Color.CYAN)
project_logger = get_logger("project", LoggerHelper.Color.MAGENTA)


def characterize(bench: Bench) -> None:
    """Select the configured DUT and its characterization resources.

    Replace the final log with the project-specific board setup and
    instrument measurement calls as those driver APIs are implemented.
    """
    board = bench.boards.characterization_board
    dut = bench.duts.characterized_ic
    project = bench.projects.characterization
    multimeter = bench.instruments.primary_dmm
    counter = bench.instruments.frequency_counter

    dut_logger.info(
        "Characterizing IC DUT: project {}, revision {}, corner {} ({})",
        project.project.name,
        dut.dut.revision,
        dut.dut.corner,
        dut.dut.asset_tag,
    )
    dut_logger.info(
        "Traceability: lot={}, wafer={}, die=({}, {})",
        dut.dut.lot_number,
        dut.dut.wafer_id,
        dut.dut.die_x,
        dut.dut.die_y,
    )
    board_logger.info(
        "Fixture: {} {} ({})",
        board.board.maker,
        board.board.model,
        board.board.asset_tag,
    )
    instrument_logger.info("DMM: {}", multimeter.instrument.asset_tag)
    instrument_logger.info("Counter: {}", counter.instrument.asset_tag)
    project_logger.info("Project ID: {}", project.get_id())
    project_logger.info("Ready to apply the characterization sequence.")


def main() -> None:
    """Run the example with a representative IC identity."""
    configure_example_logging()
    characterize(load_example_bench())


if __name__ == "__main__":
    main()
