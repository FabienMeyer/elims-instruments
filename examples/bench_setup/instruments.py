"""Load all example instrument drivers directly from the database."""

from __future__ import annotations

import logging

from elims_instruments.bench.instruments import InstrumentFactory
from elims_instruments.database import InstrumentCrud
from elims_instruments.utils.logger import LOGGER_HELPER, get_logger
from examples.bench_setup.constants import BENCH_CONFIGURATION

logger = get_logger(__name__)


def main() -> None:
    """Load database records, create their drivers, and display them."""
    LOGGER_HELPER.configure()
    repository = InstrumentCrud(logging.getLogger(__name__), BENCH_CONFIGURATION)
    try:
        instruments = repository.fetchall()
    finally:
        repository.engine.dispose()

    for instrument in instruments:
        driver = InstrumentFactory.create(instrument)
        logger.info(
            f"{instrument.id}: {type(driver).__name__} for "
            f"{instrument.maker} {instrument.model} "
            f"(asset tag: {instrument.asset_tag})"
        )


if __name__ == "__main__":
    main()
