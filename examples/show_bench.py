"""Load the stored example bench and display its laboratory resources."""

from enum import StrEnum
from pathlib import Path

from elims_instruments.bench import Bench

EXAMPLE_CONFIGURATION = Path(__file__).with_name("bench.toml")


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


def load_example_bench() -> Bench:
    """Load the project names and assets stored beside this script."""
    return Bench(
        EXAMPLE_CONFIGURATION,
        authorized_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
        authorized_dut_names=ProjectDutName,
    )


def show_bench(bench: Bench) -> None:
    """Print the database identity behind every resolved driver."""
    print("Instruments:")
    for name, driver in bench.instruments.items():
        instrument = driver.instrument
        print(
            f"  {name}: {instrument.maker} {instrument.model} "
            f"({instrument.asset_tag})"
        )

    print("Boards:")
    for name, board_driver in bench.boards.items():
        board = board_driver.board
        print(f"  {name}: {board.maker} {board.model} ({board.asset_tag})")

    print("DUTs:")
    for name, dut_object in bench.duts.items():
        dut = dut_object.dut
        print(
            f"  {name}: revision {dut.revision}, corner {dut.corner} "
            f"({dut.asset_tag})"
        )


def main() -> None:
    """Load and display the example bench."""
    show_bench(load_example_bench())


if __name__ == "__main__":
    main()
