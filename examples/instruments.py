"""Load all example instrument drivers directly from the database."""

from __future__ import annotations

import logging
from pathlib import Path

from elims_instruments.database import InstrumentCrud
from elims_instruments.instruments import InstrumentFactory

from elims_instruments.utils.logger import LOGGER_HELPER, get_logger

logger = get_logger(__name__)

def main() -> None:
    """Load database records, create their drivers, and display them."""
    LOGGER_HELPER.configure()
    CONFIGURATION = Path(__file__).with_name("bench.toml")

    repository = InstrumentCrud(logging.getLogger(__name__), CONFIGURATION)
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
