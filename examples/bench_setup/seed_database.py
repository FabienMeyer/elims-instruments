"""Populate the SQLite database used by all examples."""

from __future__ import annotations

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    InstrumentCrud,
    InstrumentModel,
    InstrumentType,
    ProjectCrud,
    ProjectModel,
    USBConnection,
    VisaConnection,
)
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.constants import (
    BENCH_CONFIGURATION,
    BOARD_DRIVER_NAME,
    PROJECT_DRIVER_NAME,
)
from examples.characterization.specifications import create_revision_specifications

logger = get_logger(__name__)


def main() -> None:
    """Insert or update every resource referenced by the example bench."""
    LOGGER_HELPER.configure()

    with InstrumentCrud(logger, BENCH_CONFIGURATION) as instruments:
        instruments.upsert_many(
            [
                InstrumentModel(
                    id="demo-dmm",
                    asset_tag="DMM-001",
                    type=InstrumentType.MULTIMETER,
                    maker="Keysight",
                    model="34401A",
                    connection=VisaConnection(resource_name="GPIB0::1::INSTR"),
                ),
                InstrumentModel(
                    id="demo-counter",
                    asset_tag="CNT-001",
                    type=InstrumentType.COUNTER,
                    maker="Keysight",
                    model="53220A",
                    connection=VisaConnection(resource_name="GPIB0::2::INSTR"),
                ),
            ]
        )
    board = BoardModel(
        id="demo-characterization-board",
        asset_tag="BRD-001",
        type=BOARD_DRIVER_NAME,
        maker="ELIMS",
        model="Demo Characterization Board",
        connection=USBConnection(vendor_id=0x1209, product_id=0x0001),
    )
    with BoardCrud(logger, BENCH_CONFIGURATION) as boards:
        boards.upsert_many([board])

    dut = DutModel(
        id="demo-dut",
        asset_tag="DUT-001",
        project=PROJECT_DRIVER_NAME,
        corner="TT",
        die_revision="A",
        metal_revision=0,
        package_revision="R1",
        lot_number="LOT-001",
        wafer_id="W01",
        die_x=12,
        die_y=8,
    )
    with DutCrud(logger, BENCH_CONFIGURATION) as duts:
        duts.upsert_many([dut])

    project = ProjectModel(
        id="project-1",
        internal_name=PROJECT_DRIVER_NAME,
        datasheet_name="Example IC Characterization",
        specifications=[create_revision_specifications()],
    )
    project.supported_boards = [board]
    project.supported_duts = [dut]

    with ProjectCrud(logger, BENCH_CONFIGURATION) as projects:
        projects.upsert_many([project])

    logger.info("Seeded example database: {}", BENCH_CONFIGURATION)


if __name__ == "__main__":
    main()
