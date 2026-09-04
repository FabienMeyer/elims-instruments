"""Populate the SQLite database stored with the bench examples."""

import logging
from datetime import date

import yaml
from show_bench import EXAMPLE_CONFIGURATION

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    CalibrationStatus,
    DutCrud,
    DutModel,
    InstrumentCrud,
    InstrumentModel,
    InstrumentType,
    ProjectCrud,
    ProjectModel,
    USBConnection,
    VisaConnection,
    parse_project_specifications,
)

PROJECT_SPECIFICATIONS = EXAMPLE_CONFIGURATION.with_name("project-specifications.yaml")


def seed_database() -> None:
    """Insert or update every asset referenced by the example bench."""
    repository_logger = logging.getLogger(__name__)
    instruments = InstrumentCrud(repository_logger, EXAMPLE_CONFIGURATION)
    try:
        instruments.upsert_many(
            [
                InstrumentModel(
                    id="demo-dmm",
                    asset_tag="DMM-001",
                    type=InstrumentType.MULTIMETER,
                    maker="Keysight",
                    model="34401A",
                    calibration_date=date(2026, 1, 15),
                    calibration_due_date=date(2027, 1, 15),
                    calibration_certificate_number="CAL-DMM-2026-001",
                    calibration_status=CalibrationStatus.VALID,
                    connection=VisaConnection(resource_name="GPIB0::1::INSTR"),
                ),
                InstrumentModel(
                    id="demo-counter",
                    asset_tag="CNT-001",
                    type=InstrumentType.COUNTER,
                    maker="Keysight",
                    model="53220A",
                    calibration_status=CalibrationStatus.NOT_REQUIRED,
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
    boards = BoardCrud(repository_logger, EXAMPLE_CONFIGURATION)
    try:
        boards.upsert_many([board])
    finally:
        boards.engine.dispose()

    dut = DutModel(
        id="demo-dut",
        asset_tag="DUT-001",
        project="demo-project",
        corner="TT",
        die_revision="A",
        metal_revision=0,
        package_revision="R1",
        lot_number="LOT-001",
        wafer_id="W01",
        die_x=12,
        die_y=8,
    )
    revised_dut = DutModel(
        id="demo-dut-revision-b",
        asset_tag="DUT-002",
        project="demo-project",
        corner="TT",
        die_revision="B",
        metal_revision=1,
        package_revision="R2",
        lot_number="LOT-002",
        wafer_id="W03",
        die_x=4,
        die_y=15,
    )
    duts = DutCrud(repository_logger, EXAMPLE_CONFIGURATION)
    try:
        duts.upsert_many([dut, revised_dut])
    finally:
        duts.engine.dispose()

    project = ProjectModel(
        id="demo-characterization-project",
        internal_name="demo-project",
        datasheet_name="ELIMS Demo IC",
        specifications=parse_project_specifications(
            yaml.safe_load(PROJECT_SPECIFICATIONS.read_text(encoding="utf-8"))
        ),
    )
    project.supported_duts = [dut, revised_dut]
    project.supported_boards = [board]
    projects = ProjectCrud(repository_logger, EXAMPLE_CONFIGURATION)
    try:
        projects.upsert_many([project])
    finally:
        projects.engine.dispose()


if __name__ == "__main__":
    seed_database()
