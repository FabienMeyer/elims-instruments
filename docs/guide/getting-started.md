# Getting started

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) for the locked repository workflow

Python 3.11 and 3.12 are exercised in CI. Hardware communication can require a
vendor VISA runtime or another PyVISA backend in addition to the Python package;
the bundled simulation does not require one.

## Install from source

This alpha repository is the documented installation source:

```powershell
git clone https://github.com/FabienMeyer/elims-instruments.git
cd elims-instruments
uv sync --frozen
```

Confirm the command and test suite:

```powershell
uv run elims --help
uv run pytest
```

## Run the bundled simulation

The repository includes a ready-to-use `bench.toml`, seeded SQLite database,
custom board/DUT/project implementations, and callback-backed simulated
temperature and voltage sources.

```powershell
uv run python -m examples.bench_setup.bench
uv run python -m examples.characterization.report
```

The first command resolves two instruments, one board, one DUT, and one project.
The second runs 16 measurement points and writes
`examples/reports/characterization.csv`. See [Examples](examples.md) for the
step-by-step modules.

## Create a fresh database

Create `bench.toml` with the database configuration and required instrument
assignment table:

```toml
[database]
url = "sqlite:///instruments.db"
echo = false

[instruments]
```

Apply every schema migration:

```powershell
uv run elims database upgrade --config bench.toml
```

Relative SQLite paths resolve beside `bench.toml`, so a bench directory remains
self-contained when it is moved. Loading `Bench` does not create missing tables.

## Next steps

- Populate and inspect records with [Inventory and database](inventory.md) and
  the [CLI guide](cli.md).
- Assign those records in [Bench configuration](bench-configuration.md).
- Check the current [driver support](driver-support.md).
- Run a real project workflow with [Characterization](characterization.md).
