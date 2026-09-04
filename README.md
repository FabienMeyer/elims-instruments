# ELIMS Instruments

Drivers, asset storage, and project bench configuration for ELIMS laboratories.

## Setup

```powershell
uv sync
uv run pytest
```

## CLI

The CLI manages instruments, boards, DUTs, and projects in the configured database:

```powershell
uv run elims instruments gets --config bench.toml
uv run elims boards gets --config bench.toml
uv run elims duts gets --config bench.toml
uv run elims projects gets --config bench.toml
```

Each group supports `add`, `get`, `gets`, `update`, `delete`, `sync`, and
`export`. Run `uv run elims GROUP --help` for its options.

Upgrade an existing database after pulling schema changes:

```powershell
uv run elims database upgrade --config bench.toml
```

Example additions:

```powershell
uv run elims instruments add dmm-1 --asset-tag DMM-001 `
  --type multimeter --maker Keysight --model 34401A `
  --connection visa --resource-name GPIB0::1::INSTR

uv run elims boards add board-1 --asset-tag BRD-001 `
  --type characterization --maker ELIMS --model Fixture-A `
  --connection usb --vendor-id 4617 --product-id 1

uv run elims duts add dut-1 --asset-tag DUT-001 `
  --project demo-project --corner TT --revision A

uv run elims projects add project-1 --name demo-project `
  --dut DUT-001 --board BRD-001
```

## Bench configuration

Instruments and boards are reusable assets. A DUT belongs to one project.
Names in `bench.toml` are project-defined roles that point to asset tags:

```toml
[database]
url = "sqlite:///instruments.db"
echo = false

[instruments]
primary_dmm = "DMM-001"

[boards]
characterization_board = "BRD-001"

[duts]
characterized_ic = "DUT-001"

[projects]
characterization = "demo-project"
```

Relative SQLite paths are resolved from the directory containing `bench.toml`.

Projects authorize those names with `StrEnum` classes and load the bench:

```python
from enum import StrEnum

from elims_instruments.bench import Bench


class InstrumentName(StrEnum):
    PRIMARY_DMM = "primary_dmm"


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

print(bench.instruments.primary_dmm)
print(bench.boards.characterization_board)
print(bench.duts.characterized_ic)
print(bench.projects.characterization)
```

Concrete DUT and project builders must be registered for their database project
names before loading assigned DUTs or projects.

## Examples

The `examples` directory contains a ready-to-use `bench.toml` and SQLite
database:

```powershell
uv run python examples/show_bench.py
uv run python examples/characterize_ic.py
```

See [examples/README.md](examples/README.md) for database seeding.

## Documentation

Preview the documentation with live reload:

```powershell
uv run mkdocs serve
```

Validate the complete site, including generated API reference pages:

```powershell
uv run mkdocs build --strict
```

The generated `site/` directory is ignored by Git. Documentation sources and
contributor guidance live under [docs](docs/index.md).

## Driver status

Asset storage, bench loading, and CLI management are implemented. The current
Keysight classes identify supported models, but hardware operations still raise
`NotImplementedError` until their communication commands are implemented.
Import driver factories from `elims_instruments.instruments`.

Library logging is silent until configured. CLI commands enable warning-level
terminal logging and rotating debug files automatically.
