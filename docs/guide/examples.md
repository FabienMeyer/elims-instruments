# Examples

Run the examples from the repository root. The `bench_setup` package contains
the basic database-backed definitions, while `characterization` builds them
into a complete sweep and report:

1. `bench_setup/dut.py`, `board.py`, `instruments.py`, and `project.py`
   introduce the objects used by a test bench. Shared names and paths live in
   `constants.py`.
2. `bench_setup/bench.py` combines those definitions with `bench.toml` and the
   example database.
3. `characterization/specifications.py` is the single source of truth for the
   seeded project's revision-dependent electrical and thermal limits. The
   simulated sources and sweep points are built from that profile.
4. `characterization/temperature.py` and `voltage.py` demonstrate individual
   simulated sources.
5. `characterization/voltages.py` reuses the voltage builders to create an
   ordered collection and defines `SupplySetPoints`.
6. `characterization/outer_sweep.py` reuses the DUT, temperature, and voltage
   examples to build an `OuterMatrix` and execute every operating point.
7. `characterization/inner_sweep.py` adds the test-specific iterations and
   frequency points performed at every outer operating condition.
8. `characterization/report.py` reuses both matrices, writes the complete CSV
   header before testing, and saves one row after each completed inner sweep.

Run the progression with:

```powershell
uv run python -m examples.bench_setup.bench
uv run python -m examples.characterization.specifications
uv run python -m examples.characterization.temperature
uv run python -m examples.characterization.voltage
uv run python -m examples.characterization.voltages
uv run python -m examples.characterization.outer_sweep
uv run python -m examples.characterization.inner_sweep
uv run python -m examples.characterization.report
```

The individual inventory and factory modules are also executable when you want
to inspect one resource layer:

```powershell
uv run python -m examples.bench_setup.instruments
uv run python -m examples.bench_setup.board
uv run python -m examples.bench_setup.dut
uv run python -m examples.bench_setup.project
```

The complete report contains 16 rows: two temperatures × two adjustable voltage
points × two iterations × two bandgap measurements. It is written to
`examples/reports/characterization.csv`.

The builder functions such as `create_characterization_setup()`,
`create_revision_specifications()`, `create_adjustable_temperature()`,
`create_voltages()`, `create_outer_matrix()`, and `create_characterization()`
can also be imported into a project and adapted to real instrument drivers.

The repository includes a ready-to-use `instruments.db`. Run
`uv run python -m examples.bench_setup.seed_database` only when you need to
recreate its example records.

For the contracts demonstrated by these modules, continue with
[Characterization](characterization.md) and
[Reports and analysis](reports.md).
