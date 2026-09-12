"""Populate the SQLite database used by all examples."""

from __future__ import annotations

from elims_instruments.characterization import (
    TemperatureSpecification,
    VoltageSpecification,
)
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
    ProjectRevisionSpecifications,
    USBConnection,
    VisaConnection,
)
from elims_instruments.utils import Limits
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.constants import BENCH_CONFIGURATION

logger = get_logger(__name__)


def main() -> None:
    """Insert or update every resource referenced by the example bench."""
    LOGGER_HELPER.configure()

    instruments = InstrumentCrud(logger, BENCH_CONFIGURATION)
    try:
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
    finally:
        instruments.engine.dispose()

    board = BoardModel(
        id="demo-characterization-board",
        asset_tag="BRD-001",
        type="characterization",
        maker="ELIMS",
        model="Demo Characterization Board",
        connection=USBConnection(vendor_id=0x1209, product_id=0x0001),
    )
    boards = BoardCrud(logger, BENCH_CONFIGURATION)
    try:
        boards.upsert_many([board])
    finally:
        boards.engine.dispose()

    dut = DutModel(
        id="demo-dut",
        asset_tag="DUT-001",
        project="example-project",
        corner="TT",
        die_revision="A",
        metal_revision=0,
        package_revision="R1",
        lot_number="LOT-001",
        wafer_id="W01",
        die_x=12,
        die_y=8,
    )
    duts = DutCrud(logger, BENCH_CONFIGURATION)
    try:
        duts.upsert_many([dut])
    finally:
        duts.engine.dispose()

    project = ProjectModel(
        id="project-1",
        internal_name="example-project",
        datasheet_name="Example IC Characterization",
        specifications=[
            ProjectRevisionSpecifications(
                die_revision="A",
                metal_revision=0,
                package_revision="R1",
                voltage_specifications=[
                    VoltageSpecification(
                        name="VDD",
                        voltage_limits=Limits(
                            minimum=1.14,
                            typical=1.20,
                            maximum=1.26,
                        ),
                    )
                ],
                temperature_specifications=[
                    TemperatureSpecification(
                        name="DUT",
                        temperature_limits=Limits(
                            minimum=-40,
                            typical=25,
                            maximum=125,
                        ),
                    )
                ],
            )
        ],
    )
    project.supported_boards = [board]
    project.supported_duts = [dut]

    projects = ProjectCrud(logger, BENCH_CONFIGURATION)
    try:
        projects.upsert_many([project])
    finally:
        projects.engine.dispose()

    logger.info("Seeded example database: {}", BENCH_CONFIGURATION)


if __name__ == "__main__":
    main()
