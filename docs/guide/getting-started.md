# Getting started

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) for the documented development workflow

## Install the project

Clone the repository and install the locked development environment:

```powershell
git clone https://github.com/FabienMeyer/elims-instruments.git
cd elims-instruments
uv sync --frozen
```

Confirm the installation:

```powershell
uv run elims --help
uv run pytest
```

## Run the bundled example

The example directory contains a bench configuration, a seeded SQLite database,
and minimal concrete DUT and project implementations.

```powershell
uv run python examples/seed_database.py
uv run python examples/show_bench.py
uv run python examples/characterize_ic.py
```

`show_bench.py` resolves and displays two instruments, one board, one DUT, and
one project with its supported resource relationships.

## Create a fresh database

Create `bench.toml` with a database table:

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

The SQLite path is resolved relative to the configuration file, so a bench can
be moved as a self-contained directory.

## Next steps

- Define role assignments in [Bench configuration](bench-configuration.md).
- Populate records with the [command-line interface](cli.md).
- Add concrete implementations using [Extending drivers](extending-drivers.md).
