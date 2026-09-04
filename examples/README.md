# Bench examples

The example directory includes `bench.toml` and `instruments.db`, containing:

- `DMM-001`: primary multimeter
- `CNT-001`: frequency counter
- `BRD-001`: IC characterization board or fixture
- `DUT-001`: project-owned IC with corner, revision, lot, wafer, and die data
- `demo-project`: characterization project supporting `DUT-001` and `BRD-001`

The examples register minimal concrete DUT and project classes, then load the
instruments, board, DUT, and project directly from the configured bench.

Run the examples from the project directory:

```powershell
uv run python examples/show_bench.py
uv run python examples/characterize_ic.py
```

To recreate or update the stored database from the sample definitions:

```powershell
uv run python examples/seed_database.py
```
