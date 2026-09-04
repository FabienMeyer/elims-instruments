# Bench configuration

`Bench` combines a TOML assignment file with records stored in the configured
database. Assignment keys are stable names used by characterization code;
values identify records in the database.

## Complete configuration

```toml
[database]
url = "sqlite:///instruments.db"
echo = false

[instruments]
primary_dmm = "DMM-001"
frequency_counter = "CNT-001"

[boards]
characterization_board = "BRD-001"

[duts]
characterized_ic = "DUT-001"

[projects]
characterization = "demo-project"
```

The `[instruments]` table is required. Board, DUT, and project tables are
optional. Instruments, boards, and DUTs resolve by asset tag; projects resolve
by their unique database name.

## Authorize names

The application owns the allowed role names. `StrEnum` keeps those names typed
and prevents configuration from exposing unexpected attributes.

```python
from enum import StrEnum

from elims_instruments.bench import Bench


class InstrumentName(StrEnum):
    PRIMARY_DMM = "primary_dmm"
    FREQUENCY_COUNTER = "frequency_counter"


class BoardName(StrEnum):
    CHARACTERIZATION_BOARD = "characterization_board"


class DutName(StrEnum):
    CHARACTERIZED_IC = "characterized_ic"


class ProjectName(StrEnum):
    CHARACTERIZATION = "characterization"


bench = Bench(
    authorized_instrument_names=InstrumentName,
    authorized_board_names=BoardName,
    authorized_dut_names=DutName,
    authorized_project_names=ProjectName,
)
```

Collections support both mapping and attribute access:

```python
dmm = bench.instruments.primary_dmm
same_dmm = bench.instruments["primary_dmm"]
project = bench.projects.characterization

assert dmm is same_dmm
```

## Validation rules

Bench loading fails before characterization begins when:

- a role is not present in its authorized-name collection;
- a role is not a public, non-keyword Python identifier;
- a reference is empty, duplicated within a section, or absent from the database;
- an instrument category or model has no registered factory;
- a DUT or project name has no registered concrete builder.

The returned collections are read-only views, which prevents a characterization
sequence from silently replacing configured resources.

## Database URLs

Relative SQLite paths are resolved beside `bench.toml`:

```toml
[database]
url = "sqlite:///data/assets.db"
```

For a configuration at `C:/benches/lab-a/bench.toml`, this resolves to
`C:/benches/lab-a/data/assets.db`.
