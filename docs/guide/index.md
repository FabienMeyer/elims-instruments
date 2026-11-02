# User guide

Follow the guides in the order that matches your task:

1. [Getting started](getting-started.md) installs the locked environment and
   runs the bundled simulation.
2. [Inventory and database](inventory.md) covers persistent assets, project
   relationships, migrations, repositories, and YAML interchange.
3. [Bench configuration](bench-configuration.md) maps project-owned role names
   to stored resources.
4. [Driver support](driver-support.md) distinguishes recognized models from
   implemented hardware operations.
5. [Characterization](characterization.md) builds specifications, callback
   adapters, outer conditions, inner tests, and safe execution.
6. [Reports and analysis](reports.md) documents the CSV contract and Polars
   reader.
7. [Command-line interface](cli.md) provides inventory workflows; command help
   remains the exhaustive option reference.
8. [Extending drivers](extending-drivers.md) registers custom instruments,
   boards, DUTs, and projects.
9. [Examples](examples.md) lists the executable progression from records to a
   complete report.
10. [Troubleshooting and logging](troubleshooting.md) maps common failures to
    corrective actions.

Exact classes, methods, parameters, and exceptions are generated from source
docstrings in the [API reference](../api/index.md). The guides focus on workflows
and contracts so those details are not maintained twice.
