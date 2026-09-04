"""Skeleton for an IC-characterization script using a configured bench."""

from pathlib import Path

from show_bench import (
    EXAMPLE_CONFIGURATION,
    configure_example_logging,
    load_example_bench,
)

from elims_instruments.bench import Bench
from elims_instruments.database import InstrumentCrud
from elims_instruments.reports import CsvReport
from elims_instruments.utils.logger import LoggerHelper, get_logger
from elims_instruments.utils.timestamp import Timestamp

dut_logger = get_logger("dut", LoggerHelper.Color.YELLOW)
board_logger = get_logger("board", LoggerHelper.Color.GREEN)
instrument_logger = get_logger("instrument", LoggerHelper.Color.CYAN)
project_logger = get_logger("project", LoggerHelper.Color.MAGENTA)
REPORT_DIRECTORY = Path(__file__).with_name("reports")


def create_and_verify_report(bench: Bench) -> Path:
    """Create a report and verify its instrument tags against audit history."""
    report_timestamp = Timestamp.now()
    report = CsvReport(
        REPORT_DIRECTORY / "characterization.csv",
        bench.duts.characterized_ic,
        timestamp=report_timestamp,
    )
    report.save_dut_information()
    report.save_instrument_information(bench.instruments)

    repository = InstrumentCrud(
        instrument_logger,
        EXAMPLE_CONFIGURATION,
        create_tables=False,
    )
    try:
        for role, driver in bench.instruments.items():
            instrument = driver.instrument
            historical = repository.fetch_at(
                instrument.asset_tag,
                report_timestamp.value,
            )
            if historical is None or historical.model_dump() != instrument.model_dump():
                raise RuntimeError(
                    f"Instrument history does not match report asset "
                    f"{instrument.asset_tag}"
                )
            revisions = repository.history_for_instrument(instrument.id)
            instrument_logger.info(
                "Verified {} ({}) against {} stored revision(s)",
                role,
                instrument.asset_tag,
                len(revisions),
            )
    finally:
        repository.engine.dispose()

    instrument_logger.info("CSV report: {}", report.path)
    return report.path


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
    voltage_specifications = project.voltage_specifications_for(dut.dut)
    temperature_specifications = project.temperature_specifications_for(dut.dut)

    dut_logger.info(
        "Characterizing IC DUT: project {} [{}], die revision {}, metal revision {}, "
        "package revision {}, corner {} ({})",
        project.project.datasheet_name,
        project.project.internal_name,
        dut.dut.die_revision,
        dut.dut.metal_revision,
        dut.dut.package_revision,
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
    for voltage_specification in voltage_specifications:
        limits = voltage_specification.voltage_limits
        dut_logger.info(
            "Voltage {}: minimum={} V, typical={} V, maximum={} V",
            voltage_specification.name,
            limits.minimum,
            limits.typical,
            limits.maximum,
        )
    for temperature_specification in temperature_specifications:
        limits = temperature_specification.temperature_limits
        dut_logger.info(
            "Temperature {}: minimum={} °C, typical={} °C, maximum={} °C",
            temperature_specification.name,
            limits.minimum,
            limits.typical,
            limits.maximum,
        )
    board_logger.info(
        "Fixture: {} {} ({})",
        board.board.maker,
        board.board.model,
        board.board.asset_tag,
    )
    instrument_logger.info("DMM: {}", multimeter.instrument.asset_tag)
    instrument_logger.info("Counter: {}", counter.instrument.asset_tag)
    create_and_verify_report(bench)
    project_logger.info("Project ID: {}", project.get_id())
    project_logger.info("Ready to apply the characterization sequence.")


def main() -> None:
    """Run the example with a representative IC identity."""
    configure_example_logging()
    characterize(load_example_bench())


if __name__ == "__main__":
    main()
