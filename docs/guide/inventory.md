# Inventory and database

The database is the persistent source of truth for laboratory assets and project
relationships. Runtime drivers are created later, when a `Bench` resolves the
records assigned in `bench.toml`.

## Configure and initialize the database

Every database operation reads the same TOML table:

```toml
[database]
url = "sqlite:///instruments.db"
echo = false
```

`url` is any SQLAlchemy URL supported by the installed driver. A relative SQLite
path is resolved from the directory containing the TOML file. `echo` is optional
and must be a Boolean.

Apply the versioned schema before loading a bench or opening a repository with
table creation disabled:

```powershell
uv run elims database upgrade --config bench.toml
```

Bench loading never creates missing tables. This makes a missing migration fail
early instead of silently creating only part of a newer schema.

## Stored records

| Record | Identity and purpose |
| --- | --- |
| `InstrumentModel` | An instrument asset, category, maker/model, calibration state, and connection |
| `BoardModel` | A reusable fixture or interface and its connection |
| `DutModel` | One device, its owning project, manufacturing corner, revision, and traceability |
| `ProjectModel` | Internal and datasheet names, supported DUTs/boards, and revision profiles |

Database IDs are stable synchronization keys. Asset tags identify physical
instruments, boards, and DUTs and must be unique within each asset table.
Projects instead have a unique `internal_name`, which is also used by DUT
records, driver registration, and bench assignments.

Project specifications are selected by an exact tuple of die, metal, and package
revision. Every supported DUT must belong to the project's `internal_name` and
must have a matching profile. Temperature values are exposed as Celsius floats;
the JSON column stores integer deci-degrees, so values must be representable to
0.1 °C.

## Connection models

The persisted models support four validated connection shapes:

| Kind | Required fields | Important optional fields |
| --- | --- | --- |
| `socket` | IPv4 `ip_address`, `port` | `mac_address`, `timeout_seconds` |
| `visa` | `resource_name` | timeout and read/write terminators |
| `com` | serial `port` | baud rate, byte size, stop bits, parity, timeout |
| `usb` | `vendor_id`, `product_id` | serial number, interface, timeout |

The CLI intentionally exposes socket and VISA connections for instruments, and
socket, COM, and USB connections for boards. Connection-specific options are
rejected unless their matching connection kind is selected. See the
[CLI guide](cli.md) for task-level commands and `elims GROUP COMMAND --help` for
the exhaustive option reference.

## Use repositories from Python

Repositories are context managers and should be closed after use:

```python
import logging
from pathlib import Path

from elims_instruments.database import InstrumentCrud


with InstrumentCrud(
    logging.getLogger(__name__),
    Path("bench.toml"),
    create_tables=False,
) as instruments:
    dmm = instruments.fetch("asset_tag", "DMM-001")
    all_instruments = instruments.fetchall()
```

The common repository operations are:

| Operation | Contract |
| --- | --- |
| `fetchall()` | Return all records for the repository model |
| `fetch(field, value)` | Return the first match or `None`; unknown fields are rejected |
| `add(record)` | Validate and insert one record |
| `remove(field, value)` | Delete one match and return whether it existed |
| `upsert_many(records)` | Create or fully replace records by stable database ID |
| `update_by_asset_tag(tag, changes)` | Validate and update one instrument, board, or DUT |

Repository constructors create missing SQLModel tables by default. Applications
that rely on the migration history should upgrade first and pass
`create_tables=False`, as the bench factories do.

`ProjectCrud` owns relationship-specific validation. Related DUTs and boards
must already exist; synchronization updates the relationships rather than
duplicating those assets.

Foreign keys prevent deleting a DUT or board while a project references it.
Remove the relationship from the project first, then delete the asset.

## Instrument history

Instrument inserts, updates, and deletions create immutable snapshots in the
same transaction. Use `history(asset_tag)` for the history under one tag,
`history_for_instrument(id)` to follow tag changes, and `fetch_at(tag, timestamp)`
to reconstruct the state visible at a point in time.

```python
from datetime import datetime

at = datetime.fromisoformat("2026-10-31T12:00:00+00:00")

with InstrumentCrud(
    logging.getLogger(__name__),
    Path("bench.toml"),
    create_tables=False,
) as instruments:
    revisions = instruments.history("DMM-001")
    old_state = instruments.fetch_at("DMM-001", at)
```

Naive timestamps passed to `fetch_at()` are interpreted as UTC. The query follows
tag reassignment and returns the owner active at that time. It returns `None`
before the tag existed and during periods when it was deleted or unassigned.

## Bulk YAML workflow

Use CLI `export` and `sync` for reviewable bulk changes. Synchronization is
ID-based and replaces all modeled fields. Project YAML embeds supported DUT and
board records for readability, but those assets must already exist in the target
database.

The exact models, validators, repository signatures, and exceptions are in the
[database API reference](../api/database/index.md).
