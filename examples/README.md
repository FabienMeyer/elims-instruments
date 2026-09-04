# Bench examples

Project creation is also available as two isolated CLI examples:

- [`with_yaml`](with_yaml/README.md) imports multiple revision profiles from a
  YAML file.
- [`without_yaml`](without_yaml/README.md) creates one profile entirely from
  CLI options.

The example directory includes `bench.toml` and `instruments.db`, containing:

- `DMM-001`: primary multimeter
- `CNT-001`: frequency counter
- `BRD-001`: IC characterization board or fixture
- `DUT-001`: revision A/0/R1 of the project-owned IC
- `DUT-002`: revision B/1/R2 of the same IC family
- `demo-characterization-project`: database ID of the characterization project
- `demo-project`: internal project name used by DUTs, driver registration, and
  `bench.toml`
- `ELIMS Demo IC`: client-facing datasheet name

The project supports both DUT revisions and `BRD-001`, with different voltage
and temperature specifications for each revision.

The examples register minimal concrete DUT and project classes, then load the
instruments, board, DUT, and project directly from the configured bench.

Run the examples from the project directory:

```powershell
uv run python examples/show_bench.py
uv run python examples/characterize_ic.py
uv run python examples/sweep_test.py
```

`sweep_test.py` is hardware-independent. It demonstrates a complete nested
test: the outer matrix resets the DUT and applies temperature and DUT-ordered
voltage rails; the inner matrix writes test-specific registers and repeats each
frequency/divider combination.

`characterize_ic.py` creates a timestamped CSV report containing the DUT and
instrument asset tags. It then uses the report timestamp to reconstruct every
instrument from the append-only database history and verifies that the stored
snapshot matches the configuration used by the test.

Inspect the complete instrument history associated with a generated report:

```powershell
uv run python examples/check_instrument_history.py `
  examples/reports/characterization_<timestamp>.csv
```

Inspect the same records through the CLI. Collection commands use `list`, while
single-record commands use stable database IDs:

```powershell
uv run elims instruments list --config examples/bench.toml
uv run elims boards list --config examples/bench.toml
uv run elims duts get demo-dut --config examples/bench.toml
uv run elims projects get demo-characterization-project `
  --config examples/bench.toml
```

To recreate or update the stored database from the sample definitions:

```powershell
uv run python examples/seed_database.py
```

The revision profiles loaded by the seed script are defined in
`project-specifications.yaml`. The characterization example selects the profile
matching `DUT-001` and prints its actual voltage and temperature limits.
The API uses Celsius floats; their database representation uses integer
deci-degrees (`100.1 °C` is stored as `1001`).
