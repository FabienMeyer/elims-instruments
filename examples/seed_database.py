"""Populate the SQLite database used by all examples."""

from __future__ import annotations

import logging
from pathlib import Path

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
from elims_instruments.temperatures import TemperatureSpecification
from elims_instruments.utils import Limits
from elims_instruments.voltages import VoltageSpecification

CONFIGURATION = Path(__file__).with_name("bench.toml")


def main() -> None:
    """Insert or update every resource referenced by the example bench."""
    logger = logging.getLogger(__name__)

    instruments = InstrumentCrud(logger, CONFIGURATION)
    try:
        instruments.upsert_many(
            [
                InstrumentModel(
                    id="demo-dmm",
                    asset_tag="DMM-001",
                    type=InstrumentType.MULTIMETER,
                    maker="Keysight",
                    model="34401A",
                    connection=VisaConnection(
                        resource_name="GPIB0::1::INSTR"
                    ),
                ),
                InstrumentModel(
                    id="demo-counter",
                    asset_tag="CNT-001",
                    type=InstrumentType.COUNTER,
                    maker="Keysight",
                    model="53220A",
                    connection=VisaConnection(
                        resource_name="GPIB0::2::INSTR"
                    ),
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
    boards = BoardCrud(logger, CONFIGURATION)
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
    duts = DutCrud(logger, CONFIGURATION)
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

    projects = ProjectCrud(logger, CONFIGURATION)
    try:
        projects.upsert_many([project])
    finally:
        projects.engine.dispose()

    print(f"Seeded example database: {CONFIGURATION}")


if __name__ == "__main__":
    main()
