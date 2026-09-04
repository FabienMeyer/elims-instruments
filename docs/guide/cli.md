# Command-line interface

The `elims` command manages the same validated models used by the Python API.

```powershell
uv run elims --help
```

## Command groups

| Group | Purpose |
| --- | --- |
| `instruments` | Instrument identity, type, model, and connection settings |
| `boards` | Board identity and connection settings |
| `duts` | DUT identity and manufacturing traceability |
| `projects` | Projects and supported DUT/board relationships |
| `database` | Alembic schema upgrades |

Every asset group provides `add`, `get`, `gets`, `update`, `delete`, `sync`, and
`export`. Use group or command help for the complete option set:

```powershell
uv run elims instruments add --help
uv run elims projects update --help
```

## Add related records

Create the physical resources first:

```powershell
uv run elims boards add board-1 `
  --asset-tag BRD-001 --type characterization `
  --maker ELIMS --model Fixture-A `
  --connection usb --vendor-id 4617 --product-id 1 `
  --config bench.toml

uv run elims duts add dut-1 `
  --asset-tag DUT-001 --project demo-project `
  --corner TT --revision A --config bench.toml
```

Then create a project relationship. `--dut` and `--board` accept either a
database ID or an asset tag and may be repeated.

```powershell
uv run elims projects add project-1 `
  --name demo-project --dut DUT-001 --board BRD-001 `
  --config bench.toml
```

## Synchronize YAML

Export current records before bulk editing:

```powershell
uv run elims instruments export instruments.yaml --config bench.toml
uv run elims projects export projects.yaml --config bench.toml
```

Apply a YAML list by stable record ID:

```powershell
uv run elims instruments sync instruments.yaml --config bench.toml
uv run elims projects sync projects.yaml --config bench.toml
```

Project YAML contains nested DUT and board records. Those related records must
already exist in the target database; synchronization creates the relationships,
not duplicate assets.

!!! warning "Protect exported files"

    Export refuses to overwrite an existing file unless `--force` is supplied.
    Review synchronized YAML in version control before applying it to a shared
    laboratory database.

## Upgrade the schema

```powershell
uv run elims database upgrade --config bench.toml
```

Run schema upgrades before using code that introduces new model fields or tables.
