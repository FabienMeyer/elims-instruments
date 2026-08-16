# Getting Started

Minimal steps to set up a development environment, run tests, and try the CLI.

Prerequisites

- Python 3.11+
- Git

Quick setup (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install --upgrade pip
# Install the project dev tool `uv` (used in project tasks)
pip install uv
# Install project dependencies defined by the toolchain
uv install
```

Run the test suite

```powershell
uv run pytest -q
```

Build the documentation

```powershell
uv run mkdocs build --strict
```

Try the CLI

```powershell
# show available command groups
uv run elims --help

# instruments group
uv run elims instruments --help

# boards group
uv run elims boards --help
```

Notes

- The CLI uses a TOML database configuration file (default `database.toml`).
- Example configuration is created automatically by tests; see `tests/` for sample usage.
