"""Load example DUTs from the database and create their runtime drivers."""

from __future__ import annotations

import logging

from elims_instruments.bench import Dut, DutFactory
from elims_instruments.database import DutCrud, DutModel
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.constants import (
    BENCH_CONFIGURATION,
    PROJECT_DRIVER_NAME,
)

logger = get_logger(__name__)


class ExampleDut(Dut):
    """Runtime behavior backed by a DUT record from the database."""

    def get_id(self) -> str:
        """Return the persistent database identifier."""
        return self.dut.id

    def reset(self) -> None:
        """Reset the DUT to its known initial state.

        Replace this placeholder with the project-specific reset sequence when
        the example is connected to hardware.
        """
        super().reset()


# DutModel records identify their runtime driver by ``project``.
DutFactory.register(PROJECT_DRIVER_NAME, ExampleDut)

def get_duts() -> list[DutModel]:
    repository = DutCrud(logging.getLogger(__name__), BENCH_CONFIGURATION)
    try:
        duts = repository.fetchall()
    finally:
        repository.engine.dispose()
    return duts

def main() -> None:
    """Load DUT records, create their drivers, and display them."""
    LOGGER_HELPER.configure()

    for dut in get_duts():
        driver = DutFactory.create(dut)
        logger.info(driver.report_value())

if __name__ == "__main__":
    main()
