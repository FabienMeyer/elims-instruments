# Troubleshooting and logging

Most startup failures are deliberate validation errors. Resolve them before
allowing a characterization sequence to change hardware state.

## Common failures

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Missing-table or SQL schema error | The configured database has not been migrated | Run `elims database upgrade --config PATH` |
| `Unknown DUT project` or `Unknown project` | Concrete builders were not imported and registered | Import registrations before constructing `Bench` |
| Unsupported instrument type/model | No category or model factory is registered | Check [Driver support](driver-support.md) or register a driver |
| Unauthorized or invalid bench name | A TOML role is absent from the authorized names, is not a public identifier, or collides with collection methods | Align the `StrEnum` and TOML keys |
| Assigned asset not found | A TOML value does not match an existing asset tag or project internal name | Inspect inventory with the matching CLI `list` command |
| Unsupported board or DUT | A selected project does not reference the assigned asset | Update the project's supported relationships |
| No project specifications for a DUT | Die, metal, or package revision has no exact profile | Add the missing project revision profile |
| Connection option rejected | An option belongs to a different connection kind, or update omitted `--connection` | Select the connection kind and provide all required fields |
| Report cannot read a condition | A temperature or voltage getter is missing | Supply readable callbacks before running characterization |
| Duplicate report headers | Two context or measurement columns share a name | Qualify custom names and rebuild the runner |
| Report files cannot be combined | CSV column order or declared schema differs | Read compatible report generations separately |

The CLI turns model and configuration validation failures into concise command
errors. Add `--help` after the exact group and command to inspect accepted
options.

## Logging behavior

Library imports are silent by default. Applications opt in to terminal and file
sinks:

```python
from elims_instruments.utils.logger import LOGGER_HELPER

LOGGER_HELPER.configure()
```

The shared library helper writes informational messages to the terminal and
debug messages to timestamped files under `logs/`. The CLI configures its own
warning-level terminal and rotating debug-file sinks automatically.

Module code obtains a bound logger without configuring global output:

```python
from elims_instruments.utils.logger import LoggerHelper, get_logger

logger = get_logger(__name__, LoggerHelper.Color.CYAN)
logger.info("Loaded {} resources", count)
```

Configure sinks once at the application entry point. Repeatedly configuring
different helpers can intentionally add multiple Loguru sinks and duplicate
output.

## Diagnose partial characterization runs

The report header is written before the first hardware action. Completed rows
are flushed one at a time, so a file left by a failure shows the last successful
inner point. No row is added for the failing measurement.

Hardware cleanup is best-effort and preserves simultaneous errors in an
exception group. Inspect every contained exception: the first usually explains
the operation failure, while later exceptions identify rails or temperature
sources that also failed during shutdown.

The current built-in Keysight classes do not communicate with real hardware.
Their connection methods raise `NotImplementedError`; use simulated examples or
provide concrete implementations before treating a failed connection as a
bench-configuration problem.
