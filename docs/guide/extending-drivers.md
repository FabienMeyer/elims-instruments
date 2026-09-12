# Extending drivers

Factories separate persisted identity from project-specific behavior. Concrete
implementations are registered once during application startup, before loading a
bench.

## Add an instrument model

Instrument categories have a category factory and, where useful, a family base
class. A concrete driver inherits its category/family behavior:

```python
from elims_instruments.instruments.power_supply.ks36300 import KeysightE36300


class KeysightE36399A(KeysightE36300):
    """Driver for a hypothetical E36399A model."""
```

Register every accepted database model spelling in the package initializer:

```python
PowerSupplyFactory.register("Keysight E36399A", KeysightE36399A)
PowerSupplyFactory.register("E36399A", KeysightE36399A)
```

Model lookup strips whitespace and ignores case.

## Add a DUT implementation

`Dut` is an abstract base class. A concrete class must implement `get_id()` and
may add project-specific register maps or limits.

The complete minimal example is in `examples/dut.py`, where the `ExampleDut` class is
registered for the `demo-project` project:

```python
from examples.dut import ExampleDut
```

The registry key matches `DutModel.project` and must be registered before
loading the bench:

```python
from pathlib import Path

from elims_instruments.bench import Bench

from examples.dut import ExampleDut  # noqa: F401

bench = Bench(
    Path("examples/bench.toml"),
    authorized_instrument_names=("primary_dmm", "frequency_counter"),
    authorized_board_names=("characterization_board",),
    authorized_dut_names=("characterized_ic",),
    authorized_project_names=("characterization",),
)
dut = bench.duts.characterized_ic

assert dut.dut.asset_tag == "DUT-001"
assert isinstance(dut, ExampleDut)
```

The bench assignment resolves the physical DUT by asset tag:

```toml
[duts]
characterized_ic = "DUT-001"
```

The CLI remains an inventory-only interface. Use it to create and update the
`DutModel` record, but use a registered Python implementation and `Bench` when
you need runtime DUT behavior:

```powershell
uv run elims duts get dut-1 --config examples/bench.toml
```

This separation allows a DUT to exist in the inventory before a concrete
runtime driver has been implemented.

## Add a board implementation

`Board` is the base class for characterization fixtures and interfaces. A
concrete class can add board-specific communication, reset, and measurement
operations. The complete minimal example is in `examples/board.py`, where
`ExampleBoard` is
registered for the `characterization` board type:

```python
from examples.board import ExampleBoard
```

Import the implementation before loading the bench:

```python
from pathlib import Path

from elims_instruments.bench import Bench

from examples.board import ExampleBoard  # noqa: F401

bench = Bench(
    Path("examples/bench.toml"),
    authorized_instrument_names=("primary_dmm", "frequency_counter"),
    authorized_board_names=("characterization_board",),
    authorized_dut_names=("characterized_ic",),
    authorized_project_names=("characterization",),
)
board = bench.boards.characterization_board

assert board.board.asset_tag == "BRD-001"
assert isinstance(board, ExampleBoard)
```

The registry key matches `BoardModel.type` and is normalized by stripping
whitespace and ignoring case. The bench assignment still resolves the physical
board by asset tag:

```toml
[boards]
characterization_board = "BRD-001"
```

Create and update the inventory record independently with the CLI:

```powershell
uv run elims boards get board-1 --config examples/bench.toml
```

## Add a project implementation

`Project` is also abstract. Concrete projects can expose sequences or domain
operations while retaining the validated `ProjectModel` relationship data.

```python
from elims_instruments.projects import Project, ProjectFactory


class CharacterizationProject(Project):
    def get_id(self) -> str:
        return self.project.id


ProjectFactory.register("demo-project", CharacterizationProject)
```

The registry key matches `ProjectModel.internal_name`; `datasheet_name` is the
client-facing name and does not affect driver selection.

## Registration guidance

- Register builders during deterministic application startup.
- Keep database records free of executable Python import paths.
- Reject unknown models/projects rather than selecting a vaguely compatible driver.
- Unit-test aliases, invalid registrations, and the concrete type returned.
- Keep hardware communication out of constructors so bench loading is predictable.
