# Characterization

Defines test conditions, nested sweeps, and incremental reports.

## Run API

`Characterization` coordinates one test run. Its constructor accepts:

- `file_helper: FileHelper`: the destination for the incremental report.
- `bench: Bench`: the object providing the bench report columns.
- `outer_matrix: OuterMatrix`: the operating-condition points.
- `inner_matrix: InnerMatrix[DutT]`: the test-specific points.
- `measurement_headers: Sequence[str]`: column names for those values.

`run() -> Path` writes the complete header, executes the nested sweeps,
appends one row per completed inner point, and returns the report path. Each
row contains bench values, outer-point values, inner-point values, then the
values returned by `InnerSweep.run()`. The runner verifies that those values
match `measurement_headers` in count.

An empty outer or inner matrix is an error because the runner cannot derive a
complete report schema from it. The runner prepares the schema before changing
hardware state and shuts down supplies and temperature control if setup or a
measurement fails. `OuterMatrix` contains operating conditions; the DUT is
provided by the bench and inner matrix.

`Bench` remains a setup dependency for callers that need to resolve hardware;
the runner receives the configured objects directly. Logging configuration
also remains with the application entry point.

::: elims_instruments.characterization
