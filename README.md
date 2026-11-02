# ELIMS Instruments

Python tools for laboratory inventory, typed bench configuration, instrument
driver selection, IC characterization sweeps, and incremental CSV reports.

The package keeps persistent identity separate from runtime behavior:

- SQLModel records store instruments, boards, DUTs, projects, connections, and
  revision-dependent operating limits.
- `Bench` resolves project-owned role names into validated runtime objects.
- Characterization composes temperature and voltage conditions with nested
  sweeps and failure-safe cleanup.
- The `elims` CLI manages inventory, YAML synchronization, and migrations.

> [!WARNING]
> This is an alpha package. Built-in Keysight classes currently recognize
> supported models but do not implement hardware communication. See the
> [driver support matrix](docs/guide/driver-support.md).

## Quick start

The supported development workflow uses Python 3.11 or newer and
[uv](https://docs.astral.sh/uv/):

```powershell
uv sync --frozen
uv run pytest
```

Run the database-backed bench and complete simulated characterization:

```powershell
uv run python -m examples.bench_setup.bench
uv run python -m examples.characterization.report
```

The second command writes `examples/reports/characterization.csv` without
requiring laboratory hardware.

For a fresh database, configure `[database]` in `bench.toml` and apply the
schema before loading a bench:

```powershell
uv run elims database upgrade --config bench.toml
```

## Documentation

- [Getting started](docs/guide/getting-started.md)
- [Inventory and database](docs/guide/inventory.md)
- [Bench configuration](docs/guide/bench-configuration.md)
- [Characterization](docs/guide/characterization.md)
- [CLI workflows](docs/guide/cli.md)
- [API reference](docs/api/index.md)

Preview and validate the documentation locally:

```powershell
uv run mkdocs serve
uv run mkdocs build --strict
```

Contributor setup, quality gates, migrations, and documentation conventions are
in the [development guide](docs/development/index.md).
