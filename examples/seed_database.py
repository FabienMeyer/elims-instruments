"""Populate the SQLite database stored with the bench examples."""

import logging

from show_bench import EXAMPLE_CONFIGURATION

from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    InstrumentCrud,
    InstrumentModel,
    InstrumentType,
    USBConnection,
    VisaConnection,
)


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

    boards = BoardCrud(repository_logger, EXAMPLE_CONFIGURATION)
    try:
        boards.upsert_many(
            [
                BoardModel(
                    id="demo-characterization-board",
                    asset_tag="BRD-001",
                    type="characterization",
                    maker="ELIMS",
                    model="Demo Characterization Board",
                    connection=USBConnection(vendor_id=0x1209, product_id=0x0001),
                )
            ]
        )
    finally:
        boards.engine.dispose()

    duts = DutCrud(repository_logger, EXAMPLE_CONFIGURATION)
    try:
        duts.upsert_many(
            [
                DutModel(
                    id="demo-dut",
                    asset_tag="DUT-001",
                    project="demo-project",
                    corner="TT",
                    revision="A",
                    lot_number="LOT-001",
                    wafer_id="W01",
                    die_x=12,
                    die_y=8,
                )
            ]
        )
    finally:
        duts.engine.dispose()


if __name__ == "__main__":
    seed_database()
