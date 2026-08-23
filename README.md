# ELIMS Instruments

Drivers, asset storage, and project bench configuration for ELIMS laboratories.

## Setup

```powershell
uv sync --extra dev
uv run pytest
```

## CLI

The CLI manages instruments, boards, and DUTs in the configured database:

```powershell
uv run elims instruments gets --config bench.toml
uv run elims boards gets --config bench.toml
uv run elims duts gets --config bench.toml
```

Each group supports `add`, `get`, `gets`, `update`, `delete`, `sync`, and
`export`. Run `uv run elims GROUP --help` for its options.

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
```

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


bench = Bench(
    authorized_names=InstrumentName,
    authorized_board_names=BoardName,
    authorized_dut_names=DutName,
)

print(bench.instruments.primary_dmm)
print(bench.boards.characterization_board)
print(bench.duts.characterized_ic)
```

## Examples

The `examples` directory contains a ready-to-use `bench.toml` and SQLite
database:

```powershell
uv run python examples/show_bench.py
uv run python examples/characterize_ic.py
```

See [examples/README.md](examples/README.md) for database seeding.
