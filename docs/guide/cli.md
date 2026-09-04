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

Every resource group provides `add`, `get`, `list`, `update`, `delete`, `sync`,
and `export`. `get`, `update`, and `delete` consistently select one record by
its database ID. Use group or command help for the complete option set:

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
  --corner TT --die-revision A `
  --metal-revision 0 --package-revision R1 --config bench.toml
```

Then create a project relationship. `--dut` and `--board` accept either a
database ID or an asset tag and may be repeated. Inline options create one
operating profile for an exact die, metal, and package revision combination.
The internal name is used by code, DUT records, and `bench.toml`; the datasheet
name is the client-facing product name used in reports and logs.

```powershell
uv run elims projects add project-1 `
  --internal-name demo-project --datasheet-name "ELIMS Demo IC" `
  --dut DUT-001 --board BRD-001 `
  --die-revision A --metal-revision 0 --package-revision R1 `
  --voltage-name VDD --voltage-minimum 1.1 `
  --voltage-typical 1.2 --voltage-maximum 1.3 `
  --temperature-name DUT --temperature-minimum -40 `
  --temperature-typical 25 --temperature-maximum 125 `
  --config bench.toml
```

Each profile contains one or more named voltage rails and temperature conditions.
The project selects a profile only when all three revision values match the DUT.
Use `--specifications project-specifications.yaml` instead of the inline options
when creating several revision profiles or several named rails and conditions.
On `projects update`, either form replaces the complete specification list; use
`export`, edit the YAML, and `sync` when preserving several existing profiles.

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

Project YAML contains its revision-dependent specifications plus nested DUT and
board records. Those related records must already exist in the target database;
synchronization creates the relationships, not duplicate assets.

!!! warning "Protect exported files"

    Export refuses to overwrite an existing file unless `--force` is supplied.
    Review synchronized YAML in version control before applying it to a shared
    laboratory database.

## Upgrade the schema

```powershell
uv run elims database upgrade --config bench.toml
```

Run schema upgrades before using code that introduces new model fields or tables.
