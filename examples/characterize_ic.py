"""Skeleton for an IC-characterization script using a configured bench."""

from show_bench import load_example_bench

from elims_instruments.bench import Bench


def characterize(bench: Bench) -> None:
    """Select the configured DUT and its characterization resources.

    Replace the final print with the project-specific board setup and
    instrument measurement calls as those driver APIs are implemented.
    """
    board = bench.boards.characterization_board
    dut = bench.duts.characterized_ic
    multimeter = bench.instruments.primary_dmm
    counter = bench.instruments.frequency_counter

    print(
        "Characterizing IC DUT: "
        f"project {dut.dut.project}, revision {dut.dut.revision}, "
        f"corner {dut.dut.corner} "
        f"({dut.dut.asset_tag})"
    )
    print(
        f"Traceability: lot={dut.dut.lot_number}, wafer={dut.dut.wafer_id}, "
        f"die=({dut.dut.die_x}, {dut.dut.die_y})"
    )
    print(
        "Fixture: "
        f"{board.board.maker} {board.board.model} ({board.board.asset_tag})"
    )
    print(f"DMM: {multimeter.instrument.asset_tag}")
    print(f"Counter: {counter.instrument.asset_tag}")
    print("Ready to apply the characterization sequence.")


def main() -> None:
    """Run the example with a representative IC identity."""
    characterize(load_example_bench())


if __name__ == "__main__":
    main()
