"""Check instruments recorded by a characterization CSV against audit history."""

from __future__ import annotations

import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from show_bench import EXAMPLE_CONFIGURATION

from elims_instruments.database import InstrumentCrud

if TYPE_CHECKING:
    from collections.abc import Sequence


def _read_report(report_path: Path) -> tuple[datetime, list[str]]:
    """Read the report timestamp and ordered instrument asset tags."""
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))
    if len(rows) != 1:
        raise ValueError("The characterization report must contain exactly one row")

    row = rows[0]
    raw_timestamp = row.get("report_timestamp_iso")
    if not raw_timestamp:
        raise ValueError("The characterization report has no ISO timestamp")
    asset_tags = [
        value
        for field, value in row.items()
        if field.startswith("instrument_") and field.endswith("_asset_tag") and value
    ]
    if not asset_tags:
        raise ValueError("The characterization report contains no instruments")
    return datetime.fromisoformat(raw_timestamp), asset_tags


def check_instrument_history(
    report_path: Path,
    configuration: Path = EXAMPLE_CONFIGURATION,
) -> None:
    """Display the audit trail applicable to every report instrument."""
    report_timestamp, asset_tags = _read_report(report_path)
    repository = InstrumentCrud(
        logging.getLogger(__name__),
        configuration,
        create_tables=False,
    )
    try:
        print(f"Report timestamp: {report_timestamp.isoformat()}")
        for asset_tag in asset_tags:
            instrument = repository.fetch_at(asset_tag, report_timestamp)
            if instrument is None:
                raise RuntimeError(
                    f"No instrument revision matches {asset_tag} at "
                    f"{report_timestamp.isoformat()}"
                )
            revisions = repository.history_for_instrument(instrument.id)
            print(
                f"{asset_tag}: {instrument.maker} {instrument.model}, "
                f"calibration={instrument.calibration_status.value}, "
                f"{len(revisions)} revision(s)"
            )
            for revision in revisions:
                print(
                    f"  {revision.recorded_at.isoformat()} "
                    f"{revision.action.value}: {revision.snapshot}"
                )
    finally:
        repository.engine.dispose()


def main(arguments: Sequence[str] | None = None) -> None:
    """Parse command-line arguments and check one characterization report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Characterization CSV report")
    parser.add_argument(
        "--config",
        type=Path,
        default=EXAMPLE_CONFIGURATION,
        help="Bench TOML containing the instrument database configuration",
    )
    options = parser.parse_args(arguments)
    check_instrument_history(options.report, options.config)


if __name__ == "__main__":
    main()
