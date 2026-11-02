# ELIMS Instruments

ELIMS Instruments connects laboratory inventory to typed runtime resources and
repeatable characterization reports.

!!! warning "Alpha hardware support"

    Inventory, bench loading, validation, simulated characterization, reports,
    and CLI workflows are implemented. Built-in Keysight classes recognize
    models but do not yet implement hardware communication. Check
    [Driver support](guide/driver-support.md) before connecting a bench.

## Choose a starting point

| Goal | Start here |
| --- | --- |
| Install the repository and run the simulation | [Getting started](guide/getting-started.md) |
| Create assets, projects, and revision profiles | [Inventory and database](guide/inventory.md) |
| Assign stored resources to typed roles | [Bench configuration](guide/bench-configuration.md) |
| Build conditions, sweeps, and safe cleanup | [Characterization](guide/characterization.md) |
| Read and combine result files | [Reports and analysis](guide/reports.md) |
| Manage records from the terminal | [Command-line interface](guide/cli.md) |
| Add hardware or project-specific behavior | [Extending drivers](guide/extending-drivers.md) |
| Look up exact Python signatures | [API reference](api/index.md) |

## Package map

| Package | Responsibility |
| --- | --- |
| `elims_instruments.database` | Validated persistence, connections, repositories, history, and migrations |
| `elims_instruments.bench` | Factory registration, configuration resolution, and named resources |
| `elims_instruments.characterization` | Limits, conditions, nested sweeps, lifecycle cleanup, and reports |
| `elims_instruments.cli` | Inventory, YAML synchronization, and migration commands |
| `elims_instruments.utils` | Numeric limits, file names, timestamps, and logging support |

The [architecture](architecture/index.md) explains how those boundaries fit
together. Contributor commands and conventions are in
[Development](development/index.md).
