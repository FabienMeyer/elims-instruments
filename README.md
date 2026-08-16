# ELIMS Instruments

Communication drivers and bench configuration for ELIMS laboratory instruments.

## Development

Create the virtual environment and install the project with its development
dependencies:

```powershell
uv sync --extra dev
```

## Instrument database

`database.toml` configures a local SQLite database. Pass that file to
`InstrumentCrud`, then use the same validated SQLModel for both application data
and persistence:

```python
import logging
from pathlib import Path

from elims_instruments.database import (
    InstrumentCrud,
    InstrumentModel,
    SocketConnection,
)

instruments = InstrumentCrud(logging.getLogger(__name__), Path("database.toml"))
instruments.add(
    InstrumentModel(
        id="scope-1",
        type="oscilloscope",
        maker="Keysight",
        model="DSOX1204G",
        connection=SocketConnection(ip_address="192.168.1.10", port=5025),
    )
)
```

### Command-line interface

The root CLI is organized into command groups so more modules can be registered
later. Use `uv run elims instruments ...`, or the shorter backward-compatible
`uv run instruments ...` command shown below.

```powershell
# Add a socket instrument
uv run instruments add scope-1 --type oscilloscope --maker Keysight `
  --model DSOX1204G --connection socket `
  --ip-address 192.168.1.10 --port 5025

# Read one or all instruments
uv run instruments get scope-1
uv run instruments gets

# Update selected fields by ID
uv run instruments update scope-1 --model DSOX1204A

# Delete by ID
uv run instruments delete scope-1

# Export the database to YAML
uv run instruments export instruments.yaml

# Add missing IDs and fully update existing IDs from YAML
uv run instruments sync instruments.yaml
```

Pass `--config path/to/database.toml` to any command to select another database.
Run `uv run instruments COMMAND --help` for all available options, including VISA
connections.
