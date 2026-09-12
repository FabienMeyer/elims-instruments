# Examples

Run the examples from the repository root. The `bench_setup` package contains
the basic database-backed definitions, while `characterization` builds them
into a complete sweep and report:

1. `bench_setup/dut.py`, `board.py`, `instruments.py`, and `project.py`
   introduce the objects used by a test bench. Shared names and paths live in
   `constants.py`.
2. `bench_setup/bench.py` combines those definitions with `bench.toml` and the
   example database.
3. `characterization/temperature.py` and `voltage.py` demonstrate individual
   simulated sources.
4. `characterization/voltages.py` reuses the voltage builders to create an
   ordered collection and defines `SupplySetPoints`.
5. `characterization/outer_sweep.py` reuses the DUT, temperature, and voltage
   examples to build an `OuterMatrix` and execute every operating point.
6. `characterization/inner_sweep.py` adds the test-specific iterations and
   frequency points performed at every outer operating condition.
7. `characterization/report.py` reuses both matrices, writes the complete CSV
   header before testing, and saves one row after each completed inner sweep.

Run the progression with:

```powershell
uv run python -m examples.bench_setup.bench
uv run python -m examples.characterization.temperature
uv run python -m examples.characterization.voltage
uv run python -m examples.characterization.voltages
uv run python -m examples.characterization.outer_sweep
uv run python -m examples.characterization.inner_sweep
uv run python -m examples.characterization.report
```

The builder functions such as `create_bench()`, `create_dut_temperature()`,
`create_voltages()`, `create_outer_matrix()`, and `create_inner_matrix()` can
also be imported into a project and adapted to real instrument drivers.

The repository includes a ready-to-use `instruments.db`. Run
`uv run python -m examples.bench_setup.seed_database` only when you need to
recreate its example records.
