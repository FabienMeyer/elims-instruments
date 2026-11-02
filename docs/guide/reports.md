# Reports and analysis

Characterization reports are UTF-8 CSV files written incrementally. The schema
is committed before hardware state changes, and a row is appended only after an
inner measurement completes.

## Column layout

Columns always appear in this order:

1. `test_id` and `timestamp`;
2. role-qualified bench metadata for instruments, boards, and DUTs;
3. outer temperature and voltage values;
4. inner sweep arguments;
5. measurement columns supplied to `Characterization`.

Bench column names include their asset category and configured role, for example
`instrument_primary_dmm_asset_tag`. This prevents collisions when several
resources expose the same metadata field.

All headers must be globally unique. Context values and measurements must have
the same total width as the header.

## File names and timestamps

`FileHelper` creates its destination directory during construction and
lowercases the complete file name. Give it an optional `Timestamp` to append a
local-time suffix:

```python
from pathlib import Path

from elims_instruments.utils.files import FileHelper
from elims_instruments.utils.timestamp import Timestamp


report_file = FileHelper(
    directory=Path("reports"),
    stem="Characterization",
    suffix=FileHelper.FileSuffix.CSV,
    timestamp=Timestamp.now(),
)
```

CSV row timestamps use the same local-time, second-resolution file format. Use
`Timestamp.iso()` when an ISO 8601 value with timezone and microseconds is needed
outside the characterization runner.

## Write a custom report

Most applications should let `Characterization` configure `WriteCsvReport`.
For another incremental workflow, compose callable sections and write the
header before any data:

```python
from elims_instruments.characterization.reports import CsvSection, WriteCsvReport


report = WriteCsvReport(
    report_file,
    sections=[CsvSection(context.report_header, context.report_value)],
    measurement_headers=["result"],
)
report.write_header()
report.write_data("test-1", Timestamp.now().file(), ["1.23"])
```

Once a row has been written, the header cannot change. Treat one report writer
or characterization runner as a single-use run object.

## Read reports with Polars

`ReadCsvReport` accepts one file, one directory, or a sequence of paths. Directory
searches use a filename pattern and return sorted, de-duplicated matches:

```python
from pathlib import Path

from elims_instruments.characterization import ReadCsvReport


reader = ReadCsvReport(Path("reports"), pattern="characterization*.csv")
frame = reader.read()
```

Every combined file must have identical columns in identical order. Header-only
files retain their columns, and no matches produce an empty `polars.DataFrame`.
CSV parse and type failures identify the offending file.

Supply a complete column-to-Polars-type mapping to disable inference. For a
minimal three-column report:

```python
import polars as pl

reader = ReadCsvReport(
    Path("reports"),
    schema={
        "test_id": pl.String,
        "timestamp": pl.String,
        "result": pl.Float64,
    },
)
```

The schema must contain every CSV column exactly; partial schemas are rejected.

For data sets that should not be combined into one frame, iterate bounded
batches:

```python
for batch in reader.iter_chunks(chunk_size=100_000):
    analyze(batch)
```

Chunk iteration preserves file and row order while applying the same column and
schema validation.

See the [report API](../api/characterization/reports/index.md) for exact
signatures.
