"""Load the stored example bench and display its laboratory resources."""

from enum import StrEnum
from pathlib import Path

from elims_instruments.bench import Bench
from elims_instruments.duts import Dut, DutFactory
from elims_instruments.projects import Project, ProjectFactory
from elims_instruments.utils.logger import (
    LOGGER_HELPER,
    LoggerHelper,
    get_logger,
)

EXAMPLE_CONFIGURATION = Path(__file__).with_name("bench.toml")
EXAMPLE_LOG_DIRECTORY = Path(__file__).with_name("logs")
example_logger = get_logger("example", LoggerHelper.Color.LIGHT_CYAN)
instrument_logger = get_logger("instrument", LoggerHelper.Color.CYAN)
board_logger = get_logger("board", LoggerHelper.Color.GREEN)
dut_logger = get_logger("dut", LoggerHelper.Color.YELLOW)
project_logger = get_logger("project", LoggerHelper.Color.MAGENTA)


class ProjectInstrumentName(StrEnum):
    """Instrument names used by the example characterization setup."""

    PRIMARY_DMM = "primary_dmm"
    FREQUENCY_COUNTER = "frequency_counter"


class ProjectBoardName(StrEnum):
    """Board names used by the example characterization setup."""

    CHARACTERIZATION_BOARD = "characterization_board"


class ProjectDutName(StrEnum):
    """DUT names used by the example characterization setup."""

    CHARACTERIZED_IC = "characterized_ic"


class ProjectName(StrEnum):
    """Project roles used by the example bench."""

    CHARACTERIZATION = "characterization"


class ExampleDut(Dut):
    """Minimal concrete DUT for the example project."""

    def get_id(self) -> str:
        """Return the persistent DUT ID."""
        return self.dut.id


class ExampleProject(Project):
    """Minimal concrete characterization project."""

    def get_id(self) -> str:
        """Return the persistent project ID."""
        return self.project.id


DutFactory.register("demo-project", ExampleDut)
ProjectFactory.register("demo-project", ExampleProject)


def configure_example_logging() -> None:
    """Write example logs to the terminal and the example directory."""
    LOGGER_HELPER.file_directory = EXAMPLE_LOG_DIRECTORY
    LOGGER_HELPER.configure()


def load_example_bench() -> Bench:
    """Load the project names and assets stored beside this script."""
    return Bench(
        EXAMPLE_CONFIGURATION,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
        authorized_dut_names=ProjectDutName,
        authorized_project_names=ProjectName,
    )


def show_bench(bench: Bench) -> None:
    """Log the database identity behind every resolved driver."""
    example_logger.info("Instruments:")
    for name, driver in bench.instruments.items():
        instrument = driver.instrument
        instrument_logger.info(
            "{}: {} {} ({})",
            name,
            instrument.maker,
            instrument.model,
            instrument.asset_tag,
        )

    example_logger.info("Boards:")
    for name, board_driver in bench.boards.items():
        board = board_driver.board
        board_logger.info(
            "{}: {} {} ({})",
            name,
            board.maker,
            board.model,
            board.asset_tag,
        )

    example_logger.info("DUTs:")
    for name, dut_object in bench.duts.items():
        dut = dut_object.dut
        dut_logger.info(
            "{}: revision {}, corner {} ({})",
            name,
            dut.revision,
            dut.corner,
            dut.asset_tag,
        )

    example_logger.info("Projects:")
    for name, project_object in bench.projects.items():
        project = project_object.project
        dut_ids = ", ".join(dut.asset_tag for dut in project.supported_duts)
        board_ids = ", ".join(board.asset_tag for board in project.supported_boards)
        project_logger.info(
            "{}: {} ({}), DUTs [{}], boards [{}]",
            name,
            project.name,
            project_object.get_id(),
            dut_ids,
            board_ids,
        )


def main() -> None:
    """Load and display the example bench."""
    configure_example_logging()
    show_bench(load_example_bench())


if __name__ == "__main__":
    main()
